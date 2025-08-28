# file_manager.py
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


from gi.repository import Adw, Gio, GLib, GObject, Gtk
from typing import Any
import os
import pickle
import polars
import tempfile
import threading
import zipfile

from . import globals
from .file_save_as_dialog import FileSaveAsDialog
from .sheet_document import SheetDocument
from .sheet_notebook import SheetNotebook
from .window import Window

class FileManager(GObject.Object):
    __gtype_name__ = 'FileManager'

    __gsignals__ = {
        'file-cancel'   : (GObject.SIGNAL_RUN_FIRST, None, ()),
        'file-opened'   : (GObject.SIGNAL_RUN_FIRST, None, (str, bool)),
        'file-saved'    : (GObject.SIGNAL_RUN_FIRST, None, (str,)),
        'file-exported' : (GObject.SIGNAL_RUN_FIRST, None, (str,)),
    }

    def read_file(self,
                  application: Gtk.Application,
                  file_path:   str) -> Any:
        file_format = file_path.split('.')[-1].lower()

        if file_format == 'erbook':
            return self.read_erbook(application, file_path)

        # We usually call this function whenever the user wants to open
        # a file to work with. Or when the user for example enable the
        # "open last file" feature everytime the application starts for
        # instance. TODO: user should be able to setup the file reader
        # parameters in case the file uses no ordinary format or it's
        # just a TSV file maybe which is should be read as a CSV file
        # with a different separator.
        read_methods = {
            'json'    : polars.read_json,
            'parquet' : polars.read_parquet,
            'csv'     : polars.read_csv,
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

            # We wait for a second before sending the notification to make sure that
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

    def read_erbook(self,
                    application: Gtk.Application,
                    file_path:   str) -> polars.DataFrame:
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                with tempfile.TemporaryDirectory() as temp_dir:
                    zip_file.extractall(temp_dir)

                    with open(os.path.join(temp_dir, 'workspace_schema'), 'rb') as pickle_file:
                        workspace_schema = pickle.load(pickle_file)

                    for sheet in workspace_schema['sheets']:
                        if sheet['stype'] == 'worksheet':
                            sheet['data']['dataframes'] = []
                            for dataframe_path in sheet['data']['dataframe-paths']:
                                loaded_dataframe = polars.read_parquet(os.path.join(temp_dir, dataframe_path))
                                sheet['data']['dataframes'].append(loaded_dataframe)
                            del sheet['data']['dataframe-paths']

            # Load the workspace
            application.load_user_workspace(workspace_schema)

            return 0 # special return value

        except Exception as e:
            print(e)

        globals.send_notification(f'Cannot read file: {file_path}')
        return None

    def write_file(self,
                   window:      Window,
                   file_path:   str,
                   export:      bool = False,
                   **kwargs) -> bool:
        file_format = file_path.split('.')[-1].lower()

        if file_format == 'erbook':
            return self.write_erbook(window, file_path, export)

        has_backup = False

        # Make a backup of the original file (non-erbook files only)
        # TODO: this behaviour should be customizable
        if os.path.exists(file_path):
            os.rename(file_path, file_path + '.erbak')
            has_backup = True

        sheet_document = window.get_current_active_document()
        dataframe = sheet_document.data.dfs[0]

        write_methods = {
            'csv'     : dataframe.write_csv,
            'json'    : dataframe.write_json,
            'parquet' : dataframe.write_parquet,
        }

        # This function can be called whenever the users want to save their work
        # or they just want to save the file in a different format.
        try:
            if file_format in write_methods:
                write_methods[file_format](file_path, **kwargs)

                # Update the file signature if needed
                if not export:
                    window.file = Gio.File.new_for_path(file_path)

                # Note that we keep, if exists, the backup file intentionally
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

    def write_erbook(self,
                     window:    Window,
                     file_path: str,
                     export:    bool) -> bool:
        # Read the UI states
        sidebar_collapsed = window.split_view.get_collapsed()

        selected_page = window.tab_view.get_selected_page()
        current_active_tab = window.tab_view.get_page_position(selected_page)

        pinned_tabs = []
        for page_index in range(window.tab_view.get_n_pages()):
            tab_page = window.tab_view.get_nth_page(page_index)
            if tab_page.get_pinned():
                pinned_tabs.append(page_index)

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                workspace_schema = {
                    'signature'          : file_path,
                    'sheets'             : [],
                    'sidebar-collapsed'  : sidebar_collapsed,
                    'current-active-tab' : current_active_tab,
                    'pinned-tabs'        : pinned_tabs,
                }

                all_dataframe_paths = []

                for sheet_document in window.sheet_manager.sheets.values():
                    if isinstance(sheet_document, SheetDocument):
                        stype = 'worksheet'

                        bounding_boxes = [{
                            'column'      : bbox.column,
                            'row'         : bbox.row,
                            'column-span' : bbox.column_span,
                            'row-span'    : bbox.row_span,
                        } for bbox in sheet_document.data.bbs]

                        dataframe_paths = [
                            f'{sheet_document.document_id}_{dfi}.ersnap'
                            for dfi in range(len(sheet_document.data.dfs))
                        ]
                        all_dataframe_paths.extend(dataframe_paths)

                        workspace_schema['sheets'].append({
                            'stype'                       : stype,
                            'title'                       : sheet_document.title,
                            'data': {
                                'bounding-boxes'          : bounding_boxes,
                                'dataframe-paths'         : dataframe_paths,
                                'has-main-dataframe'      : sheet_document.data.has_main_dataframe,
                            },
                            'display': {
                                'row-visibility-flags'    : sheet_document.display.row_visibility_flags.to_list(),
                                'column-visibility-flags' : sheet_document.display.column_visibility_flags.to_list(),
                                'row-heights'             : sheet_document.display.row_heights.to_list(),
                                'column-widths'           : sheet_document.display.column_widths.to_list(),
                            },
                            'current-sorts'               : sheet_document.current_sorts,
                            'current-filters'             : sheet_document.current_filters,
                        })

                        for dfi, dataframe in enumerate(sheet_document.data.dfs):
                            dataframe_path = os.path.join(temp_dir, dataframe_paths[dfi])
                            dataframe.write_parquet(dataframe_path, compression='uncompressed', statistics=False)

                    if isinstance(sheet_document, SheetNotebook):
                        stype = 'notebook'

                        list_items = []

                        for list_item in sheet_document.view.list_items:
                            ctype = list_item['ctype']

                            text_buffer = list_item['source_view'].get_buffer()
                            start_iter = text_buffer.get_start_iter()
                            end_iter = text_buffer.get_end_iter()

                            value = text_buffer.get_text(start_iter, end_iter, True)
                            value = value.strip()

                            list_items.append({
                                'ctype': ctype,
                                'value': value,
                            })

                        workspace_schema['sheets'].append({
                            'stype'      : stype,
                            'title'      : sheet_document.title,
                            'list-items' : list_items,
                        })

                workspace_schema_bytes = pickle.dumps(workspace_schema)

                with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    zip_file.writestr('workspace_schema', workspace_schema_bytes)
                    for dataframe_path in all_dataframe_paths:
                        zip_file.write(os.path.join(temp_dir, dataframe_path), dataframe_path)

                # Update the file signature if needed
                if not export:
                    window.file = Gio.File.new_for_path(file_path)

                return True

        except Exception as e:
            print(e)

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

    def open_file(self,
                  window:   Window,
                  in_place: bool = False) -> None:
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

        FILTER_ERBOOK = Gtk.FileFilter()
        FILTER_ERBOOK.set_name('Eruo Workbook')
        FILTER_ERBOOK.add_pattern('*.erbook')
        FILTER_ERBOOK.add_mime_type('application/vnd.eruo.erbook')

        # This option is not intended to be used by the users to force
        # opening unsupported files. Instead, it can be used for example
        # to verify whether they are in the right directory or to see
        # whether the file exists but it's not currently supported.
        FILTER_ALL = Gtk.FileFilter()
        FILTER_ALL.set_name('All Files')
        FILTER_ALL.add_pattern('*')

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(FILTER_ALL)
        filters.append(FILTER_ERBOOK)
        filters.append(FILTER_PARQUET)
        filters.append(FILTER_JSON)
        filters.append(FILTER_TXT)

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

        if save_as_is := not file_path:
            file_path = file.get_path()

        # If the user wants to save the file in the original format (not .erbook),
        # we show a confirmation dialog to the user so that the user awares that
        # any incompatible changes will be lost.
        file_format = file_path.split('.')[-1].lower()
        if save_as_is and file_format != 'erbook':
            def proceed_to_save() -> None:
                self.save_file(window, file_path, **kwargs)
            self.show_save_as_is_confirmation(window, proceed_to_save)
            return

        # A successful write will trigger the `file-saved` signal so that the users
        # can be notified that their work has been saved. Otherwise, the `write_file`
        # function will send an in-app notification to the user if something went wrong.
        def write_file() -> None:
            if self.write_file(window, file_path, **kwargs):
                GLib.idle_add(self.emit, 'file-saved', file_path)

        # FIXME: Using a thread to write the file to avoid blocking the main thread,
        #        but potentially it can introduce to some race conditions.
        threading.Thread(target=write_file, daemon=True).start()

    def export_file(self,
                    window:      Window,
                    file_path:   str = '',
                    **kwargs) -> None:

        def write_file() -> None:
            if self.write_file(window, file_path, export=True, **kwargs):
                GLib.idle_add(self.emit, 'file-exported', file_path)

        # FIXME: Using a thread to write the file to avoid blocking the main thread,
        #        but potentially it can introduce to some race conditions.
        threading.Thread(target=write_file, daemon=True).start()

    def show_save_as_is_confirmation(self,
                                     window:   Window,
                                     callback: callable) -> None:
        alert_dialog = Adw.AlertDialog()

        alert_dialog.set_heading(_('Keep This Format?'))
        alert_dialog.set_body(_('Saving in the original file format will leave '
                                'any incompatible features.'))

        alert_dialog.add_response('cancel', _('_Cancel'))
        alert_dialog.add_response('save-as', _('_Choose Format...'))
        alert_dialog.add_response('save', _('_Keep This Format'))

        alert_dialog.set_response_appearance('save', Adw.ResponseAppearance.DESTRUCTIVE)

        alert_dialog.set_default_response('save')
        alert_dialog.set_close_response('cancel')

        def on_alert_dialog_dismissed(dialog: Adw.AlertDialog,
                                      result: Gio.Task) -> None:
            if result.had_error():
                return

            response = dialog.choose_finish(result)

            if response == 'save-as':
                self.save_as_file(window)
                return

            if response == 'save':
                callback()
                return

            GLib.idle_add(self.emit, 'file-cancel')

        alert_dialog.choose(window, None, on_alert_dialog_dismissed)

    def save_as_file(self, window: Window) -> None:
        # In here, we just open a file save-as dialog to let the users
        # configure where and in which format they want to save the work.
        dialog = FileSaveAsDialog(window, self.save_file)
        dialog.present(window)

    def export_as_file(self, window: Window) -> None:
        dialog = FileSaveAsDialog(window, self.export_file)
        dialog.view_stack.set_visible_child_name('csv')
        dialog.save_button.set_label('Export')
        dialog.present(window)