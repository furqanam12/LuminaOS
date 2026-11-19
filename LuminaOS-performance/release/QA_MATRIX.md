# LuminaOS 1.1 QA matrix

Status legend: **Source-pass** = automated source validation passed. **Live-1.0-pass** = executed against the installed 1.0 VM; any 1.0-only failures are recorded and fixed in source. **Guest-pending** = requires a booted 1.1 ISO. No 1.1 guest test has been performed in this package.

| ID | Area | Test case | Expected result | Status |
|---|---|---|---|---|
| BUILD-01 | Build | Build source on Debian/Ubuntu x86-64 | `LuminaOS-1.1-amd64.iso` created | Guest-pending |
| BUILD-02 | Build | Verify ISO checksum | `sha256sum -c` passes | Guest-pending |
| TEST-01 | Automation | `tools/test-features.py` | 21/21 pass | Source-pass |
| TEST-02 | Automation | `tools/test-installer.py` | 10/10 pass | Source-pass |
| TEST-03 | Automation | `tools/test-performance.py` | 51/51 pass | Source-pass |
| TEST-04 | Automation | `tools/test-performance.js` | 25/25 pass | Source-pass |
| TEST-05 | Automation | `tools/test-release.py` | 7/7 pass | Source-pass |
| TEST-06 | Automation | `tools/test-live.py` on installed 1.0 VM | 77/81 checks pass; 2 known 1.0-only failures fixed in source | Live-1.0-pass |
| BOOT-01 | Live ISO | Standard GRUB entry | Boots to usable desktop | Guest-pending |
| BOOT-02 | Live ISO | Safe-graphics GRUB entry | Boots to usable desktop with `nomodeset` | Guest-pending |
| BOOT-03 | Live ISO | Automatic sign-in | User `lumina` signed in | Guest-pending |
| UI-01 | Desktop | Installer shortcut | Shows “Install LuminaOS” and launches Calamares | Guest-pending |
| UI-02 | Shell | Dock/top bar/Control Centre | Render and respond correctly | Guest-pending |
| INST-01 | Installer | Full installation to virtual disk | Completes without error | Guest-pending |
| INST-02 | Installed boot | Boot from installed disk | Boots without ISO | Guest-pending |
| INST-03 | Recovery | Installed safe-graphics entry | Present in GRUB and boots | Guest-pending |
| SETUP-01 | First run | Setup opens on first installed login | Opens exactly once | Guest-pending |
| SETUP-02 | First run | Account and system setup | Password, hostname, timezone and appearance apply | Guest-pending |
| SETUP-03 | First run | Completion marker | `setup-complete` exists; wizard does not reopen | Guest-pending |
| PERF-01 | Performance | Balanced preset | Effects restored | Guest-pending |
| PERF-02 | Performance | VM / low-power preset | Effects reduced, compositor remains on | Guest-pending |
| PERF-03 | Performance | Idle benchmark | Baseline and low-power JSON archived | Guest-pending |
| A11Y-01 | Accessibility | UI scale | Built-in apps scale; shell input regions remain correct | Guest-pending |
| A11Y-02 | Accessibility | High contrast | Text and borders readable | Guest-pending |
| A11Y-03 | Accessibility | Strong focus | Keyboard focus clearly visible | Guest-pending |
| A11Y-04 | Accessibility | Keyboard navigation | Tab / Enter / Space work in common controls | Guest-pending |
| CMD-01 | Command palette | Ctrl+K | Palette opens | Guest-pending |
| CMD-02 | Command palette | Search and keyboard selection | Results filter and launch correctly | Guest-pending |
| FILE-01 | Files | Undo / redo | Reversible operations restore state | Guest-pending |
| FILE-02 | Files | Split view | Independent navigation and drag/drop copy | Guest-pending |
| FILE-03 | Files | Conflict dialog | Keep both / Replace / Skip behave correctly | Guest-pending |
| FILE-04 | Files | Archives | ZIP/TAR extract; ZIP create | Guest-pending |
| FILE-05 | Files | Permissions | Octal mode reads and applies | Guest-pending |
| FILE-06 | Files | Address editing | Ctrl+L and click-edit navigate correctly | Guest-pending |
| NOTIF-01 | Notifications | Action buttons | Actions run and notification clears | Guest-pending |
| NOTIF-02 | Notifications | Snooze | Banners silenced for 15 minutes | Guest-pending |
| NOTIF-03 | Notifications | Quiet hours | Overnight schedule works | Guest-pending |
| NOTIF-04 | Notifications | App rules | Normal / Silent / Off honored | Guest-pending |
| COMPAT-01 | Compatibility | Wizard checks | Environment status accurate | Guest-pending |
| COMPAT-02 | Compatibility | Wine setup | Wine initializes and settings open | Guest-pending |
| COMPAT-03 | Compatibility | Flatpak / Store | Store opens from wizard | Guest-pending |
| COMPAT-04 | Compatibility | Waydroid guard | Live session reports unsupported | Guest-pending |
| REL-01 | Release | Sign-off | All blocking items resolved or accepted | Pending |
