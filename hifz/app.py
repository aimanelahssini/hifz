"""The Hifz window: a small fixed-size prompter that slides one ayah up per key press."""

import sys

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Graphene', '1.0')
from gi.repository import Adw, Gdk, Gio, GLib, Graphene, Gtk, Pango  # noqa: E402

from . import APP_ID, quran  # noqa: E402
from .audio import RECITERS, Downloader, Player  # noqa: E402
from .state import SPEEDS, State  # noqa: E402

WIDTH, HEIGHT = 440, 212
PAD = 18
HEAD = 30
VIEW = HEIGHT - HEAD - PAD          # the part where the lines scroll
SLIDE_MS = 420

CSS = """
window.hifz, window.hifz.background { background: none; box-shadow: none; }
.card {
  background-color: rgba(16, 16, 20, 0.76);
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.09);
}
.head { padding: 0 10px 0 16px; min-height: 30px; }
.head label { font-size: 11px; color: rgba(255, 255, 255, 0.52); }
.head .surah { font-weight: 600; color: rgba(255, 255, 255, 0.72); }
.head button {
  min-height: 22px; min-width: 22px; padding: 2px; border-radius: 99px;
  color: rgba(255, 255, 255, 0.45); background: none; box-shadow: none;
}
.head button:hover { color: white; background: rgba(255, 255, 255, 0.10); }
.head button.on { color: white; }
.head .close { opacity: 0; transition: opacity 160ms ease; }
.card:hover .head .close { opacity: 1; }
.count {
  font-size: 11px; font-weight: 700; color: rgba(255, 255, 255, 0.60);
  background: rgba(255, 255, 255, 0.08); border-radius: 99px; padding: 1px 8px 1px 6px;
  transition: background 300ms ease, color 300ms ease;
}
.count.zero { color: rgba(255, 255, 255, 0.32); }
.count.bump { background: rgba(120, 220, 160, 0.30); color: white; }
.line {
  font-size: 19px; font-weight: 500; letter-spacing: 0.005em;
  color: rgba(255, 255, 255, 0.56);
  transition: color 360ms ease, opacity 360ms ease;
}
.line.current { color: #ffffff; text-shadow: 0 1px 2px rgba(0, 0, 0, 0.35); }
.line.d1 { opacity: 1; }
.line.d2 { opacity: 0.78; }
.line.d3 { opacity: 0.58; }
.line.far { opacity: 0.42; }
.line.past { opacity: 0; }
.line .ar {
  font-family: "Amiri Quran", "Amiri", "KFGQPC Uthmanic Script HAFS", "Noto Naskh Arabic", serif;
  font-size: 18px; font-weight: 400; opacity: 0.85;
}
.lines { padding: 0 20px 0 18px; }
.content { transition: filter 260ms ease, opacity 260ms ease; }
.content.blurred { filter: blur(7px); opacity: 0.55; }
.finish { background: rgba(10, 10, 14, 0.30); border-radius: 18px; }
.finish .question { font-size: 17px; font-weight: 600; color: white; }
.finish .sub { font-size: 12px; color: rgba(255, 255, 255, 0.60); }
.finish button {
  border-radius: 99px; padding: 6px 18px; font-weight: 600;
  background: rgba(255, 255, 255, 0.12); color: white; box-shadow: none;
}
.finish button:hover { background: rgba(255, 255, 255, 0.20); }
.finish button.yes { background: #ffffff; color: #111114; }
.finish button.yes:hover { background: rgba(255, 255, 255, 0.86); }
.hint { font-size: 11px; color: rgba(255, 255, 255, 0.50); }
"""


class LineView(Gtk.Box):
    def __init__(self, line):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.add_css_class('line')
        self.line = line
        self.ph = Gtk.Label(label=line.phonetic, xalign=0, wrap=True,
                            wrap_mode=Pango.WrapMode.WORD_CHAR, justify=Gtk.Justification.LEFT)
        self.ph.set_max_width_chars(1)        # wrap at the box width, never widen it
        self.ph.set_hexpand(True)
        self.append(self.ph)
        self.ar = Gtk.Label(label=line.arabic, xalign=1, wrap=True,
                            wrap_mode=Pango.WrapMode.WORD_CHAR)
        self.ar.set_max_width_chars(1)
        self.ar.set_hexpand(True)
        self.ar.set_direction(Gtk.TextDirection.RTL)
        self.ar.add_css_class('ar')
        self.ar.set_visible(False)
        self.append(self.ar)

    def set_distance(self, d):
        for c in ('current', 'd1', 'd2', 'd3', 'far', 'past'):
            self.remove_css_class(c)
        if d < 0:
            self.add_css_class('past')
        elif d == 0:
            self.add_css_class('current')
        elif d <= 3:
            self.add_css_class(f'd{d}')
        else:
            self.add_css_class('far')


class Prompter(Adw.ApplicationWindow):
    def __init__(self, app, state, surah):
        super().__init__(application=app, title='Hifz')
        self.state = state
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(WIDTH, HEIGHT)
        self.add_css_class('hifz')

        self.audio_on = False      # always starts muted
        self.player = Player(self._audio_ended)
        self.player.set_speed(state.speed)
        self.downloads = Downloader()
        self.anim = None
        self.views = []
        self.index = 0
        self.finishing = False
        self.scroll_acc = 0.0

        self._build()
        self._actions()
        self.load_surah(surah)

        keys = Gtk.EventControllerKey()
        # Capture phase: space must move the text, never press a focused button.
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect('key-pressed', self._key)
        self.add_controller(keys)
        scroll = Gtk.EventControllerScroll(flags=Gtk.EventControllerScrollFlags.VERTICAL)
        scroll.connect('scroll', self._scroll)
        self.add_controller(scroll)
        click = Gtk.GestureClick(button=3)
        click.connect('pressed', self._menu_at)
        self.add_controller(click)
        self.connect('close-request', self._closing)

    # ---------- building ----------

    def _build(self):
        card = Gtk.Overlay()
        card.add_css_class('card')
        card.set_overflow(Gtk.Overflow.HIDDEN)
        card.set_size_request(WIDTH - 2, HEIGHT - 2)   # + 1px border on each side
        self.set_content(card)

        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.content.add_css_class('content')
        card.set_child(self.content)

        head = Gtk.Box(spacing=4)
        head.add_css_class('head')
        head.set_size_request(-1, HEAD)
        self.title = Gtk.Label(xalign=0)
        self.title.add_css_class('surah')
        self.where = Gtk.Label(xalign=0)
        self.where.set_hexpand(True)
        close = Gtk.Button(icon_name='window-close-symbolic', tooltip_text='Close (Ctrl+Q)',
                           valign=Gtk.Align.CENTER)
        close.add_css_class('close')
        close.connect('clicked', lambda *_: self.close())
        self.audio_btn = Gtk.Button(icon_name='audio-volume-muted-symbolic', valign=Gtk.Align.CENTER,
                                    tooltip_text='Recitation off (M)')
        self.audio_btn.connect('clicked', lambda *_: self.toggle_audio())
        self.spinner = Gtk.Spinner(visible=False)
        self.spinner.set_size_request(12, 12)
        count_box = Gtk.Box(spacing=3, valign=Gtk.Align.CENTER)
        count_box.add_css_class('count')
        count_box.append(Gtk.Image(icon_name='object-select-symbolic', pixel_size=10))
        self.count = Gtk.Label()
        count_box.append(self.count)
        self.count_box = count_box
        count_box.set_tooltip_text('Times you finished this surah')
        for w in (self.title, self.where, close, self.spinner, self.audio_btn, count_box):
            w.set_focusable(False)
            head.append(w)
        self.content.append(head)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.box.add_css_class('lines')
        self.scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                           vscrollbar_policy=Gtk.PolicyType.EXTERNAL)
        self.scroller.set_size_request(-1, VIEW)
        self.scroller.set_propagate_natural_height(False)
        self.scroller.set_kinetic_scrolling(False)
        self.scroller.set_child(self.box)
        self.scroller.set_vexpand(True)
        self.scroller.set_margin_top(6)
        self.content.append(self.scroller)

        # The "did you finish?" question, over a blurred copy of the text.
        fin = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                      halign=Gtk.Align.FILL, valign=Gtk.Align.FILL)
        fin.add_css_class('finish')
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                        halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, vexpand=True)
        self.question = Gtk.Label()
        self.question.add_css_class('question')
        self.sub = Gtk.Label()
        self.sub.add_css_class('sub')
        row = Gtk.Box(spacing=10, halign=Gtk.Align.CENTER)
        row.set_margin_top(10)
        no = Gtk.Button(label='Not yet')
        no.connect('clicked', lambda *_: self.answer(False))
        yes = Gtk.Button(label='Yes, I finished')
        yes.add_css_class('yes')
        yes.connect('clicked', lambda *_: self.answer(True))
        row.append(no)
        row.append(yes)
        for w in (self.question, self.sub, row):
            inner.append(w)
        fin.append(inner)
        fin.set_visible(False)
        self.finish = fin
        self.yes_btn = yes
        card.add_overlay(fin)

    def _actions(self):
        speed = Gio.SimpleAction.new_stateful('speed', GLib.VariantType('s'),
                                              GLib.Variant('s', fmt_speed(self.state.speed)))
        speed.connect('activate', self._set_speed)
        self.add_action(speed)
        reciter = Gio.SimpleAction.new_stateful('reciter', GLib.VariantType('s'),
                                                GLib.Variant('s', self.state.reciter))
        reciter.connect('activate', self._set_reciter)
        self.add_action(reciter)
        arabic = Gio.SimpleAction.new_stateful('arabic', None, GLib.Variant('b', self.state.show_arabic))
        arabic.connect('activate', self._toggle_arabic)
        self.add_action(arabic)
        auto = Gio.SimpleAction.new_stateful('auto', None, GLib.Variant('b', self.state.auto))
        auto.connect('activate', self._toggle_auto)
        self.add_action(auto)
        audio = Gio.SimpleAction.new_stateful('audio', None, GLib.Variant('b', False))
        audio.connect('activate', lambda *_: self.toggle_audio())
        self.add_action(audio)
        for name, cb in (('restart', lambda *_: self.go(0, slow=True)),
                         ('close', lambda *_: self.close())):
            a = Gio.SimpleAction.new(name, None)
            a.connect('activate', cb)
            self.add_action(a)

        menu = Gio.Menu()
        speeds = Gio.Menu()
        for s in SPEEDS:
            item = Gio.MenuItem.new(f'{fmt_speed(s)}×', None)
            item.set_action_and_target_value('win.speed', GLib.Variant('s', fmt_speed(s)))
            speeds.append_item(item)
        menu.append_section('Speed', speeds)
        opts = Gio.Menu()
        opts.append('Recitation', 'win.audio')
        reciters = Gio.Menu()
        for rid, rname in RECITERS:
            item = Gio.MenuItem.new(rname, None)
            item.set_action_and_target_value('win.reciter', GLib.Variant('s', rid))
            reciters.append_item(item)
        opts.append_submenu('Reciter', reciters)
        opts.append('Continue automatically', 'win.auto')
        opts.append('Show Arabic', 'win.arabic')
        menu.append_section(None, opts)
        end = Gio.Menu()
        end.append('Back to the beginning', 'win.restart')
        end.append('Close', 'win.close')
        menu.append_section(None, end)
        self.menu = Gtk.PopoverMenu.new_from_model(menu)
        self.menu.set_parent(self.get_content())
        self.menu.set_has_arrow(False)

    # ---------- surah and lines ----------

    def load_surah(self, n):
        if self.anim:
            self.anim.pause()
        self.player.halt()
        self.surah = n
        self.state.surah = n
        self.lines = quran.lines(n)
        child = self.box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.box.remove(child)
            child = nxt
        self.views = [LineView(line) for line in self.lines]
        for v in self.views:
            v.ar.set_visible(self.state.show_arabic)
            self.box.append(v)
        spacer = Gtk.Box()
        spacer.set_size_request(-1, VIEW)          # lets the last line slide to the top
        self.box.append(spacer)
        self.title.set_label(quran.name(n))
        self.index = min(self.state.line(n), len(self.lines) - 1)
        self._hide_finish()
        self._refresh()
        self.state.save()
        # Jump (no slide) once the new lines have their size.
        GLib.idle_add(self._snap)

        if self.audio_on:
            self._prefetch_all()
            self._play_current()

    def _snap(self):
        y = self._y(self.index)
        if y is None:
            GLib.timeout_add(16, self._snap)
            return GLib.SOURCE_REMOVE
        self.scroller.get_vadjustment().set_value(y)
        return GLib.SOURCE_REMOVE

    def _y(self, i):
        ok, p = self.views[i].compute_point(self.box, Graphene.Point())
        if not ok or self.views[i].get_height() == 0:
            return None
        return p.y

    def _refresh(self):
        for k, v in enumerate(self.views):
            v.set_distance(k - self.index)
        line = self.lines[self.index]
        total = quran.SURAHS[self.surah - 1][1]
        self.where.set_label(f'  ·  {line.ayah} / {total}' if line.ayah else '  ·  Bismillah')
        n = self.state.finished(self.surah)
        self.count.set_label(str(n))
        (self.count_box.add_css_class if n == 0 else self.count_box.remove_css_class)('zero')

    def _slide_to(self, y, ms=SLIDE_MS):
        adj = self.scroller.get_vadjustment()
        if self.anim:
            self.anim.pause()
        target = Adw.CallbackAnimationTarget.new(adj.set_value)
        self.anim = Adw.TimedAnimation.new(self.scroller, adj.get_value(), y, ms, target)
        self.anim.set_easing(Adw.Easing.EASE_OUT_CUBIC)
        self.anim.play()

    def go(self, i, slow=False):
        i = max(0, min(i, len(self.lines) - 1))
        self.index = i
        self.state.set_line(self.surah, i)
        self.state.save()
        self._refresh()
        y = self._y(i)
        if y is not None:
            self._slide_to(y, 700 if slow else SLIDE_MS)
        if self.audio_on:
            self._play_current()

    def next(self):
        if self.finishing:
            return
        # A long ayah taller than the window scrolls inside itself first.
        adj = self.scroller.get_vadjustment()
        view = self.views[self.index]
        top = self._y(self.index) or 0
        bottom = top + view.get_height()
        shown = self.anim.get_value_to() if self.anim and self.anim.get_state() == Adw.AnimationState.PLAYING else adj.get_value()
        if bottom > shown + VIEW - 8:
            self._slide_to(min(shown + VIEW * 0.7, bottom - VIEW * 0.5))
            return
        if self.index >= len(self.lines) - 1:
            self._ask_finish()
            return
        self.go(self.index + 1)

    def prev(self):
        if self.finishing:
            self._hide_finish()
            return
        adj = self.scroller.get_vadjustment()
        top = self._y(self.index) or 0
        if adj.get_value() > top + 4:
            self._slide_to(max(top, adj.get_value() - VIEW * 0.7))
            return
        if self.index > 0:
            self.go(self.index - 1)

    # ---------- finishing ----------

    def _ask_finish(self):
        self.finishing = True
        self.question.set_label(f'Finished {quran.name(self.surah)}?')
        n = self.state.finished(self.surah)
        self.sub.set_label('It will count as your first time' if n == 0 else
                           f'Finished {n} time{"s" if n != 1 else ""} so far')
        self.content.add_css_class('blurred')
        self.finish.set_visible(True)
        self.yes_btn.grab_focus()

    def _hide_finish(self):
        self.finishing = False
        self.content.remove_css_class('blurred')
        self.finish.set_visible(False)

    def answer(self, yes):
        self._hide_finish()
        if not yes:
            return
        self.state.add_finish(self.surah)
        self.state.save()
        self.count_box.add_css_class('bump')
        GLib.timeout_add(900, lambda: self.count_box.remove_css_class('bump') or GLib.SOURCE_REMOVE)
        self.player.halt()
        self.go(0, slow=True)

    # ---------- audio ----------

    def toggle_audio(self):
        self.audio_on = not self.audio_on
        self.lookup_action('audio').set_state(GLib.Variant('b', self.audio_on))
        if self.audio_on:
            self.player.start()
            self.player.set_speed(self.state.speed)
            self.audio_btn.set_icon_name('audio-volume-high-symbolic')
            self.audio_btn.add_css_class('on')
            self.audio_btn.set_tooltip_text('Recitation on (M)')
            self._prefetch_all()
            self._play_current()
        else:
            self.player.stop()     # the whole pipeline goes away: no sound at all
            self.audio_btn.set_icon_name('audio-volume-muted-symbolic')
            self.audio_btn.remove_css_class('on')
            self.audio_btn.set_tooltip_text('Recitation off (M)')
            self._loading(False)

    def _play_current(self):
        self.player.halt()
        want = (self.state.reciter, self.surah, self.lines[self.index].ayah)
        self._want = want

        def ready(path):
            if not self.audio_on or self._want != want:
                return
            self._loading(False)
            if path:
                self.audio_btn.set_icon_name('audio-volume-high-symbolic')
                self.audio_btn.set_tooltip_text('Recitation on (M)')
                self.player.play(path)
            else:
                # No connection, or the server is down: say so on the speaker.
                self.audio_btn.set_icon_name('network-offline-symbolic')
                self.audio_btn.set_tooltip_text("Couldn't download this ayah's recitation")
        self._loading(True)
        self.downloads.fetch(*want, done=ready, urgent=True)

    def _prefetch_all(self):
        for line in self.lines[self.index:] + self.lines[:self.index]:
            self.downloads.fetch(self.state.reciter, self.surah, line.ayah)

    def _loading(self, on):
        # Only show the spinner if the file takes a moment.
        if getattr(self, '_spin_id', 0):
            GLib.source_remove(self._spin_id)
            self._spin_id = 0
        if on:
            def show():
                self._spin_id = 0
                self.spinner.set_visible(True)
                self.spinner.start()
                return GLib.SOURCE_REMOVE
            self._spin_id = GLib.timeout_add(250, show)
        else:
            self.spinner.stop()
            self.spinner.set_visible(False)

    def _audio_ended(self):
        if not (self.audio_on and self.state.auto) or self.finishing:
            return
        if self.index >= len(self.lines) - 1:
            self._ask_finish()
        else:
            self.go(self.index + 1)

    # ---------- menu actions ----------

    def _set_speed(self, action, value):
        action.set_state(value)
        self.state.speed = float(value.get_string())
        self.state.save()
        self.player.set_speed(self.state.speed)

    def _set_reciter(self, action, value):
        action.set_state(value)
        self.state.reciter = value.get_string()
        self.state.save()
        if self.audio_on:
            self._prefetch_all()
            self._play_current()

    def _toggle_arabic(self, action, _):
        on = not action.get_state().get_boolean()
        action.set_state(GLib.Variant('b', on))
        self.state.show_arabic = on
        self.state.save()
        for v in self.views:
            v.ar.set_visible(on)
        GLib.idle_add(self._snap)


    def _toggle_auto(self, action, _):
        on = not action.get_state().get_boolean()
        action.set_state(GLib.Variant('b', on))
        self.state.auto = on
        self.state.save()

    def _menu_at(self, gesture, n, x, y):
        r = Gdk.Rectangle()
        r.x, r.y, r.width, r.height = int(x), int(y), 1, 1
        self.menu.set_pointing_to(r)
        self.menu.popup()


    # ---------- input ----------

    def _key(self, ctl, keyval, code, mods):
        # The input method can hand the same letter key over twice; act on it once.
        stamp = (keyval, ctl.get_current_event_time())

        if stamp == getattr(self, '_last_key', None):
            return True
        self._last_key = stamp
        ctrl = mods & Gdk.ModifierType.CONTROL_MASK
        if ctrl and keyval in (Gdk.KEY_q, Gdk.KEY_w):
            self.close()
            return True
        if self.finishing:
            if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_y):
                self.answer(True)
            elif keyval in (Gdk.KEY_Escape, Gdk.KEY_n, Gdk.KEY_BackSpace):
                self.answer(False)
            return True
        if keyval in (Gdk.KEY_space, Gdk.KEY_Down, Gdk.KEY_Right, Gdk.KEY_Page_Down, Gdk.KEY_j):
            self.next()
        elif keyval in (Gdk.KEY_BackSpace, Gdk.KEY_Up, Gdk.KEY_Left, Gdk.KEY_Page_Up, Gdk.KEY_k):
            self.prev()
        elif keyval in (Gdk.KEY_m, Gdk.KEY_M):
            self.toggle_audio()
        elif keyval in (Gdk.KEY_a, Gdk.KEY_A):
            self.activate_action('win.arabic', None)
        elif keyval == Gdk.KEY_Home:
            self.go(0, slow=True)
        elif keyval == Gdk.KEY_Menu:
            self._menu_at(None, 1, WIDTH - 40, HEAD)
        else:
            return False
        return True

    def _scroll(self, ctl, dx, dy):
        if self.finishing:
            return True
        unit = ctl.get_unit() if hasattr(ctl, 'get_unit') else Gdk.ScrollUnit.WHEEL
        self.scroll_acc += dy if unit == Gdk.ScrollUnit.WHEEL else dy / 40
        while self.scroll_acc >= 1:
            self.scroll_acc -= 1
            self.next()
        while self.scroll_acc <= -1:
            self.scroll_acc += 1
            self.prev()
        return True

    def _closing(self, *_):
        self.player.stop()
        self.state.save()
        return False


def fmt_speed(s):
    return f'{s:g}'


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.win = None

    def do_startup(self):
        Adw.Application.do_startup(self)
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        css = Gtk.CssProvider()
        css.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def do_command_line(self, cmd):
        args = cmd.get_arguments()[1:]
        surah = None
        if '--surah' in args:
            try:
                surah = int(args[args.index('--surah') + 1])
            except (IndexError, ValueError):
                surah = None
        if surah is not None and not 1 <= surah <= 114:
            surah = None
        if self.win is None:
            state = State.load()
            self.win = Prompter(self, state, surah or state.surah)
            self.win.connect('destroy', lambda *_: setattr(self, 'win', None))
        elif surah:
            self.win.load_surah(surah)
        self.win.present()
        return 0


def main():
    return App().run(sys.argv)
