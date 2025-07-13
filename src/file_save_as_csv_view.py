# file_save_as_csv_view.py
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

@Gtk.Template(resource_path='/com/macipra/eruo/ui/file-save-as-csv-view.ui')
class FileSaveAsCsvView(Adw.PreferencesPage):
    __gtype_name__ = 'FileSaveAsCsvView'

    save_as = Gtk.Template.Child()
    save_to = Gtk.Template.Child()

    include_header = Gtk.Template.Child()

    separator = Gtk.Template.Child()
    line_terminator = Gtk.Template.Child()
    quote_character = Gtk.Template.Child()

    datetime_format = Gtk.Template.Child()
    date_format = Gtk.Template.Child()
    time_format = Gtk.Template.Child()

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

    @Gtk.Template.Callback()
    def on_reset_default_clicked(self, button: Gtk.Button) -> None:
        self.include_header.set_active(True)

        self.separator.set_text(',')
        self.line_terminator.set_text('\\n')
        self.quote_character.set_text('"')

        self.datetime_format.set_text('%Y-%m-%d %H:%M:%S')
        self.date_format.set_text('%Y-%m-%d')
        self.time_format.set_text('%H:%M:%S')