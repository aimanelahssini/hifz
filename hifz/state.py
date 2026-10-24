"""Where Hifz keeps your place, your finished counts and your settings.

Everything lives in one small JSON file, $XDG_STATE_HOME/hifz/progress.json
(~/.local/state/hifz/progress.json), written atomically after every change.
"""

import datetime
import json
import os

SPEEDS = (0.5, 0.75, 1.0, 1.1, 1.25, 1.5, 1.75, 2.0)     # the right-click menu
SPEED_MIN, SPEED_MAX = 0.5, 2.0                          # ← and → go in steps of 0.05
DEFAULT_SURAH = 56          # Al-Wâqi'a


def state_dir():
    base = os.environ.get('XDG_STATE_HOME') or os.path.expanduser('~/.local/state')
    return os.path.join(base, 'hifz')


def path():
    return os.path.join(state_dir(), 'progress.json')


class State:
    def __init__(self, data=None):
        d = data or {}
        self.surah = d.get('surah', DEFAULT_SURAH)
        self.speed = d.get('speed', 1.0)
        self.reciter = d.get('reciter', 'Alafasy_128kbps')
        self.show_arabic = d.get('show_arabic', False)
        self.auto = d.get('auto', False)
        self.surahs = d.get('surahs', {})
        self.saved = [n for n in d.get('saved', []) if isinstance(n, int) and 1 <= n <= 114]
        if not (1 <= int(self.surah) <= 114):
            self.surah = DEFAULT_SURAH
        try:
            self.speed = round(min(SPEED_MAX, max(SPEED_MIN, float(self.speed))) * 20) / 20
        except (TypeError, ValueError):
            self.speed = 1.0

    @classmethod
    def load(cls):
        try:
            with open(path(), encoding='utf-8') as f:
                return cls(json.load(f))
        except (OSError, ValueError):
            return cls()

    def save(self):
        os.makedirs(state_dir(), exist_ok=True)
        tmp = path() + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump({
                'version': 1,
                'surah': self.surah,
                'speed': self.speed,
                'reciter': self.reciter,
                'show_arabic': self.show_arabic,
                'auto': self.auto,
                'saved': self.saved,
                'surahs': self.surahs,
            }, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path())

    def _entry(self, n):
        return self.surahs.setdefault(str(n), {'line': 0, 'finished': 0, 'finishes': []})

    def toggle_saved(self, n):
        if n in self.saved:
            self.saved.remove(n)
        else:
            self.saved.append(n)
            self.saved.sort()

    def line(self, n):
        return self.surahs.get(str(n), {}).get('line', 0)

    def set_line(self, n, line):
        self._entry(n)['line'] = line

    def finished(self, n):
        return self.surahs.get(str(n), {}).get('finished', 0)

    def add_finish(self, n):
        e = self._entry(n)
        e['finished'] = e.get('finished', 0) + 1
        e.setdefault('finishes', []).append(datetime.datetime.now().isoformat(timespec='seconds'))
        e['line'] = 0
