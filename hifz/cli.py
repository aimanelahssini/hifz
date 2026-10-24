"""The `quran` command: pick a surah in the terminal, then Hifz opens on its own.

    quran            list the 114 surahs and ask which one (Enter keeps the last one)
    quran 56         open Al-Wâqi'a straight away
    quran waqia      a name works too
    quran stats      how many times you finished each surah
    hifz             open the last surah without asking

The window is started in its own session, so closing the terminal doesn't close it.
If Hifz is already open, it just switches to the surah you picked.
"""

import os
import re
import shutil
import subprocess
import sys
import unicodedata

from . import quran
from .state import State

BOLD, DIM, GREEN, YELLOW, RESET = '\033[1m', '\033[2m', '\033[32m', '\033[33m', '\033[0m'


def plain(s):
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if c.isalpha())
    return s.replace('ou', 'u').replace('ch', 'sh')


def find(text):
    """Surah numbers matching what was typed: a number or part of a name."""
    text = text.strip()
    if text.isdigit():
        n = int(text)
        return [n] if 1 <= n <= 114 else []
    q = plain(text)
    if not q:
        return []
    names = [(n, plain(quran.name(n))) for n in range(1, 115)]
    article = '^(al|an|ar|as|at|ad|adh|ach|az)'
    for strip in (lambda x: x, lambda x: x.rstrip('h')):     # waqia, waqiah
        exact = [n for n, p in names if strip(q) in (strip(p), strip(re.sub(article, '', p)))]
        if exact:
            return exact
    return [n for n, p in names if q in p or q.rstrip('h') in p]


def show_list(state, color):
    width = shutil.get_terminal_size((100, 30)).columns
    def mark(n):
        done = state.finished(n)
        return (f' ✓{done}' if done else '') + (' ★' if n in state.saved else '')
    cell = 3 + max(len(f'{n:3}  {quran.name(n)}{mark(n)}') for n in range(1, 115))
    cols = max(1, min(6, width // cell))
    rows = -(-114 // cols)
    for r in range(rows):
        parts = []
        for c in range(cols):
            n = c * rows + r + 1
            if n > 114:
                continue
            name = quran.name(n)
            text = f'{n:3}  {name}{mark(n)}'
            pad = ' ' * max(1, cell - len(text))
            if color:
                # The last surah in bold yellow, finished ones in green, the rest plain.
                tone = f'{BOLD}{YELLOW}' if n == state.surah else GREEN if state.finished(n) else ''
                text = f'{DIM}{n:3}{RESET}  {tone}{name}{RESET}{DIM}{mark(n)}{RESET}'
            parts.append(text + pad)
        print(''.join(parts).rstrip())


def launch(n):
    """Start the window in its own session, detached from this terminal."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = dict(os.environ)
    env['PYTHONPATH'] = here + os.pathsep + env.get('PYTHONPATH', '')
    subprocess.Popen([sys.executable, '-m', 'hifz', '--surah', str(n)], cwd=here, env=env,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


def stats(state):
    rows = [(n, state.finished(n)) for n in range(1, 115) if state.finished(n)]
    if not rows:
        print('No surah finished yet.')
        return
    for n, k in sorted(rows, key=lambda r: -r[1]):
        print(f'{n:3}  {quran.name(n):18} {k} time{"s" if k != 1 else ""}')


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    state = State.load()
    color = sys.stdout.isatty() and not os.environ.get('NO_COLOR')
    if argv and argv[0] in ('-h', '--help'):
        print(__doc__.strip())
        return 0
    if argv and argv[0] == '--open':
        launch(int(argv[1]) if len(argv) > 1 and argv[1].isdigit() else state.surah)
        return 0
    if argv and argv[0] == 'stats':
        stats(state)
        return 0
    if argv:
        found = find(' '.join(argv))
        if len(found) == 1:
            launch(found[0])
            print(f'{found[0]}  {quran.name(found[0])}')
            return 0
        print('No surah matches that.' if not found else
              'Several match: ' + ', '.join(f'{n} {quran.name(n)}' for n in found))
        return 1

    show_list(state, color)
    last = f'{state.surah} {quran.name(state.surah)}'
    while True:
        try:
            answer = input(f'\nSurah number {DIM if color else ""}(Enter = {last}){RESET if color else ""}: ')
        except (EOFError, KeyboardInterrupt):
            print()
            return 1
        if not answer.strip():
            n = state.surah
            break
        if answer.strip().lower() in ('q', 'quit', 'exit'):
            return 1
        found = find(answer)
        if len(found) == 1:
            n = found[0]
            break
        if found:
            print('Several match: ' + ', '.join(f'{k} {quran.name(k)}' for k in found[:8]))
        else:
            print('Type a number from 1 to 114, or part of a name.')
    launch(n)
    print(f'Opening {quran.name(n)}. You can close this terminal.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
