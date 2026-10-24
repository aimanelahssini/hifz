"""Checks the French phonetic text against hand-checked lines.  python3 -m unittest"""
import unittest

from hifz import quran
from hifz.cli import find
from hifz.phonetic import transcribe

EXPECTED = {
    (1, 1): 'Bismi-llâhi-r-rahmâni-r-rahîm',
    (1, 2): "Al-hamdou lillâhi rabbi-l-'âlamîn",
    (1, 5): "Iyyâka na'boudou wa'iyyâka nasta'în",
    (1, 6): 'Ihdina-s-sirâta-l-moustaqîm',
    (56, 1): "Idhâ waqa'ati-l-wâqi'ah",
    (56, 3): "Khâfidatour-râfi'ah",
    (56, 6): "Fakânat habâ'am-moumbaththâ",
    (56, 10): 'Wa-s-sâbiqoûna-s-sâbiqoûn',
    (56, 13): 'Thoullatoum-mina-l-awwalîn',
    (56, 18): "Bi'akwâbin wa'abârîqa waka'sim-mim-ma'în",
    (56, 61): "'Alâ an-noubaddila amthâlakoum wanounchi'akoum fî mâ lâ ta'lamoûn",
    (56, 74): "Fasabbih bismi rabbika-l-'adhîm",
    (56, 80): "Tanzîloum-mir-rabbi-l-'âlamîn",
    (2, 1): 'Alif-lâm-mîm',
    (2, 255): None,                      # just must not fail
    (4, 1): None,
    (11, 42): None,
    (21, 88): "Fastajabnâ lahoû wanajjaynâhou mina-l-ghammi wakadhâlika nounji-l-mou'minîn",
    (36, 1): 'Yâ-sîn',
    (55, 13): "Fabi'ayyi âlâ'i rabbikoumâ toukadhdhibân",
    (73, 2): 'Qoumi-l-layla illâ qalîlâ',
    (112, 1): 'Qoul houwa-llâhou ahad',
    (112, 2): 'Allâhou-s-samad',
    (114, 5): 'Alladhî youwaswisou fî soudoûri-n-nâs',
}


class Phonetic(unittest.TestCase):
    def test_lines(self):
        for (s, a), want in EXPECTED.items():
            got = next(line.phonetic for line in quran.lines(s) if line.ayah == a)
            if want is not None:
                self.assertEqual(got, want, f'{s}:{a}')

    def test_whole_quran(self):
        n = 0
        for s in range(1, 115):
            lines = quran.lines(s)
            self.assertEqual(sum(1 for line in lines if line.ayah), quran.SURAHS[s - 1][1], s)
            for line in lines:
                self.assertRegex(line.phonetic, r"^[A-Za-z'âîûÂÎ][A-Za-z' \-âîûÂÎ]*$", f'{s}:{line.ayah}')
                n += 1
        self.assertEqual(n, 6236 + 112)  # every ayah, plus a basmala for all but 1 and 9

    def test_basmala_line(self):
        self.assertEqual(quran.lines(56)[0].ayah, 0)
        self.assertEqual(quran.lines(1)[0].ayah, 1)
        self.assertEqual(quran.lines(9)[0].ayah, 1)
        self.assertEqual(quran.lines(97)[0].ayah, 0)    # written بِّسْمِ in Tanzil

    def test_transcribe_standalone(self):
        self.assertEqual(transcribe('قُلْ هُوَ ٱللَّهُ أَحَدٌ'), 'Qoul houwa-llâhou ahad')

    def test_find(self):
        self.assertEqual(find('56'), [56])
        self.assertEqual(find('waqia'), [56])
        self.assertEqual(find('Al-Waqiah'), [56])
        self.assertEqual(find('yasin'), [36])
        self.assertEqual(find('115'), [])


if __name__ == '__main__':
    unittest.main()
