# database_add_connection_sqlite_view.py
#
# Copyright (c) 2025 Naufan Rusyda Faikar
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from gi.repository import Adw, Gio, Gtk
import os

from .window import Window

@Gtk.Template(resource_path='/com/macipra/eruo/ui/database-add-connection-sqlite-view.ui')
class DatabaseAddConnectionSqliteView(Adw.PreferencesPage):
    __gtype_name__ = 'DatabaseAddConnectionSqliteView'

    connect_as = Gtk.Template.Child()
    connect_to = Gtk.Template.Child()

    def __init__(self,
                 window: Window,
                 **kwargs) -> None:
        super().__init__(**kwargs)

        self.window = window

    @Gtk.Template.Callback()
    def on_connect_to_activated(self, button: Gtk.Button) -> None:
        FILTER_SQLITE = Gtk.FileFilter()
        FILTER_SQLITE.set_name('SQLite Database')
        FILTER_SQLITE.add_pattern('*.sqlite')
        FILTER_SQLITE.add_pattern('*.db')
        FILTER_SQLITE.add_mime_type('application/vnd.sqlite3')

        FILTER_ALL = Gtk.FileFilter()
        FILTER_ALL.set_name('All Files')
        FILTER_ALL.add_pattern('*')

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(FILTER_SQLITE)
        filters.append(FILTER_ALL)

        dialog = Gtk.FileDialog()
        dialog.set_title('Database File')
        dialog.set_modal(True)
        dialog.set_filters(filters)

        def on_open_file_dialog_dismissed(dialog: Gtk.FileDialog,
                                          result: Gio.Task) -> None:
            if result.had_error():
                return

            file = dialog.open_finish(result)
            self.connect_to.set_subtitle(file.get_path())

            if self.connect_as.get_text() == 'New Connection':
                basename = os.path.basename(file.get_path())
                filename = os.path.splitext(basename)[0]
                self.connect_as.set_text(filename)

        dialog.open(self.window, None, on_open_file_dialog_dismissed)