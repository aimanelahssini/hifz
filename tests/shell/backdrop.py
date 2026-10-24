"""A plain light window behind Hifz in the headless tests: shows how it reads over a page."""
import sys

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gtk

TEXT = '\n\n'.join([
    'Notes',
    'Revise the first part before the evening prayer. Read slowly, one ayah at a time, '
    'and say it again without looking before moving on.',
    'Tomorrow: the next ten ayahs, then everything from the start.',
] * 6)


def activate(app):
    Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
    win = Adw.ApplicationWindow(application=app, title='Notes')
    view = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD, left_margin=80, right_margin=80, top_margin=60)
    view.get_buffer().set_text(TEXT)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.append(Adw.HeaderBar())
    sw = Gtk.ScrolledWindow(vexpand=True)
    sw.set_child(view)
    box.append(sw)
    win.set_content(box)
    if '--window' in sys.argv:
        win.set_default_size(560, 520)
    else:
        win.maximize()
    win.present()


app = Adw.Application(application_id='org.example.Backdrop')
app.connect('activate', activate)
app.run([])
