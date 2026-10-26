"""Per-ayah recitation: download once, cache, and play at the chosen speed.

The audio comes from everyayah.com, one MP3 per ayah. When the sound is off there is no
GStreamer pipeline at all, so nothing reaches PipeWire: muted means silent, not quiet.
"""

import collections
import os
import threading
import urllib.request

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst  # noqa: E402

RECITERS = [
    ('Alafasy_128kbps', 'Mishary Alafasy'),
    ('Husary_128kbps', 'Mahmoud Khalil Al-Husary'),
    ('Minshawy_Murattal_128kbps', 'Mohamed Siddiq Al-Minshawi'),
    ('Abdul_Basit_Murattal_192kbps', 'Abdul Basit Abdul Samad'),
    ('Abdurrahmaan_As-Sudais_192kbps', 'Abdul Rahman Al-Sudais'),
    ('MaherAlMuaiqly128kbps', 'Maher Al-Muaiqly'),
    ('Saood_ash-Shuraym_128kbps', 'Saud Al-Shuraim'),
    ('Yasser_Ad-Dussary_128kbps', 'Yasser Al-Dosari'),
]
BASE = 'https://everyayah.com/data/{reciter}/{surah:03d}{ayah:03d}.mp3'


def cache_dir(reciter):
    base = os.environ.get('XDG_CACHE_HOME') or os.path.expanduser('~/.cache')
    return os.path.join(base, 'hifz', 'audio', reciter)


def file_for(reciter, surah, ayah):
    """The basmala (ayah 0) is played from Al-Fâtiha 1:1."""
    if ayah == 0:
        surah, ayah = 1, 1
    return os.path.join(cache_dir(reciter), f'{surah:03d}{ayah:03d}.mp3'), BASE.format(
        reciter=reciter, surah=surah, ayah=ayah)


class Downloader:
    """Fetches ayah files one by one in the background. Urgent requests jump the queue."""

    def __init__(self):
        self._q = collections.deque()
        self._cv = threading.Condition()
        threading.Thread(target=self._run, daemon=True).start()

    def fetch(self, reciter, surah, ayah, done=None, urgent=False):
        path, url = file_for(reciter, surah, ayah)
        if os.path.exists(path):
            if done:
                GLib.idle_add(done, path)
            return
        with self._cv:
            (self._q.appendleft if urgent else self._q.append)((path, url, done))
            self._cv.notify()

    def _run(self):
        while True:
            with self._cv:
                while not self._q:
                    self._cv.wait()
                path, url, done = self._q.popleft()
            ok = os.path.exists(path)
            if not ok:
                try:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    req = urllib.request.Request(url, headers={'User-Agent': 'Hifz/1.0'})
                    with urllib.request.urlopen(req, timeout=30) as r:
                        data = r.read()
                    tmp = path + '.part'
                    with open(tmp, 'wb') as f:
                        f.write(data)
                    os.replace(tmp, path)
                    ok = True
                except OSError:
                    ok = False
            if done:
                GLib.idle_add(done, path if ok else None)


def _log(*what):
    """HIFZ_PLAYLOG=FILE records what plays when (the demo video's soundtrack is built from it)."""
    path = os.environ.get('HIFZ_PLAYLOG')
    if path:
        with open(path, 'a') as f:
            f.write(' '.join(str(w) for w in (GLib.get_monotonic_time(),) + what) + '\n')


FADE_OUT_MS = 40          # moving away mid-ayah: a quick fade, never a cut (a cut clicks)
FADE_IN_MS = 15


class _Ayah:
    """One ayah's own little pipeline: the file, SoundTouch for the speed, the sound output."""

    def __init__(self, path, speed, on_eos):
        self.path = path
        self.pipe = Gst.ElementFactory.make('playbin', None)
        self.pipe.set_property('video-sink', Gst.ElementFactory.make('fakesink', None))
        # SoundTouch's "pitch" element: changes the speed and keeps the voice as it is.
        self.tempo = Gst.ElementFactory.make('pitch', None)
        if self.tempo is not None:
            self.tempo.set_property('tempo', speed)
            self.pipe.set_property('audio-filter', self.tempo)
        sink = os.environ.get('HIFZ_AUDIO_SINK')      # tests: "fakesink sync=true"
        if sink:
            self.pipe.set_property('audio-sink', Gst.parse_launch(sink))
        self.pipe.set_property('uri', Gst.filename_to_uri(path))
        self.pipe.set_property('volume', 0.0)
        bus = self.pipe.get_bus()
        bus.add_signal_watch()
        bus.connect('message::eos', lambda *_: on_eos(self))
        bus.connect('message::error', lambda *_: on_eos(self))
        self.pipe.set_state(Gst.State.PAUSED)     # ready to start at once

    def set_speed(self, speed):
        if self.tempo is not None:
            self.tempo.set_property('tempo', speed)

    def start(self):
        self.pipe.set_state(Gst.State.PLAYING)
        _ramp(self.pipe, 0.0, 1.0, FADE_IN_MS)

    def dispose(self, fade=True):
        """Stop it, fading out first if it is sounding."""
        pipe, self.pipe = self.pipe, None
        if pipe is None:
            return

        def end():
            pipe.set_state(Gst.State.NULL)
            pipe.get_bus().remove_signal_watch()
        if fade and pipe.get_state(0)[1] == Gst.State.PLAYING:
            _ramp(pipe, pipe.get_property('volume'), 0.0, FADE_OUT_MS, end)
        else:
            end()


def _ramp(pipe, start, stop, ms, done=None):
    steps = max(1, ms // 5)
    state = {'k': 0}

    def step():
        state['k'] += 1
        pipe.set_property('volume', start + (stop - start) * state['k'] / steps)
        if state['k'] < steps:
            return True
        if done:
            done()
        return False
    pipe.set_property('volume', start)
    GLib.timeout_add(5, step)


class Player:
    """Plays one ayah at a time. Call start() to switch the sound on and stop() to drop it all.

    Each ayah has its own short pipeline. With "continue automatically" the next one is
    prepared while the current one plays, and starts right when it ends, after the breath.
    """

    def __init__(self, on_end, on_next=None):
        Gst.init(None)
        self.on_end = on_end
        self.on_next = on_next     # the queued ayah has started
        self.speed = 1.0
        self.breath = 0.0          # seconds of silence between two ayahs (at 1x)
        self.playing = None        # the file being played
        self.active = False
        self._cur = None           # _Ayah sounding (or paused)
        self._next = None          # _Ayah prepared, waiting
        self._gen = 0              # a new one at every play or stop: older timers are ignored

    def start(self):
        self.active = True

    def stop(self):
        _log('stop')
        self.halt()
        self.active = False

    def halt(self):
        """Stop the current ayah (with a quick fade) and forget the queued one."""
        if self._cur or self._next:
            _log('stop')
        self._gen += 1
        for a in (self._cur, self._next):
            if a:
                a.dispose()
        self._cur = self._next = None
        self.playing = None

    def play(self, path):
        if not self.active:
            return
        self.halt()
        self._cur = _Ayah(path, self.speed, self._eos)
        self._cur.start()
        self.playing = path
        _log('play', path, self.speed)

    @property
    def queued(self):
        return [self._next.path] if self._next else []

    @queued.setter
    def queued(self, paths):
        """The ayah to go on with: prepared now, so it starts without delay."""
        if self._next:
            self._next.dispose(fade=False)
            self._next = None
        if paths and self.active and os.path.exists(paths[0]):
            self._next = _Ayah(paths[0], self.speed, self._eos)

    @property
    def paused(self):
        return bool(self._cur and self._cur.pipe and self._cur.pipe.get_state(0)[1] == Gst.State.PAUSED)

    def pause(self):
        if self._cur and self._cur.pipe:
            _log('stop')
            self._cur.pipe.set_state(Gst.State.PAUSED)

    def resume(self):
        if self._cur and self._cur.pipe:
            _log('resume', self.playing, self.speed)
            self._cur.pipe.set_state(Gst.State.PLAYING)

    def set_speed(self, speed):
        self.speed = speed
        _log('speed', speed)
        for a in (self._cur, self._next):
            if a:
                a.set_speed(speed)

    def _eos(self, ayah):
        if ayah is not self._cur:
            return                 # an ayah you already moved away from
        ayah.dispose(fade=False)
        self._cur = None
        nxt, gen = self._next, self._gen
        if not nxt:
            self.playing = None
            self.on_end()
            return
        self._next = None

        def go_on():
            if gen != self._gen:
                nxt.dispose(fade=False)     # you moved meanwhile
                return False
            self._cur = nxt
            self.playing = nxt.path
            nxt.start()
            _log('play', nxt.path, self.speed)
            if self.on_next:
                self.on_next()
            return False
        if self.breath > 0:
            GLib.timeout_add(int(self.breath / self.speed * 1000), go_on)
        else:
            go_on()
