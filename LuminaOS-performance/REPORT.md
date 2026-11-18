# LuminaOS 1.0 "Aurora" — Project Report

LuminaOS is an original desktop operating system that ships as a bootable ISO for VirtualBox (or any x86-64 PC or VM). It mixes three design languages:

- the Windows 11 layout (Start menu, Explorer-style Files, Task Manager, Snip, caption buttons);
- macOS motion (top menu bar, dock with magnification, Launchpad, spring animations);
- HarmonyOS softness (rounded "super-ellipse" icons, soft cards, Control Centre tiles, gentle gradients).

The visual target was FlowOS by Velotic Studios. FlowOS has its own desktop with glass panels over real nature wallpapers, a bar along the top and a dock at the bottom ([Velotic Studios guide](https://veloticstudios.com/blog/flowos/what-is-flowos/)). Its own apps are Files, Settings, Task Manager, Notepad, Calculator, Snip and a Store ([Velotic Studios guide](https://veloticstudios.com/blog/flowos/what-is-flowos/)); see also the [FlowOS website](https://flowos.veloticstudios.com/).

LuminaOS re-creates that look and feel with its own code, artwork and branding. No FlowOS, Microsoft, Apple or Huawei code, icons or trademarks are used.

## Deliverables

| Item | Path |
|---|---|
| Bootable ISO (hybrid BIOS + UEFI, 784 MB) | `lumina/LuminaOS-1.0-amd64.iso` |
| SHA-256 checksum (`9cfe28e5…e2ed9e2`) | `lumina/LuminaOS-1.0-amd64.iso.sha256` |
| VirtualBox VM creator (Windows) | `lumina/virtualbox/create-luminaos-vm.ps1` |
| VirtualBox VM creator (Linux/macOS) | `lumina/virtualbox/create-luminaos-vm.sh` |
| Full source + reproducible builder | `lumina/build.sh`, `lumina/src/`, `lumina/system/`, `lumina/tools/` |
| Screenshots | `lumina/screenshots/` (`vm-*` = taken inside the booted ISO) |

Login for the live session: the user `lumina` is signed in automatically. If a password is ever asked for, it is `live`.

## Architecture

```
GRUB (Lumina theme) ─► Plymouth (Lumina logo) ─► LightDM autologin ─► lumina-session
                                                                      │
   ┌──────────────────────────────────────────────────────────────────┤
   │ xfwm4 (window manager + XRender compositor, Lumina-Dark theme)   │
   │ lumina-shell  (Python + GTK3 + WebKitGTK 4.1)                    │
   │   ├─ desktop window    (wallpaper, icons, rubber-band select)    │
   │   ├─ top bar           (app menu, tray, clock)                   │
   │   ├─ dock              (pinned + running apps, magnify, badges)  │
   │   ├─ overlay           (Start, Search, Control Centre, Launchpad,│
   │   │                     Task View, Notification Centre, Lock,    │
   │   │                     Power)                                   │
   │   ├─ toasts            (freedesktop notification daemon)         │
   │   └─ api.py            HTTP + Server-Sent Events on 127.0.0.1:7700│
   │ lumina-app <id>        one WebKit window per built-in app        │
   │ lumina-pkg             privileged helper for apt / flatpak       │
   └──────────────────────────────────────────────────────────────────┘
Base: Debian 13 (trixie) live system, kernel 6.12, live-boot + live-config, Calamares installer
```

- **Code size:** about 6,000 lines of HTML/CSS/JS/Python across 4 shell windows, 10 apps, and a 60+ endpoint local API. The API covers files, settings, processes, windows, workspaces, store, power, notifications, wallpapers and snip.
- **Animations:** 19 keyframe sets, including:
  - `winOpen`, `winClose`, `winMin`, `winRestore`;
  - `popIn`, `menuIn`, `riseIn`, `slideUp`;
  - `lpIn` (Launchpad), `twIn` (Task View), `zoomOut`, `breathe` (lock screen), `shake` (wrong password), `ripple`.

  Motion uses spring curves such as `cubic-bezier(.2,1.25,.35,1)` and `cubic-bezier(.16,1,.3,1)`. "Reduce motion" and "Transparency" switches are in Settings.
- **Glass effect:** a pre-blurred copy of the current wallpaper is painted at screen coordinates under each panel. This gives the frosted-glass look of FlowOS without a GPU-heavy `backdrop-filter`, so it stays smooth in a VM.

## Design mapping

| Element | Windows 11 | macOS | HarmonyOS | FlowOS reference | LuminaOS |
|---|---|---|---|---|---|
| Top bar | – | Menu bar with app menu | Status bar | Bar along the top ([guide](https://veloticstudios.com/blog/flowos/what-is-flowos/)) | Glass top bar with logo, active-app menus, tray, clock |
| Dock / taskbar | Centred taskbar | Dock with magnify | Rounded dock | Dock at the bottom ([guide](https://veloticstudios.com/blog/flowos/what-is-flowos/)) | Centred glass dock: Start, Search, Task View, Launchpad, pinned + running apps, Trash |
| Start | Start menu (Pinned / Recommended / All apps) | – | – | Start-style launcher | Start menu with search, Pinned, Recommended, All Apps, user + power |
| App grid | – | Launchpad | App grid | – | Full-screen Launchpad with search |
| Quick settings | Quick Settings | Control Centre | Control panel tiles | – | Control Centre: Wi-Fi, Bluetooth, Dark mode, Focus, volume, brightness, workspaces |
| Notifications | Notification Centre + calendar | Notification Centre | – | – | Notification Centre with calendar and toasts |
| Window buttons | Min / Max / Close, red hover | – | – | Windows-style buttons | Win11 caption buttons on both web and native windows (xfwm4 theme) |
| Icons | Fluent | Squircle | Super-ellipse, soft gradients | Own colourful icons | 21 original squircle SVG app icons + Papirus-Dark for the rest |
| Wallpapers | – | – | – | Real nature wallpapers ([guide](https://veloticstudios.com/blog/flowos/what-is-flowos/)) | 7 CC-licensed nature photos (credits below) |

## Built-in apps

| App | Highlights |
|---|---|
| **Files** (File Explorer) | Home with Quick access and Recent; sidebar; tabs; grid/list; copy/move/rename/trash; search; thumbnails; drive mounting; undo/redo; split view; conflicts; archives; permissions |
| **Settings** | System, Bluetooth & devices, Network, Personalisation, Accessibility, Apps, Accounts, Time & language, Notifications with app rules and quiet hours, Windows programs & Android, Update & drivers, About |
| **Lumina Store** | Home with hero carousel, categories, app detail pages, install progress rings over SSE, Essentials multi-install, Library. Catalogue: 35 apps (apt, Flatpak, Android via Waydroid) across 7 categories |
| **Task Manager** | Processes (CPU / memory / disk with heat colouring), Performance graphs, App history, Startup apps, Users, Details, Services, End task |
| **Notepad** | Tabs, File/Edit/View menus, word wrap, status bar |
| **Calculator** | Standard mode, history, keyboard input |
| **Photos** | Viewer with filmstrip, zoom, rotate, slideshow |
| **Snip** | Rectangle / Window / Full-screen modes, delay, saves to Pictures/Screenshots with a toast |
| **Command palette** | Ctrl+K search across actions, settings and apps |
| **Compatibility wizard** | Guided Wine, Flatpak and Waydroid checks and setup |
| **Welcome** | Live-session tour: theme, accent, wallpaper, Store essentials, shortcuts, and a branded "Install LuminaOS" button |
| **About LuminaOS** | Device, processor, memory, graphics, storage, kernel, base; check for updates |
| **First-run setup** | Installed-system wizard for account password, device name, time zone, appearance/performance, Store essentials and installed-system checks |
| **Installer** | Calamares with LuminaOS branding and slides, a branded installer launcher, a correctly named desktop shortcut, hidden generic Calamares launchers, and a safe-graphics recovery entry on installed systems |

Keyboard shortcuts:

| Action | Shortcut |
|---|---|
| Start | Super |
| Control Centre | Super+A |
| Files | Super+E |
| Lock | Super+L |
| Search | Super+S or Super+Space |
| Task View | Super+Tab |
| Launchpad | Super+G |
| Notification Centre | Super+N |
| Settings | Super+I |
| Snip a region | Print or Super+Shift+S |
| Snip full screen | Shift+Print |
| Task Manager | Ctrl+Shift+Esc |
| Command palette | Ctrl+K |
| Terminal | Ctrl+Alt+T |
| Switch windows | Alt+Tab |
| Close window | Alt+F4 |
| Tile window | Super+arrows |
| Switch workspace | Ctrl+Super+arrows |

## Build process

`sudo bash build.sh` (about 15 minutes when the chroot is reused) does the following:

1. Generates the artwork:
   - app icons (`tools/gen-icons.py`);
   - the PNG xfwm4 window themes with Win11 caption buttons (`tools/gen-xfwm.py`);
   - the GRUB theme, Plymouth theme and Calamares images (`tools/gen-brand.sh`).
2. Bootstraps or reuses a Debian 13 chroot. It then installs the base system (kernel, live-boot, live-config, **user-setup**, Xorg) and the runtime packages in `packages.list`: WebKitGTK, wnck, psutil, PipeWire, LightDM, slick-greeter, Calamares, Firefox ESR, Papirus, Inter and others.
3. Installs the Lumina shell, apps, API, icons, themes and `system/` overlay. The overlay contains:
   - LightDM autologin;
   - the xsession;
   - xfconf defaults: theme, fonts, xfwm4 compositor, shortcuts;
   - polkit and sudoers rules for the Store helper;
   - MIME defaults;
   - a live-config hook that guarantees the live user exists.
4. Builds the xz squashfs and creates a hybrid BIOS/UEFI ISO with `grub-mkrescue` (volume ID `LUMINAOS`).

## Test results

Testing was done in QEMU (software CPU emulation, no KVM), using the same ISO you run in VirtualBox.

| Test | Result |
|---|---|
| GRUB menu with Lumina theme (`screenshots/00-grub-boot-menu.png`) | Pass |
| Clean boot of the final ISO to desktop with automatic sign-in and Welcome (`vm-00-first-boot-welcome.png`) | Pass (after fix 1) |
| Desktop, top bar, dock, wallpaper rendering (`vm-01-desktop.png`) | Pass (after fixes 2 and 3) |
| Start menu (`vm-02-start-menu.png`) | Pass (after fix 4) |
| Control Centre (`vm-03`), Launchpad (`vm-04`), Notification Centre (`vm-05`) | Pass |
| Files (`vm-06`), Settings (`vm-07`), Store (`vm-08`), Task Manager (`vm-09`) | Pass |
| Welcome, About, Calculator, Notepad, Task View, Lock screen | Pass (`vm-10`…`vm-15`) |
| Native window theme (xfce4-terminal with Win11 caption buttons) | Pass |
| Notepad, Calculator (7×8 = 56), Photos, Snip (capture + toast), Store detail/library | Pass on the development display |

### Bugs found and fixed during VM testing

1. **No live user / login refused.** A cleanup step (`apt autoremove`) had removed the `user-setup` package, so live-config never created the user `lumina`. Every login, including the text console, failed with "Authentication failure".
   - Fix: `user-setup` is now in the base package list.
   - New `/usr/lib/live/config/2000-lumina` hook: creates the user if it's missing, sets the password `live`, and adds the autologin groups.
   - LightDM now has an explicit `autologin-user=lumina`.
2. **Black desktop / half-painted windows.** WebKitGTK 2.54 (Debian 13) only presents some regions when hardware acceleration is set to "never". The wallpaper and most panels stayed black.
   - Fix: the shell and apps now use WebKit's accelerated path by default. It falls back to Mesa software GL in VMs.
   - The obsolete `WEBKIT_DISABLE_*` variables were removed.
   - `LUMINA_GPU=never` in `~/.config/lumina/env` still forces the old mode.
3. **Compositor stalls in VMs.** xfwm4's GLX vblank mode stalls on virtual GPUs without 3D.
   - Fix: the default is now `vblank_mode=off`, which uses the XRender compositor.
4. **Start menu would not open.** Newer PyGObject rejects `None` in `input_shape_combine_region`, so the overlay crashed when it asked for full-window input.
   - Fix: the shell now passes a full-window region.

## Run it in VirtualBox

1. Install [VirtualBox](https://www.virtualbox.org/wiki/Downloads) 7.x.
2. Windows (PowerShell):
   `.\create-luminaos-vm.ps1 -Iso "C:\Users\you\Downloads\LuminaOS-1.0-amd64.iso"`
   Linux/macOS (Intel): `./create-luminaos-vm.sh ~/Downloads/LuminaOS-1.0-amd64.iso`
3. The script creates a VM with these settings and starts it:
   - Debian 64-bit, 4 GB RAM, 2 CPUs;
   - VMSVGA graphics, 128 MB video memory, 3D off;
   - EFI firmware, 30 GB disk;
   - NAT network, USB tablet, shared clipboard.
4. Manual setup also works: create a "Debian (64-bit)" VM with VMSVGA graphics and attach the ISO as the optical drive.
5. At the GRUB menu press Enter (it auto-starts after a few seconds). Use "safe graphics" if the screen stays black.
6. To install to the virtual disk, double-click **Install LuminaOS** on the desktop or use the button in Welcome.

## Limitations

- **macOS apps don't run.** There is no legal or technical way to run macOS apps on a Linux base, so the macOS influence is visual only.
- **Windows apps are partial.** Wine is not preinstalled; install "Wine (Windows apps)" from the Store. Compatibility depends on the app.
- **Android apps are experimental.** They use Waydroid, which needs binder kernel support and a Wayland session, so they won't work in the live session.
- **Performance in VMs:** with VirtualBox's 3D acceleration off, the glass and animation effects are drawn on the CPU. They are smooth on a modern host but slower on old hardware. "Reduce motion" and turning off "Transparency" in Settings help.
- **QEMU only:** `-vga vmware` in QEMU isn't supported by the vmwgfx driver (black screen). Use `-vga std` or virtio there. VirtualBox VMSVGA is fine.
- **Installer presentation:** fixed in this source update. Generic Calamares launchers are hidden, and the live user receives a branded "Install LuminaOS" desktop shortcut that launches through `lumina-install`.
- **Installed first run:** fixed in this source update. Installed systems open a setup wizard once; it can be reopened from Settings → Accounts or the Help menu.
- **Branding:** "Windows", "macOS", "HarmonyOS" and "FlowOS" are trademarks of their owners and are named here only to describe the design inspiration.

## Wallpaper credits

| File | Title | Artist | License | Source |
|---|---|---|---|---|
| aurora.jpg | Northern lights over Mývatn (Iceland) | Giles Laurent | CC BY-SA 4.0 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:039_Northern_lights_over_M%C3%BDvatn_(Iceland)_Photo_by_Giles_Laurent.jpg) |
| northern-lights.jpg | Aurora in Abisko near Torneträsk | Pavel.shyshkouski | CC BY-SA 4.0 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Aurora_in_Abisko_near_Tornetr%C3%A4sk.jpg) |
| loch-reflection.jpg | Glencoe Lochan reflections | Daniel Kraft | CC BY-SA 3.0 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Glencoe_Lochan_reflections_3_20211022.jpg) |
| alpine-lakes.jpg | Zagedan Lakes, Caucasus Mountains | Vyacheslav Argenberg | CC BY 4.0 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Zagedan_Lakes,_Mountain_cirque,_Caucasus_Mountains.jpg) |
| dunes.jpg | Death Valley Mesquite Flats Sand Dunes | Tuxyso | CC BY-SA 3.0 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Death_Valley_Mesquite_Flats_Sand_Dunes_2013.jpg) |
| kirkjufell.jpg | Kirkjufell, Iceland | Jakub Hałun | CC BY 4.0 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Kirkjufell,_Iceland,_20240714_1631_0713.jpg) |
| clearwater.jpg | Lake Clearwater, Canterbury, New Zealand | Michal Klajban | CC BY-SA 4.0 | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Lake_Clearwater,_Canterbury,_New_Zealand_02.jpg) |

Fonts: Inter (SIL OFL). Fallback icon theme: Papirus (GPL-3.0). Base system: Debian GNU/Linux (various free licenses).
