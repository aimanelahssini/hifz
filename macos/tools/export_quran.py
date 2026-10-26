#!/usr/bin/env python3
"""Export the Quran text (Arabic + French phonetics) as quran.json for the macOS app.

Uses the same hifz.quran.lines() as the Linux app, so the phonetics match byte for byte.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

from hifz import quran  # noqa: E402


def main():
    out = os.environ.get('HIFZ_QURAN_JSON') or os.path.join(
        HERE, '..', 'Hifz', 'Resources', 'quran.json')
    surahs = []
    for n in range(1, 115):
        name, ayahs = quran.SURAHS[n - 1]
        lines = [
            {'ayah': line.ayah, 'arabic': line.arabic, 'phonetic': line.phonetic}
            for line in quran.lines(n)
        ]
        surahs.append({'number': n, 'name': name, 'ayahs': ayahs, 'lines': lines})
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({'version': 1, 'surahs': surahs}, f, ensure_ascii=False, separators=(',', ':'))
    print(f'Wrote {len(surahs)} surahs to {out}', file=sys.stderr)


if __name__ == '__main__':
    main()
