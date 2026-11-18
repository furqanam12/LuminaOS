#!/usr/bin/env python3
"""Generate LuminaOS app icons (original artwork) as SVG."""
import os, sys
OUT = sys.argv[1] if len(sys.argv) > 1 else "src/ui/img/apps"
os.makedirs(OUT, exist_ok=True)
SQ = "M20 4h24c11 0 16 5 16 16v24c0 11-5 16-16 16H20C9 60 4 55 4 44V20C4 9 9 4 20 4z"

DEFS = """<defs>
<linearGradient id="dk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a3a44"/><stop offset="1" stop-color="#16161c"/></linearGradient>
<linearGradient id="rd" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ff6b8e"/><stop offset="1" stop-color="#d81b4f"/></linearGradient>
<linearGradient id="rd2" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ff8aa6"/><stop offset="1" stop-color="#e3245c"/></linearGradient>
<linearGradient id="gl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".22"/><stop offset=".5" stop-color="#fff" stop-opacity="0"/></linearGradient>
<linearGradient id="bl" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5ac8fa"/><stop offset="1" stop-color="#2f6bff"/></linearGradient>
<linearGradient id="gr" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5ee39a"/><stop offset="1" stop-color="#16a34a"/></linearGradient>
<linearGradient id="am" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffd36b"/><stop offset="1" stop-color="#ff8a00"/></linearGradient>
<linearGradient id="vi" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#c58cff"/><stop offset="1" stop-color="#6d3bff"/></linearGradient>
<filter id="sh" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="1.5" stdDeviation="1.4" flood-color="#000" flood-opacity=".35"/></filter>
</defs>"""

def tile(fill, body):
    return (f'<path d="{SQ}" fill="{fill}"/><path d="{SQ}" fill="url(#gl)"/>'
            f'<path d="{SQ}" fill="none" stroke="#fff" stroke-opacity=".10" stroke-width="1"/>' + body)

R = "#ff375f"
ICONS = {
 "files": '<g filter="url(#sh)"><path d="M6 16a5 5 0 0 1 5-5h13l6 6h23a5 5 0 0 1 5 5v4H6z" fill="#c7174a"/>'
          '<path d="M6 22a5 5 0 0 1 5-5h42a5 5 0 0 1 5 5v24a6 6 0 0 1-6 6H12a6 6 0 0 1-6-6z" fill="url(#rd2)"/>'
          '<path d="M6 24h52" stroke="#fff" stroke-opacity=".35" stroke-width="1.2"/></g>',
 "store": tile("url(#rd)", '<path d="M19 24h26l-2 24a3 3 0 0 1-3 3H24a3 3 0 0 1-3-3z" fill="#fff"/>'
          '<path d="M25 25v-4a7 7 0 0 1 14 0v4" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round"/>'
          f'<path d="M32 30c.8 4 2 5.2 6 6-4 .8-5.2 2-6 6-.8-4-2-5.2-6-6 4-.8 5.2-2 6-6z" fill="{R}"/>'),
 "notepad": '<g filter="url(#sh)"><rect x="12" y="6" width="40" height="52" rx="6" fill="#fbfbfd"/>'
          '<path d="M12 12a6 6 0 0 1 6-6h28a6 6 0 0 1 6 6v5H12z" fill="url(#rd)"/>'
          '<g fill="#9aa0ab"><rect x="19" y="25" width="26" height="2.6" rx="1.3"/><rect x="19" y="32" width="26" height="2.6" rx="1.3"/>'
          '<rect x="19" y="39" width="26" height="2.6" rx="1.3"/><rect x="19" y="46" width="15" height="2.6" rx="1.3"/></g>'
          '<path d="M44 52l9-14 4 3-9 14-5 2z" fill="#f2b84b" stroke="#7a4b00" stroke-width=".8"/></g>',
 "calculator": tile("url(#dk)", ''.join(
          f'<rect x="{x}" y="{y}" width="9" height="9" rx="2.6" fill="{c}"/>'
          for (x, y, c) in [(15,15,"#8e8e98"),(27.5,15,"#8e8e98"),(40,15,R),(15,27.5,"#5b5b66"),(27.5,27.5,"#5b5b66"),
                            (40,27.5,R),(15,40,"#5b5b66"),(27.5,40,"#5b5b66"),(40,40,R)])),
 "settings": tile("url(#dk)", f'<g transform="translate(32 32)" fill="{R}"><path d="M-3.2-17h6.4l1 5.1 3.3 1.4 4.3-2.9 4.5 4.5-2.9 4.3 1.4 3.3 5.1 1v6.4l-5.1 1-1.4 3.3 2.9 4.3-4.5 4.5-4.3-2.9-3.3 1.4-1 5.1h-6.4l-1-5.1-3.3-1.4-4.3 2.9-4.5-4.5 2.9-4.3-1.4-3.3-5.1-1v-6.4l5.1-1 1.4-3.3-2.9-4.3 4.5-4.5 4.3 2.9 3.3-1.4z"/>'
          '<circle r="5.6" fill="#24242c"/></g>'),
 "taskmgr": tile("url(#dk)", '<path d="M14 46h36" stroke="#55555f" stroke-width="2" stroke-linecap="round"/>'
          f'<path d="M14 40l9-9 7 5 9-13 11 6" fill="none" stroke="{R}" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"/>'
          f'<path d="M14 40l9-9 7 5 9-13 11 6V46H14z" fill="{R}" opacity=".18"/>'),
 "terminal": tile("url(#dk)", f'<path d="M17 22l10 9-10 9" fill="none" stroke="{R}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
          '<rect x="31" y="40" width="16" height="4" rx="2" fill="#e8e8ee"/>'),
 "snip": tile("url(#rd)", '<rect x="15" y="17" width="34" height="30" rx="4" fill="none" stroke="#fff" stroke-width="3" stroke-dasharray="5 3.5"/>'
          '<circle cx="24" cy="38" r="4.5" fill="none" stroke="#fff" stroke-width="2.6"/><circle cx="40" cy="38" r="4.5" fill="none" stroke="#fff" stroke-width="2.6"/>'
          '<path d="M27 35l11-12M37 35L26 23" stroke="#fff" stroke-width="2.6" stroke-linecap="round"/>'),
 "welcome": tile("url(#dk)", ''.join(f'<circle cx="19" cy="{y}" r="3.3" fill="{R}"/><rect x="26" y="{y-2}" width="20" height="4" rx="2" fill="#e8e8ee"/>' for y in (21, 32, 43))),
 "about": tile("url(#dk)", f'<circle cx="32" cy="32" r="16" fill="none" stroke="{R}" stroke-width="3.4"/><circle cx="32" cy="24.5" r="2.6" fill="#fff"/><rect x="29.8" y="30" width="4.4" height="12" rx="2.2" fill="#fff"/>'),
 "photos": tile("url(#dk)", '<rect x="13" y="16" width="38" height="32" rx="5" fill="#fff" opacity=".1"/>'
          '<circle cx="40" cy="25" r="4.4" fill="url(#am)"/><path d="M14 45l12-14 8 9 5-5 11 10v1a2 2 0 0 1-2 2H16a2 2 0 0 1-2-2z" fill="url(#rd2)"/>'),
 "browser": tile("url(#bl)", '<circle cx="32" cy="32" r="16" fill="none" stroke="#fff" stroke-width="3"/><ellipse cx="32" cy="32" rx="7" ry="16" fill="none" stroke="#fff" stroke-width="2.4"/><path d="M16 32h32M18.5 23h27M18.5 41h27" stroke="#fff" stroke-width="2.2"/>'),
 "android": tile("url(#dk)", '<rect x="22" y="12" width="20" height="40" rx="5" fill="url(#gr)"/><rect x="25" y="17" width="14" height="25" rx="2" fill="#0d3b1f"/><circle cx="32" cy="47" r="2" fill="#0d3b1f"/>'),
 "windows": tile("url(#dk)", f'<g fill="{R}"><rect x="15" y="15" width="15.5" height="15.5" rx="2.5"/><rect x="33.5" y="15" width="15.5" height="15.5" rx="2.5" opacity=".8"/><rect x="15" y="33.5" width="15.5" height="15.5" rx="2.5" opacity=".8"/><rect x="33.5" y="33.5" width="15.5" height="15.5" rx="2.5" opacity=".6"/></g>'),
 "drivers": tile("url(#dk)", '<rect x="20" y="20" width="24" height="24" rx="3" fill="url(#am)"/><rect x="26" y="26" width="12" height="12" rx="1.5" fill="#7a4b00"/>'
          + ''.join(f'<rect x="{x}" y="14" width="2.6" height="6" fill="#ffb84d"/><rect x="{x}" y="44" width="2.6" height="6" fill="#ffb84d"/><rect x="14" y="{x}" width="6" height="2.6" fill="#ffb84d"/><rect x="44" y="{x}" width="6" height="2.6" fill="#ffb84d"/>' for x in (24, 30.7, 37.4))),
 "music": tile("url(#rd)", '<path d="M26 42V20l18-4v22" fill="none" stroke="#fff" stroke-width="3.2" stroke-linejoin="round"/><circle cx="22" cy="42" r="5" fill="#fff"/><circle cx="40" cy="38" r="5" fill="#fff"/>'),
 "video": tile("url(#dk)", f'<circle cx="32" cy="32" r="16" fill="{R}"/><path d="M28 24l12 8-12 8z" fill="#fff"/>'),
 "trash": tile("url(#dk)", '<path d="M21 22h22l-2 24a3 3 0 0 1-3 3H26a3 3 0 0 1-3-3z" fill="#cfd2da"/><rect x="18" y="17" width="28" height="4" rx="2" fill="#cfd2da"/><path d="M28 27v16M36 27v16" stroke="#7b7f8a" stroke-width="2.4" stroke-linecap="round"/>'),
 "disks": tile("url(#dk)", '<rect x="13" y="22" width="38" height="20" rx="4" fill="#d6d8de"/><circle cx="44" cy="32" r="2.4" fill="#2ecc71"/><rect x="18" y="30" width="16" height="3" rx="1.5" fill="#8a8f99"/>'),
 "launchpad": tile("url(#dk)", ''.join(f'<rect x="{x}" y="{y}" width="10" height="10" rx="3" fill="{c}"/>' for x, y, c in [(15,15,R),(27,15,"#ff9f0a"),(39,15,"#30d158"),(15,27,"#64d2ff"),(27,27,"#bf5af2"),(39,27,"#ffd60a"),(15,39,"#ff6482"),(27,39,"#5e5ce6"),(39,39,"#66d4cf")])),
 "logo": '',
}

# LuminaOS logo: four rounded petals with a gradient (original mark)
LOGO = ('<defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ff8fab"/>'
        '<stop offset="1" stop-color="#e3245c"/></linearGradient><linearGradient id="lg2" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffb3c4"/>'
        '<stop offset="1" stop-color="#ff375f"/></linearGradient></defs>'
        '<path d="M31 31H14C8 31 5 27 5 21.5 5 12 12 5 21.5 5 27 5 31 8 31 14z" fill="url(#lg)"/>'
        '<path d="M33 31V14c0-6 4-9 9.5-9C52 5 59 12 59 21.5 59 27 56 31 50 31z" fill="url(#lg2)" opacity=".92"/>'
        '<path d="M33 33h17c6 0 9 4 9 9.5C59 52 52 59 42.5 59 37 59 33 56 33 50z" fill="url(#lg)"/>'
        '<path d="M31 33v17c0 6-4 9-9.5 9C12 59 5 52 5 42.5 5 37 8 33 14 33z" fill="url(#lg2)" opacity=".92"/>')
ICONS["logo"] = LOGO

for name, body in ICONS.items():
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">'
           + (DEFS if name != "logo" else "") + body + "</svg>")
    open(os.path.join(OUT, name + ".svg"), "w").write(svg)
print("wrote", len(ICONS), "icons to", OUT)
