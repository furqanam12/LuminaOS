#!/bin/bash
# Generates GRUB theme, Plymouth theme and Calamares artwork for LuminaOS
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"; B="$HERE/build/brand"; UI="$HERE/src/ui"
mkdir -p "$B/grub/lumina" "$B/plymouth/lumina" "$B/calamares"
rsvg-convert -w 256 -h 256 "$UI/img/apps/logo.svg" -o "$B/logo-256.png"
rsvg-convert -w 128 -h 128 "$UI/img/apps/logo.svg" -o "$B/logo-128.png"
rsvg-convert -w 96 -h 96 "$UI/img/apps/logo.svg" -o "$B/logo-96.png"
INTER=/usr/share/fonts/opentype/inter
# GRUB
convert "$UI/img/wallpapers/aurora.jpg" -resize 1920x1080^ -gravity center -extent 1920x1080 -blur 0x18 -fill '#0b0b12' -colorize 55% \
  "$B/logo-128.png" -gravity north -geometry +0+170 -composite \
  -font "$INTER/Inter-Bold.otf" -pointsize 54 -fill white -gravity north -annotate +0+318 'LuminaOS' \
  -font "$INTER/Inter-Regular.otf" -pointsize 22 -fill '#ffffffb0' -annotate +0+392 'Windows 11 layout  ·  macOS motion  ·  HarmonyOS softness' \
  "$B/grub/lumina/background.png"
grub-mkfont -s 22 -o "$B/grub/lumina/inter-22.pf2" "$INTER/Inter-Regular.otf"
grub-mkfont -s 16 -o "$B/grub/lumina/inter-16.pf2" "$INTER/Inter-Regular.otf"
# selection highlight (rounded pill), 9-slice
python3 - "$B/grub/lumina" <<'PY'
import sys
from PIL import Image, ImageDraw
d=sys.argv[1]
im=Image.new("RGBA",(60,60),(0,0,0,0)); ImageDraw.Draw(im).rounded_rectangle([0,0,59,59],radius=8,fill=(255,55,95,235))
parts={"nw":(0,0,8,8),"n":(8,0,52,8),"ne":(52,0,60,8),"w":(0,8,8,52),"c":(8,8,52,52),"e":(52,8,60,52),"sw":(0,52,8,60),"s":(8,52,52,60),"se":(52,52,60,60)}
for k,b in parts.items(): im.crop(b).save(f"{d}/select_{k}.png")
bg=Image.new("RGBA",(60,60),(0,0,0,0)); ImageDraw.Draw(bg).rounded_rectangle([0,0,59,59],radius=8,fill=(20,20,28,170),outline=(255,255,255,40))
for k,b in parts.items(): bg.crop(b).save(f"{d}/menu_{k}.png")
PY
cat > "$B/grub/lumina/theme.txt" <<'T'
title-text: ""
desktop-image: "background.png"
desktop-color: "#0b0b12"
terminal-font: "Inter Regular 16"
terminal-box: "menu_*.png"
+ boot_menu {
  left = 50%-300
  top = 50%+20
  width = 600
  height = 200
  item_font = "Inter Regular 22"
  item_color = "#e6e6ee"
  selected_item_color = "#ffffff"
  item_height = 40
  item_padding = 14
  item_spacing = 16
  icon_width = 0
  icon_height = 0
  menu_pixmap_style = "menu_*.png"
  selected_item_pixmap_style = "select_*.png"
  scrollbar = false
}
+ label {
  left = 0
  top = 100%-60
  width = 100%
  align = "center"
  id = "__timeout__"
  text = "Starting LuminaOS in %d seconds  ·  ↑ ↓ to choose, Enter to boot"
  font = "Inter Regular 16"
  color = "#ffffff90"
}
T
# Plymouth (script theme: logo with breathing glow + progress dots)
cp "$B/logo-128.png" "$B/plymouth/lumina/logo.png"
convert -size 10x10 xc:none -fill '#ffffff' -draw 'circle 5,5 5,1' "$B/plymouth/lumina/dot.png"
convert -size 10x10 xc:none -fill '#ff375f' -draw 'circle 5,5 5,1' "$B/plymouth/lumina/dot-on.png"
cat > "$B/plymouth/lumina/lumina.plymouth" <<'T'
[Plymouth Theme]
Name=LuminaOS
Description=LuminaOS boot splash
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/lumina
ScriptFile=/usr/share/plymouth/themes/lumina/lumina.script
T
cat > "$B/plymouth/lumina/lumina.script" <<'T'
Window.SetBackgroundTopColor(0.043, 0.043, 0.07);
Window.SetBackgroundBottomColor(0.07, 0.05, 0.10);
logo.image = Image("logo.png");
logo.sprite = Sprite(logo.image);
cx = Window.GetWidth() / 2; cy = Window.GetHeight() / 2;
logo.sprite.SetPosition(cx - logo.image.GetWidth() / 2, cy - logo.image.GetHeight() / 2 - 40, 1);
title.image = Image.Text("LuminaOS", 1, 1, 1, 1, "Sans Bold 22");
title.sprite = Sprite(title.image);
title.sprite.SetPosition(cx - title.image.GetWidth() / 2, cy + 50, 1);
dot = Image("dot.png"); doton = Image("dot-on.png");
for (i = 0; i < 5; i++) { d[i] = Sprite(dot); d[i].SetPosition(cx - 50 + i * 22, cy + 110, 1); d[i].SetOpacity(0.35); }
t = 0;
fun refresh() {
  t++;
  a = Math.Sin(t / 18) * 0.15 + 0.85;
  logo.sprite.SetOpacity(a);
  k = Math.Int(t / 9) % 5;
  for (i = 0; i < 5; i++) { if (i == k) { d[i].SetImage(doton); d[i].SetOpacity(1); } else { d[i].SetImage(dot); d[i].SetOpacity(0.35); } }
}
Plymouth.SetRefreshFunction(refresh);
msg.sprite = Sprite();
fun message_cb(text) { msg.image = Image.Text(text, 1, 1, 1, 0.7, "Sans 11"); msg.sprite.SetImage(msg.image); msg.sprite.SetPosition(cx - msg.image.GetWidth() / 2, Window.GetHeight() - 60, 2); }
Plymouth.SetMessageFunction(message_cb);
fun password_cb(prompt, bullets) { message_cb(prompt + "  " + bullets); }
Plymouth.SetDisplayPasswordFunction(password_cb);
T
# Calamares artwork
convert "$UI/img/wallpapers/aurora.jpg" -resize 800x440^ -gravity center -extent 800x440 -fill '#0b0b12' -colorize 45% \
  "$B/logo-96.png" -gravity center -geometry +0-70 -composite \
  -font "$INTER/Inter-Bold.otf" -pointsize 40 -fill white -annotate +0+30 'Welcome to LuminaOS' \
  -font "$INTER/Inter-Regular.otf" -pointsize 17 -fill '#ffffffc0' -annotate +0+78 'Install it to keep your apps, files and settings.' "$B/calamares/welcome.png"
for i in 1 2 3; do
  case $i in 1) T1='A desktop that feels familiar'; T2='Start menu, taskbar-style dock and snap layouts like Windows 11.';;
             2) T1='Smooth, fluid motion'; T2='macOS-style dock, Launchpad and spring animations.';;
             3) T1='Thousands of free apps'; T2='Get apps from the Lumina Store, and run many Windows programs with Wine.';; esac
  convert "$UI/img/wallpapers/aurora.jpg" -resize 800x440^ -gravity center -extent 800x440 -fill '#0b0b12' -colorize 60% \
    -font "$INTER/Inter-Bold.otf" -pointsize 34 -fill white -gravity center -annotate +0-20 "$T1" \
    -font "$INTER/Inter-Regular.otf" -pointsize 17 -fill '#ffffffc0' -annotate +0+30 "$T2" "$B/calamares/slide$i.png"
done
cp "$B/logo-256.png" "$B/calamares/logo.png"
echo "brand assets in $B"
