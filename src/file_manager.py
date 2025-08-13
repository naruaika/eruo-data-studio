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
        'file-opened' : (GObject.SIGNAL_RUN_FIRST, None, (str, bool)),
        'file-saved'  : (GObject.SIGNAL_RUN_FIRST, None, (str,)),
    }

    def read_file(self, file_path: str) -> polars.DataFrame:
        # We usually call this function whenever the user wants to open
        # a file to work with. Or when the user for example enable the
        # "open last file" feature everytime the application starts for
        # instance. TODO: user should be able to setup the file reader
        # parameters in case the file uses no ordinary format or it's
        # just a TSV file maybe which is should be read as a CSV file
        # with a different separator.
        file_format = file_path.split('.')[-1]
        read_methods = {
            'json':    polars.read_json,
            'parquet': polars.read_parquet,
            'csv':     polars.read_csv,
        }

        # If it's a text file, we might want to try to read it as CSV?
        if file_format not in read_methods:
            globals.send_notification(f'Unsupported file format: {file_format}')
            return None

        try:
            return read_methods[file_format](file_path)
        except Exception as e:
            print(e)

        # Unless it's a CSV file, we won't retry to read the file after the first failure
        if file_format != 'csv':
            globals.send_notification(f'Cannot read file: {file_path}')
            return None

        try:
            # Retry by ignoring any errors
            return read_methods[file_format](file_path,
                                             ignore_errors=True,
                                             infer_schema=False)
        except Exception as e:
            print(e)

        try:
            def send_parse_error_notification():
                # Using getattr to prevent wrong references during runtime
                callback = getattr(globals, 'send_notification', None)
                callback(f'Cannot parse file: {file_path}')

            # We wait for 1 second before sending the notification to make sure that
            # we send the notification to the newly opened window if any.
            GLib.timeout_add(1000, send_parse_error_notification)

            # We use non-standard parameters to force loading the entire file contents
            # without losing any data by forcing opinionated behaviour. We supposed to
            # put all the data into one column. Let's the user decide what to do next.
            return read_methods[file_format](file_path,
                                             ignore_errors=True,
                                             infer_schema=False,
                                             quote_char=None,
                                             separator='\x1f',
                                             truncate_ragged_lines=True)
        except Exception as e:
            print(e)

        globals.send_notification(f'Cannot read file: {file_path}')
        return None

    def write_file(self,
                   file_path:   str,
                   sheet_data:  SheetData,
                   dfi:         int = 0,
                   **kwargs) -> bool:
        has_backup = False

        # Make a backup of the original file
        # TODO: make this behaviour customizable
        if os.path.exists(file_path):
            os.rename(file_path, file_path + '.backup')
            has_backup = True

        # This function can be called whenever the users want to save their work
        # or they just want to save the file in a different format.
        try:

            file_format = file_path.split('.')[-1]
            write_methods = {
                'json':    sheet_data.dfs[dfi].write_json,
                'parquet': sheet_data.dfs[dfi].write_parquet,
                'csv':     sheet_data.dfs[dfi].write_csv,
            }

            if file_format in write_methods:
                write_methods[file_format](file_path, **kwargs)
                return True

            globals.send_notification(f'Unsupported file format: {file_format}')
            return False

        except Exception as e:
            print(e)

            # Restore the original file
            if has_backup:
                os.rename(file_path + '.backup', file_path)

        globals.send_notification(f'Cannot write file: {file_path}')
        return False

    def delete_file(self, file_path: str) -> bool:
        # We usually call this function to delete a snapshot file created by
        # the history manager. So, even if we fail to delete the file, it's
        # not a big deal as by default we put all the snapshots in the system
        # temporary directory which will be cleaned up automatically whenever
        # for example the user restarts or shutdowns the operating system.
        try:
            os.remove(file_path)
            return True

        except Exception as e:
            print(e)

        globals.send_notification(f'Cannot delete file: {file_path}')
        return False

    def open_file(self, window: Window, in_place: bool = False) -> None:
        # This function is intended to open the file dialog and let the user
        # select a file to open. Then we call the `read_file` function to read
        # the actual file content.

        # By now we only support a limited set of text files, JSON files, and
        # Parquet files. More formats will be supported in the future.
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

        # This option is not intended to be used by the users to force
        # opening unsupported files. Instead, it can be used for example
        # to verify whether they are in the right directory or to see
        # whether the file exists but it's not currently supported.
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

        def on_open_file_dialog_dismissed(dialog: Gtk.FileDialog,
                                          result: Gio.Task) -> None:
            if result.had_error():
                self.emit('file-opened', '', in_place)
                return

            file = dialog.open_finish(result)
            self.emit('file-opened', file.get_path(), in_place)

        # Return the result to the main application thread. If an error
        # had occurred or the user cancelled, we pass an empty string.
        dialog.open(window, None, on_open_file_dialog_dismissed)

    def save_file(self,
                  window:      Window,
                  file_path:   str = '',
                  **kwargs) -> None:
        # Opening a file in a new window will always store the file object
        # in the window object. When the reference to the file object is
        # missing, it means that the user open a new window with a blank
        # worksheet or it can also be mean it failed to open a file. In
        # this case, we trigger the `save_as_file` function so the users
        # can decide where and in which format they want to save the work.
        if (file := window.file) is None:
            self.save_as_file(window)
            return

        if not file_path:
            file_path = file.get_path()

        # TODO: we are supposed to handle saving multiple sheets here
        # The original file is always stored in the first sheet. If the users
        # have a working file that is not in a proprietary format, we want to
        # always ask them if they want to save all the changed that only supported
        # by the proprietary format, otherwise we just overwrite the original file
        # and discard any unsupported changes, like formatting and formulas. I'm
        # wondering if we can also save the changes to a kind of sidecar file when
        # the users want to keep the original format?
        sheets = list(window.sheet_manager.sheets.values())
        sheet_data = sheets[0].data

        # A successful write will trigger the `file-saved` signal so that the users
        # can be notified that their work has been saved. Otherwise, the `write_file`
        # function will send an in-app notification to the user.
        def write_file() -> None:
            if self.write_file(file_path, sheet_data, **kwargs):
                GLib.idle_add(self.emit, 'file-saved', file_path)

        # FIXME: Using a thread to write the file to avoid blocking the main thread,
        #        but potentially it can introduce to some race conditions.
        threading.Thread(target=write_file, daemon=True).start()

    def save_as_file(self, window: Window) -> None:
        # In here, we just open a file save-as dialog to let the users
        # configure where and in which format they want to save the work.
        dialog = FileSaveAsDialog(window, self.save_file)
        dialog.present(window)