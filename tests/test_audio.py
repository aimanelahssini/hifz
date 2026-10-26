"""The recitation player, with real GStreamer but no sound (fakesink at real speed).

    python3 -m unittest tests.test_audio

Needs a few ayahs of Al-Wâqi'a in the audio cache (they are downloaded if missing).
"""
import os
import time
import unittest

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst  # noqa: E402

os.environ['HIFZ_AUDIO_SINK'] = 'fakesink sync=true'
from hifz import audio  # noqa: E402

RECITER = 'Alafasy_128kbps'


def ayah(n):
    path, url = audio.file_for(RECITER, 56, n)
    if not os.path.exists(path):
        import urllib.request
        os.makedirs(os.path.dirname(path), exist_ok=True)
        req = urllib.request.Request(url, headers={'User-Agent': 'Hifz/1.0'})
        with urllib.request.urlopen(req, timeout=30) as r, open(path, 'wb') as f:
            f.write(r.read())
    return path


def run(seconds, until=lambda: False):
    loop = GLib.MainLoop()
    end = time.monotonic() + seconds

    def tick():
        if until() or time.monotonic() > end:
            loop.quit()
            return False
        return True
    GLib.timeout_add(20, tick)
    loop.run()


class Player(unittest.TestCase):
    def test_going_back_quickly_does_not_skip_ahead(self):
        """↑ four times in a row while reciting: only the ayah you land on plays, and the
        recitation then goes on to the one right after it, not further."""
        started, ended = [], []
        p = audio.Player(lambda: ended.append(p.playing), lambda: started.append(p.playing))
        p.start()
        p.breath = 0
        p.play(ayah(9))
        p.queued = [ayah(10)]
        run(0.6)
        for n in (8, 7, 6, 5):            # going back, one press every 150 ms
            p.halt()
            p.play(ayah(n))
            p.queued = [ayah(n + 1)]
            run(0.15)
        run(12, until=lambda: len(started) >= 1 and ended)
        p.stop()
        self.assertEqual(started, [ayah(6)], 'only ayah 6 follows ayah 5')

    def test_a_breath_between_ayahs(self):
        """With a pause set, the next ayah starts after the breath, and only then moves the text."""
        started, times = [], []
        t0 = time.monotonic()
        p = audio.Player(lambda: None, lambda: (started.append(p.playing), times.append(time.monotonic() - t0)))
        p.start()
        p.set_speed(2.0)
        p.breath = 0.4
        p.play(ayah(1))
        p.queued = [ayah(2)]
        run(10, until=lambda: started)
        p.stop()
        self.assertEqual(started, [ayah(2)])
        # 056001 lasts about 3.5 s: at 2x, 1.75 s, then the 0.4 s breath at 2x (0.2 s).
        self.assertAlmostEqual(times[0], 1.75 + 0.2, delta=0.25)

    def test_speed_keeps_its_timing(self):
        """SoundTouch at 1.1x: the ayah lasts its length / 1.1."""
        ended = []
        t0 = time.monotonic()
        p = audio.Player(lambda: ended.append(time.monotonic() - t0), None)
        p.start()
        p.set_speed(1.1)
        p.play(ayah(1))
        self.assertEqual(p._cur.tempo.get_factory().get_name(), 'pitch')
        run(10, until=lambda: ended)
        p.stop()
        self.assertAlmostEqual(ended[0], 3.49 / 1.1, delta=0.25)

    def test_moving_away_fades_instead_of_cutting(self):
        """A cut mid-sound clicks: the ayah you leave fades out over a few ms first."""
        p = audio.Player(lambda: None, None)
        p.start()
        p.play(ayah(1))
        run(0.8)
        old = p._cur.pipe
        volumes = []
        old.connect('notify::volume', lambda *_: volumes.append(old.get_property('volume')))
        p.halt()
        run(0.3)
        self.assertGreater(len(volumes), 3, 'several steps, not a jump')
        self.assertEqual(volumes, sorted(volumes, reverse=True))
        self.assertAlmostEqual(volumes[-1], 0.0)
        self.assertEqual(old.get_state(0)[1], Gst.State.NULL)
        p.stop()


if __name__ == '__main__':
    unittest.main()
