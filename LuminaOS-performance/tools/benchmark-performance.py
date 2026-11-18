#!/usr/bin/env python3
"""Read-only idle benchmark. Run inside LuminaOS with the desktop signed in.

Example: python3 tools/benchmark-performance.py --label baseline --seconds 30
Run again with --label low-power after selecting Settings > System > Performance.
This samples the API; it does not launch apps, change settings or measure FPS.
"""
import argparse
import datetime
import json
import math
import shutil
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def read_json(base, endpoint):
    start = time.perf_counter()
    with urllib.request.urlopen(base + endpoint, timeout=8) as response:
        result = json.load(response)
    return result, (time.perf_counter() - start) * 1000


def summary(values):
    return {"mean": round(statistics.mean(values), 2),
            "median": round(statistics.median(values), 2),
            "min": round(min(values), 2), "max": round(max(values), 2)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=30, help="Idle sample count (5 to 600)")
    parser.add_argument("--label", default="baseline", help="Identify this benchmark run")
    parser.add_argument("--url", default="http://127.0.0.1:7700", help="Local Lumina API origin")
    args = parser.parse_args()
    parsed = urllib.parse.urlsplit(args.url)
    if (parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1")
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment
            or parsed.username or parsed.password):
        parser.error("--url must be a loopback HTTP origin without credentials or a path")
    if not 5 <= args.seconds <= 600:
        parser.error("--seconds must be between 5 and 600")
    base = args.url.rstrip("/")
    cpu, memory, latency = [], [], []
    try:
        settings, _ = read_json(base, "/api/settings")
        read_json(base, "/api/stats")  # Establish a CPU-time baseline; do not count it.
        started = time.monotonic()
        for index in range(args.seconds):
            due = started + (index + 1) * 1.05
            time.sleep(max(0.0, due - time.monotonic()))
            sample, elapsed = read_json(base, "/api/stats")
            values = (float(sample["cpu"]), float(sample["mem"]["used"]) / (1024 * 1024), elapsed)
            if not all(math.isfinite(value) for value in values):
                raise ValueError("The API returned a non-finite measurement")
            cpu.append(values[0]); memory.append(values[1]); latency.append(values[2])
        duration = time.monotonic() - started
    except (OSError, ValueError, KeyError, TypeError, urllib.error.URLError) as error:
        print("Benchmark failed: " + str(error) + ". Run inside the signed-in LuminaOS desktop.", file=sys.stderr)
        return 1
    result = {
        "label": args.label,
        "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "Idle system CPU/RAM and statistics API latency; not boot time, app startup or FPS",
        "samples": len(cpu), "elapsed_seconds": round(duration, 2), "sample_interval_seconds": 1.05,
        "performance_settings": {key: settings.get(key) for key in
                                 ("performancePreset", "reduceMotion", "transparency", "dockMagnify", "perfShadows", "widgets")},
        "system_cpu_percent": summary(cpu), "system_ram_used_mib": summary(memory),
        "stats_api_latency_ms": summary(latency),
    }
    command = shutil.which("systemd-analyze") if sys.platform.startswith("linux") else None
    if command:
        try:
            output = subprocess.run([command, "time"], capture_output=True, text=True, timeout=5)
            if output.returncode == 0:
                result["systemd_boot_timing"] = output.stdout.strip()
                result["boot_timing_note"] = "systemd service-start timing; not time until the desktop is usable"
        except (OSError, subprocess.SubprocessError):
            pass
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
