#!/usr/bin/env python3
"""Focused checks for the LuminaOS 1.1 release-readiness kit."""
import ast
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release"
REQUIRED_DOCS = [
    "README.md", "RELEASE_NOTES.md", "RELEASE_CHECKLIST.md", "QA_MATRIX.md",
    "BUILD_AND_ACCEPTANCE.md", "RELEASE_STATUS.md", "ARTIFACT_MANIFEST.md",
    "SIGNOFF_TEMPLATE.md", "wsl2/README.md",
]
REQUIRED_SCRIPTS = [
    "tools/build-release.sh", "tools/validate-guest.py",
    "release/wsl2/prepare-wsl2.ps1", "release/wsl2/wsl-build.sh",
    "release/wsl2/build-in-wsl.ps1", "release/wsl2/vm-acceptance.ps1",
]


class ReleaseTests(unittest.TestCase):
    def test_build_version(self):
        build = (ROOT / "build.sh").read_text(encoding="utf-8")
        self.assertIn('VERSION="1.1"', build)
        for rel in ("virtualbox/create-luminaos-vm.sh", "virtualbox/create-luminaos-vm.ps1"):
            self.assertIn("LuminaOS-1.1-amd64.iso", (ROOT / rel).read_text(encoding="utf-8"))

    def test_release_documents(self):
        for name in REQUIRED_DOCS:
            path = RELEASE / name
            self.assertTrue(path.is_file(), name)
            self.assertGreater(len(path.read_text(encoding="utf-8").strip()), 200, name)
        checklist = (RELEASE / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
        matrix = (RELEASE / "QA_MATRIX.md").read_text(encoding="utf-8")
        status = (RELEASE / "RELEASE_STATUS.md").read_text(encoding="utf-8")
        self.assertIn("Guest-pending", matrix)
        self.assertIn("[GUEST]", checklist)
        self.assertIn("No ISO was built", status)

    def test_release_scripts_exist_and_parse(self):
        for rel in REQUIRED_SCRIPTS:
            self.assertTrue((ROOT / rel).is_file(), rel)
        result = subprocess.run(["bash", "-n", str(ROOT / "tools/build-release.sh")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        source = (ROOT / "tools/validate-guest.py").read_text(encoding="utf-8")
        compile(source, str(ROOT / "tools/validate-guest.py"), "exec")
        for rel in ("release/wsl2/wsl-build.sh", "virtualbox/create-luminaos-vm.sh"):
            result = subprocess.run(["bash", "-n", str(ROOT / rel)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, rel + ": " + result.stderr)

    def test_guest_validator_is_read_only(self):
        source = (ROOT / "tools/validate-guest.py").read_text(encoding="utf-8")
        for forbidden in ("urlopen(request", "Request(", "L.setSettings", "subprocess", "os.chmod", "os.remove"):
            self.assertNotIn(forbidden, source)

    def test_wsl2_workflow_safety(self):
        readme = (RELEASE / "wsl2/README.md").read_text(encoding="utf-8")
        prepare = (RELEASE / "wsl2/prepare-wsl2.ps1").read_text(encoding="utf-8")
        build = (RELEASE / "wsl2/build-in-wsl.ps1").read_text(encoding="utf-8")
        self.assertIn("does **not** unregister", readme)
        self.assertIn("wsl.exe --shutdown", prepare)
        self.assertIn("Press Enter to continue", prepare)
        self.assertNotIn("wsl.exe --unregister", prepare)
        self.assertNotIn("Remove-Item", prepare)
        self.assertIn("LuminaBuild", build)
        self.assertIn("E:\\LuminaOS-Artifacts", build)

    def test_manifest_checksums(self):
        manifest = (RELEASE / "ARTIFACT_MANIFEST.md").read_text(encoding="utf-8")
        pattern = r"`([0-9a-f]{64})`"
        hashes = re.findall(pattern, manifest)
        self.assertEqual(len(hashes), 3)
        for h in hashes:
            self.assertEqual(len(h), 64)

    def test_no_false_release_claim(self):
        status = (RELEASE / "RELEASE_STATUS.md").read_text(encoding="utf-8")
        self.assertIn("pending", status.lower())
        self.assertIn("No ISO was built", status)
        self.assertIn("No virtual machine was booted", status)
    def test_release_manifest_is_json_serializable(self):
        builder = (ROOT / "tools/build-release.sh").read_text(encoding="utf-8")
        start = builder.index("<<'PY'\n") + len("<<'PY'\n")
        end = builder.index("\nPY\n", start)
        script = builder[start:end]
        with tempfile.TemporaryDirectory(prefix="lumina-manifest-") as temp:
            temp_path = pathlib.Path(temp)
            iso = temp_path / "LuminaOS-1.1-amd64.iso"
            checksum = temp_path / (iso.name + ".sha256")
            manifest = temp_path / "build-manifest.json"
            iso.write_bytes(b"LuminaOS manifest fixture")
            checksum.write_text("fixture", encoding="ascii")
            result = subprocess.run([sys.executable, "-c", script, str(iso), str(checksum), "1.1", str(manifest)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(data["version"], "1.1")
            self.assertEqual(data["product"], "LuminaOS")
            self.assertEqual(data["guest_validation"], "pending")
            self.assertEqual(len(data["iso_sha256"]), 64)
    def test_professional_documentation_suite(self):
        pages = ("README.md", "USER_GUIDE.md", "COMPATIBILITY_GUIDE.md",
                 "BUILD_AND_DEPLOY.md", "ARCHITECTURE.md", "SHARE_WITH_FRIEND.md")
        for name in pages:
            text = (ROOT / "docs" / name).read_text(encoding="utf-8")
            self.assertGreater(len(text), 1000, name)
            self.assertNotIn("LumiEnglandOS", text)
            self.assertNotIn("UNDENOTE", text)
            self.assertNotIn("â†’", text)
        index = ROOT / "docs" / "index.html"
        self.assertTrue(index.is_file())
        source = index.read_text(encoding="utf-8")
        self.assertEqual(source.count('class="chapter"'), 5)
        self.assertIn("hero h1.title,.hero .brand h3{color:#fff}", source)
        self.assertIn('href="#chapter-user_guide"', source)
        pdf = ROOT / "docs" / "LuminaOS-Documentation.pdf"
        self.assertGreater(pdf.stat().st_size, 100000)
        self.assertTrue(pdf.read_bytes().startswith(b"%PDF-"))
        rebuilt = subprocess.run([sys.executable, str(ROOT / "tools/build-docs.py"), "--no-pdf"],
                                 capture_output=True, text=True, timeout=30)
        self.assertEqual(rebuilt.returncode, 0, rebuilt.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
