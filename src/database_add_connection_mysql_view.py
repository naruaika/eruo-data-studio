# database_add_connection_mysql_view.py
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

from .window import Window

@Gtk.Template(resource_path='/com/macipra/eruo/ui/database-add-connection-mysql-view.ui')
class DatabaseAddConnectionMysqlView(Adw.PreferencesPage):
    __gtype_name__ = 'DatabaseAddConnectionMysqlView'

    name = Gtk.Template.Child()
    host = Gtk.Template.Child()
    port = Gtk.Template.Child()
    database = Gtk.Template.Child()
    username = Gtk.Template.Child()
    password = Gtk.Template.Child()

    def __init__(self,
                 window: Window,
                 **kwargs) -> None:
        super().__init__(**kwargs)

        self.window = window