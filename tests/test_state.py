"""Settings: Arabic is off unless you turn it on.   python3 -m unittest tests.test_state"""
import unittest

from hifz.state import State


class Text(unittest.TestCase):
    def test_phonetics_by_default(self):
        self.assertEqual(State().language, 'ph')
        self.assertFalse(State().show_arabic)

    def test_arabic_filled_in_by_the_update_is_turned_off_once(self):
        # Files from the version that put Arabic first for everyone.
        self.assertEqual(State({'language': 'ar', 'show_arabic': True}).language, 'ph')
        self.assertEqual(State({'show_arabic': True}).language, 'ph')

    def test_arabic_you_turn_on_stays_on(self):
        s = State()
        s.language = 'ar'
        saved = {'language': s.language, 'text_v': 2}
        self.assertEqual(State(saved).language, 'ar')

    def test_translations_are_kept(self):
        self.assertEqual(State({'language': 'en'}).language, 'en')

    def test_pause_between_ayahs(self):
        self.assertEqual(State().pause, 'short')
        self.assertEqual(State({'pause': 'none'}).pause, 'none')
        self.assertEqual(State({'pause': 'nonsense'}).pause, 'short')


if __name__ == '__main__':
    unittest.main()
