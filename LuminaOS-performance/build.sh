#!/usr/bin/env bash
# =====================================================================
#  LuminaOS build script  ->  LuminaOS-<ver>-amd64.iso
#  Debian 13 (trixie) live system + the Lumina shell (WebKitGTK + xfwm4)
#  Run on Debian/Ubuntu x86_64 with sudo and ~8 GB free disk.
#  Re-uses an existing chroot at work/chroot if present (fast rebuilds).
# =====================================================================
set -euo pipefail
VERSION="1.1"; CODENAME="Aurora"
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$HERE/work"; CH="$WORK/chroot"; ISO="$WORK/iso"
OUT="$HERE/LuminaOS-$VERSION-amd64.iso"
MIRROR="http://deb.debian.org/debian"
SRC="$HERE/src"; SYS="$HERE/system"; BRAND="$HERE/build/brand"

echo "==> Host tools"
need=(debootstrap mksquashfs xorriso grub-mkrescue grub-mkfont rsvg-convert convert python3)
for t in "${need[@]}"; do command -v "$t" >/dev/null || MISSING=1; done
if [ -n "${MISSING:-}" ]; then
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq debootstrap squashfs-tools xorriso grub-pc-bin \
    grub-efi-amd64-bin grub-common mtools dosfstools debian-archive-keyring librsvg2-bin imagemagick dpkg-dev \
    rsync python3-pil fonts-inter
fi

echo "==> Generating artwork (icons, window theme, boot branding)"
python3 "$HERE/tools/gen-icons.py" >/dev/null
python3 "$HERE/tools/gen-xfwm.py" "$HERE/build/themes" >/dev/null
bash "$HERE/tools/gen-brand.sh" >/dev/null 2>&1

mkdir -p "$WORK"
if [ ! -x "$CH/bin/bash" ]; then
  echo "==> Bootstrapping Debian 13 (trixie)"
  sudo debootstrap --arch=amd64 --variant=minbase \
    --keyring=/usr/share/keyrings/debian-archive-keyring.gpg trixie "$CH" "$MIRROR"
fi
sudo tee "$CH/etc/apt/sources.list" >/dev/null <<SRCS
deb $MIRROR trixie main contrib non-free non-free-firmware
deb $MIRROR trixie-updates main contrib non-free non-free-firmware
deb http://security.debian.org/debian-security trixie-security main contrib non-free non-free-firmware
SRCS
echo luminaos | sudo tee "$CH/etc/hostname" >/dev/null
mnt(){ for d in dev dev/pts proc sys run; do mountpoint -q "$CH/$d" || sudo mount --bind "/$d" "$CH/$d"; done; }
umnt(){ for d in run sys proc dev/pts dev; do sudo umount -l "$CH/$d" 2>/dev/null || true; done; }
trap umnt EXIT
mnt
sudo rm -f "$CH/etc/resolv.conf"; sudo cp -L /etc/resolv.conf "$CH/etc/resolv.conf"
sudo mkdir -p "$CH/etc/network"

echo "==> Base system + Lumina runtime packages"
BASE="linux-image-amd64 live-boot live-config live-config-systemd user-setup systemd-sysv sudo locales console-setup
 keyboard-configuration dbus-x11 polkitd xserver-xorg-core xserver-xorg-input-all xserver-xorg-video-vmware
 xserver-xorg-video-fbdev xserver-xorg-video-vesa xinit grub-pc-bin grub-efi-amd64-bin grub-common grub2-common
 efibootmgr zenity network-manager-gnome"
sudo chroot "$CH" bash -c "echo 'locales locales/default_environment_locale select en_US.UTF-8' | debconf-set-selections
  echo 'locales locales/locales_to_be_generated multiselect en_US.UTF-8 UTF-8' | debconf-set-selections"
sudo chroot "$CH" apt-get update -qq
sudo chroot "$CH" env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
  $BASE $(grep -v '^#' "$HERE/packages.list" | tr '\n' ' ')

echo "==> Removing leftovers from older desktop builds (if the chroot was re-used)"
sudo chroot "$CH" env DEBIAN_FRONTEND=noninteractive apt-get purge -y -qq plank rofi xfce4-panel xfdesktop4 \
  xfce4-whiskermenu-plugin xfce4-appmenu-plugin appmenu-gtk3-module appmenu-registrar xfce4-pulseaudio-plugin \
  xfce4-notifyd mugshot thunar thunar-volman thunar-archive-plugin xfce4-appfinder mousepad ristretto \
  xfce4-screenshooter xfce4-taskmanager gnome-calculator tumbler xfce4-session 2>/dev/null || true
sudo chroot "$CH" env DEBIAN_FRONTEND=noninteractive apt-get autoremove -y -qq --purge || true
sudo rm -rf "$CH"/usr/local/bin/orchard-* "$CH"/etc/xdg/autostart/orchard-* "$CH"/usr/local/share/applications/* \
  "$CH"/usr/share/orchardos "$CH"/usr/share/plank "$CH"/usr/share/themes/WhiteSur* "$CH"/usr/share/icons/WhiteSur* \
  "$CH"/etc/lightdm/lightdm.conf.d/50-orchardos.conf "$CH"/etc/live/config.conf.d/orchardos.conf \
  "$CH"/etc/xdg/xfce4/panel "$CH"/etc/xdg/xfce4/whiskermenu "$CH"/usr/share/backgrounds/orchardos \
  "$CH"/etc/default/grub.d/orchardos.cfg "$CH"/etc/calamares/branding/debian/orchard-*
sudo chroot "$CH" sh -c 'dpkg-divert --list | grep -q xfce-x.svg && rm -f /usr/share/backgrounds/xfce/xfce-x.svg && dpkg-divert --quiet --local --rename --remove /usr/share/backgrounds/xfce/xfce-x.svg' || true

echo "==> Installing Lumina shell, apps and system config"
L="$CH/usr/share/lumina"
sudo rm -rf "$L"; sudo mkdir -p "$L" "$CH/usr/libexec/lumina"
sudo rsync -a --exclude __pycache__ "$SRC/ui" "$SRC/lib" "$SRC/data" "$L/"
for b in lumina-shell lumina-app lumina-ctl lumina-session lumina-install; do sudo install -m 755 "$SRC/bin/$b" "$CH/usr/bin/$b"; done
sudo install -m 755 "$SRC/libexec/lumina-pkg" "$CH/usr/libexec/lumina/lumina-pkg"
sudo install -m 644 "$SRC"/data/applications/*.desktop "$CH/usr/share/applications/"
sudo mkdir -p "$CH/usr/share/icons/hicolor/scalable/apps"
for f in "$SRC"/ui/img/apps/*.svg; do sudo install -m 644 "$f" "$CH/usr/share/icons/hicolor/scalable/apps/lumina-$(basename "$f")"; done
sudo mkdir -p "$CH/usr/share/themes"; sudo rm -rf "$CH"/usr/share/themes/Lumina-*; sudo cp -r "$HERE"/build/themes/Lumina-* "$CH/usr/share/themes/"
sudo rsync -a --chown=root:root "$SYS/" "$CH/"
sudo chmod 0440 "$CH/etc/sudoers.d/lumina"
# boot splash + installer artwork
sudo rm -rf "$CH/usr/share/plymouth/themes/lumina"; sudo cp -r "$BRAND/plymouth/lumina" "$CH/usr/share/plymouth/themes/"
sudo mkdir -p "$CH/usr/share/lumina/brand"; sudo cp "$BRAND"/logo-*.png "$BRAND"/calamares/*.png "$CH/usr/share/lumina/brand/"
sudo mkdir -p "$CH/boot/grub/themes"; sudo rm -rf "$CH/boot/grub/themes/lumina"; sudo cp -r "$BRAND/grub/lumina" "$CH/boot/grub/themes/"

sudo tee "$CH/tmp/customize.sh" >/dev/null <<CUST
#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive
VERSION="$VERSION"; CODENAME="$CODENAME"
CUST
sudo tee -a "$CH/tmp/customize.sh" >/dev/null <<'CUST'
# --- identity ---
sed -i -E '/^(PRETTY_NAME|LUMINA_VERSION|LUMINA_CODENAME|HOME_URL|SUPPORT_URL|BUG_REPORT_URL)=/d' /usr/lib/os-release
cat >> /usr/lib/os-release <<OS
PRETTY_NAME="LuminaOS $VERSION"
LUMINA_VERSION="$VERSION"
LUMINA_CODENAME="$CODENAME"
HOME_URL="https://www.debian.org/"
SUPPORT_URL="https://www.debian.org/support"
BUG_REPORT_URL="https://bugs.debian.org/"
OS
printf 'LuminaOS %s \\n \\l\n\n' "$VERSION" > /etc/issue
echo "LuminaOS $VERSION" > /etc/issue.net
# --- hide technical / duplicate launchers, rename the installer ---
L=/usr/local/share/applications; mkdir -p $L
hide(){ for f in "$@"; do s=/usr/share/applications/$f.desktop; [ -f "$s" ] || continue
  cp "$s" $L/$f.desktop; sed -i '/^NoDisplay=/d; /^\[Desktop Entry\]/a NoDisplay=true' $L/$f.desktop; done; }
hide xfce4-terminal-settings xfce-settings-manager xfce4-settings-editor xfce-display-settings xfce-keyboard-settings \
  xfce-mouse-settings xfce-ui-settings xfce-wm-settings xfce-wmtweaks-settings xfce-workspaces-settings \
  xfce4-accessibility-settings xfce4-mime-settings xfce-backdrop-settings nm-connection-editor display-im6.q16 \
  python3.13 debian-uxterm debian-xterm xfce4-terminal x-terminal-emulator xfce4-color-settings xfce4-file-manager \
  xfce4-web-browser xfce4-mail-reader org.gnome.Zenity
for s in /usr/share/applications/calamares*.desktop /usr/share/applications/org.calamares*.desktop; do
  [ -f "$s" ] || continue
  f=$(basename "$s")
  cp "$s" "$L/$f"
  sed -i '/^NoDisplay=/d; /^\[Desktop Entry\]/a NoDisplay=true' "$L/$f"
done
mkdir -p /etc/skel/Desktop
install -m 644 /usr/share/applications/lumina-install.desktop /etc/skel/Desktop/Install\ LuminaOS.desktop
update-alternatives --set x-terminal-emulator /usr/bin/xfce4-terminal.wrapper 2>/dev/null || true
# --- default session: Lumina ---
rm -f /usr/share/xsessions/xfce.desktop /usr/share/xsessions/lightdm-xsession.desktop
update-alternatives --install /usr/bin/x-session-manager x-session-manager /usr/bin/lumina-session 90 || true
# --- calamares branding ---
B=/etc/calamares/branding/debian
if [ -f $B/branding.desc ]; then
  sed -i -E 's/(productName|shortProductName|bootloaderEntryName): .*/\1: "LuminaOS"/;
             s/(version|shortVersion): .*/\1: "'"$VERSION"'"/;
             s/(versionedName|shortVersionedName): .*/\1: "LuminaOS '"$VERSION"'"/;
             s/(productUrl|supportUrl|knownIssuesUrl|releaseNotesUrl): .*/\1: "https:\/\/www.debian.org\/"/;
             s/^( *productLogo:).*/\1 "lumina-logo.png"/;
             s/^( *productIcon:).*/\1 "lumina-logo.png"/;
             s/^( *productWelcome:).*/\1 "lumina-welcome.png"/;
             s/^( *sidebarBackground:).*/\1 "#16161c"/;
             s/^( *sidebarText:).*/\1 "#ffffff"/;
             s/^( *sidebarTextSelect:).*/\1 "#ff375f"/' $B/branding.desc
  cp /usr/share/lumina/brand/logo-256.png $B/lumina-logo.png
  cp /usr/share/lumina/brand/welcome.png $B/lumina-welcome.png
  for i in 1 2 3; do cp /usr/share/lumina/brand/slide$i.png $B/slide$i.png; done
  [ -f $B/show.qml ] && sed -i -E 's/slide[0-9]+\.(png|svg)/slide1.png/' $B/show.qml || true
fi
# --- installed system: grub theme + plymouth ---
mkdir -p /etc/default/grub.d
cat > /etc/default/grub.d/lumina.cfg <<'G'
GRUB_DISTRIBUTOR="LuminaOS"
GRUB_TIMEOUT=3
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash loglevel=3"
GRUB_GFXMODE=1920x1080,1280x800,auto
GRUB_THEME="/boot/grub/themes/lumina/theme.txt"
G
plymouth-set-default-theme lumina 2>/dev/null || ln -sf /usr/share/plymouth/themes/lumina/lumina.plymouth /etc/alternatives/default.plymouth
# --- misc ---
locale-gen >/dev/null 2>&1 || true
update-locale LANG=en_US.UTF-8 || true
gtk-update-icon-cache -f /usr/share/icons/hicolor >/dev/null 2>&1 || true
gtk-update-icon-cache -f /usr/share/icons/Papirus-Dark >/dev/null 2>&1 || true
fc-cache -f >/dev/null 2>&1 || true
update-desktop-database /usr/local/share/applications /usr/share/applications 2>/dev/null || true
glib-compile-schemas /usr/share/glib-2.0/schemas 2>/dev/null || true
python3 -m compileall -q /usr/share/lumina/lib >/dev/null 2>&1 || true
systemctl enable NetworkManager lightdm >/dev/null 2>&1 || true
systemctl set-default graphical.target >/dev/null 2>&1 || true
passwd -l root >/dev/null
update-initramfs -u -k all >/dev/null 2>&1
chmod 0755 /etc/grub.d/45_lumina_recovery 2>/dev/null || true
update-grub >/dev/null 2>&1 || true
apt-get clean
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache
echo "customize: done"
CUST
sudo chroot "$CH" bash /tmp/customize.sh
umnt; trap - EXIT
sudo rm -f "$CH/etc/resolv.conf"; sudo touch "$CH/etc/resolv.conf"

echo "==> ISO tree"
mkdir -p "$ISO/live" "$ISO/boot/grub/themes"
# offline bootloader packages for the installer (from a previous build, if present)
if [ ! -d "$ISO/pool" ] && [ -d "$HERE/../orchardos/work/iso/pool" ]; then
  cp -r "$HERE/../orchardos/work/iso/pool" "$HERE/../orchardos/work/iso/dists" "$ISO/"
fi
sudo cp "$CH"/boot/vmlinuz-* "$ISO/live/vmlinuz"; sudo cp "$CH"/boot/initrd.img-* "$ISO/live/initrd.img"
sudo chown -R "$USER" "$ISO"
rm -rf "$ISO/boot/grub/themes/lumina"; cp -r "$BRAND/grub/lumina" "$ISO/boot/grub/themes/"
rm -f "$ISO/boot/grub/background.png"
cp "$HERE/iso-grub.cfg" "$ISO/boot/grub/grub.cfg"
echo "LuminaOS $VERSION \"$CODENAME\" - built $(date -u +%F)" > "$ISO/LUMINAOS"

echo "==> squashfs (xz)"
rm -f "$ISO/live/filesystem.squashfs"
sudo mksquashfs "$CH" "$ISO/live/filesystem.squashfs" -comp xz -Xbcj x86 -b 1M -noappend -no-progress \
  -wildcards -e 'proc/*' 'sys/*' 'dev/*' 'run/*' 'tmp/*' 'var/cache/apt/archives/*.deb'
sudo chown "$USER" "$ISO/live/filesystem.squashfs"

echo "==> Hybrid BIOS + UEFI ISO"
grub-mkrescue -o "$OUT" "$ISO" -- -volid LUMINAOS
sha256sum "$OUT" > "$OUT.sha256"
ls -lh "$OUT"
echo "Done: $OUT"
