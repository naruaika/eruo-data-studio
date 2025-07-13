# file_manager.py
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


from gi.repository import Gio, GLib, GObject, Gtk
import os
import polars
import threading

from . import globals
from .file_save_as_dialog import FileSaveAsDialog
from .sheet_data import SheetData
from .window import Window

class FileManager(GObject.Object):
    __gtype_name__ = 'FileManager'

    __gsignals__ = {
        'file-opened': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
        'file-saved': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
    }

    def __init__(self) -> None:
        super().__init__()

    def read_file(self, file_path: str) -> polars.DataFrame:
        file_format = file_path.split('.')[-1]
        read_methods = {
            'json': polars.read_json,
            'parquet': polars.read_parquet,
            'csv': polars.read_csv,
        }
        if file_format in read_methods:
            return read_methods[file_format](file_path)
        raise ValueError(f"Unsupported file format: {file_format}")

    def write_file(self, file_path: str, sheet_data: SheetData, dfi: int = 0, **kwargs) -> bool:
        try:
            file_format = file_path.split('.')[-1]
            write_methods = {
                'json': sheet_data.dfs[dfi].write_json,
                'parquet': sheet_data.dfs[dfi].write_parquet,
                'csv': sheet_data.dfs[dfi].write_csv,
            }
            if file_format in write_methods:
                write_methods[file_format](file_path, **kwargs)
                return True
            raise ValueError(f"Unsupported file format: {file_format}")
        except Exception:
            globals.send_notification(f'Cannot write file: {file_path}')
        return False

    def delete_file(self, file_path: str) -> bool:
        try:
            os.remove(file_path)
        except Exception as e:
            globals.send_notification(f'Cannot delete file: {file_path}')
        return True

    def open_file(self, window: Window) -> None:
        FILTER_TXT = Gtk.FileFilter()
        FILTER_TXT.set_name('Text')
        FILTER_TXT.add_pattern('*.txt')
        FILTER_TXT.add_pattern('*.csv')
        FILTER_TXT.add_mime_type('text/plain')
        FILTER_TXT.add_mime_type('text/csv')

        FILTER_JSON = Gtk.FileFilter()
        FILTER_JSON.set_name('JSON')
        FILTER_JSON.add_pattern('*.json')
        FILTER_JSON.add_mime_type('application/json')

        FILTER_PARQUET = Gtk.FileFilter()
        FILTER_PARQUET.set_name('Parquet')
        FILTER_PARQUET.add_pattern('*.parquet')
        FILTER_PARQUET.add_mime_type('application/vnd.apache.parquet')

        FILTER_ALL = Gtk.FileFilter()
        FILTER_ALL.set_name('All Files')
        FILTER_ALL.add_pattern('*')

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(FILTER_TXT)
        filters.append(FILTER_JSON)
        filters.append(FILTER_PARQUET)
        filters.append(FILTER_ALL)

        dialog = Gtk.FileDialog()
        dialog.set_title('Open')
        dialog.set_modal(True)
        dialog.set_filters(filters)

        dialog.open(window, None, self.on_open_file_dialog_dismissed)

    def on_open_file_dialog_dismissed(self, dialog: Gtk.FileDialog, result: Gio.Task) -> None:
        if result.had_error():
            self.emit('file-opened', '')
            return

        file = dialog.open_finish(result)
        self.emit('file-opened', file.get_path())

    def save_file(self, window: Window) -> None:
        file = window.file
        if file is None:
            self.save_as_file(window)
            return

        sheets = list(window.sheet_manager.sheets.values())
        sheet_data = sheets[0].data

        def write_file() -> None:
            if self.write_file(file.get_path(), sheet_data):
                GLib.idle_add(self.emit, 'file-saved', file.get_path())
        threading.Thread(target=write_file, daemon=True).start()

    def save_as_file(self, window: Window) -> None:

        def save_file(file_path: str, **kwargs) -> None:
            sheets = list(window.sheet_manager.sheets.values())
            sheet_data = sheets[0].data

            def write_file() -> None:
                if self.write_file(file_path, sheet_data, **kwargs):
                    GLib.idle_add(self.emit, 'file-saved', file_path)
            threading.Thread(target=write_file, daemon=True).start()

        dialog = FileSaveAsDialog(window, save_file)
        dialog.present(window)