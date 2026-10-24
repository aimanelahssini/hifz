"""A plain terminal window for the demo video (Ptyxis needs a systemd user bus, which the
headless test session doesn't have)."""
import os

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Vte', '3.91')
gi.require_version('Pango', '1.0')
from gi.repository import Adw, Gdk, GLib, Gtk, Pango, Vte


def activate(app):
    Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
    win = Adw.ApplicationWindow(application=app, title='Terminal', default_width=900, default_height=640)
    term = Vte.Terminal()
    term.set_font(Pango.FontDescription.from_string('Adwaita Mono 11'))
    bg, fg = Gdk.RGBA(), Gdk.RGBA()
    bg.parse('#1d1d22')
    fg.parse('#e8e8ec')
    term.set_colors(fg, bg, None)
    term.set_margin_start(12)
    term.set_margin_top(8)
    term.spawn_async(Vte.PtyFlags.DEFAULT, os.environ['HOME'], ['/bin/bash', '--noprofile', '--rcfile',
                     os.path.join(os.environ['HOME'], '.bashrc'), '-i'], None,
                     GLib.SpawnFlags.DEFAULT, None, None, -1, None, None, None)
    term.connect('child-exited', lambda *_: win.close())
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.append(Adw.HeaderBar())
    term.set_vexpand(True)
    box.append(term)
    win.set_content(box)
    win.present()
    term.grab_focus()


app = Adw.Application(application_id='org.example.Terminal')
app.connect('activate', activate)
app.run([])
