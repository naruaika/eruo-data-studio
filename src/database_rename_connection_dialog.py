# database_rename_connection_dialog.py
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

@Gtk.Template(resource_path='/com/macipra/eruo/ui/database-rename-connection-dialog.ui')
class DatabaseRenameConnectionDialog(Adw.Dialog):
    __gtype_name__ = 'DatabaseRenameConnectionDialog'

    entry = Gtk.Template.Child()

    def __init__(self,
                 old_name: str,
                 callback: callable,
                 **kwargs) -> None:
        super().__init__(**kwargs)

        self.callback = callback

        self.entry.set_text(old_name)
        self.entry.grab_focus()

    @Gtk.Template.Callback()
    def on_entry_activated(self, entry: Gtk.Entry) -> None:
        self.callback(entry.get_text())
        self.close()

    @Gtk.Template.Callback()
    def on_rename_button_clicked(self, button: Gtk.Button) -> None:
        self.on_entry_activated(self.entry)