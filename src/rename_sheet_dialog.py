# rename_sheet_dialog.py
#
# Copyright 2025 Naufan Rusyda Faikar
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later


from gi.repository import Adw, Gtk

@Gtk.Template(resource_path='/com/macipra/eruo/ui/rename-sheet-dialog.ui')
class RenameSheetDialog(Adw.Dialog):
    __gtype_name__ = 'RenameSheetDialog'

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