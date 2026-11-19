# Share LuminaOS with a friend

Give your friend a ready-to-use LuminaOS system in VirtualBox. They do **not** need Linux, source code, builds, or terminal commands on their computer.

## What to send them

Send exactly **two files**:

1. `LuminaOS-1.1-amd64.iso`
2. `LuminaOS-1.1-amd64.iso.sha256`

Optional: a PDF/printout of this guide.

Keep the ISO and `.sha256` together in one folder.

> **Important:** an ISO file can be large (1â€“4 GB). Use a USB drive, cloud drive, or any file-transfer app that handles large files.

## Requirements on your friendâ€™s computer

- Windows 10/11, macOS, or Linux
- **VirtualBox 7.0 or newer** from https://www.virtualbox.org/
- **6 GB** minimum free RAM allocated to the VM (**8 GB** recommended)
- **20 GB** minimum free disk for the VM (**40 GB+** recommended)
- **2 CPU cores** minimum (**4** if available)
- Virtualisation enabled in BIOS (`Intel VT-x`, `AMD-V`, or `SVM`)
- Internet connection during setup (for apps and updates)

## 5-minute VM setup

### 1) Install VirtualBox
Install VirtualBox normally. Reboot if prompted.

### 2) Create a VM
In VirtualBox, click **New**, then fill in:

- **Name:** `LuminaOS`
- **Type:** `Linux`
- **Version:** `Debian (64-bit)`

Click **Next**.

### 3) Allocate memory
Allocate **4096 MB (4 GB)** minimum. Choose **6144â€“8192 MB (6â€“8 GB)** for best performance.

### 4) Create disk
Select **Create a Virtual Hard Disk Now â†’ VDI â†’ Dynamically allocated â†’ 40 GB**.

### 5) Configure the VM
Select `LuminaOS` â†’ click **Settings**:

- **System â†’ Motherboard â†’ Enable EFI** â†’ ON
- **System â†’ Processor** â†’ 2 cores (4 if available)
- **System â†’ Acceleration â†’ Hardware virtualization** â†’ ON
- **Display â†’ Video memory** â†’ 128 MB or 256 MB
- **Display â†’ Graphics controller** â†’ `VBoxVGA`
- **Display â†’ Enable 3D Acceleration** â†’ ON
- **USB Tablet / pointing device** â†’ USB tablet (smooth mouse)

Under **Storage**, attach the ISO to the virtual optical drive:

1. Click the empty **Controller: IDE â†’ Optical Drive**.
2. Click the CD icon â†’ **Choose a disk file**.
3. Select `LuminaOS-1.1-amd64.iso`.

Under **Audio**, set:
- **Audio Controller:** `Intel HD Audio`
- **Enable Audio Input/output:** ON

Under **Network**, set:
- **Adapter 1:** NAT (default)
- **Enable Network Adapter:** ON

Click **OK**.

### 6) Boot and install
Click **Start**. The VM boots into the **LuminaOS live session**.

To install LuminaOS on the VM disk:

1. Open the **Install LuminaOS** app.
2. Choose keyboard layout and disk.
3. Select **Erase disk** (deletes only the *VM* disk, not the host).
4. Set up the user account and password.
5. Finish install, then restart the VM when prompted.

### 7) Remove the ISO after install
After the installation completes and the VM restarts:

- Go to **Devices â†’ Optical Drives â†’ Remove disk from virtual drive**
- This prevents booting the installer again

### 8) Guest Additions (for smooth mouse, shared clipboard, display resize)
In the running VM:

1. Click **Devices â†’ Insert Guest Additions CD image**
2. In LuminaOS, open Terminal and run:
   ```sh
   sudo /media/cdrom/VBoxLinuxAdditions.run
   reboot
   ```

## First-time account / passwords

- **Live session**: no password required
- **Installed mode**: use the password created during setup
- **Terminal**: `lumina-terminal`
- **Kali terminal**: `lumina-terminal --kali`

## What apps work

| Type | Works? | How |
|---|---|---|
| **Linux .deb** | Yes | Double-click in Files â†’ auto-install via Store/lumina-pkg |
| **Flatpak** | Yes | Store or `.flatpakref` / `.flatpak` file |
| **AppImage** | Yes | Double-click â€” FUSE enabled at build |
| **Windows .exe / .msi** | Usually | Wine configured in **Compatibility wizard** |
| **Kali tools (nmap, etc.)** | Yes | `kali-tools` or **Compatibility â†’ Kali** |
| **Android .apk** | Experimental | Waydroid requires Wayland + binder kernel |
| **macOS .dmg / .pkg** | Inspect only | Darling + extraction; native GUI macOS apps not emulated |

## Share ability / one-click summary

To share a quick demo of your OS with your friend, you can also:

1. Run LuminaOS in your own VM
2. Take screenshots (`Screenshot` app, or `maim`)
3. Send them along with this guide

## Troubleshooting

**Black screen after starting VM**  
â†’ Turn on **Enable EFI**, use `VBoxVGA`, and enable 3D acceleration.

**Mouse jumpy**  
â†’ Insert Guest Additions and reboot.

**No internet in VM**  
â†’ Ensure NAT adapter is connected.

**No audio**  
â†’ Use Intel HD Audio controller in VM settings.

**AppImage won't run**  
â†’ Enable FUSE via **Compatibility â†’ AppImage Setup**.

**Kali Terminal says "profile not found"**  
â†’ Use regular terminal, or run `sudo install -Dm644 /usr/share/lumina/etc/lumina/kali-profile.sh /etc/lumina/kali-profile.sh`.

**Wine .exe shows "not installed"**  
â†’ Open Compatibility wizard â†’ Set up Wine (multiarch). Internet required.

## File integrity verification (optional but recommended)

On Windows:
```powershell
$expected = (Get-Content LuminaOS-1.1-amd64.iso.sha256).Split()[0]
$actual = (Get-FileHash LuminaOS-1.1-amd64.iso -Algorithm SHA256).Hash.ToLower()
if ($actual -eq $expected) { "OK: ISO is intact" } else { "MISMATCH: re-download" }
```

On Linux / macOS:
```sh
sha256sum -c LuminaOS-1.1-amd64.iso.sha256
```

---

Built with LuminaOS â€” share what you create.

