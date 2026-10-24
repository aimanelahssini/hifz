"""The Quran text, surah names and the lines Hifz shows for each surah."""

import functools
import os

from .phonetic import transcribe

DATA = os.path.join(os.path.dirname(__file__), 'data', 'quran-uthmani.txt')

# Surah names as French phonetic Qurans write them, with the number of ayahs.
SURAHS = [
    ('Al-Fâtiha', 7), ('Al-Baqara', 286), ("Âl 'Imrân", 200), ("An-Nisâ'", 176),
    ("Al-Mâ'ida", 120), ("Al-An'âm", 165), ("Al-A'râf", 206), ('Al-Anfâl', 75),
    ('At-Tawba', 129), ('Yoûnous', 109), ('Hoûd', 123), ('Yoûsouf', 111),
    ("Ar-Ra'd", 43), ('Ibrâhîm', 52), ('Al-Hijr', 99), ('An-Nahl', 128),
    ("Al-Isrâ'", 111), ('Al-Kahf', 110), ('Maryam', 98), ('Tâ-Hâ', 135),
    ("Al-Anbiyâ'", 112), ('Al-Hajj', 78), ("Al-Mou'minoûn", 118), ('An-Noûr', 64),
    ('Al-Fourqân', 77), ("Ach-Chou'arâ'", 227), ('An-Naml', 93), ('Al-Qasas', 88),
    ("Al-'Ankaboût", 69), ('Ar-Roûm', 60), ('Louqmân', 34), ('As-Sajda', 30),
    ('Al-Ahzâb', 73), ("Saba'", 54), ('Fâtir', 45), ('Yâ-Sîn', 83),
    ('As-Sâffât', 182), ('Sâd', 88), ('Az-Zoumar', 75), ('Ghâfir', 85),
    ('Foussilat', 54), ('Ach-Choûrâ', 53), ('Az-Zoukhrouf', 89), ('Ad-Doukhân', 59),
    ('Al-Jâthiya', 37), ('Al-Ahqâf', 35), ('Mouhammad', 38), ('Al-Fath', 29),
    ('Al-Houjourât', 18), ('Qâf', 45), ('Adh-Dhâriyât', 60), ('At-Toûr', 49),
    ('An-Najm', 62), ('Al-Qamar', 55), ('Ar-Rahmân', 78), ("Al-Wâqi'a", 96),
    ('Al-Hadîd', 29), ('Al-Moujâdala', 22), ('Al-Hachr', 24), ('Al-Moumtahana', 13),
    ('As-Saff', 14), ("Al-Joumou'a", 11), ('Al-Mounâfiqoûn', 11), ('At-Taghâboun', 18),
    ('At-Talâq', 12), ('At-Tahrîm', 12), ('Al-Moulk', 30), ('Al-Qalam', 52),
    ('Al-Hâqqa', 52), ("Al-Ma'ârij", 44), ('Noûh', 28), ('Al-Jinn', 28),
    ('Al-Mouzzammil', 20), ('Al-Mouddaththir', 56), ('Al-Qiyâma', 40), ('Al-Insân', 31),
    ('Al-Moursalât', 50), ("An-Naba'", 40), ("An-Nâzi'ât", 46), ("'Abasa", 42),
    ('At-Takwîr', 29), ('Al-Infitâr', 19), ('Al-Moutaffifîn', 36), ('Al-Inchiqâq', 25),
    ('Al-Bouroûj', 22), ('At-Târiq', 17), ("Al-A'lâ", 19), ('Al-Ghâchiya', 26),
    ('Al-Fajr', 30), ('Al-Balad', 20), ('Ach-Chams', 15), ('Al-Layl', 21),
    ('Ad-Douhâ', 11), ('Ach-Charh', 8), ('At-Tîn', 8), ("Al-'Alaq", 19),
    ('Al-Qadr', 5), ('Al-Bayyina', 8), ('Az-Zalzala', 8), ("Al-'Âdiyât", 11),
    ("Al-Qâri'a", 11), ('At-Takâthour', 8), ("Al-'Asr", 3), ('Al-Houmaza', 9),
    ('Al-Fîl', 5), ('Qouraych', 4), ("Al-Mâ'oûn", 7), ('Al-Kawthar', 3),
    ('Al-Kâfiroûn', 6), ('An-Nasr', 3), ('Al-Masad', 5), ('Al-Ikhlâs', 4),
    ('Al-Falaq', 5), ('An-Nâs', 6),
]

SHADDA = 'ّ'


def name(n):
    return SURAHS[n - 1][0]


@functools.lru_cache(maxsize=1)
def _text():
    ayahs = {}
    with open(DATA, encoding='utf-8') as f:
        for line in f:
            if '|' not in line or line.startswith('#'):
                continue
            s, a, t = line.rstrip('\n').split('|', 2)
            ayahs.setdefault(int(s), []).append(t)
    return ayahs


class Line:
    """One line of the prompter: an ayah, or the basmala that opens a surah."""
    __slots__ = ('ayah', 'arabic', 'phonetic')

    def __init__(self, ayah, arabic):
        self.ayah = ayah           # 0 for the basmala
        self.arabic = arabic
        self.phonetic = transcribe(arabic)


@functools.lru_cache(maxsize=8)
def lines(n):
    """The lines of surah n. Every surah but 1 and 9 opens with the basmala as line 0."""
    ayahs = list(_text()[n])
    out = []
    if n not in (1, 9):
        # Tanzil writes the basmala at the start of ayah 1; it is a line of its own here.
        basmala = _text()[1][0].split()
        words = ayahs[0].split()
        if [w.replace(SHADDA, '') for w in words[:4]] == [w.replace(SHADDA, '') for w in basmala]:
            out.append(Line(0, ' '.join(basmala)))
            ayahs[0] = ' '.join(words[4:])
    out.extend(Line(i + 1, t) for i, t in enumerate(ayahs))
    return out
