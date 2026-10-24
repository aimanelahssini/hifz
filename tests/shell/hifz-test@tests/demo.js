// Records the demo video in the headless test shell (tests/shell/demo.sh). The screen is
// recorded with GNOME's own screencast; the recitation is added afterwards from play.log,
// because the test session has no sound output at all.
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const OUT = GLib.getenv('HIFZ_OUT');
const call = (name, path, iface, method, params, type = null) => new Promise((resolve, reject) => {
    Gio.DBus.session.call(name, path, iface, method, params, type ? new GLib.VariantType(type) : null,
        Gio.DBusCallFlags.NONE, -1, null, (c, res) => {
            try {
                resolve(c.call_finish(res).deepUnpack());
            } catch (e) {
                reject(e);
            }
        });
});

// HiDPI: scale 2 on the 2560x1440 virtual monitor, so the zoomed part of the video is sharp.
async function scale2() {
    const [serial, monitors] = await call('org.gnome.Mutter.DisplayConfig', '/org/gnome/Mutter/DisplayConfig',
        'org.gnome.Mutter.DisplayConfig', 'GetCurrentState', null);
    const [spec, modes] = monitors[0];
    const mode = modes.find(m => m[6]['is-current']?.deepUnpack?.() ?? m[6]['is-current']) ?? modes[0];
    const config = new GLib.Variant('(uua(iiduba(ssa{sv}))a{sv})', [serial, 1,
        [[0, 0, 2.0, 0, true, [[spec[0], mode[0], {}]]]], {}]);
    await call('org.gnome.Mutter.DisplayConfig', '/org/gnome/Mutter/DisplayConfig',
        'org.gnome.Mutter.DisplayConfig', 'ApplyMonitorsConfig', config);
}

const screencast = (method, params) => call('org.gnome.Shell.Screencast', '/org/gnome/Shell/Screencast',
    'org.gnome.Shell.Screencast', method, params);

export async function demo(h) {
    const {press, launch, waitWindow, rectOf, hifzWindows, sleep, out} = h;
    let pointer;
    const now = () => GLib.get_monotonic_time();
    let px = 0, py = 0;
    async function glide(x, y, ms = 600) {
        pointer ??= Clutter.get_default_backend().get_default_seat()
            .create_virtual_device(Clutter.InputDeviceType.POINTER_DEVICE);
        const steps = Math.max(1, Math.round(ms / 16));
        const [x0, y0] = [px, py];
        for (let i = 1; i <= steps; i++) {
            const k = i / steps;
            const e = k < 0.5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2;
            pointer.notify_absolute_motion(now(), x0 + (x - x0) * e, y0 + (y - y0) * e);
            await sleep(16);
        }
        [px, py] = [x, y];
    }
    async function clickAt(x, y, button = Clutter.BUTTON_PRIMARY, ms = 600) {
        await glide(x, y, ms);
        await sleep(150);
        pointer.notify_button(now(), button, Clutter.ButtonState.PRESSED);
        await sleep(70);
        pointer.notify_button(now(), button, Clutter.ButtonState.RELEASED);
        await sleep(100);
    }
    async function type(text, gap = 110) {
        for (const ch of text) {
            await press(ch === '\n' ? Clutter.KEY_Return : Clutter.unicode_to_keysym(ch.codePointAt(0)));
            await sleep(gap);
        }
    }
    const playLog = () => {
        try {
            return new TextDecoder().decode(GLib.file_get_contents(`${OUT}/play.log`)[1]).trim().split('\n');
        } catch (e) {
            return [];
        }
    };

    Main.overview.hide();
    // No "recording" dot in the top bar of the video.
    const hideRecording = actor => {
        const cls = actor.style_class ?? '';
        const icon = actor.icon_name ?? actor.gicon?.to_string?.() ?? '';
        if (/screencast|recording|screen-shar/.test(cls) || /record|screencast|screen-shared|battery-missing/.test(icon))
            actor.opacity = 0;
        for (const c of actor.get_children())
            hideRecording(c);
    };
    GLib.timeout_add(GLib.PRIORITY_DEFAULT, 50, () => {
        hideRecording(Main.panel);
        return GLib.SOURCE_CONTINUE;
    });
    await scale2();
    await sleep(1500);
    h.backdrop();
    await sleep(2500);
    // The notes window on the left, out of the zoomed corner.
    global.display.list_all_windows().find(x => x.get_title() === 'Notes')?.move_frame(true, 90, 130);
    await sleep(500);
    // Park the pointer on the notes window.
    await glide(700, 500, 10);

    const [ok, file] = await screencast('Screencast', new GLib.Variant('(sa{sv})', [`${OUT}/raw.webm`, {
        'draw-cursor': new GLib.Variant('b', true),
        'framerate': new GLib.Variant('i', 30),
    }]));
    const t0 = now();
    GLib.file_set_contents(`${OUT}/record-start.txt`, `${t0}\n`);
    out(`screencast ${ok} ${file}`);
    const mark = name => out(`mark ${name} ${((now() - t0) / 1e6).toFixed(2)}`);
    await sleep(1500);

    // 1. Type `quran` in a terminal and pick 56.
    mark('terminal');
    const term = new Gio.SubprocessLauncher({flags: Gio.SubprocessFlags.NONE});
    term.spawnv(['python3', `${GLib.getenv('HIFZ_REPO')}/tests/shell/term.py`]);
    let tw = null;
    for (let t = 0; t < 20000 && !tw; t += 100) {
        await sleep(100);
        tw = global.display.list_all_windows().find(x => x.get_title() === 'Terminal' &&
            x.get_compositor_private()?.visible);
    }
    await sleep(1500);
    tw?.activate(global.get_current_time());
    await sleep(300);
    await press(Clutter.KEY_Shift_L);   // the first virtual key event gets lost
    await sleep(300);
    await type('quran\n', 140);
    await sleep(2200);
    await type('56', 260);
    await sleep(500);
    await type('\n');
    let w = await waitWindow();
    mark('hifz-open');
    await sleep(1800);
    tw?.activate(global.get_current_time());
    await sleep(400);
    await type('exit\n', 90);
    await sleep(1500);

    // 2. Read with Space.
    mark('zoom');
    const r = rectOf(w);
    const S = r[2] / 440;             // stage pixels per app pixel (2 on this HiDPI monitor)
    const at = (x, y) => [r[0] + x * S, r[1] + y * S];
    w.activate(global.get_current_time());
    await glide(...at(260, 150), 900);
    await sleep(800);
    for (let i = 0; i < 4; i++) {
        await press(Clutter.KEY_space);
        await sleep(1500);
    }
    await press(Clutter.KEY_BackSpace);
    await sleep(1300);
    await press(Clutter.KEY_space);
    await sleep(1200);

    // 3. Every surah from the name: the list, then back.
    mark('dropdown');
    await clickAt(...at(60, 15), Clutter.BUTTON_PRIMARY, 700);
    await sleep(2200);
    await press(Clutter.KEY_Escape);
    await sleep(600);

    // 4. Right-click: "Continue automatically", then the sound on.
    mark('menu');
    await clickAt(...at(250, 120), Clutter.BUTTON_SECONDARY, 500);
    await sleep(900);
    // The first item is already selected: 10 down is "Continue automatically".
    for (let i = 0; i < 10; i++) {
        await press(Clutter.KEY_Down);
        await sleep(110);
    }
    await sleep(500);
    await press(Clutter.KEY_Return);
    await sleep(700);
    mark('audio');
    await clickAt(...at(377, 16), Clutter.BUTTON_PRIMARY, 700);
    await glide(...at(300, 270), 700);
    const plays = () => playLog().filter(l => l.includes(' play ')).length;
    for (let t = 0; t < 40000 && plays() < 3; t += 100)
        await sleep(100);
    await sleep(1500);
    // Space pauses, Space plays on.
    mark('pause');
    await press(Clutter.KEY_space);
    await sleep(1800);
    await press(Clutter.KEY_space);
    for (let t = 0; t < 40000 && plays() < 4; t += 100)
        await sleep(100);
    // Faster with the right arrow, 0.05 a press, shown next to the speaker.
    mark('speed');
    for (let i = 0; i < 5; i++) {
        await press(Clutter.KEY_Right);
        await sleep(350);
    }
    // Mute as soon as the 7th ayah is over (the 8th has just begun).
    for (let t = 0; t < 40000 && plays() < 8; t += 50)
        await sleep(50);
    mark('mute');
    await clickAt(...at(377, 16), Clutter.BUTTON_PRIMARY, 60);
    await sleep(900);
    // After this surah: the next one.
    mark('mode');
    await clickAt(...at(306, 16), Clutter.BUTTON_PRIMARY, 700);
    await sleep(1800);

    // 5. Close it, and it opens again where you left off; near the end this time.
    mark('close');
    await press(Clutter.KEY_Control_L, Clutter.KEY_q);
    await sleep(1500);
    const path = `${GLib.get_user_state_dir()}/hifz/progress.json`;
    const state = JSON.parse(new TextDecoder().decode(GLib.file_get_contents(path)[1]));
    state.surahs['56'].line = 93;
    state.auto = false;
    GLib.file_set_contents(path, JSON.stringify(state));
    launch();
    w = await waitWindow();
    mark('reopen');
    await sleep(1500);
    w.activate(global.get_current_time());
    for (let i = 0; i < 3; i++) {
        await press(Clutter.KEY_space);
        await sleep(1400);
    }
    // 6. The end: "Finished?", Yes, and the counter goes up.
    mark('finish');
    await press(Clutter.KEY_space);
    await sleep(2000);
    await clickAt(...at(270, 144), Clutter.BUTTON_PRIMARY, 900);
    await sleep(3500);
    await glide(...at(-120, 330), 900);
    await sleep(800);
    mark('end');
    await screencast('StopScreencast', null);
    await sleep(1500);
    out(`windows ${hifzWindows().length}`);
    out('DONE');
}
