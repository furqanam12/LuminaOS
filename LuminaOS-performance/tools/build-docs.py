#!/usr/bin/env python3
"""Build the LuminaOS Markdown documentation into HTML and printable PDF.

No third-party Python packages are required. PDF generation uses an installed
Chromium-based browser (Chrome, Chromium or Edge), when available.
"""
from __future__ import annotations

import argparse
import html
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAGES = [
    ("README.md", "Documentation home"),
    ("USER_GUIDE.md", "User guide"),
    ("COMPATIBILITY_GUIDE.md", "Compatibility"),
    ("BUILD_AND_DEPLOY.md", "Build & deployment"),
    ("ARCHITECTURE.md", "Architecture"),
]


def inline(text: str) -> str:
    value = html.escape(text.strip(), quote=False)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    value = re.sub(r"\[([^\]]+)\]\(([^\s()]+)\)", r'<a href="\2">\1</a>', value)
    value = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", value)
    return value


def cells(line: str) -> list[str]:
    return [inline(part.strip()) for part in line.strip().strip("|").split("|")]


def markdown(source: str) -> str:
    lines, output, index = source.replace("\r\n", "\n").split("\n"), [], 0
    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        if stripped.startswith("```"):
            language = html.escape(stripped[3:].strip())
            fence = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                fence.append(lines[index])
                index += 1
            output.append('<pre><code class="%s">%s</code></pre>' % (
                "language-" + language if language else "code",
                html.escape("\n".join(fence))))
            index += 1
            continue
        heading = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip()
            anchor = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            output.append('<h%d id="%s">%s</h%d>' % (level, anchor, inline(title), level))
            index += 1
            continue
        if stripped in ("---", "***"):
            output.append("<hr>")
            index += 1
            continue
        if (stripped.startswith("|") and index + 1 < len(lines)
                and re.match(r"^\s*\|?\s*:?-{3,}", lines[index + 1])):
            headers = cells(stripped)
            index += 2
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(cells(lines[index]))
                index += 1
            allowed = re.compile(r"^\d+$")
            colgroup = "".join('<col style="width:16ch">' if allowed.match(x or "") else "<col>" for x in headers)
            table = ["<table>", colgroup, "<thead><tr>"]
            table += ["<th>" + h + "</th>" for h in headers]
            table += ["</tr></thead><tbody>"]
            for row in rows:
                table.append("<tr>" + "".join("<td>" + value + "</td>" for value in row) + "</tr>")
            table.append("</tbody></table>")
            output.append("".join(table))
            continue
        if stripped.startswith(">"):
            parts = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                parts.append(lines[index].strip()[1:].strip())
                index += 1
            output.append("<blockquote><p>" + inline(" ".join(parts)) + "</p></blockquote>")
            continue
        if re.match(r"^[-*+]\s+", stripped) or re.match(r"^\d+\.\s+", stripped):
            ordered = bool(re.match(r"^\d+\.\s+", stripped))
            tag = "ol" if ordered else "ul"
            parts = ["<%s>" % tag]
            pattern = r"^\d+\.\s+(.+)$" if ordered else r"^[-*+]\s+(.+)$"
            while index < len(lines):
                item = re.match(pattern, lines[index].strip())
                if not item:
                    break
                parts.append("<li>" + inline(item.group(1)) + "</li>")
                index += 1
            parts.append("</%s>" % tag)
            output.append("".join(parts))
            continue
        paragraph = [stripped]
        index += 1
        while index < len(lines) and lines[index].strip() and not re.match(
                r"^(#{1,4}\s+|[-*+]\s+|\d+\.\s+|```|>|\||---$)", lines[index].strip()):
            paragraph.append(lines[index].strip())
            index += 1
        output.append("<p>" + inline(" ".join(paragraph)) + "</p>")
    return "\n".join(output)


CSS = r"""
:root{--navy:#0b1f36;--blue:#0a63c9;--cyan:#11a9b0;--ink:#152435;--muted:#5d6d80;--line:#dce4ef;--paper:#fff;--wash:#f3f6fb}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--wash);color:var(--ink);font:15px/1.7 system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:#075eae;text-decoration:none}a:hover{text-decoration:underline}header.hero{padding:52px max(6vw,40px);background:linear-gradient(120deg,#07182d,#103f6b 58%,#087f91);color:#fff}.brand{display:flex;align-items:center;gap:14px}.mark{display:grid;place-items:center;width:46px;height:46px;border-radius:13px;background:linear-gradient(140deg,#57e4ec,#287add);font-size:25px;font-weight:800;box-shadow:0 8px 30px #0014}.eyebrow{text-transform:uppercase;letter-spacing:.12em;font-size:11px;opacity:.75;font-weight:700}h1.title{font-size:clamp(31px,5vw,48px);letter-spacing:-.035em;line-height:1.15;margin:24px 0 10px}.hero p{max-width:760px;color:#cde7f5;font-size:17px}.hero h1.title,.hero .brand h3{color:#fff}.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:24px}.badge{border:1px solid #ffffff36;border-radius:99px;padding:4px 10px;font-size:11px;background:#ffffff0c;color:#e0f5fa}
.layout{max-width:1380px;margin:0 auto;display:grid;grid-template-columns:254px minmax(0,1fr);gap:27px;padding:32px 30px 60px}aside{position:sticky;top:22px;align-self:start;background:var(--paper);padding:20px;border:1px solid var(--line);border-radius:14px}aside h3{margin:0 0 12px;font-size:13px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}aside a{display:block;padding:7px 9px;border-radius:7px;color:var(--muted);font-size:13px}aside a:hover{background:#eaf3fd;color:#075eae;text-decoration:none}aside .print-doc{margin-top:18px;padding-top:14px;border-top:1px solid var(--line)}
main{min-width:0}.chapter{background:var(--paper);padding:36px clamp(22px,4.5vw,62px);margin-bottom:24px;border:1px solid var(--line);border-radius:15px;box-shadow:0 5px 18px #15243504}h1,h2,h3,h4{color:var(--navy);line-height:1.3;letter-spacing:-.015em}h1{font-size:33px;margin:0 0 24px;padding-bottom:16px;border-bottom:2px solid #327cdd2a}h1:not(:first-child){margin-top:24px}h2{margin:33px 0 12px;font-size:22px;border-left:3px solid var(--cyan);padding-left:12px}h3{margin:24px 0 10px;font-size:17px}p{margin:10px 0}li{margin:5px 0}code{background:#edf2fa;padding:1px 4px;border-radius:4px;font:12px/1.55 ui-monospace,Consolas,monospace;color:#123556}pre{padding:16px;background:#0c1c2d;color:#dfeefd;border-radius:9px;overflow:auto;line-height:1.6}pre code{display:block;background:transparent;color:inherit;padding:0}blockquote{border-left:4px solid #e9a824;background:#fff9e7;padding:13px 16px;margin:18px 0;border-radius:0 7px 7px 0}blockquote p{margin:0}table{width:100%;border-collapse:collapse;margin:16px 0;table-layout:auto;font-size:13px}th{text-align:left;background:#eaf1fa;color:var(--navy);font-weight:700}th,td{padding:9px 11px;border:1px solid var(--line);vertical-align:top}tbody tr:nth-child(even){background:#f8fbfe}hr{border:0;border-top:1px solid var(--line);margin:30px 0}footer{padding:25px 30px;text-align:center;font-size:12px;color:var(--muted)}
@media(max-width:880px){.layout{grid-template-columns:1fr;padding:18px 14px}aside{position:static;display:grid;grid-template-columns:repeat(2,1fr);gap:4px}aside h3,aside .print-doc{grid-column:1/-1}.chapter{padding:28px 22px}header.hero{padding:35px 24px}th,td{padding:7px;font-size:12px}}
@media print{body{background:#fff;color:#111;font-size:10.2pt;line-height:1.5}header.hero{padding:70mm 20mm 25mm;background:#0b1f36!important;print-color-adjust:exact;-webkit-print-color-adjust:exact}h1.title{font-size:36pt}.layout{display:block;padding:12mm 15mm}aside,footer{display:none}.chapter{border:0;border-radius:0;box-shadow:none;padding:0;margin:0}.chapter:not(:first-of-type){break-before:page}h1{font-size:23pt;break-after:avoid}h2,h3{break-after:avoid}table{break-inside:auto;font-size:8.7pt}tr,li,blockquote{break-inside:avoid}thead{display:table-header-group}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f2f4f7!important;color:#111!important;print-color-adjust:exact;-webkit-print-color-adjust:exact}a{color:#111;text-decoration:none}a[href^="https://"]::after{content:" ("attr(href)")";font-size:8pt;color:#555;word-break:break-all}.hero .badge{display:none}@page{size:A4;margin:0}}
"""


def render_html() -> str:
    nav = "\n".join('<a href="#chapter-%s">%s</a>' % (Path(filename).stem.lower(), title) for filename, title in PAGES)
    chapters = []
    for filename, title in PAGES:
        body = markdown((DOCS / filename).read_text(encoding="utf-8"))
        chapters.append('<section class="chapter" id="chapter-%s" aria-label="%s">\n%s\n</section>' % (
            Path(filename).stem.lower(), html.escape(title), body))
    template = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="LuminaOS 1.1 user, compatibility, build and architecture documentation">
<title>LuminaOS 1.1 — Professional Documentation</title>
<style>{css}</style></head><body>
<header class="hero"><div class="brand"><div class="mark">L</div><div><h3 style="margin:0">LuminaOS</h3><div class="eyebrow">Aurora Update 1</div></div></div>
<h1 class="title">Documentation &amp; release handbook</h1>
<p>A practical guide to using, evaluating and building LuminaOS — with clear compatibility boundaries, repeatable checks and production-ready release practices.</p>
<div class="badges"><span class="badge">Edition 1.1</span><span class="badge">Revision 1.0</span><span class="badge">20 November 2026</span><span class="badge">Users · Developers · QA</span></div></header>
<div class="layout"><aside><h3>Documentation</h3>{nav}<div class="print-doc"><a href="LuminaOS-Documentation.pdf">Download PDF</a><a href="https://github.com/furqanam12/LuminaOS">GitHub repository</a></div></aside>
<main>{chapters}</main></div>
<footer>LuminaOS documentation · Generated from version-controlled Markdown; no third-party renderer required.<br>Review release status before distributing a new image.</footer>
</body></html>
"""
    formatted = template.format(css=CSS, nav=nav, chapters="\n".join(chapters))
    for filename, _title in PAGES:
        formatted = formatted.replace('href="%s"' % filename,
                                      'href="#chapter-%s"' % Path(filename).stem.lower())
    formatted = re.sub(r'href="\.\./(.+?)"',
                       r'href="https://github.com/furqanam12/LuminaOS/blob/main/LuminaOS-performance/\1"',
                       formatted)
    return formatted


def browser_binary(explicit: str | None) -> str | None:
    if explicit:
        return explicit if Path(explicit).is_file() or shutil.which(explicit) else None
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate
    for candidate in ("google-chrome", "chromium", "chromium-browser", "msedge"):
        found = shutil.which(candidate)
        if found:
            return found
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", help="Chrome/Chromium/Edge executable")
    parser.add_argument("--no-pdf", action="store_true", help="Generate HTML only")
    args = parser.parse_args()
    output = DOCS / "index.html"
    output.write_text(render_html(), encoding="utf-8")
    print("HTML: " + str(output))
    if args.no_pdf:
        return 0
    browser = browser_binary(args.browser)
    if not browser:
        print("PDF: skipped (Chrome/Chromium/Edge not found)")
        return 0
    pdf = DOCS / "LuminaOS-Documentation.pdf"
    with tempfile.TemporaryDirectory(prefix="lumina-docs-print-") as profile:
        url = output.resolve().as_uri()
        command = [browser, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                   "--user-data-dir=" + profile, "--print-to-pdf=" + str(pdf), url]
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    if result.returncode or not pdf.is_file() or pdf.stat().st_size < 1000:
        print("PDF: generation failed: " + (result.stderr or result.stdout)[-600:])
        return 1
    print("PDF: %s (%s bytes)" % (pdf, pdf.stat().st_size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
