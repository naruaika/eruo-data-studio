# file_save_as_parquet_view.py
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


from gi.repository import Adw, Gio, GObject, Gtk
from pathlib import Path

@Gtk.Template(resource_path='/com/macipra/eruo/ui/file-save-as-parquet-view.ui')
class FileSaveAsParquetView(Adw.PreferencesPage):
    __gtype_name__ = 'FileSaveAsParquetView'

    save_as = Gtk.Template.Child()
    save_to = Gtk.Template.Child()

    statistics = Gtk.Template.Child()

    compression = Gtk.Template.Child()
    compression_level = Gtk.Template.Child()

    def __init__(self,
                 file_name:   str,
                 folder_path: str,
                 **kwargs) -> None:
        super().__init__(**kwargs)

        if file_name is not None:
            self.save_as.set_text(file_name)

        if folder_path is not None:
            self.save_to.set_subtitle(folder_path)

    @Gtk.Template.Callback()
    def on_save_to_activated(self, button: Gtk.Button) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title('Save To')
        dialog.set_modal(True)

        home_path = Gio.File.new_for_path(str(Path.home()))
        dialog.set_initial_folder(home_path)

        dialog.select_folder(self.get_root(),
                             None,
                             self.on_save_to_dialog_dismissed)

    def on_save_to_dialog_dismissed(self,
                                    dialog: Gtk.FileDialog,
                                    result: Gio.Task) -> None:
        if result.had_error():
            return

        folder = dialog.select_folder_finish(result)
        self.save_to.set_subtitle(folder.get_path())

    @Gtk.Template.Callback()
    def on_compression_selected(self,
                                combo_box: Adw.ComboRow,
                                pspec:     GObject.ParamSpec) -> None:
        compression_map = {
            'zstd': (1, 22),
            'brotli': (0, 11),
            'uncompressed': (0, 0),
        }
        default_range = (1, 9)

        selected = combo_box.get_selected_item().get_string()
        start, end = compression_map.get(selected, default_range)
        self.compression_level.set_range(start, end)

        level = self.compression_level.get_value()
        level = max(min(level, end), start)
        self.compression_level.set_value(level)

    @Gtk.Template.Callback()
    def on_reset_default_clicked(self, button: Gtk.Button) -> None:
        self.statistics.set_active(True)

        self.compression.set_selected_item('zstd')
        self.compression_level.set_value(1)