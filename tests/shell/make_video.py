"""Turns a demo recording into docs/demo.mp4.  make_video.py OUT_DIR TARGET.mp4

OUT_DIR is what tests/shell/demo.sh leaves: raw.mp4 (the screen at 2560x1440, scale 2),
results.txt (timed marks), record-start.txt and play.log (which ayah played when, at what
speed). The video starts on the whole desktop, zooms into the top-right corner once Hifz is
open, and gets the recitation that the app played, in time with the screen.
"""

import os
import subprocess
import sys

OUT, TARGET = sys.argv[1], sys.argv[2]
CACHE = os.path.expanduser('~/.cache/hifz-tests/audio')
ZOOM_IN = 1.4      # seconds the zoom takes


def marks():
    m = {}
    for line in open(os.path.join(OUT, 'results.txt')):
        if line.startswith('mark '):
            _, name, t = line.split()
            m[name] = float(t)
    return m


def segments():
    """(start, source offset, duration, speed, file) for every stretch of recitation."""
    t0 = int(open(os.path.join(OUT, 'record-start.txt')).read())
    out = []
    cur = None                  # [start, offset, speed, file]
    speed = 1.0
    last = None                 # (file, offset reached) when it stopped, for a resume

    def close(t):
        nonlocal cur, last
        if cur:
            start, off, v, f = cur
            if t > start:
                out.append((start, off, t - start, v, f))
            last = (f, off + (t - start) * v)
            cur = None

    for line in open(os.path.join(OUT, 'play.log')):
        parts = line.split()
        t = (int(parts[0]) - t0) / 1e6
        what = parts[1]
        if what == 'play':
            close(t)
            f = os.path.join(CACHE, *parts[2].split('/audio/')[1].split('/'))
            cur = [t, 0.0, float(parts[3]), f]
        elif what == 'stop':
            close(t)
        elif what == 'resume' and last:
            cur = [t, last[1], float(parts[3]), last[0]]
        elif what == 'speed':
            speed = float(parts[2])
            if cur and speed != cur[2]:
                start, off, v, f = cur
                close(t)
                cur = [t, off + (t - start) * v, speed, f]
    return [s for s in out if s[0] >= 0]


def main():
    m = marks()
    z0 = m['zoom']
    end = m['end'] + 0.6
    # Zoom: 2560x1440 scaled to 1920x1080 (whole desktop) -> 1:1 crop of the top-right corner.
    k = f"clip((t-{z0})/{ZOOM_IN},0,1)"
    ease = f"(3*pow({k},2)-2*pow({k},3))"
    f = f"(0.75+0.25*{ease})"
    vf = (f"fps=30,scale=w='trunc(2560*{f}/2)*2':h='trunc(1440*{f}/2)*2':eval=frame:flags=lanczos,"
          f"crop=1920:1080:x='trunc(2560*{f}/2)*2-1920':y=0,format=yuv420p")
    segs = segments()
    inputs = ['-i', os.path.join(OUT, 'raw.mp4')]
    chains = []
    for i, (start, off, dur, v, path) in enumerate(segs):
        inputs += ['-i', path]
        ms = int(start * 1000)
        chains.append(f"[{i + 1}:a]atrim=start={off:.3f}:duration={dur * v:.3f},asetpts=PTS-STARTPTS,"
                      f"atempo={v},aresample=48000,adelay={ms}|{ms}[a{i}]")
    mix = ''.join(f'[a{i}]' for i in range(len(segs)))
    fc = ';'.join(chains + [f"{mix}amix=inputs={len(segs)}:normalize=0:duration=longest,"
                            f"apad,atrim=0:{end:.2f},afade=t=out:st={end - 0.6:.2f}:d=0.6[aud]",
                            f"[0:v]trim=0:{end:.2f},setpts=PTS-STARTPTS,{vf},"
                            f"fade=t=in:st=0:d=0.5,fade=t=out:st={end - 0.6:.2f}:d=0.6[vid]"])
    cmd = ['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex', fc, '-map', '[vid]', '-map', '[aud]',
           '-c:v', 'libx264', '-preset', 'slow', '-crf', '22', '-c:a', 'aac', '-b:a', '128k',
           '-movflags', '+faststart', TARGET]
    subprocess.run(cmd, check=True)
    # A poster frame for the website: zoomed in, the text on screen.
    poster = os.path.splitext(TARGET)[0] + '-poster.jpg'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f"{m['menu'] - 1.5:.2f}", '-i', TARGET,
                    '-frames:v', '1', '-q:v', '3', poster], check=True)
    print(TARGET, poster, f'{end:.1f}s', len(segs), 'ayah segments')


if __name__ == '__main__':
    main()
