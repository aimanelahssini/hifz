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


class Player:
    """Plays one ayah at a time. Call start() to create the pipeline and stop() to drop it."""

    def __init__(self, on_end):
        Gst.init(None)
        self.on_end = on_end
        self.pipe = None
        self.tempo = None
        self.speed = 1.0
        self.playing = None        # (path) of the file being played

    @property
    def active(self):
        return self.pipe is not None

    def start(self):
        if self.pipe:
            return
        self.pipe = Gst.ElementFactory.make('playbin', 'hifz')
        self.pipe.set_property('video-sink', Gst.ElementFactory.make('fakesink', None))
        # Pitch-preserving speed: soundtouch's "pitch" element, or scaletempo.
        self.tempo = Gst.ElementFactory.make('pitch', None)
        if self.tempo is not None:
            self.tempo.set_property('tempo', self.speed)
        else:
            self.tempo = Gst.ElementFactory.make('scaletempo', None)
        if self.tempo is not None:
            self.pipe.set_property('audio-filter', self.tempo)
        sink = os.environ.get('HIFZ_AUDIO_SINK')      # tests: "fakesink sync=true"
        if sink:
            self.pipe.set_property('audio-sink', Gst.parse_launch(sink))
        bus = self.pipe.get_bus()
        bus.add_signal_watch()
        bus.connect('message::eos', self._eos)
        bus.connect('message::error', self._eos)
        bus.connect('message::async-done', self._async_done)

    def stop(self):
        _log('stop')
        if self.pipe:
            self.pipe.set_state(Gst.State.NULL)
            self.pipe.get_bus().remove_signal_watch()
            self.pipe = None
            self.tempo = None
        self.playing = None

    def halt(self):
        """Stop the current ayah but keep the pipeline."""
        _log('stop')
        if self.pipe:
            self.pipe.set_state(Gst.State.READY)
        self.playing = None

    def play(self, path):
        if not self.pipe:
            return
        self.pipe.set_state(Gst.State.READY)
        self.pipe.set_property('uri', Gst.filename_to_uri(path))
        self.playing = path
        _log('play', path, self.speed)
        self._needs_rate = self.tempo is not None and self.tempo.get_factory().get_name() == 'scaletempo'
        self.pipe.set_state(Gst.State.PLAYING)

    def set_speed(self, speed):
        self.speed = speed
        _log('speed', speed)
        if self.tempo is None:
            return
        if self.tempo.get_factory().get_name() == 'pitch':
            self.tempo.set_property('tempo', speed)
        elif self.playing:
            self._seek_rate()

    def _seek_rate(self):
        ok, pos = self.pipe.query_position(Gst.Format.TIME)
        self.pipe.seek(self.speed, Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                       Gst.SeekType.SET, pos if ok else 0, Gst.SeekType.NONE, 0)

    def _async_done(self, bus, msg):
        if getattr(self, '_needs_rate', False) and self.speed != 1.0:
            self._needs_rate = False
            self._seek_rate()

    def _eos(self, bus, msg):
        if self.pipe:
            self.pipe.set_state(Gst.State.READY)
        was = self.playing
        self.playing = None
        if was:
            self.on_end()
