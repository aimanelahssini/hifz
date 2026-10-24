"""French-style phonetic transcription of the Uthmani Quran text (Tanzil edition).

The output is written the way French phonetic Qurans write Arabic: "ou" for the u sound,
"ch" for sh, â/î/oû for long vowels, ' for hamza and ʿayn, and the article joined with
hyphens (waqa'ati-l-wâqi'ah, bismi-llâhi-r-rahmâni-r-rahîm). It follows what a reciter
actually says: the alif wasla is dropped inside a sentence, sun letters and idghâm are
assimilated (khâfidatour-râfi'ah), iqlâb turns n into m, and the last word of an ayah is
read in its pausal form (ta marbuta becomes h, -an becomes -â, final short vowels go).
"""

import re
import unicodedata

FATHA, DAMMA, KASRA = 'َ', 'ُ', 'ِ'
FATHATAN, DAMMATAN, KASRATAN = 'ً', 'ٌ', 'ٍ'
SHADDA, SUKUN, SUKUN2 = 'ّ', 'ْ', 'ۡ'
MADDA, HAMZA_ABOVE, DAGGER = 'ٓ', 'ٔ', 'ٰ'
SILENT = ('۟', '۠')            # small high rounded / rectangular zero
IQLAB = ('ۢ', 'ۭ')             # small high / low meem
SMALL_WAW, SMALL_YEH, SMALL_HIGH_YEH = 'ۥ', 'ۦ', 'ۧ'
SMALL_HIGH_NOON = 'ۨ'
WASLA, TATWEEL = 'ٱ', 'ـ'
ALIF, ALIF_MAQSURA, TA_MARBUTA = 'ا', 'ى', 'ة'
WAW, YA, LAM, NUN, HA = 'و', 'ي', 'ل', 'ن', 'ه'
HAMZAS = 'ءأإؤئ'

CONSONANTS = {
    'ب': 'b', 'ت': 't', 'ث': 'th', 'ج': 'j', 'ح': 'h',
    'خ': 'kh', 'د': 'd', 'ذ': 'dh', 'ر': 'r', 'ز': 'z',
    'س': 's', 'ش': 'ch', 'ص': 's', 'ض': 'd', 'ط': 't',
    'ظ': 'dh', 'ع': "'", 'غ': 'gh', 'ف': 'f', 'ق': 'q',
    'ك': 'k', 'ل': 'l', 'م': 'm', 'ن': 'n', 'ه': 'h',
    'و': 'w', 'ي': 'y', 'ة': 't',
    **{h: "'" for h in HAMZAS},
}
SHORT = {FATHA: 'a', DAMMA: 'ou', KASRA: 'i'}
TANWIN = {FATHATAN: 'a', DAMMATAN: 'ou', KASRATAN: 'i'}
VOWEL_MARKS = set(SHORT) | set(TANWIN)
# Pause signs, sajda, hizb and other marks that are not pronounced.
IGNORED = set('ۖۗۘۙۚۛۜ۝۞ۣ۩۪۫۬')
LETTER_NAMES = {
    'ا': 'alif', 'ل': 'lâm', 'م': 'mîm', 'ر': 'râ', 'ك': 'kâf',
    'ه': 'hâ', 'ي': 'yâ', 'ع': "'ayn", 'ص': 'sâd', 'ط': 'tâ',
    'س': 'sîn', 'ح': 'hâ', 'ق': 'qâf', 'ن': 'noûn',
}
SUN = set('تثدذرزسشصضطظلن')
SHORTEN = {'â': 'a', 'î': 'i', 'oû': 'ou'}


class Unit:
    """One base letter with the marks written on it."""
    __slots__ = ('base', 'marks')

    def __init__(self, base):
        self.base, self.marks = base, ''

    def has(self, *marks):
        return any(m in self.marks for m in marks)

    @property
    def vowel(self):
        for m in self.marks:
            if m in VOWEL_MARKS:
                return m
        return None

    @property
    def bare(self):
        """No vowel, no sukun, no shadda written on it."""
        return not self.has(*VOWEL_MARKS, SHADDA, SUKUN, SUKUN2)

    def __repr__(self):
        return f'{self.base}{self.marks}'


def units(word):
    out = []
    for ch in word:
        if ch in IGNORED:
            continue
        if unicodedata.category(ch) == 'Mn' and out:
            out[-1].marks += ch
        else:
            out.append(Unit(ch))
    return out


def is_allah(us, k):
    """us[k] is the doubled lam of Allah (ٱللَّه, لِلَّه); Tanzil writes it without a dagger alif."""
    return (0 < k and k + 1 < len(us) and us[k].base == LAM and us[k + 1].base == HA
            and us[k - 1].base == LAM and not us[k - 1].has(FATHA, DAMMA, SUKUN)
            and (k + 2 == len(us) or us[k + 2].base == '\u0645'))   # allâhou, allâhoumma


def is_relative(us, k):
    """us[k] is the doubled lam of alladhî, allatî, alladhîna, allâ'î..."""
    return k + 1 < len(us) and us[k + 1].base in ('\u0630', '\u062a', TATWEEL)


def is_muqattaat(us):
    return len(us) > 0 and all(u.base in LETTER_NAMES and not u.has(*VOWEL_MARKS, SHADDA, SUKUN, DAGGER)
                               for u in us)


class Word:
    """A transcribed word, kept in pieces so neighbours can join it (wasl, idghâm)."""

    def __init__(self, us):
        self.us = us
        self.text = ''
        self.wasl = bool(us) and us[0].base == WASLA
        self.article = ''          # 'l', a sun consonant, or 'll' (Allah, alladhî...)


def transcribe_word(us, start, last):
    """Return (text, info) for one word. start: first word of the line. last: last word."""
    w = Word(us)
    out = []                       # list of output chunks
    prev_vowel = None              # the vowel letter of the last output syllable
    i = 0
    n = len(us)
    skip_apostrophe = False

    def put(s, vowel=None):
        nonlocal prev_vowel
        out.append(s)
        prev_vowel = vowel

    def lengthen(v):
        # Turn the vowel just written into a long one.
        if out and prev_vowel in ('a', 'i', 'ou') and out[-1].endswith(prev_vowel):
            out[-1] = out[-1][:-len(prev_vowel)] + {'a': 'â', 'i': 'î', 'ou': 'oû'}[prev_vowel]
            return True
        return False

    if n > 2 and us[0].base == YA and us[0].has(FATHA) and us[1].base == TATWEEL and us[1].has(DAGGER):
        # Vocative yâ written onto the word: yâ ayyouhâ, yâ qawmi.
        put('yâ ', None)
        i = 2
        skip_apostrophe = True

    while i < n:
        u = us[i]
        b = u.base
        nxt = us[i + 1] if i + 1 < n else None

        if u.has(*SILENT):
            # Silent letter; the upright zero is pronounced at a pause (ana -> anâ).
            if u.has(SILENT[1]) and last and i == n - 1 and b == ALIF:
                lengthen('a')
            i += 1
            continue

        if b == WASLA:
            is_article = nxt is not None and nxt.base == LAM and i + 2 < n
            if is_article:
                after = us[i + 2]
                if nxt.has(SHADDA):
                    # One lam with a shadda: the article on a word that starts with l
                    # (al-layl), or the relative pronoun (alladhî, allatî).
                    art = 'll' if is_relative(us, i + 1) else 'l'
                    nxt.marks = nxt.marks.replace(SHADDA, '')
                    i += 1
                elif nxt.bare and after.has(SHADDA):
                    # Sun letter (ar-rahmân), or Allah written with two lams.
                    art = 'll' if after.base == LAM else CONSONANTS[after.base]
                    after.marks = after.marks.replace(SHADDA, '')
                    i += 2
                else:
                    art = 'l'      # moon letter: al-qamar
                    i += 2
                skip_apostrophe = True
                if out:
                    # Prefix + article inside the word: wa-l-ardi, wa-s-sâbiqoûna, wa-llâhou.
                    if prev_vowel in SHORTEN:
                        out[-1] = out[-1][:-len(prev_vowel)] + SHORTEN[prev_vowel]
                    put('-l' if art == 'll' else '-' + art + '-')
                else:
                    w.article = art
                continue
            if not out:
                # Wasl of a verb or noun read at the start of a line: ihdinâ, ismou, ourjou'.
                third = us[i + 2] if i + 2 < n else None
                w.lead = 'ou' if third is not None and third.has(DAMMA) else 'i'
            i += 1                 # inside a word after a prefix it is silent: bismi
            continue

        if b == TATWEEL and u.has(SMALL_HIGH_NOON):
            put('n')               # nounjî (21:88)
            i += 1
            continue
        if b == TATWEEL:
            if u.has(HAMZA_ABOVE):
                b = 'ء'       # hamza written on a tatweel: treat as hamza
            else:
                if u.has(DAGGER):
                    lengthen('a') or put('â', 'â')
                i += 1
                continue

        if b == SMALL_WAW:
            if not (last and i == n - 1):
                lengthen('ou') or put('oû', 'oû')
            i += 1
            continue
        if b in (SMALL_YEH,):
            if not (last and i == n - 1):
                lengthen('i') or put('î', 'î')
            i += 1
            continue

        if b == ALIF and not u.has(*VOWEL_MARKS):
            if prev_vowel == 'a':
                lengthen('a')
            elif prev_vowel == 'an':
                pass               # the alif after fathatan
            i += 1
            continue

        if b == ALIF_MAQSURA and u.has(SHADDA, *VOWEL_MARKS):
            b = YA                 # written ى but read as a y: al-hayyou, ayyi
        if b == ALIF_MAQSURA:
            if u.has(DAGGER) or prev_vowel == 'a':
                lengthen('a') or put('â', 'â')
            elif prev_vowel == 'i':
                lengthen('i')
            elif u.vowel:
                put('y' + SHORT.get(u.vowel, ''), SHORT.get(u.vowel))
            i += 1
            continue

        if b in (WAW, YA) and u.bare and not u.has(DAGGER):
            want = 'ou' if b == WAW else 'i'
            if prev_vowel == want:
                lengthen(want)
                if u.has(SMALL_HIGH_YEH):
                    pass
                i += 1
                continue
            if nxt is not None and nxt.has(SHADDA) and not u.vowel and i + 1 < n:
                i += 1             # assimilated (rare inside a word)
                continue
            put(CONSONANTS[b], None)
            i += 1
            continue

        if b in (WAW, YA, ALIF_MAQSURA) and u.has(DAGGER) and not u.has(*VOWEL_MARKS):
            # Silent carrier of a dagger alif: ٱلصَّلَوٰة -> as-salâh.
            lengthen('a') or put('â', 'â')
            i += 1
            continue

        if b == SMALL_HIGH_NOON:
            put('n')
            i += 1
            continue

        if b not in CONSONANTS:
            i += 1
            continue

        c = CONSONANTS[b]
        if b == 'آ':
            put("'â", 'â')
            i += 1
            continue
        if b in HAMZAS and ((not out and i == 0) or skip_apostrophe):
            c = ''                 # no apostrophe for a hamza that starts a word: inna, al-ardou
        if b == NUN and u.has(*IQLAB):
            c = 'm'

        if u.bare and b not in HAMZAS:
            # Sukun not written: assimilated into a following shadda, or a plain n (ikhfâ').
            if nxt is not None and nxt.has(SHADDA):
                i += 1
                continue
            put(c, None)
            i += 1
            continue

        skip_apostrophe = False
        if u.has(SHADDA) and not (start and i == 0):
            c = c + c              # a doubled letter that starts a line is read single
        v = u.vowel
        if b == TA_MARBUTA and last and i == n - 1:
            put('h', None)
            i += 1
            continue
        if v in TANWIN:
            if last and i == n - 1 or (last and i == n - 2 and us[-1].base == ALIF):
                # Pausal tanwin: -an -> -â, others dropped.
                if v == FATHATAN and b != TA_MARBUTA:
                    put(c + 'â', 'â')
                else:
                    put('h' if b == TA_MARBUTA else c, None)
                i += 1
                continue
            m = 'm' if u.has(*IQLAB) or (nxt is not None and nxt.has(*IQLAB)) else 'n'
            put(c + TANWIN[v] + m, 'an' if v == FATHATAN else None)
            w.tanwin = True
            i += 1
            continue
        if v:
            s = SHORT[v]
            if b == LAM and v == FATHA and is_allah(us, i):
                s = 'â'
                put(c + s, 'â')
            elif u.has(DAGGER):
                s = {'a': 'â', 'i': 'î', 'ou': 'oû'}[s] if s == 'a' else s
                put(c + s, 'â' if s == 'â' else s)
            else:
                put(c + s, s)
            if last and i == n - 1:
                out[-1] = c      # pausal: drop the final short vowel
                prev_vowel = None
            i += 1
            continue
        if u.has(DAGGER):
            put(c + 'â', 'â')
            i += 1
            continue
        put(c, None)               # consonant with sukun
        i += 1

    w.text = ''.join(out)
    # Pausal pronoun hoû/hî: tazra'oûnahoû -> tazra'oûnah at the end of an ayah.
    if last and n >= 2 and us[-1].base in (SMALL_WAW, SMALL_YEH):
        w.text = re.sub(r'(ou|i)$', '', w.text)
    return w


def join(words, pausal=True):
    """Join word transcriptions of one line, applying wasl and idghâm across words."""
    texts = []
    for k, w in enumerate(words):
        t = w.text
        art = w.article
        if not texts:
            # First word of the line.
            if w.wasl:
                if art == 'll':
                    t = 'al' + t
                elif art:
                    t = 'a' + art + '-' + (t if art == 'l' else t)
                else:
                    t = getattr(w, 'lead', 'i') + t
            texts.append(t)
            continue
        prev = texts[-1]
        pw = words[k - 1]
        first = w.us[0] if w.us else None
        if w.wasl:
            # The alif wasla is silent: hook this word onto the previous one.
            for long_, short in SHORTEN.items():
                if prev.endswith(long_):
                    prev = prev[:-len(long_)] + short
                    break
            if getattr(pw, 'tanwin', False):
                prev += 'i'
            if art == 'll':
                texts[-1] = prev + '-l' + t
            elif art:
                texts[-1] = prev + '-' + art + '-' + t
            else:
                texts[-1] = prev + '-' + t
            continue
        if first is not None and first.has(SHADDA) and w.text:
            ends_bare = pw.us and pw.us[-1].bare and pw.us[-1].base in CONSONANTS and pw.us[-1].base not in (WAW, YA)
            if getattr(pw, 'tanwin', False) or ends_bare:
                # Idghâm: the n (or other unvoiced letter) merges into the doubled letter.
                if getattr(pw, 'tanwin', False):
                    prev = prev[:-1]
                elif ends_bare:
                    c = CONSONANTS[pw.us[-1].base]
                    if pw.us[-1].has(*IQLAB):
                        c = 'm'
                    if prev.endswith(c):
                        prev = prev[:-len(c)]
                lead = consonant_prefix(t)
                texts[-1] = prev + lead[:len(lead) // 2] + '-' + t[len(lead) // 2:]
                continue
        texts.append(t)
    return ' '.join(texts)


def consonant_prefix(t):
    m = re.match(r"[^aiouâîû]+", t)
    return m.group(0) if m else ''


def transcribe(text, pausal=True):
    """Transcribe one ayah (or any line of Uthmani text)."""
    raw = [x for x in text.split() if x]
    groups = [units(x) for x in raw]
    groups = [g for g in groups if g]
    if groups and all(is_muqattaat(g) for g in groups[:1]):
        pass
    words = []
    for k, us in enumerate(groups):
        if is_muqattaat(us):
            w = Word(us)
            w.text = '-'.join(LETTER_NAMES[u.base] for u in us)
            words.append(w)
            continue
        words.append(transcribe_word(us, k == 0, pausal and k == len(groups) - 1))
    line = join(words)
    line = line.replace("''", "'")
    return capitalize(line)


def capitalize(s):
    for i, ch in enumerate(s):
        if ch.isalpha():
            return s[:i] + ch.upper() + s[i + 1:]
    return s
