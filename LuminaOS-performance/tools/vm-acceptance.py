#!/usr/bin/env python3
"""Create an isolated LuminaOS live VM and run read-only/limited guest checks.

Windows + VirtualBox 7.x host. Requires the Python ``paramiko`` package locally.
The original working VM is never modified or powered off. The new VM boots only
from the supplied ISO; no installation, host shutdown, or host reboot is done.

Example:
  python tools/vm-acceptance.py --iso E:\\LuminaOS-Artifacts\\LuminaOS-1.1-amd64.iso
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def run_vbox(vbox: str, *args: str, timeout: int = 60) -> str:
    result = subprocess.run([vbox, *args], capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError("VBoxManage %s failed: %s" % (args[0], (result.stderr or result.stdout).strip()))
    return result.stdout


def capture(vbox: str, name: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        run_vbox(vbox, "controlvm", name, "screenshotpng", str(path), timeout=30)
    except Exception as exc:
        print("Screenshot unavailable: %s" % exc)


def ssh_exec(ssh, command: str, timeout: int = 60) -> tuple[int, str, str]:
    _stdin, stdout, stderr = ssh.exec_command("timeout %d sh -c %s" % (
        max(timeout, 1), __import__("shlex").quote(command)), timeout=15)
    code = stdout.channel.recv_exit_status()
    return code, stdout.read().decode("utf-8", "replace"), stderr.read().decode("utf-8", "replace")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", required=True, help="Path to the tested LuminaOS ISO")
    parser.add_argument("--vm-name", default="LuminaOS-1.1-Acceptance")
    parser.add_argument("--basefolder", help="Dedicated new VM parent folder; defaults to VirtualBox's default")
    parser.add_argument("--ram", type=int, default=4096)
    parser.add_argument("--cpus", type=int, default=2)
    parser.add_argument("--disk-gb", type=int, default=30)
    parser.add_argument("--ssh-port", type=int, default=2225, help="Unused loopback host port for new guest SSH")
    parser.add_argument("--user", default="lumina")
    parser.add_argument("--password", default=os.environ.get("LUMINA_LIVE_PASSWORD", "live"),
                        help="Default is the documented live-session password; never an installed account password")
    parser.add_argument("--boot-timeout", type=int, default=600)
    parser.add_argument("--report", type=Path, default=ROOT / "release/vm-live-report.json")
    args = parser.parse_args()
    import paramiko

    iso = Path(args.iso).resolve()
    if not iso.is_file():
        parser.error("ISO not found: " + str(iso))
    if not 1 <= args.ssh_port <= 65535:
        parser.error("--ssh-port must be a valid TCP port")
    if args.ram < 1536:
        parser.error("At least 1536 MiB of guest RAM is required for this test")
    vbox = str(Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
               / "Oracle" / "VirtualBox" / "VBoxManage.exe")
    if not Path(vbox).is_file():
        raise SystemExit("VirtualBox VBoxManage was not found")

    configured_path = Path.home() / ".VirtualBox" / "VirtualBox.xml"
    names = [line.strip() for line in run_vbox(vbox, "list", "vms").splitlines()
             if line.strip().startswith('"' + args.vm_name + '"')]
    if names:
        raise SystemExit("Refusing to reuse existing VM: " + args.vm_name)

    create = ["createvm", "--name", args.vm_name, "--ostype", "Debian_64", "--register"]
    if args.basefolder:
        Path(args.basefolder).mkdir(parents=True, exist_ok=True)
        create.extend(["--basefolder", str(Path(args.basefolder).resolve())])
    run_vbox(vbox, *create)
    run_vbox(vbox, "modifyvm", args.vm_name, "--memory", str(args.ram), "--cpus", str(args.cpus),
             "--vram", "128", "--accelerate3d", "off", "--graphicscontroller", "vmsvga",
             "--firmware", "efi", "--rtc-use-utc", "on", "--nic1", "nat",
             "--audio-enabled", "on", "--audio-out", "on", "--mouse", "usbtablet",
             "--usb-xhci", "on", "--clipboard-mode", "bidirectional", "--drag-and-drop", "bidirectional",
             "--boot1", "dvd", "--boot2", "disk", "--boot3", "none", "--boot4", "none")
    run_vbox(vbox, "modifyvm", args.vm_name, "--natpf1", "lumina-ssh,tcp,127.0.0.1,%d,,22" % args.ssh_port)

    config = run_vbox(vbox, "showvminfo", args.vm_name, "--machinereadable")
    match = re.search(r'^CfgFile="(.+)"$', config, re.M)
    if not match:
        raise RuntimeError("Could not locate the new VM configuration")
    disk = Path(match.group(1)).parent / (args.vm_name + ".vdi")
    run_vbox(vbox, "createmedium", "disk", "--filename", str(disk), "--size", str(args.disk_gb * 1024),
             "--format", "VDI", timeout=120)
    run_vbox(vbox, "storagectl", args.vm_name, "--name", "SATA", "--add", "sata",
             "--controller", "IntelAhci", "--portcount", "2", "--bootable", "on")
    run_vbox(vbox, "storageattach", args.vm_name, "--storagectl", "SATA", "--port", "0", "--device", "0",
             "--type", "hdd", "--medium", str(disk), "--nonrotational", "on")
    run_vbox(vbox, "storageattach", args.vm_name, "--storagectl", "SATA", "--port", "1", "--device", "0",
             "--type", "dvddrive", "--medium", str(iso))
    run_vbox(vbox, "startvm", args.vm_name, "--type", "gui", timeout=60)
    print("Started isolated VM %s. Waiting for live-session SSH..." % args.vm_name, flush=True)

    client = None
    deadline = time.monotonic() + args.boot_timeout
    last_error = "not attempted"
    while time.monotonic() < deadline:
        candidate = paramiko.SSHClient()
        candidate.set_missing_host_key_policy(paramiko.WarningPolicy())
        try:
            candidate.connect("127.0.0.1", port=args.ssh_port, username=args.user,
                              password=args.password, timeout=8, banner_timeout=8, auth_timeout=8,
                              look_for_keys=False, allow_agent=False)
            candidate.exec_command("true", timeout=10)
            client = candidate
            break
        except Exception as exc:
            last_error = str(exc)
            candidate.close()
            time.sleep(5)
    if client is None:
        shot = args.report.parent / "vm-boot-failure.png"
        capture(vbox, args.vm_name, shot)
        print("SSH readiness timed out: %s\nScreenshot: %s" % (last_error, shot))
        print("VM left running for diagnosis; it was not shut down automatically.")
        return 2

    evidence_dir = args.report.parent
    evidence_dir.mkdir(parents=True, exist_ok=True)
    guest_dir = "/tmp/lumina-acceptance"
    result = {"started_utc": datetime.now(timezone.utc).isoformat(), "vm": args.vm_name,
              "iso": str(iso), "session_type": "live", "ssh_port": args.ssh_port}
    try:
        ssh_exec(client, "rm -rf %s && mkdir -p %s" % (guest_dir, guest_dir))
        sftp = client.open_sftp()
        for filename in ("test-live.py", "validate-guest.py"):
            sftp.put(str(ROOT / "tools" / filename), guest_dir + "/" + filename)
        code, out, err = ssh_exec(client, "id && uname -a && systemctl is-active ssh && command -v lumina-shell", 30)
        result["guest_probe"] = {"exit": code, "output": (out + err)[-2000:]}
        capture(vbox, args.vm_name, evidence_dir / "vm-live-desktop.png")

        live_code, live_out, live_err = ssh_exec(client, "python3 %s/test-live.py" % guest_dir, 900)
        result["live_suite_exit"] = live_code
        print(live_out[-8000:] + live_err[-2000:])
        try:
            sftp.get(guest_dir + "/lumina-live-report.json", str(evidence_dir / "lumina-live-report.json"))
        except FileNotFoundError:
            result["missing_live_report"] = True
        validation_code, validation_out, validation_err = ssh_exec(
            client, "python3 %s/validate-guest.py --session live" % guest_dir, 180)
        result["guest_validation_exit"] = validation_code
        result["guest_validation_output"] = (validation_out + validation_err)[-16000:]
        sftp.close()
    finally:
        ssh_exec(client, "rm -rf %s" % guest_dir, 20)
        client.close()
    result["ok"] = result.get("live_suite_exit") == 0 and result.get("guest_validation_exit") == 0
    args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Result: %s\nEvidence: %s" % ("PASS" if result["ok"] else "FAIL", args.report))
    print("The isolated VM was left running; no VM was shut down by this test.")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
