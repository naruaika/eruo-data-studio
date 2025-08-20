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


from gi.repository import Adw, Gio, Gtk
import duckdb
import re

from .database_add_connection_mysql_view import DatabaseAddConnectionMysqlView
from .database_add_connection_postgresql_view import DatabaseAddConnectionPostgresqlView
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

        view = DatabaseAddConnectionMysqlView(window)
        self.view_stack.add_titled(view, 'mysql', 'MySQL')

        view = DatabaseAddConnectionPostgresqlView(window)
        self.view_stack.add_titled(view, 'postgresql', 'PostgreSQL')

        view = DatabaseAddConnectionSqliteView(window)
        self.view_stack.add_titled(view, 'sqlite', 'SQLite')

    @Gtk.Template.Callback()
    def on_connect_button_clicked(self, button: Gtk.Button) -> None:
        view = self.view_stack.get_visible_child()

        connection = duckdb.connect()

        try:
            match view:
                case DatabaseAddConnectionMysqlView():
                    cname = view.name.get_text() or 'New Connection'
                    chost = view.host.get_text() or 'localhost'
                    cport = view.port.get_text() or '3306'
                    database = view.database.get_text() or 'NULL'
                    username = view.username.get_text() or 'root'
                    password = view.password.get_text() or 'NULL'
                    curl = f"ATTACH 'host={chost} port={cport} " \
                           f"user={username} passwd={password} " \
                           f"db={database}' AS \"{cname}\" " \
                           f"(TYPE mysql);"
                    cschema = {
                        'ctype' : 'MySQL',
                        'cname' : cname,
                        'curl'  : curl,
                    }

                case DatabaseAddConnectionPostgresqlView():
                    cname = view.name.get_text() or 'New Connection'
                    chost = view.host.get_text() or 'localhost'
                    cport = view.port.get_text() or '5432'
                    database = view.database.get_text() or 'NULL'
                    username = view.username.get_text() or 'root'
                    password = view.password.get_text() or 'NULL'
                    curl = f"ATTACH 'host={chost} port={cport} " \
                           f"user={username} password={password} " \
                           f"dbname={database}' AS \"{cname}\" " \
                           f"(TYPE postgres);"
                    cschema = {
                        'ctype' : 'PostgreSQL',
                        'cname' : cname,
                        'curl'  : curl,
                    }

                case DatabaseAddConnectionSqliteView():
                    cname = view.name.get_text() or 'New Connection'
                    database = view.database.get_subtitle() or '~/sample.db'
                    cschema = {
                        'ctype' : 'SQLite',
                        'cname' : cname,
                        'curl'  : f"ATTACH '{database}' AS \"{cname}\" (TYPE sqlite);",
                    }
                    import sqlite3
                    sqlite3.connect(database)

            # Remove all parameters that are NULL
            cschema['curl'] = re.sub(r'\s+\w+=NULL', '', cschema['curl'])

            connection.execute(cschema['curl'])

        except Exception as e:
            message = str(e)
            print(message)

            if message.startswith('unable'):
                message = message.capitalize()
            if 'Access denied for user' in message:
                message = 'Access' + message.split('Access')[1]
            if "Can't connect to MySQL server" in message:
                message = "Can't" + message.split("Can't")[1]

            alert_dialog = Adw.AlertDialog()

            alert_dialog.set_heading(_('Connection Failed'))
            alert_dialog.set_body(message)

            alert_dialog.add_response('retry', _('_Retry'))
            alert_dialog.add_response('ok', _('_OK'))

            alert_dialog.set_default_response('retry')
            alert_dialog.set_close_response('ok')

            def on_alert_dialog_dismissed(dialog: Adw.AlertDialog,
                                          result: Gio.Task) -> None:
                if result.had_error():
                    return
                response = dialog.choose_finish(result)
                if response != 'retry':
                    return
                self.on_connect_button_clicked(button)

            alert_dialog.choose(self.window, None, on_alert_dialog_dismissed)

            connection.close()
            return

        connection.close()
        self.callback(cschema)
        self.close()