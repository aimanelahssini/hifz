// Keeps the Hifz window in the top-right corner, always on top and on every desktop.
// Wayland apps can't place themselves or ask to stay on top, so the shell does it for them.
import GLib from 'gi://GLib';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const APP_ID = 'io.github.aimanelahssini.Hifz';
const MARGIN = 12;

export default class HifzExtension extends Extension {
    enable() {
        this._windows = new Map();
        this._pending = new Map();
        this._timeouts = new Set();
        this._created = global.display.connect('window-created', (_d, w) => this._watch(w, true));
        this._workareas = global.display.connect('workareas-changed', () => this._placeAll());
        for (const actor of global.get_window_actors())
            this._watch(actor.meta_window, false);
    }

    disable() {
        global.display.disconnect(this._created);
        global.display.disconnect(this._workareas);
        for (const [w, id] of this._pending)
            w.disconnect(id);
        this._pending = null;
        this._timeouts.forEach(id => GLib.source_remove(id));
        this._timeouts = null;
        for (const [w, ids] of this._windows) {
            ids.forEach(id => w.disconnect(id));
            if (w.is_above())
                w.unmake_above();
            if (w.is_on_all_workspaces())
                w.unstick();
        }
        this._windows = null;
    }

    _isHifz(w) {
        return w.get_gtk_application_id() === APP_ID || w.get_wm_class() === APP_ID;
    }

    _watch(w, fresh) {
        if (!w || this._windows.has(w) || this._pending.has(w))
            return;
        if (!this._isHifz(w)) {
            // The app id can arrive a moment after the window does.
            const id = w.connect('notify::wm-class', () => {
                w.disconnect(id);
                this._pending.delete(w);
                this._watch(w, fresh);
            });
            this._pending.set(w, id);
            w.connect('unmanaged', () => this._pending?.delete(w));
            return;
        }
        const ids = [
            w.connect('size-changed', () => this._place(w)),
            w.connect('unmanaged', () => this._windows?.delete(w)),
        ];
        this._windows.set(w, ids);
        // A new window is pinned once it is shown: by then mutter has placed it and it is in
        // the stack. Placing it any earlier gets overridden by mutter's own placement.
        if (fresh) {
            const id = w.connect('shown', () => {
                w.disconnect(id);
                this._pin(w);
            });
        } else {
            this._pin(w);
        }
    }

    _pin(w) {
        if (!this._windows?.has(w))
            return;
        w.make_above();
        w.stick();
        this._place(w);
        // Mutter can still apply the client's first configure after this; place it again.
        for (const ms of [50, 200, 600]) {
            const id = GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
                this._timeouts?.delete(id);
                if (this._windows?.has(w))
                    this._place(w);
                return GLib.SOURCE_REMOVE;
            });
            this._timeouts.add(id);
        }
    }

    _place(w) {
        const r = w.get_frame_rect();
        if (r.width <= 1)
            return;
        const monitor = global.display.get_primary_monitor();
        const area = global.workspace_manager.get_active_workspace().get_work_area_for_monitor(monitor);
        const x = area.x + area.width - r.width - MARGIN;
        const y = area.y + MARGIN;
        if (r.x !== x || r.y !== y)
            w.move_frame(true, x, y);
    }

    _placeAll() {
        for (const w of this._windows.keys())
            this._place(w);
    }
}
