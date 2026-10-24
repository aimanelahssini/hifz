"""Draws the SVG illustrations in docs/ and the website's sample text (site/waqia.json).  python3 docs/illustrations.py

They are drawings of the product, not screenshots: the same card as the app, at the same
proportions, with the real phonetic text of Al-Wâqi'a.
"""

import os
import sys
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from hifz import quran  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SANS = "Inter, 'Adwaita Sans', Cantarell, 'Segoe UI', system-ui, sans-serif"
MONO = "'Adwaita Mono', 'JetBrains Mono', 'DejaVu Sans Mono', monospace"
W, H = 440, 212
LINES = [line.phonetic for line in quran.lines(56)]

DEFS = f"""
<defs>
  <linearGradient id="wall" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#1e2a4a"/>
    <stop offset="0.55" stop-color="#284b63"/>
    <stop offset="1" stop-color="#3b6e6a"/>
  </linearGradient>
  <radialGradient id="glow" cx="0.78" cy="0.18" r="0.6">
    <stop offset="0" stop-color="#f6d98b" stop-opacity="0.22"/>
    <stop offset="1" stop-color="#f6d98b" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#f6d98b"/>
    <stop offset="1" stop-color="#d9a441"/>
  </linearGradient>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="160%">
    <feDropShadow dx="0" dy="10" stdDeviation="14" flood-color="#000" flood-opacity="0.35"/>
  </filter>
  <filter id="blur" x="-5%" y="-20%" width="110%" height="140%">
    <feGaussianBlur stdDeviation="5"/>
  </filter>
  <style>
    text {{ font-family: {SANS}; }}
    .mono {{ font-family: {MONO}; }}
  </style>
</defs>
"""


def svg(width, height, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">'
            f'<title>{escape(title)}</title>{DEFS}{body}</svg>\n')


def t(x, y, s, size=14, fill='#fff', weight=400, anchor='start', opacity=1, cls=''):
    c = f' class="{cls}" xml:space="preserve"' if cls else ''
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'fill-opacity="{opacity}" text-anchor="{anchor}"{c}>{escape(s)}</text>')


def speaker(x, y, on, color='#fff', opacity=0.5):
    # A small speaker icon, 14 px, with waves when on and a cross when muted.
    g = (f'<g transform="translate({x},{y})" fill="{color}" fill-opacity="{opacity}" '
         f'stroke="{color}" stroke-opacity="{opacity}">'
         '<path d="M0 4.5h3l4-3.5v12l-4-3.5H0z" stroke="none"/>')
    if on:
        g += ('<path d="M9.2 4.2a3.6 3.6 0 0 1 0 5.6M11.2 2.2a6.4 6.4 0 0 1 0 9.6" fill="none" '
              'stroke-width="1.5" stroke-linecap="round"/>')
    else:
        g += '<path d="M9.5 4.5l4 4m0-4l-4 4" fill="none" stroke-width="1.5" stroke-linecap="round"/>'
    return g + '</g>'


def count(x, y, n, bump=False):
    """The finished-count pill; x is its right edge."""
    w = 34 + 7 * (len(str(n)) - 1)
    fill = '#78dca0' if bump else '#ffffff'
    op = 0.32 if bump else 0.08
    color = '#ffffff' if bump or n else '#ffffff'
    tone = 1 if bump else (0.62 if n else 0.34)
    return (f'<rect x="{x - w}" y="{y}" width="{w}" height="17" rx="8.5" fill="{fill}" fill-opacity="{op}"/>'
            f'<path d="M{x - w + 7} {y + 8.8}l2.6 2.6 4.6-5" fill="none" stroke="{color}" '
            f'stroke-opacity="{tone}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
            + t(x - 9, y + 12.6, str(n), 11, color, 700, 'end', tone))


def card(x, y, index=4, finished=3, audio=False, blur=False, surah="Al-Wâqi'a", lines=None,
         total=96, scale=1.0, shadow=True, offset=0.0):
    """The Hifz card at (x, y). index: the current line (0 = basmala). offset: 0..1 of a slide."""
    lines = lines or LINES
    g = [f'<g transform="translate({x},{y}) scale({scale})">']
    g.append(f'<rect width="{W}" height="{H}" rx="18" fill="#101014" fill-opacity="0.80"'
             f'{" filter=" + chr(34) + "url(#shadow)" + chr(34) if shadow else ""}/>')
    g.append(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="17.5" fill="none" '
             'stroke="#fff" stroke-opacity="0.10"/>')
    inner = []
    where = f'·  {index} / {total}' if index else '·  Bismillah'
    inner.append(t(16, 19.5, surah, 11, '#fff', 600, opacity=0.74))
    inner.append(t(16 + 6.4 * len(surah) + 10, 19.5, where, 11, '#fff', 400, opacity=0.5))
    inner.append(speaker(W - 66, 12.5, audio, opacity=1 if audio else 0.45))
    inner.append(count(W - 12, 11, finished))
    # The lines: current one white, the next ones grey and fading. Long ones wrap.
    tones = [1, 0.56, 0.44, 0.33, 0.24]
    clip = f'clip{x}{y}'.replace('.', '')
    g.append(f'<clipPath id="{clip}"><rect x="0" y="36" width="{W}" height="{H - 36}"/></clipPath>')
    body = [f'<g clip-path="url(#{clip})">']
    yy = 66
    for k in range(0, 6):
        i = index + k
        if not 0 <= i < len(lines):
            continue
        tone = tones[min(k, 4)]
        for row in wrap(lines[i]):
            body.append(t(18, yy, row, 19, '#fff', 500, opacity=tone))
            yy += 23
        yy += 12
    body.append('</g>')
    if blur:
        inner = [f'<g filter="url(#blur)" opacity="0.55">'] + inner + body + ['</g>']
    else:
        inner += body
    g += inner
    g.append('</g>')
    return ''.join(g)


def wrap(s, width=37):
    """Break a line where the app would (spaces and hyphens), about 400 px at 19 px."""
    rows, cur = [], ''
    for part in s.replace('-', '-\0').replace(' ', ' \0').split('\0'):
        if len(cur) + len(part.rstrip()) > width and cur:
            rows.append(cur.rstrip())
            cur = ''
        cur += part
    if cur:
        rows.append(cur.rstrip())
    return rows


def finish_overlay(x, y, surah="Al-Wâqi'a", n=3):
    g = [f'<g transform="translate({x},{y})">',
         f'<rect width="{W}" height="{H}" rx="18" fill="#0a0a0e" fill-opacity="0.30"/>',
         t(W / 2, 92, f'Finished {surah}?', 17, '#fff', 600, 'middle'),
         t(W / 2, 114, f'Finished {n} times so far', 12, '#fff', 400, 'middle', 0.6),
         '<rect x="104" y="132" width="92" height="34" rx="17" fill="#fff" fill-opacity="0.12"/>',
         t(150, 154, 'Not yet', 14, '#fff', 600, 'middle'),
         '<rect x="206" y="132" width="132" height="34" rx="17" fill="#fff"/>',
         t(272, 154, 'Yes, I finished', 14, '#111114', 600, 'middle'),
         '</g>']
    return ''.join(g)


def keycap(x, y, label, w=96, pressed=False):
    dy = 2 if pressed else 0
    return (f'<g transform="translate({x},{y})">'
            f'<rect x="0" y="4" width="{w}" height="40" rx="9" fill="#000" fill-opacity="0.35"/>'
            f'<rect x="0" y="{dy}" width="{w}" height="40" rx="9" fill="#f4f4f6"/>'
            f'<rect x="0.5" y="{dy + 0.5}" width="{w - 1}" height="39" rx="8.5" fill="none" stroke="#000" stroke-opacity="0.08"/>'
            + t(w / 2, 26 + dy, label, 14, '#2a2a33', 600, 'middle') + '</g>')


def desktop(width, height, clock='Fri 24 Oct  14:05'):
    """A plain GNOME-like desktop: wallpaper, top bar and a light window."""
    g = [f'<rect width="{width}" height="{height}" fill="url(#wall)"/>',
         f'<rect width="{width}" height="{height}" fill="url(#glow)"/>',
         f'<rect width="{width}" height="28" fill="#000"/>',
         '<rect x="14" y="10" width="26" height="8" rx="4" fill="#fff"/>',
         '<circle cx="50" cy="14" r="3" fill="#fff" fill-opacity="0.5"/>',
         t(width / 2, 19, clock, 13, '#fff', 700, 'middle'),
         f'<circle cx="{width - 44}" cy="14" r="4" fill="none" stroke="#fff" stroke-width="2"/>',
         f'<rect x="{width - 30}" y="9" width="8" height="11" rx="2" fill="none" stroke="#fff" stroke-width="2"/>']
    return ''.join(g)


def doc_window(x, y, w, h):
    g = [f'<g transform="translate({x},{y})" filter="url(#shadow)">',
         f'<rect width="{w}" height="{h}" rx="12" fill="#fafafb"/>',
         f'<path d="M0 12a12 12 0 0 1 12-12h{w - 24}a12 12 0 0 1 12 12v34H0z" fill="#ebebed"/>',
         t(w / 2, 28, 'Notes', 13, '#1f1f24', 700, 'middle'),
         f'<circle cx="{w - 24}" cy="23" r="9" fill="#000" fill-opacity="0.06"/>']
    yy = 84
    widths = [0.55, 0.92, 0.86, 0.64, 0, 0.9, 0.8, 0.88, 0.4, 0, 0.94, 0.7, 0.83, 0.6]
    for k, f in enumerate(widths):
        if yy > h - 30:
            break
        if f:
            g.append(f'<rect x="48" y="{yy}" width="{(w - 96) * f:.0f}" height="9" rx="4.5" '
                     f'fill="#1f1f24" fill-opacity="{0.55 if k == 0 else 0.16}"/>')
        yy += 24
    g.append('</g>')
    return ''.join(g)


def hero():
    w, h = 1200, 640
    body = desktop(w, h)
    body += doc_window(90, 92, 640, 500)
    cx, cy = w - W - 26, 44
    body += card(cx, cy, index=4, finished=3)
    # Space: the text slides up one line.
    body += keycap(cx + W - 120, cy + H + 40, 'Space', 120, pressed=True)
    body += (f'<path d="M{cx + W - 60} {cy + H + 30}v-14" stroke="#fff" stroke-opacity="0.85" '
             'stroke-width="2.5" stroke-linecap="round"/>'
             f'<path d="M{cx + W - 66} {cy + H + 20}l6-7 6 7" fill="none" stroke="#fff" '
             'stroke-opacity="0.85" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>')
    body += t(cx + W - 132, cy + H + 66, 'next ayah', 13, '#fff', 500, 'end', 0.8)
    return svg(w, h, body, 'Hifz on a GNOME desktop: a small card in the top-right corner '
               'shows the current ayah in white and the next ones in grey, above a notes window.')


def slide():
    w, h = 1200, 330
    body = f'<rect width="{w}" height="{h}" rx="22" fill="url(#wall)"/>'
    body += card(40, 58, index=3, finished=3)
    body += card(720, 58, index=4, finished=3)
    body += keycap(540, 122, 'Space', 120, pressed=True)
    body += ('<path d="M512 234h176" stroke="#fff" stroke-opacity="0.6" stroke-width="2" '
             'stroke-dasharray="2 7" stroke-linecap="round"/>'
             '<path d="M680 228l9 6-9 6" fill="none" stroke="#fff" stroke-opacity="0.6" '
             'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>')
    body += t(600, 200, 'slides up one line', 13, '#fff', 500, 'middle', 0.75)
    return svg(w, h, body, 'Pressing Space slides the text up by one ayah: the next ayah '
               'becomes white at the top and the following ones stay grey.')


def finish():
    w, h = 1200, 330
    body = f'<rect width="{w}" height="{h}" rx="22" fill="url(#wall)"/>'
    last = len(LINES) - 1
    body += card(40, 58, index=last, finished=3, blur=True)
    body += finish_overlay(40, 58)
    body += card(720, 58, index=0, finished=4)
    body += ('<rect x="0" y="0" width="0" height="0"/>')
    # The bumped counter on the right card.
    body += f'<g transform="translate({720},{58})">' + count(W - 12, 11, 4, bump=True) + '</g>'
    body += ('<path d="M512 165h176" stroke="#fff" stroke-opacity="0.6" stroke-width="2" '
             'stroke-dasharray="2 7" stroke-linecap="round"/>'
             '<path d="M680 159l9 6-9 6" fill="none" stroke="#fff" stroke-opacity="0.6" '
             'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>')
    body += t(600, 150, 'Yes, I finished', 13, '#fff', 500, 'middle', 0.75)
    body += t(600, 190, '3 → 4, back to the start', 12, '#fff', 400, 'middle', 0.55)
    return svg(w, h, body, 'At the last ayah a question appears over the blurred text: '
               'Finished Al-Wâqi\'a? Yes adds one to the counter in the top-right corner and '
               'goes back to the start.')


def menu():
    w, h = 1200, 640
    body = f'<rect width="{w}" height="{h}" rx="22" fill="url(#wall)"/>'
    cx, cy = 60, 60
    body += card(cx, cy, index=7, finished=3, audio=True)
    mx, my = cx + 300, cy + 96
    items = ['0.5×', '0.75×', '1×', '1.1×', '1.25×', '1.5×', '1.75×', '2×']
    mh = 34 + len(items) * 30 + 12 + 4 * 30 + 12 + 2 * 30 + 10
    g = [f'<g transform="translate({mx},{my})" filter="url(#shadow)">',
         f'<rect width="300" height="{mh}" rx="12" fill="#2b2b31"/>',
         f'<rect x="0.5" y="0.5" width="299" height="{mh - 1}" rx="11.5" fill="none" stroke="#fff" stroke-opacity="0.08"/>',
         t(36, 26, 'Speed', 13, '#fff', 700, opacity=0.55)]
    yy = 34
    for s in items:
        sel = s == '1.25×'
        if sel:
            g.append(f'<rect x="6" y="{yy}" width="288" height="30" rx="7" fill="#fff" fill-opacity="0.10"/>')
        g.append(f'<circle cx="24" cy="{yy + 15}" r="7" fill="none" stroke="#fff" stroke-opacity="0.6" stroke-width="1.5"/>')
        if sel:
            g.append(f'<circle cx="24" cy="{yy + 15}" r="3.5" fill="#fff"/>')
        g.append(t(42, yy + 20, s, 14, '#fff', 400, opacity=0.92))
        yy += 30
    g.append(f'<rect x="10" y="{yy + 5}" width="280" height="1" fill="#fff" fill-opacity="0.10"/>')
    yy += 12
    for label, check, sub in (('Recitation', True, False), ('Reciter', False, True),
                              ('Continue automatically', False, False), ('Show Arabic', False, False)):
        if check:
            g.append(f'<path d="M17 {yy + 15}l4 4 8-9" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>')
        g.append(t(42, yy + 20, label, 14, '#fff', 400, opacity=0.92))
        if sub:
            g.append(f'<path d="M278 {yy + 9}l5 6-5 6" fill="none" stroke="#fff" stroke-opacity="0.6" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>')
        yy += 30
    g.append(f'<rect x="10" y="{yy + 5}" width="280" height="1" fill="#fff" fill-opacity="0.10"/>')
    yy += 12
    for label in ('Back to the beginning', 'Close'):
        g.append(t(42, yy + 20, label, 14, '#fff', 400, opacity=0.92))
        yy += 30
    g.append('</g>')
    body += ''.join(g)
    # Pointer.
    px, py = mx - 4, my - 6
    body += (f'<path d="M{px} {py}l0 17 4.5-4 3 6.5 3-1.4-3-6.4 6-.2z" fill="#fff" stroke="#000" '
             'stroke-width="1.2" stroke-linejoin="round"/>')
    body += t(cx + 4, cy + H + 36, 'Right-click for speed,', 13, '#fff', 500, opacity=0.75)
    body += t(cx + 4, cy + H + 56, 'reciter and options', 13, '#fff', 500, opacity=0.75)
    # The recitation follows the line.
    body += t(760, 150, 'The recitation follows your line', 22, '#fff', 700)
    body += t(760, 180, 'Turn the sound on and the current ayah', 15, '#fff', 400, opacity=0.75)
    body += t(760, 202, 'is recited when it reaches the top.', 15, '#fff', 400, opacity=0.75)
    body += t(760, 234, 'Muted by default: no sound stream at all.', 15, '#fff', 400, opacity=0.75)
    bars = [6, 14, 22, 12, 26, 18, 9, 20, 28, 15, 7, 17, 24, 11, 5, 13, 21, 10, 6]
    for k, b in enumerate(bars):
        body += (f'<rect x="{760 + k * 12}" y="{292 - b}" width="6" height="{2 * b}" rx="3" '
                 f'fill="url(#gold)" fill-opacity="{0.95 if k < 11 else 0.35}"/>')
    body += t(760, 350, '0.5×  0.75×  1×  1.1×  1.25×  1.5×  1.75×  2×', 14, '#fff', 500, opacity=0.6)
    body += t(760, 372, 'same pitch at every speed', 13, '#fff', 400, opacity=0.5)
    return svg(w, h, body, 'The right-click menu: speeds from 0.5× to 2×, Recitation, Reciter, '
               'Continue automatically, Show Arabic, Back to the beginning and Close.')


def terminal():
    w, h = 1200, 470
    body = f'<rect width="{w}" height="{h}" rx="22" fill="url(#wall)"/>'
    tx, ty, tw, th = 60, 50, 720, 370
    g = [f'<g transform="translate({tx},{ty})" filter="url(#shadow)">',
         f'<rect width="{tw}" height="{th}" rx="12" fill="#1d1d22"/>',
         f'<path d="M0 12a12 12 0 0 1 12-12h{tw - 24}a12 12 0 0 1 12 12v28H0z" fill="#2a2a30"/>',
         t(tw / 2, 25, 'Terminal', 13, '#fff', 700, 'middle', 0.85),
         '</g>']
    rows = [
        ('$ quran', 1, 700),
        ('', 0, 400),
    ]
    names = [(n, quran.name(n)) for n in range(1, 115)]
    col = [names[0:4], names[38:42], names[76:80]]
    for r in range(4):
        rows.append(('   '.join(f'{n:3}  {nm:<16}' for n, nm in (col[0][r], col[1][r], col[2][r])), 0.85, 400))
    rows.append(('', 0, 400))
    rows.append(('  ⋮', 0.5, 400))
    for r in (55, 56):
        rows.append(None)
    out = []
    yy = ty + 66
    for row in rows:
        if row is None:
            continue
        s, op, wt = row
        if s:
            out.append(t(tx + 22, yy, s, 13, '#e8e8ec', wt, opacity=op or 0.85, cls='mono'))
        yy += 21
    # The rows around Al-Wâqi'a, with the last one highlighted.
    for n in (55, 56, 57):
        hl = n == 56
        s = f'{n:3}  {quran.name(n)}' + ('  ✓3' if hl else '')
        out.append(t(tx + 22, yy, s, 13, '#7ee2a8' if hl else '#e8e8ec', 700 if hl else 400,
                     opacity=1 if hl else 0.85, cls='mono'))
        yy += 21
    yy += 12
    out.append(t(tx + 22, yy, "Surah number (Enter = 56 Al-Wâqi'a): 56", 13, '#e8e8ec', 400, cls='mono'))
    yy += 21
    out.append(t(tx + 22, yy, "Opening Al-Wâqi'a. You can close this terminal.", 13, '#e8e8ec', 400, opacity=0.7, cls='mono'))
    body += ''.join(g) + ''.join(out)
    body += card(w - W - 40, 40, index=0, finished=3, scale=0.82)
    body += t(w - 40 - W * 0.82 / 2, 40 + H * 0.82 + 34, 'stays open after the terminal closes', 13, '#fff', 500, 'middle', 0.75)
    return svg(w, h, body, "The quran command lists the 114 surahs with their numbers; typing 56 "
               "opens Al-Wâqi'a in the corner, and the terminal can be closed.")


def main():
    # The website's "try it" card uses the same lines.
    import json
    with open(os.path.join(HERE, '..', 'site', 'waqia.json'), 'w', encoding='utf-8') as f:
        json.dump(LINES, f, ensure_ascii=False)
    for name, fn in (('hero', hero), ('slide', slide), ('finish', finish), ('menu', menu),
                     ('terminal', terminal)):
        with open(os.path.join(HERE, f'{name}.svg'), 'w', encoding='utf-8') as f:
            f.write(fn())


if __name__ == '__main__':
    main()
