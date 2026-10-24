"""The Hifz window: a small fixed-size prompter that slides one ayah up per key press."""

import os
import sys

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Graphene', '1.0')
from gi.repository import Adw, Gdk, Gio, GLib, Graphene, Gtk, Pango  # noqa: E402

from . import APP_ID, quran  # noqa: E402
from .audio import RECITERS, Downloader, Player, file_for  # noqa: E402
from .state import SPEED_MAX, SPEED_MIN, SPEEDS, State  # noqa: E402

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
.head { padding: 0 10px 0 10px; min-height: 30px; }
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
.content.blurred { filter: blur(14px); opacity: 0.50; }
.finish { background: rgba(10, 10, 14, 0.45); border-radius: 18px; }
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
.head .pick { padding: 1px 6px; min-height: 20px; }
.head .pick label { color: rgba(255, 255, 255, 0.72); }
.head .pick .num { color: rgba(255, 255, 255, 0.45); font-weight: 600; }
.head .pick image { color: rgba(255, 255, 255, 0.40); }
.head .speed label { font-weight: 700; font-feature-settings: "tnum"; }
.endhint {
  font-size: 14px; font-weight: 600; font-style: italic; color: rgba(233, 196, 106, 0.90);
  transition: opacity 360ms ease;
}
.endhint.far { opacity: 0.35; }
popover.dropdown > contents { padding: 6px; min-width: 0; }
popover.dropdown list { background: none; }
popover.dropdown row { border-radius: 8px; padding: 5px 8px; min-height: 0; }
popover.dropdown row .num { color: alpha(currentColor, 0.45); font-feature-settings: "tnum"; }
popover.dropdown row .done { color: alpha(currentColor, 0.45); font-size: 12px; }
popover.dropdown row.here { background: rgba(233, 196, 106, 0.16); }
popover.dropdown row.here label { font-weight: 700; }
popover.dropdown entry { margin-bottom: 6px; }
popover.dropdown row .recited { color: #7ee2a8; }
popover.dropdown .section { font-size: 11px; font-weight: 700; color: alpha(currentColor, 0.5);
  padding: 8px 8px 3px; }
popover.dropdown row button.star {
  min-height: 20px; min-width: 20px; padding: 0; background: none; box-shadow: none;
  color: alpha(currentColor, 0.55); opacity: 0; transition: opacity 120ms ease;
}
popover.dropdown row:hover button.star { opacity: 1; }
popover.dropdown list row button.star.on { opacity: 1; }
popover.dropdown list row button.star.on image,
popover.dropdown list row button.star:hover image { color: #e9c46a; }
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
        self.player = Player(self._audio_ended, self._audio_next)
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
        self.number = Gtk.Label()
        self.number.add_css_class('num')
        pick = Gtk.Box(spacing=5)
        pick.append(self.number)
        pick.append(self.title)
        pick.append(Gtk.Image(icon_name='pan-down-symbolic', pixel_size=10))
        self.surah_pop = self._dropdown(search=True)
        self.surah_btn = Gtk.MenuButton(child=pick, popover=self.surah_pop, valign=Gtk.Align.CENTER,
                                        tooltip_text='Choose a surah')
        self.surah_btn.add_css_class('pick')
        self.surah_pop.connect('show', lambda *_: self._fill_surahs())
        self.speed_label = Gtk.Label()
        self.speed_pop = self._dropdown()
        self.speed_btn = Gtk.MenuButton(child=self.speed_label, popover=self.speed_pop,
                                        valign=Gtk.Align.CENTER, tooltip_text='Speed (← and →)')
        self.speed_btn.add_css_class('pick')
        self.speed_btn.add_css_class('speed')
        self.speed_pop.connect('show', lambda *_: self._fill_speeds())
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
        for w in (self.surah_btn, self.where, close, self.spinner, self.speed_btn, self.audio_btn, count_box):
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
        # Under the last ayah: what to do once you get there.
        self.endhint = Gtk.Label(label='Finished? Press Space or scroll', xalign=0)
        self.endhint.add_css_class('endhint')
        self.box.append(self.endhint)
        spacer = Gtk.Box()
        spacer.set_size_request(-1, VIEW)          # lets the last line slide to the top
        self.box.append(spacer)
        self.title.set_label(quran.name(n))
        self.number.set_label(str(n))
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
        last = len(self.lines) - 1
        (self.endhint.remove_css_class if last - self.index <= 3 else self.endhint.add_css_class)('far')
        self.speed_label.set_label(f'{fmt_speed(self.state.speed)}×')
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

    def go(self, i, slow=False, play=True):
        i = max(0, min(i, len(self.lines) - 1))
        self.index = i
        self.state.set_line(self.surah, i)
        self.state.save()
        self._refresh()
        y = self._y(i)
        if y is not None:
            self._slide_to(y, 700 if slow else SLIDE_MS)
        if self.audio_on and play:
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
                self._queue_next()
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

    def _queue_next(self):
        """With "continue automatically", line up the next ayah so it follows without a gap."""
        self.player.queued = None
        if self.audio_on and self.state.auto and self.index + 1 < len(self.lines):
            path, _ = file_for(self.state.reciter, self.surah, self.lines[self.index + 1].ayah)
            if os.path.exists(path):
                self.player.queued = path

    def _audio_next(self):
        # The queued ayah has started playing: move the text along with it.
        if self.finishing or self.index + 1 >= len(self.lines):
            return
        self.go(self.index + 1, play=False)
        self._queue_next()

    def _audio_ended(self):
        if not (self.audio_on and self.state.auto) or self.finishing:
            return
        if self.index >= len(self.lines) - 1:
            self._ask_finish()
        else:
            self.go(self.index + 1)

    # ---------- menu actions ----------

    def _set_speed(self, action, value):
        self.set_speed(float(value.get_string()))

    def set_speed(self, speed):
        """Any speed from 0.5x to 2x, in steps of 0.05; it is saved for next time."""
        speed = round(min(SPEED_MAX, max(SPEED_MIN, speed)) * 20) / 20
        self.state.speed = speed
        self.state.save()
        self.player.set_speed(speed)
        self.lookup_action('speed').set_state(GLib.Variant('s', fmt_speed(speed)))
        self.speed_label.set_label(f'{fmt_speed(speed)}×')

    # ---------- dropdowns ----------

    def _dropdown(self, search=False):
        pop = Gtk.Popover(has_arrow=False)
        pop.add_css_class('dropdown')
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        pop.entry = None
        if search:
            pop.entry = Gtk.SearchEntry(placeholder_text='Number or name')
            box.append(pop.entry)
        pop.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        pop.list.set_activate_on_single_click(True)
        pop.scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                        propagate_natural_height=True, max_content_height=300)
        pop.scroll.set_child(pop.list)
        box.append(pop.scroll)
        pop.set_child(box)
        # Give the keyboard back to the card, without a focus ring on the header button.
        pop.connect('closed', lambda *_: GLib.idle_add(lambda: self.set_focus(None) or False))
        return pop

    def _rows(self, pop, items, current, on_pick):
        """Fill a dropdown with (value, [labels]) rows and scroll to the current one."""
        pop.list.remove_all()
        here = None
        for value, labels in items:
            row = Gtk.ListBoxRow()
            row.value = value
            line = Gtk.Box(spacing=10)
            for text, cls, expand in labels:
                lab = Gtk.Label(label=text, xalign=1 if cls == 'num' else 0, hexpand=expand)
                if cls:
                    lab.add_css_class(cls)
                if cls == 'num':
                    lab.set_width_chars(3)
                line.append(lab)
            row.set_child(line)
            if value == current:
                row.add_css_class('here')
                here = row
            pop.list.append(row)
        if getattr(pop, 'handler', None):
            pop.list.disconnect(pop.handler)
        pop.handler = pop.list.connect('row-activated', lambda _l, row: (pop.popdown(), on_pick(row.value)))

        def scroll():
            if here is not None:
                ok, p = here.compute_point(pop.list, Graphene.Point())
                if ok:
                    adj = pop.scroll.get_vadjustment()
                    adj.set_value(max(0, p.y - adj.get_page_size() / 2 + here.get_height() / 2))
            return GLib.SOURCE_REMOVE
        GLib.idle_add(scroll)

    def _fill_surahs(self, keep_scroll=False):
        """Saved surahs first, then all 114. Finished ones are green; a star saves one."""
        pop = self.surah_pop
        adj = pop.scroll.get_vadjustment()
        top = adj.get_value()
        pop.list.remove_all()
        here = None
        rows = [(n, 'saved') for n in self.state.saved] + [(n, 'all') for n in range(1, 115)]
        for n, section in rows:
            row = Gtk.ListBoxRow()
            row.value, row.section = n, section
            line = Gtk.Box(spacing=10)
            num = Gtk.Label(label=str(n), xalign=1, width_chars=3)
            num.add_css_class('num')
            name = Gtk.Label(label=quran.name(n), xalign=0, hexpand=True)
            done = self.state.finished(n)
            if done:
                name.add_css_class('recited')
            count = Gtk.Label(label=f'✓{done}' if done else '')
            count.add_css_class('done')
            saved = n in self.state.saved
            star = Gtk.Button(icon_name='starred-symbolic' if saved else 'non-starred-symbolic',
                              tooltip_text='Remove from saved' if saved else 'Save', focusable=False)
            star.add_css_class('star')
            if saved:
                star.add_css_class('on')
            star.connect('clicked', lambda _b, n=n: self._toggle_saved(n))
            for w in (num, name, count, star):
                line.append(w)
            row.set_child(line)
            if n == self.surah and (section == 'all' or here is None):
                row.add_css_class('here')
                if section == 'all':
                    here = row
            pop.list.append(row)
        pop.list.set_header_func(self._section_header if self.state.saved else None)
        if getattr(pop, 'handler', None):
            pop.list.disconnect(pop.handler)
        pop.handler = pop.list.connect('row-activated', lambda _l, row: (pop.popdown(), self._pick_surah(row.value)))

        def scroll():
            if keep_scroll:
                adj.set_value(top)
            elif self.state.saved:
                adj.set_value(0)       # your saved surahs first
            elif here is not None:
                ok, p = here.compute_point(pop.list, Graphene.Point())
                if ok:
                    adj.set_value(max(0, p.y - adj.get_page_size() / 2 + here.get_height() / 2))
            return GLib.SOURCE_REMOVE
        GLib.idle_add(scroll)
        if keep_scroll:
            return
        entry = pop.entry
        entry.set_text('')
        if not getattr(entry, 'wired', False):
            entry.wired = True
            entry.connect('search-changed', lambda e: pop.list.invalidate_filter())
            entry.connect('activate', lambda e: self._pick_first())
            entry.connect('stop-search', lambda e: pop.popdown())
            pop.list.set_filter_func(self._match)
        GLib.idle_add(lambda: entry.grab_focus() and False)

    def _section_header(self, row, before):
        if before is None or before.section != row.section:
            label = Gtk.Label(label='Saved' if row.section == 'saved' else 'All surahs', xalign=0)
            label.add_css_class('section')
            row.set_header(label)
        else:
            row.set_header(None)

    def _toggle_saved(self, n):
        self.state.toggle_saved(n)
        self.state.save()
        self._fill_surahs(keep_scroll=True)

    def _match(self, row):
        q = self.surah_pop.entry.get_text().strip()
        if not q:
            return True
        if row.section == 'saved':
            return False           # while searching, each surah once
        if q.isdigit():
            return str(row.value).startswith(q)
        from .cli import plain
        q = plain(q).rstrip('h')
        return q in plain(quran.name(row.value))

    def _pick_first(self):
        row = self.surah_pop.list.get_first_child()
        while row is not None and not (row.get_mapped() and row.get_child_visible()):
            row = row.get_next_sibling()
        if row is not None:
            self.surah_pop.popdown()
            self._pick_surah(row.value)

    def _pick_surah(self, n):
        if n != self.surah:
            self.load_surah(n)

    def _fill_speeds(self):
        steps = [round(SPEED_MIN + k * 0.05, 2) for k in range(int((SPEED_MAX - SPEED_MIN) / 0.05) + 1)]
        items = [(v, [(f'{fmt_speed(v)}×', None, True)]) for v in steps]
        self._rows(self.speed_pop, items, round(self.state.speed, 2), self.set_speed)

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
        if self.player.playing:
            self._queue_next()

    def _menu_at(self, gesture, n, x, y):
        r = Gdk.Rectangle()
        r.x, r.y, r.width, r.height = int(x), int(y), 1, 1
        self.menu.set_pointing_to(r)
        self.menu.popup()


    # ---------- input ----------

    def _key(self, ctl, keyval, code, mods):
        if self.surah_pop.get_visible() or self.speed_pop.get_visible():
            return False           # typing in a dropdown
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
        if keyval in (Gdk.KEY_space, Gdk.KEY_Down, Gdk.KEY_Page_Down, Gdk.KEY_j):
            self.next()
        elif keyval in (Gdk.KEY_BackSpace, Gdk.KEY_Up, Gdk.KEY_Page_Up, Gdk.KEY_k):
            self.prev()
        elif keyval in (Gdk.KEY_Right, Gdk.KEY_plus, Gdk.KEY_KP_Add):
            self.set_speed(self.state.speed + 0.05)
        elif keyval in (Gdk.KEY_Left, Gdk.KEY_minus, Gdk.KEY_KP_Subtract):
            self.set_speed(self.state.speed - 0.05)
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
