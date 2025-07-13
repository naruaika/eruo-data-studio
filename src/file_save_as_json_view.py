# file_save_as_json_view.py
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


from gi.repository import Adw, Gio, Gtk
from pathlib import Path

@Gtk.Template(resource_path='/com/macipra/eruo/ui/file-save-as-json-view.ui')
class FileSaveAsJsonView(Adw.PreferencesPage):
    __gtype_name__ = 'FileSaveAsJsonView'

    save_as = Gtk.Template.Child()
    save_to = Gtk.Template.Child()

    def __init__(self, file_name: str, folder_path: str, **kwargs) -> None:
        super().__init__(**kwargs)

        if file_name is not None:
            self.save_as.set_text(file_name)

        if folder_path is not None:
            self.save_to.set_subtitle(folder_path)

    @Gtk.Template.Callback()
    def on_save_to_activated(self, button: Gtk.Button) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title('Save To')
        dialog.set_initial_folder(Gio.File.new_for_path(str(Path.home())))
        dialog.set_modal(True)

        dialog.select_folder(self.get_root(), None, self.on_save_to_dialog_dismissed)

    def on_save_to_dialog_dismissed(self, dialog: Gtk.FileDialog, result: Gio.Task) -> None:
        if result.had_error():
            return
        folder = dialog.select_folder_finish(result)
        self.save_to.set_subtitle(folder.get_path())