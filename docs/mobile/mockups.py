"""Draws the phone mockups for docs/mobile/PRD.md.  python3 docs/mobile/mockups.py

Drawings of how the apps should look, not screenshots; the card is the desktop card, at a
phone's proportions.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
from illustrations import DEFS, LINES, count, mode_icon, speaker, svg, t, wrap  # noqa: E402

PW, PH = 300, 640          # a phone, about 390x844 points at 0.77


def phone(x, y, body, dark=True, notch='punch'):
    """A phone outline with its screen content (drawn in screen coordinates)."""
    clip = f'screen{x}{y}'
    g = [f'<g transform="translate({x},{y})">',
         f'<rect x="-8" y="-8" width="{PW + 16}" height="{PH + 16}" rx="44" fill="#08090d"/>',
         f'<rect x="-8" y="-8" width="{PW + 16}" height="{PH + 16}" rx="44" fill="none" stroke="#fff" stroke-opacity="0.12"/>',
         f'<clipPath id="{clip}"><rect width="{PW}" height="{PH}" rx="36"/></clipPath>',
         f'<g clip-path="url(#{clip})">',
         f'<rect width="{PW}" height="{PH}" fill="{"#0d0f17" if dark else "#e9edf3"}"/>',
         body,
         '</g>']
    if notch == 'punch':
        g.append(f'<circle cx="{PW / 2}" cy="16" r="6" fill="#000"/>')
    g.append('</g>')
    return ''.join(g)


def status(color='#fff', time='14:05'):
    return (t(26, 22, time, 12, color, 600)
            + f'<rect x="{PW - 50}" y="13" width="22" height="11" rx="3" fill="none" stroke="{color}" stroke-opacity="0.8"/>'
            + f'<rect x="{PW - 48}" y="15" width="15" height="7" rx="1.5" fill="{color}" fill-opacity="0.8"/>')


def phone_card(x, y, w, h, index, size=17, head=10.5, finished=3, audio=False, speed='1×', mode='repeat',
               small=False, close=False):
    """The reading card at any size: header, the current ayah in bold white, the next ones grey."""
    g = [f'<g transform="translate({x},{y})">',
         f'<rect width="{w}" height="{h}" rx="{16 if small else 20}" fill="#101014" fill-opacity="0.88"/>',
         f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="{15.5 if small else 19.5}" fill="none" stroke="#fff" stroke-opacity="0.10"/>']
    hy = 20 if small else 24
    g.append(t(12, hy, '56', head, '#fff', 600, opacity=0.45))
    g.append(t(28, hy, "Al-Wâqi'a", head, '#fff', 600, opacity=0.78))
    where = f'·  {index} / 96' if index else '·  Bismillah'
    g.append(t(28 + 5.6 * 9 + (6 if small else 18), hy, where, head, '#fff', 400, opacity=0.5))
    if not small:
        g.append(f'<path d="M{28 + 5.6 * 9 + 4} {hy - 5}l3 3 3-3" fill="none" stroke="#fff" stroke-opacity="0.45" stroke-width="1.3" stroke-linecap="round"/>')
    right = w - 10
    if close:
        g.append(f'<path d="M{right - 8} {hy - 7}l7 7m0-7l-7 7" stroke="#fff" stroke-opacity="0.55" stroke-width="1.5" stroke-linecap="round"/>')
        right -= 18
    g.append(count(right, hy - 12, finished))          # the pill is 34 wide
    g.append(speaker(right - 56, hy - 8, audio, opacity=1 if audio else 0.45))
    if not small:
        g.append(t(right - 64, hy, speed, head, '#fff', 700, 'end', 0.6))
        g.append(mode_icon(right - 96, hy - 4, mode, opacity=0.55, size=0.9))
    clip = f'pc{x}{y}'.replace('.', '')
    top = hy + (12 if small else 16)
    g.append(f'<clipPath id="{clip}"><rect x="0" y="{top}" width="{w}" height="{h - top}"/></clipPath>')
    g.append(f'<g clip-path="url(#{clip})">')
    yy = top + size + 2
    tones = [1, 0.56, 0.44, 0.33, 0.24]
    chars = int((w - 30) / (size * 0.55))
    for k in range(0, 8):
        i = index + k
        if i >= len(LINES) or yy > h + size:
            break
        for row in wrap(LINES[i], chars):
            g.append(t(14, yy, row, size, '#fff', 700 if k == 0 else 500, opacity=tones[min(k, 4)]))
            yy += size * 1.22
        yy += size * (0.45 if small else 0.62)
    g.append('</g></g>')
    return ''.join(g)


def round_button(cx, cy, r, icon, primary=False):
    fill = '#fff' if primary else 'rgba(255,255,255,0.08)'
    ink = '#111114' if primary else '#fff'
    paths = {
        'up': f'M{cx - 6} {cy + 3}l6-6 6 6',
        'down': f'M{cx - 6} {cy - 3}l6 6 6-6',
        'play': f'M{cx - 5} {cy - 8}v16l13-8z',
        'pause': f'M{cx - 6} {cy - 8}v16M{cx + 6} {cy - 8}v16',
        'minus': f'M{cx - 6} {cy}h12',
        'plus': f'M{cx - 6} {cy}h12M{cx} {cy - 6}v12',
    }
    shape = (f'<path d="{paths[icon]}" fill="{ink}"/>' if icon == 'play' else
             f'<path d="{paths[icon]}" fill="none" stroke="{ink}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>')
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"/>' + shape


def logo(x, y, s):
    return (f'<g transform="translate({x},{y}) scale({s / 128})">'
            '<rect x="8" y="8" width="112" height="112" rx="28" fill="#1d2233"/>'
            '<rect x="28" y="50" width="58" height="11" rx="5.5" fill="#fff"/>'
            '<rect x="28" y="70" width="72" height="9" rx="4.5" fill="#fff" fill-opacity="0.42"/>'
            '<rect x="28" y="87" width="48" height="9" rx="4.5" fill="#fff" fill-opacity="0.22"/>'
            '<circle cx="94" cy="32" r="11" fill="url(#gold)"/></g>')


def main_screen():
    """The app's main screen, the same on both phones."""
    body = [f'<rect width="{PW}" height="340" fill="url(#wall)"/>',
            f'<rect width="{PW}" height="340" fill="url(#fade)"/>',
            status(),
            logo(14, 40, 26), t(46, 58, 'Hifz', 17, '#fff', 700),
            # float and menu
            f'<rect x="{PW - 68}" y="44" width="18" height="14" rx="3" fill="none" stroke="#fff" stroke-width="1.6"/>'
            f'<rect x="{PW - 60}" y="51" width="8" height="5" rx="1" fill="#fff"/>',
            ''.join(f'<circle cx="{PW - 26}" cy="{45 + k * 6}" r="1.8" fill="#fff"/>' for k in range(3)),
            phone_card(12, 78, PW - 24, 330, 4, size=16.5),
            round_button(PW / 2 - 70, 462, 22, 'up'), round_button(PW / 2, 462, 30, 'play', True),
            round_button(PW / 2 + 70, 462, 22, 'down'),
            f'<rect x="{PW / 2 - 62}" y="510" width="124" height="38" rx="19" fill="#fff" fill-opacity="0.06"/>',
            round_button(PW / 2 - 40, 529, 14, 'minus').replace('rgba(255,255,255,0.08)', 'none'),
            t(PW / 2, 534, '1×', 14, '#fff', 700, 'middle'),
            round_button(PW / 2 + 40, 529, 14, 'plus').replace('rgba(255,255,255,0.08)', 'none'),
            t(PW / 2, 606, 'Tap the text for the next ayah · swipe down to go back', 9.5, '#a2a8bb', 400, 'middle', 0.8),
            f'<rect x="{PW / 2 - 50}" y="{PH - 12}" width="100" height="4" rx="2" fill="#fff" fill-opacity="0.6"/>']
    return ''.join(body)


def screens():
    w, h = 1200, 760
    fade = ('<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0.4" stop-color="#0d0f17" stop-opacity="0"/><stop offset="1" stop-color="#0d0f17"/></linearGradient>')
    body = [f'<rect width="{w}" height="{h}" rx="22" fill="#14182a"/>', f'<defs>{fade}</defs>']
    body.append(phone(60, 60, main_screen()))
    # The surah list, opened from the surah's name.
    sheet = [main_screen(), f'<rect width="{PW}" height="{PH}" fill="#000" fill-opacity="0.45"/>',
             f'<rect y="150" width="{PW}" height="{PH - 150}" rx="22" fill="#1b1c22"/>',
             f'<rect x="{PW / 2 - 18}" y="160" width="36" height="4" rx="2" fill="#fff" fill-opacity="0.3"/>',
             f'<rect x="14" y="176" width="{PW - 28}" height="40" rx="12" fill="none" stroke="#e9c46a" stroke-width="1.5"/>',
             t(44, 201, 'Number or name', 13, '#fff', 400, opacity=0.45),
             '<circle cx="28" cy="196" r="5" fill="none" stroke="#fff" stroke-opacity="0.6" stroke-width="1.5"/>',
             t(20, 238, 'Saved', 10, '#a2a8bb', 700)]
    yy = 248
    star = 'M0-6l1.8 3.9 4.2.5-3.1 2.9.9 4.2L0 3.3l-3.8 2.2.9-4.2-3.1-2.9 4.2-.5z'
    rows = [(36, 'Yâ-Sîn', 0, True), (67, 'Al-Moulk', 2, True), None, (54, 'Al-Qamar', 0, False),
            (55, 'Ar-Rahmân', 1, False), (56, "Al-Wâqi'a", 3, False), (57, 'Al-Hadîd', 0, False),
            (58, 'Al-Moujâdala', 0, False), (59, 'Al-Hachr', 0, False), (60, 'Al-Moumtahana', 0, False)]
    for r in rows:
        if r is None:
            sheet.append(t(20, yy + 14, 'All surahs', 10, '#a2a8bb', 700))
            yy += 24
            continue
        n, name, done, saved = r
        if n == 56:
            sheet.append(f'<rect x="10" y="{yy}" width="{PW - 20}" height="34" rx="10" fill="#e9c46a" fill-opacity="0.16"/>')
        sheet.append(t(42, yy + 22, str(n), 12.5, '#fff', 600, 'end', 0.45))
        sheet.append(t(54, yy + 22, name, 13.5, '#7ee2a8' if done else '#fff', 700 if n == 56 else 400))
        if done:
            sheet.append(t(PW - 56, yy + 22, f'✓{done}', 11.5, '#fff', 400, 'end', 0.45))
        sheet.append(f'<path transform="translate({PW - 30},{yy + 17})" d="{star}" '
                     + ('fill="#e9c46a"/>' if saved else 'fill="none" stroke="#fff" stroke-opacity="0.3" stroke-width="1.3"/>'))
        yy += 36
    body.append(phone(450, 60, ''.join(sheet)))
    # The finish question on the phone.
    ask = [main_screen().replace(phone_card(12, 78, PW - 24, 330, 4, size=16.5), ''),
           f'<g filter="url(#blur)" opacity="0.5">{phone_card(12, 78, PW - 24, 330, 93, size=16.5)}</g>',
           f'<rect x="12" y="78" width="{PW - 24}" height="330" rx="20" fill="#0a0a0e" fill-opacity="0.45"/>',
           t(PW / 2, 214, "Finished Al-Wâqi'a?", 17, '#fff', 600, 'middle'),
           t(PW / 2, 236, 'Finished 3 times so far', 11.5, '#fff', 400, 'middle', 0.6),
           t(PW / 2, 254, 'Then 57 Al-Hadîd', 11, '#e9c46a', 400, 'middle', 0.9),
           f'<rect x="{PW / 2 - 116}" y="272" width="88" height="36" rx="18" fill="#fff" fill-opacity="0.13"/>',
           t(PW / 2 - 72, 295, 'Not yet', 13.5, '#fff', 600, 'middle'),
           f'<rect x="{PW / 2 - 18}" y="272" width="134" height="36" rx="18" fill="#fff"/>',
           t(PW / 2 + 49, 295, 'Yes, I finished', 13.5, '#111114', 600, 'middle')]
    body.append(phone(840, 60, ''.join(ask)))
    for k, label in enumerate(['Reading', 'Every surah', 'Finished?']):
        body.append(t(60 + PW / 2 + k * 390, 742, label, 15, '#fff', 600, 'middle', 0.8))
    return svg(w, h, ''.join(body), 'Three phone screens: the main reading screen with the card and the '
               'play controls, the surah list with saved and finished surahs, and the finish question '
               'over the blurred card.')


def android():
    w, h = 1200, 760
    body = [f'<rect width="{w}" height="{h}" rx="22" fill="#14182a"/>']
    # Floating over another app (a chat), dragged anywhere, with its own close button.
    chat = [status('#1f1f24'), f'<rect y="34" width="{PW}" height="52" fill="#dfe5ee"/>',
            '<circle cx="34" cy="60" r="14" fill="#b9c4d4"/>', t(56, 65, 'Family', 14, '#1f1f24', 700)]
    yy = 230
    for k, (wid, mine) in enumerate([(170, False), (120, True), (200, False), (90, True), (150, False), (180, True)]):
        x = PW - wid - 14 if mine else 14
        chat.append(f'<rect x="{x}" y="{yy}" width="{wid}" height="34" rx="14" fill="{"#c7e3d4" if mine else "#fff"}"/>')
        yy += 50
    chat.append(phone_card(PW - 262, 96, 250, 128, 4, size=13.5, head=9, small=True, close=True))
    body.append(phone(60, 60, ''.join(chat), dark=False))
    body.append(t(60 + PW / 2, 742, 'Floating over other apps', 15, '#fff', 600, 'middle', 0.8))
    # The lock screen: the ayah being recited, with controls.
    lock = [f'<rect width="{PW}" height="{PH}" fill="url(#wall)"/>', status(),
            t(PW / 2, 130, '22:05', 60, '#fff', 300, 'middle'),
            t(PW / 2, 156, 'Sunday 26 October', 13, '#fff', 400, 'middle', 0.8),
            f'<rect x="14" y="200" width="{PW - 28}" height="132" rx="22" fill="#101014" fill-opacity="0.75"/>',
            logo(28, 214, 42), t(80, 230, "56 Al-Wâqi'a · 4/96", 11, '#fff', 500, opacity=0.6),
            t(80, 250, 'Idhâ roujjati-l-ardou rajjâ', 14, '#fff', 700),
            f'<rect x="28" y="276" width="{PW - 56}" height="3" rx="1.5" fill="#fff" fill-opacity="0.2"/>',
            '<rect x="28" y="276" width="120" height="3" rx="1.5" fill="#fff"/>',
            round_button(PW / 2 - 60, 306, 14, 'up').replace('rgba(255,255,255,0.08)', 'none'),
            round_button(PW / 2, 306, 16, 'pause').replace('rgba(255,255,255,0.08)', 'none'),
            round_button(PW / 2 + 60, 306, 14, 'down').replace('rgba(255,255,255,0.08)', 'none')]
    body.append(phone(450, 60, ''.join(lock)))
    body.append(t(450 + PW / 2, 742, 'Lock screen while reciting', 15, '#fff', 600, 'middle', 0.8))
    # The evening reminder.
    note = [f'<rect width="{PW}" height="{PH}" fill="url(#wall)"/>', status(),
            t(PW / 2, 130, '22:00', 60, '#fff', 300, 'middle'),
            t(PW / 2, 156, 'Sunday 26 October', 13, '#fff', 400, 'middle', 0.8),
            f'<rect x="12" y="200" width="{PW - 24}" height="118" rx="22" fill="#1b1c22" fill-opacity="0.92"/>',
            logo(24, 214, 30), t(62, 226, 'Hifz · now', 11, '#fff', 500, opacity=0.6),
            t(62, 248, "Time for Al-Wâqi'a", 14.5, '#fff', 700),
            t(62, 267, "Recite Al-Wâqi'a before you sleep.", 12, '#fff', 400, opacity=0.75),
            f'<rect x="24" y="280" width="{PW - 48}" height="28" rx="14" fill="#fff" fill-opacity="0.1"/>',
            t(PW / 2, 298, 'Recite now', 12, '#fff', 600, 'middle')]
    body.append(phone(840, 60, ''.join(note)))
    body.append(t(840 + PW / 2, 742, 'The 22:00 reminder', 15, '#fff', 600, 'middle', 0.8))
    return svg(w, h, ''.join(body), 'Android: the small card floating over a chat app with its close '
               'button; the lock screen showing the ayah being recited with previous, pause and next; '
               'and the 22:00 reminder notification with a Recite now button.')


def island(cx, y, kind):
    """The Dynamic Island: compact (a pill) or expanded (a large rounded card)."""
    if kind == 'compact':
        w = 220
        return (f'<rect x="{cx - w / 2}" y="{y}" width="{w}" height="36" rx="18" fill="#000"/>'
                + logo(cx - w / 2 + 6, y + 6, 24)
                + t(cx + w / 2 - 44, y + 23, '56 · 4/96', 11, '#fff', 600, 'end', 0.9)
                + f'<circle cx="{cx + w / 2 - 22}" cy="{y + 18}" r="9" fill="none" stroke="#fff" stroke-opacity="0.2" stroke-width="3"/>'
                + f'<path d="M{cx + w / 2 - 22} {y + 9}a9 9 0 0 1 8.6 11.6" fill="none" stroke="#e9c46a" stroke-width="3" stroke-linecap="round"/>')
    w = PW - 20
    x = cx - w / 2
    return (f'<rect x="{x}" y="{y}" width="{w}" height="176" rx="40" fill="#000"/>'
            + logo(x + 18, y + 16, 26)
            + t(x + 52, y + 33, "56 Al-Wâqi'a · 4/96", 11, '#fff', 500, opacity=0.6)
            + f'<circle cx="{x + w - 30}" cy="{y + 29}" r="9" fill="none" stroke="#fff" stroke-opacity="0.2" stroke-width="3"/>'
            + f'<path d="M{x + w - 30} {y + 20}a9 9 0 0 1 8.6 11.6" fill="none" stroke="#e9c46a" stroke-width="3" stroke-linecap="round"/>'
            + t(x + 20, y + 72, 'Idhâ roujjati-l-ardou rajjâ', 17, '#fff', 700)
            + t(x + 20, y + 98, 'Waboussati-l-jibâlou bassâ', 15, '#fff', 500, opacity=0.5)
            + f'<rect x="{x + 20}" y="{y + 120}" width="{(w - 52) / 2}" height="40" rx="20" fill="#fff" fill-opacity="0.14"/>'
            + t(x + 20 + (w - 52) / 4, y + 145, 'Pause', 13, '#fff', 700, 'middle')
            + f'<rect x="{x + 32 + (w - 52) / 2}" y="{y + 120}" width="{(w - 52) / 2}" height="40" rx="20" fill="#fff"/>'
            + t(x + 32 + (w - 52) * 0.75, y + 145, 'Next ayah', 13, '#111114', 700, 'middle'))


def ios():
    w, h = 1200, 760
    body = [f'<rect width="{w}" height="{h}" rx="22" fill="#14182a"/>']
    # Compact island over another app.
    other = [f'<rect width="{PW}" height="{PH}" fill="#f2f2f7"/>',
             island(PW / 2, 10, 'compact'), t(22, 96, 'Notes', 26, '#1f1f24', 700)]
    for k in range(9):
        other.append(f'<rect x="22" y="{124 + k * 30}" width="{[230, 200, 250, 120, 0, 240, 210, 180, 90][k]}" '
                     'height="8" rx="4" fill="#1f1f24" fill-opacity="0.15"/>')
    body.append(phone(60, 60, ''.join(other), dark=False, notch=None))
    body.append(t(60 + PW / 2, 742, 'Dynamic Island, small', 15, '#fff', 600, 'middle', 0.8))
    # Expanded island (long-press).
    exp = [f'<rect width="{PW}" height="{PH}" fill="#f2f2f7"/>',
           island(PW / 2, 10, 'expanded'), t(22, 232, 'Notes', 26, '#1f1f24', 700)]
    body.append(phone(450, 60, ''.join(exp), dark=False, notch=None))
    body.append(t(450 + PW / 2, 742, 'Dynamic Island, open', 15, '#fff', 600, 'middle', 0.8))
    # Lock screen Live Activity.
    lock = [f'<rect width="{PW}" height="{PH}" fill="url(#wall)"/>', t(PW / 2, 130, '22:05', 64, '#fff', 300, 'middle'),
            t(PW / 2, 156, 'Sunday 26 October', 13, '#fff', 400, 'middle', 0.8),
            f'<rect x="12" y="{PH - 230}" width="{PW - 24}" height="150" rx="26" fill="#101014" fill-opacity="0.72"/>',
            logo(28, PH - 216, 26), t(62, PH - 198, "56 Al-Wâqi'a · 4/96", 11, '#fff', 500, opacity=0.6),
            count(PW - 30, PH - 212, 3),
            t(28, PH - 160, 'Idhâ roujjati-l-ardou rajjâ', 17, '#fff', 700),
            t(28, PH - 136, 'Waboussati-l-jibâlou bassâ', 15, '#fff', 500, opacity=0.5),
            f'<rect x="28" y="{PH - 118}" width="{(PW - 70) / 2}" height="30" rx="15" fill="#fff" fill-opacity="0.14"/>',
            t(28 + (PW - 70) / 4, PH - 98, 'Pause', 12.5, '#fff', 700, 'middle'),
            f'<rect x="{42 + (PW - 70) / 2}" y="{PH - 118}" width="{(PW - 70) / 2}" height="30" rx="15" fill="#fff"/>',
            t(42 + (PW - 70) * 0.75, PH - 98, 'Next ayah', 12.5, '#111114', 700, 'middle')]
    body.append(phone(840, 60, ''.join(lock), notch=None))
    body.append(t(840 + PW / 2, 742, 'Lock screen', 15, '#fff', 600, 'middle', 0.8))
    return svg(w, h, ''.join(body), 'iPhone: the Dynamic Island small (surah, ayah and a progress ring), '
               'open with the ayah, the next one, Pause and Next ayah, and the lock screen card with the '
               'same.')


def main():
    for name, fn in (('screens', screens), ('android', android), ('iphone', ios)):
        with open(os.path.join(HERE, f'{name}.svg'), 'w', encoding='utf-8') as f:
            f.write(fn())


if __name__ == '__main__':
    main()
