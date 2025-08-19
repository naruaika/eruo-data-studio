# database_add_connection_dialog.py
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


from gi.repository import Adw, Gtk

from . import globals
from .database_add_connection_sqlite_view import DatabaseAddConnectionSqliteView
from .window import Window

@Gtk.Template(resource_path='/com/macipra/eruo/ui/database-add-connection-dialog.ui')
class DatabaseAddConnectionDialog(Adw.Dialog):
    __gtype_name__ = 'DatabaseAddConnectionDialog'

    view_stack = Gtk.Template.Child()

    def __init__(self,
                 window:   Window,
                 callback: callable,
                 **kwargs) -> None:
        super().__init__(**kwargs)

        self.window = window
        self.callback = callback

        view = DatabaseAddConnectionSqliteView(window)
        self.view_stack.add_titled(view, 'sqlite', 'SQLite')

    @Gtk.Template.Callback()
    def on_connect_button_clicked(self, button: Gtk.Button) -> None:
        view = self.view_stack.get_visible_child()

        try:
            match view:
                case DatabaseAddConnectionSqliteView():
                    cname = view.connect_as.get_text()
                    curl = view.connect_to.get_subtitle()
                    import sqlite3
                    sqlite3.connect(curl)
                    connection_schema = {
                        'ctype' : 'SQLite',
                        'cname' : cname,
                        'curl'  : f"ATTACH '{curl}' AS {cname} (TYPE sqlite);",
                    }

        except Exception as e:
            print(e)

            message = str(e).capitalize()
            globals.send_notification(message)

            return

        self.callback(connection_schema)
        self.close()