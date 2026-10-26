"""Literal Quran translations (Tanzil plain-text), keyed by language code.

Arabic is the Uthmani text in quran.py — not listed as a translation file here.
Basmala (ayah 0 in the prompter) reuses the translation of 1:1.
"""

import functools
import os

from .quran import SURAHS

DATA = os.path.join(os.path.dirname(__file__), 'data', 'trans')

# (code, display name, Tanzil file stem)
LANGUAGES = [
    ('ar', 'Arabic', None),
    ('en', 'English', 'en.sahih'),
    ('fr', 'French', 'fr.hamidullah'),
    ('tr', 'Turkish', 'tr.diyanet'),
    ('id', 'Indonesian', 'id.indonesian'),
    ('es', 'Spanish', 'es.cortes'),
]

LANG_CODES = tuple(c for c, _, _ in LANGUAGES)
LANG_LABELS = {c: label for c, label, _ in LANGUAGES}


@functools.lru_cache(maxsize=8)
def _flat(stem):
    path = os.path.join(DATA, f'{stem}.txt')
    out = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            out.append(line.rstrip('\n'))
    if len(out) != 6236:
        raise RuntimeError(f'{stem}: expected 6236 ayahs, got {len(out)}')
    return out


@functools.lru_cache(maxsize=8)
def _by_surah(stem):
    flat = _flat(stem)
    i = 0
    by = {}
    for n, (_, count) in enumerate(SURAHS, 1):
        by[n] = flat[i:i + count]
        i += count
    return by


def text(lang, surah, ayah):
    """Translation for surah/ayah. ayah 0 (basmala) → 1:1. Empty if lang is Arabic."""
    if lang == 'ar' or lang not in LANG_CODES:
        return ''
    stem = next(s for c, _, s in LANGUAGES if c == lang)
    if ayah == 0:
        return _by_surah(stem)[1][0]
    rows = _by_surah(stem).get(surah)
    if not rows or ayah < 1 or ayah > len(rows):
        return ''
    return rows[ayah - 1]


def available():
    """Language codes that can be selected (Arabic always; others if the file is present)."""
    out = ['ar']
    for code, _, stem in LANGUAGES:
        if code == 'ar':
            continue
        if os.path.isfile(os.path.join(DATA, f'{stem}.txt')):
            out.append(code)
    return out
