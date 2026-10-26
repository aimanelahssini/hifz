"""Literal Quran translations (Tanzil plain-text), keyed by language code.

"Phonetics" (the transliteration alone) and Arabic (with the transliteration under it) are
not translation files; the others are.
Basmala (ayah 0 in the prompter) reuses the translation of 1:1.
"""

import functools
import os

from .quran import SURAHS

DATA = os.path.join(os.path.dirname(__file__), 'data', 'trans')

# (code, display name, Tanzil file stem)
LANGUAGES = [
    ('ph', 'Phonetics', None),
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
    """Translation for surah/ayah. ayah 0 (basmala) → 1:1. Empty for Phonetics and Arabic."""
    if lang in ('ph', 'ar') or lang not in LANG_CODES:
        return ''
    stem = next(s for c, _, s in LANGUAGES if c == lang)
    if ayah == 0:
        return _by_surah(stem)[1][0]
    rows = _by_surah(stem).get(surah)
    if not rows or ayah < 1 or ayah > len(rows):
        return ''
    return rows[ayah - 1]


def available():
    """Language codes that can be selected (Phonetics and Arabic always; others if the file is present)."""
    out = ['ph', 'ar']
    for code, _, stem in LANGUAGES:
        if stem is None:
            continue
        if os.path.isfile(os.path.join(DATA, f'{stem}.txt')):
            out.append(code)
    return out
