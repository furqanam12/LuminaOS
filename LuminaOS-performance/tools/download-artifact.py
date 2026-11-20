#!/usr/bin/env python3
"""Download an authenticated GitHub Actions artifact in resumable ranges.

Some networks/proxies stall on large full-stream downloads. This uses
small HTTP ranges, verifies every chunk and optionally extracts the ZIP safely.
Only use the token supplied by the caller's installed GitHub CLI; do not print it.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import time


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Do not send the source-host AccessToken to signed-download hosts."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None:
            original = urllib.parse.urlparse(req.full_url).hostname
            destination = urllib.parse.urlparse(newurl).hostname
            if original != destination:
                for key in ("Authorization", "authorization"):
                    redirected.headers.pop(key, None)
                    redirected.unredirected_hdrs.pop(key, None)
        return redirected


OPENER = urllib.request.build_opener(SafeRedirectHandler)


def get_bytes(url: str, token: str, start: int, end: int, expected: int, timeout: int = 90) -> bytes:
    if token:
        request = urllib.request.Request(url, headers={
            "Authorization": "Bearer " + token,
            "Range": "bytes=%d-%d" % (start, end),
        })
    else:
        request = urllib.request.Request(url, headers={"Range": "bytes=%d-%d" % (start, end)})
    with OPENER.open(request, timeout=timeout) as response:
        if response.status != 206:
            raise RuntimeError("Server rejected range %d-%d with HTTP %s" % (start, end, response.status))
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) != expected:
            raise RuntimeError("Chunk length mismatch: expected %d, server advertised %s" % (expected, content_length))
        data = response.read(expected + 1)
    if len(data) != expected:
        raise RuntimeError("Incomplete range: expected %d bytes, got %d" % (expected, len(data)))
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="GitHub artifact /zip API URL")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--extract", type=Path)
    parser.add_argument("--chunk-mib", type=int, default=4)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--retries", type=int, default=5)
    args = parser.parse_args()
    if not 1 <= args.chunk_mib <= 64 or not 1 <= args.workers <= 8:
        parser.error("Chunk 1-64 MiB and 1-8 workers are supported")
    endpoint = urllib.parse.urlparse(args.url)
    if endpoint.scheme != "https" or endpoint.hostname != "api.github.com" or not endpoint.path.endswith("/zip"):
        parser.error("Only an HTTPS GitHub Actions artifact /zip API URL is allowed")
    token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    if not token:
        parser.error("No token returned by `gh auth token`; run gh auth login")
    headers = {"Authorization": "Bearer " + token}
    with OPENER.open(urllib.request.Request(args.url, method="HEAD", headers=headers), timeout=45) as response:
        total = int(response.headers.get("Content-Length", "0"))
    if total <= 0:
        parser.error("Could not determine the artifact size")

    out = args.out.resolve()
    chunks_dir = out.parent / ("." + out.name + ".chunks")
    chunks_dir.mkdir(parents=True, exist_ok=True)
    chunk_size = args.chunk_mib * 1024 * 1024
    ranges = [(start, min(start + chunk_size - 1, total - 1)) for start in range(0, total, chunk_size)]
    print("Downloading %d bytes in %d verified ranges..." % (total, len(ranges)), flush=True)

    def fetch(indexed):
        index, (start, end) = indexed
        size = end - start + 1
        target = chunks_dir / ("%06d.bin" % index)
        if target.is_file() and target.stat().st_size == size:
            return index
        last_error = None
        for attempt in range(args.retries):
            try:
                data = get_bytes(args.url, token, start, end, size)
                temporary = target.with_suffix(".tmp")
                temporary.write_bytes(data)
                os.replace(temporary, target)
                print("  chunk %d/%d" % (index + 1, len(ranges)), flush=True)
                return index
            except Exception as exc:
                last_error = exc
                time.sleep(min(attempt + 1, 4))
        raise RuntimeError("Range %d failed after retries: %s" % (index, last_error))

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(fetch, enumerate(ranges)))

    temporary_zip = out.with_suffix(out.suffix + ".partial")
    with temporary_zip.open("wb") as combined:
        for index in range(len(ranges)):
            part = chunks_dir / ("%06d.bin" % index)
            with part.open("rb") as src:
                while True:
                    block = src.read(8 * 1024 * 1024)
                    if not block:
                        break
                    combined.write(block)
    if temporary_zip.stat().st_size != total:
        raise RuntimeError("Combined download size mismatch")
    digest = hashlib.sha256()
    with temporary_zip.open("rb") as captured:
        for block in iter(lambda: captured.read(8 * 1024 * 1024), b""):
            digest.update(block)
    with zipfile.ZipFile(temporary_zip) as archive:
        for entry in archive.infolist():
            path = Path(entry.filename)
            if path.is_absolute() or ".." in path.parts:
                raise RuntimeError("Unsafe archive path: " + entry.filename)
        if archive.testzip() is not None:
            raise RuntimeError("ZIP CRC validation failed")
        if args.extract:
            args.extract.mkdir(parents=True, exist_ok=True)
            archive.extractall(args.extract)
    os.replace(temporary_zip, out)
    for path in chunks_dir.iterdir():
        if path.is_file():
            path.unlink()
    chunks_dir.rmdir()
    print(json.dumps({"ok": True, "iso_zip": str(out), "sha256": digest.hexdigest(), "bytes": total}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
