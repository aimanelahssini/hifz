// Test driver for Hifz in a throwaway headless shell (tests/shell/run.sh). Writes results.txt
// and screenshots to $HIFZ_OUT. With HIFZ_MODE=demo it records the demo video frames instead.
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

Gio._promisify(Shell.Screenshot.prototype, 'screenshot_area');
const OUT = GLib.getenv('HIFZ_OUT');
const REPO = GLib.getenv('HIFZ_REPO');
const MODE = GLib.getenv('HIFZ_MODE');
const APP_ID = 'io.github.aimanelahssini.Hifz';
const lines = [];
const out = s => {
    lines.push(s);
    GLib.file_set_contents(`${OUT}/results.txt`, lines.join('\n') + '\n');
};
const check = (name, ok, extra = '') => out(`${ok ? 'PASS' : 'FAIL'} ${name} ${extra}`);
const sleep = ms => new Promise(r => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
    r();
    return GLib.SOURCE_REMOVE;
}));

async function shot(name, rect = null) {
    const [x, y, w, h] = rect ?? [0, 0, global.stage.width, global.stage.height];
    const stream = Gio.File.new_for_path(`${OUT}/${name}.png`).replace(null, false, Gio.FileCreateFlags.NONE, null);
    await new Shell.Screenshot().screenshot_area(x, y, w, h, stream);
    stream.close(null);
}

let keyboard, pointer;
const now = () => GLib.get_monotonic_time();
async function press(...keyvals) {
    keyboard ??= Clutter.get_default_backend().get_default_seat()
        .create_virtual_device(Clutter.InputDeviceType.KEYBOARD_DEVICE);
    for (const k of keyvals)
        keyboard.notify_keyval(now(), k, Clutter.KeyState.PRESSED);
    await sleep(25);
    for (const k of [...keyvals].reverse())
        keyboard.notify_keyval(now(), k, Clutter.KeyState.RELEASED);
    await sleep(40);
}
async function click(x, y, button = Clutter.BUTTON_PRIMARY) {
    pointer ??= Clutter.get_default_backend().get_default_seat()
        .create_virtual_device(Clutter.InputDeviceType.POINTER_DEVICE);
    pointer.notify_absolute_motion(now(), x, y);
    await sleep(120);
    pointer.notify_button(now(), button, Clutter.ButtonState.PRESSED);
    await sleep(40);
    pointer.notify_button(now(), button, Clutter.ButtonState.RELEASED);
    await sleep(80);
}
async function move(x, y) {
    pointer ??= Clutter.get_default_backend().get_default_seat()
        .create_virtual_device(Clutter.InputDeviceType.POINTER_DEVICE);
    pointer.notify_absolute_motion(now(), x, y);
    await sleep(60);
}

const procs = [];
function launch(...args) {
    const l = new Gio.SubprocessLauncher({
        flags: Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_MERGE,
    });
    l.set_cwd(REPO);
    l.setenv('PYTHONPATH', REPO, true);
    l.set_flags(Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_MERGE);
    const p = l.spawnv(['python3', '-m', 'hifz', ...args]);
    procs.push(p);
    // Keep the app's output (tracebacks) in app.log.
    const stream = new Gio.DataInputStream({base_stream: p.get_stdout_pipe()});
    const log = Gio.File.new_for_path(`${OUT}/app.log`);
    const read = () => stream.read_line_async(0, null, (s, res) => {
        const [line] = s.read_line_finish_utf8(res);
        if (line === null)
            return;
        const o = log.append_to(Gio.FileCreateFlags.NONE, null);
        o.write_all(new TextEncoder().encode(line + '\n'), null);
        o.close(null);
        read();
    });
    read();
    return p;
}

const hifzWindows = () => global.display.list_all_windows()
    .filter(w => w.get_gtk_application_id() === APP_ID || w.get_wm_class() === APP_ID);

async function waitWindow(ms = 15000) {
    for (let t = 0; t < ms; t += 100) {
        const w = hifzWindows()[0];
        if (w && w.get_frame_rect().width > 1 && w.get_compositor_private()?.visible)
            return w;
        await sleep(100);
    }
    return null;
}

async function waitGone(ms = 5000) {
    for (let t = 0; t < ms; t += 100) {
        if (!hifzWindows().length)
            return true;
        await sleep(100);
    }
    return false;
}

function progress() {
    try {
        return JSON.parse(new TextDecoder().decode(
            GLib.file_get_contents(`${GLib.get_user_state_dir()}/hifz/progress.json`)[1]));
    } catch (e) {
        return {};
    }
}

const rectOf = w => {
    const r = w.get_frame_rect();
    return [r.x, r.y, r.width, r.height];
};
const pad = (r, p) => [r[0] - p, r[1] - p, r[2] + 2 * p, r[3] + 2 * p];

// A plain window behind Hifz, so the screenshots show it over something.
function backdrop() {
    const l = new Gio.SubprocessLauncher({flags: Gio.SubprocessFlags.NONE});
    l.set_cwd(REPO);
    procs.push(l.spawnv(['python3', `${REPO}/tests/shell/backdrop.py`, ...(MODE === 'demo' ? ['--window'] : [])]));
}

async function checks() {
    Main.overview.hide();
    await sleep(1000);
    backdrop();
    await sleep(2500);

    launch('--surah', '56');
    let w = await waitWindow();
    check('window appears', !!w);
    if (!w)
        return;
    await sleep(1200);
    const area = global.workspace_manager.get_active_workspace()
        .get_work_area_for_monitor(global.display.get_primary_monitor());
    const [x, y, ww, wh] = rectOf(w);
    check('pinned top-right', x + ww === area.x + area.width - 12 && y === area.y + 12,
        `rect=${x},${y},${ww}x${wh} area=${area.x},${area.y},${area.width}x${area.height}`);
    check('always on top', w.is_above());
    check('on every desktop', w.is_on_all_workspaces());
    check('fixed size 440x212', ww === 440 && wh === 212, `${ww}x${wh}`);
    await shot('01-desktop');
    w.activate(global.get_current_time());
    await sleep(300);
    await press(Clutter.KEY_Shift_L);   // the first virtual key event can get lost
    await sleep(200);
    await shot('02-start', pad(rectOf(w), 20));

    // A slide, frame by frame.
    await press(Clutter.KEY_space);
    for (let i = 0; i < 6; i++) {
        await shot(`03-slide-${i}`, pad(rectOf(w), 20));
        await sleep(30);
    }
    await sleep(500);
    await press(Clutter.KEY_space);
    await press(Clutter.KEY_space);
    await sleep(600);
    check('space moves on', progress().surahs?.['56']?.line === 3, JSON.stringify(progress().surahs));
    await press(Clutter.KEY_BackSpace);
    await sleep(600);
    check('backspace goes back', progress().surahs?.['56']?.line === 2);
    await shot('04-line2', pad(rectOf(w), 20));
    check('size unchanged after moving', rectOf(w)[2] === 440 && rectOf(w)[3] === 212);

    // Audio: m turns it on, the ayah gets downloaded, m turns it off again.
    await press(Clutter.KEY_m);
    let got = false;
    for (let t = 0; t < 15000 && !got; t += 250) {
        await sleep(250);
        got = GLib.file_test(`${GLib.get_user_cache_dir()}/hifz/audio/Alafasy_128kbps/056002.mp3`, GLib.FileTest.EXISTS);
    }
    check('audio on downloads the current ayah', got);
    await sleep(800);
    await shot('05-audio-on', pad(rectOf(w), 20));
    await press(Clutter.KEY_m);

    // Right-click menu.
    const [rx, ry] = rectOf(w);
    await click(rx + 200, ry + 120, Clutter.BUTTON_SECONDARY);
    await sleep(700);
    await shot('06-menu', [rx - 260, ry, 440 + 300, 600]);
    await press(Clutter.KEY_Escape);
    await sleep(300);

    // Arabic on, then off again.
    await click(rx + 200, ry + 120, Clutter.BUTTON_SECONDARY);
    await sleep(500);
    await shot('06b-menu-before-arabic', [rx - 260, ry, 440 + 300, 600]);
    await press(Clutter.KEY_Escape);
    await sleep(300);

    // To the end.
    w.activate(global.get_current_time());
    for (let i = 0; i < 100; i++)
        await press(Clutter.KEY_space);
    await sleep(900);
    await shot('07-finish', pad(rectOf(w), 20));
    check('last line reached', progress().surahs?.['56']?.line === 96, `line=${progress().surahs?.['56']?.line}`);
    await press(Clutter.KEY_Return);
    await sleep(1200);
    check('finish counted', progress().surahs?.['56']?.finished === 1);
    check('back to the start', progress().surahs?.['56']?.line === 0);
    await shot('08-after-finish', pad(rectOf(w), 20));

    // Where you left off: move, close, reopen.
    for (let i = 0; i < 5; i++)
        await press(Clutter.KEY_space);
    await sleep(500);
    await press(Clutter.KEY_Control_L, Clutter.KEY_q);
    check('ctrl+q closes it', await waitGone());
    launch();
    w = await waitWindow();
    await sleep(1200);
    check('reopens', !!w);
    check('reopens at the same place', progress().surahs?.['56']?.line === 5 && progress().surah === 56);
    await shot('09-reopened', pad(rectOf(w), 20));

    // A second launch while open switches the surah in the same window.
    launch('--surah', '112');
    await sleep(2500);
    check('one window only', hifzWindows().length === 1, `${hifzWindows().length}`);
    check('switches surah', progress().surah === 112);
    await shot('10-ikhlas', pad(rectOf(hifzWindows()[0]), 20));

    // A long ayah scrolls inside itself.
    launch('--surah', '2');
    await sleep(2500);
    await shot('11-baqara', pad(rectOf(hifzWindows()[0]), 20));

    // Close button on hover.
    w = hifzWindows()[0];
    w.activate(global.get_current_time());
    const r2 = rectOf(w);
    await move(r2[0] + 100, r2[1] + 100);
    await sleep(400);
    await shot('12-hover', pad(r2, 20));
    out('DONE');
}

async function menuTest() {
    Main.overview.hide();
    await sleep(1000);
    launch('--surah', '2');
    const w = await waitWindow();
    await sleep(1500);
    w.activate(global.get_current_time());
    await press(Clutter.KEY_Shift_L);
    await move(10, 10);
    const r = rectOf(w);
    for (let i = 0; i < 3; i++)
        await press(Clutter.KEY_space);
    await sleep(700);
    await shot('l1', pad(r, 10));
    await press(Clutter.KEY_a);
    await sleep(800);
    await shot('l2-arabic', pad(r, 10));
    await sleep(2500);
    await shot('l2b-arabic', pad(r, 10));
    await move(r[0] + 100, r[1] + 100);
    await sleep(500);
    await shot('l2c-arabic', pad(r, 10));
    await press(Clutter.KEY_a);
    launch('--surah', '2');
    await sleep(400);
    // 2:282, the longest ayah: space scrolls inside it before moving on.
    for (let i = 0; i < 280; i++)
        await press(Clutter.KEY_space);
    await sleep(800);
    await shot('l3-282a', pad(r, 10));
    await press(Clutter.KEY_space);
    await sleep(700);
    await shot('l4-282b', pad(r, 10));
    await press(Clutter.KEY_space);
    await sleep(700);
    await shot('l5-282c', pad(r, 10));
    for (let i = 0; i < 6; i++)
        await press(Clutter.KEY_space);
    await sleep(700);
    await shot('l6-later', pad(r, 10));
    out(JSON.stringify(progress()));
    out('DONE');
}

// With the sound on, "continue automatically" and 2x, Al-Ikhlâs moves on by itself to the end.
async function audioTest() {
    Main.overview.hide();
    await sleep(1000);
    launch('--surah', '112');
    const w = await waitWindow();
    await sleep(1500);
    w.activate(global.get_current_time());
    await press(Clutter.KEY_Shift_L);
    const t0 = Date.now();
    await press(Clutter.KEY_m);
    const seen = [];
    for (let t = 0; t < 40000; t += 250) {
        await sleep(250);
        const l = progress().surahs?.['112']?.line;
        if (seen[seen.length - 1]?.[0] !== l)
            seen.push([l, Date.now() - t0]);
        if (l === 4)
            break;
    }
    await sleep(4000);
    await shot('a1-end', pad(rectOf(w), 10));
    out(`lines over time ${JSON.stringify(seen)}`);
    check('auto-continue reaches the last ayah', seen.some(([l]) => l === 4));
    out('DONE');
}

let started = false;

export default class HifzTest extends Extension {
    enable() {
        if (started)
            return;
        started = true;
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 3000, () => {
            const run = MODE === 'audio' ? audioTest() : MODE === 'menu' ? menuTest() : MODE === 'demo' ? import('./demo.js').then(m => m.demo({
                shot, press, click, move, launch, waitWindow, rectOf, hifzWindows, sleep, out, backdrop,
            })) : checks();
            run.catch(e => out(`ERROR ${e}\n${e.stack}`)).finally(() => {
                for (const p of procs)
                    p.force_exit();
                GLib.timeout_add(GLib.PRIORITY_DEFAULT, 500, () => {
                    global.context.terminate();
                    return GLib.SOURCE_REMOVE;
                });
            });
            return GLib.SOURCE_REMOVE;
        });
    }

    disable() {}
}
