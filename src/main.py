# main.py
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

import gi
import polars
import sys

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw, Gio, Gtk

from .utils import Log, print_log
from .window import EruoDataStudioWindow

class EruoDataStudioApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self) -> None:
        """
        Creates a new EruoDataStudioApplication.

        Sets up the application's unique ID and resource base path,
        and creates several actions that can be activated by the user.
        """
        super().__init__(application_id='com.macipra.Eruo',
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
                         resource_base_path='/com/macipra/Eruo')

        print_log('Registering application actions...', Log.DEBUG)
        self.create_action('quit', self.on_quit_action, ['<primary>q'])
        self.create_action('about', self.on_about_action)
        self.create_action('preferences', self.on_preferences_action, ['<primary>comma'])
        self.create_action('open-file', self.on_open_file_action, ['<primary>o'])

        self.create_action('sheet.column.sort-a-to-z', self.on_column_sort_a_to_z_action)
        self.create_action('sheet.column.sort-z-to-a', self.on_column_sort_z_to_a_action)
        self.create_action('sheet.column.reset-sort', self.on_column_reset_sort_action)
        self.create_action('sheet.column.apply-filter', self.on_column_apply_filter_action)
        self.create_action('sheet.column.reset-filter', self.on_column_reset_filter_action)
        for data_type in ['boolean', 'int8', 'int16', 'int32', 'int64',  'uint8', 'uint16', 'uint32', 'uint64',
                          'float32', 'float64', 'decimal', 'string', 'categorical', 'date', 'time', 'datetime']:
            self.create_action(f'sheet.column.convert-to.{data_type}', getattr(self, f'on_column_convert_to_{data_type}_action'))

    def do_activate(self) -> None:
        """
        Activates the application.

        This method is called when the application is activated,
        e.g. when the user clicks on its desktop icon or searches for it
        in their application launcher.

        The method opens a new window if none is already open.
        """
        self.open_new_window(None)

    def on_quit_action(self, *args) -> None:
        """
        Closes the currently active window.

        This method is activated when the user uses the "Quit" action,
        usually by clicking on the "Quit" menu item or pressing the
        shortcut key combination Ctrl+Q.
        """
        self.get_active_window().close()

    def on_about_action(self, *args) -> None:
        """
        Shows the about dialog for the application.

        This method is activated when the user uses the "About" action,
        usually by clicking on the "About" menu item or pressing the
        shortcut key combination Ctrl+?. The about dialog shows the
        name, icon, version, and copyright information of the application,
        as well as a list of developers and translators.
        """
        dialog = Adw.AboutDialog(application_name='Eruo Data Studio',
                                 application_icon='com.macipra.Eruo',
                                 developer_name='Naufan Rusyda Faikar',
                                 version='0.1.0',
                                 developers=['Naufan Rusyda Faikar'],
                                 copyright='© 2025 Naufan Rusyda Faikar')
        # Translators: Replace "translator-credits" with your name/username, and optionally an email or URL.
        dialog.set_translator_credits(_('translator-credits'))
        dialog.present(self.get_active_window())

    def on_open_file_action(self, *args) -> None:
        """
        Opens a file dialog for the user to select a file to open.

        This method presents a file dialog to the user, allowing them to
        select a file to be opened in the application window. The dialog
        filters files to show only text and CSV files by default, although
        all files can be displayed with the "All Files" option. This method
        is triggered by the "open-file" action and utilizes a callback to
        handle the dialog dismissal.

        Args:
            *args: Variable length argument list. Currently unused.

        Note:
            At the moment, only text and CSV files are supported.
        """
        FILTER_TXT = Gtk.FileFilter()
        FILTER_TXT.set_name(name='Text Files')
        FILTER_TXT.add_pattern(pattern='*.txt')
        FILTER_TXT.add_pattern(pattern='*.csv')
        FILTER_TXT.add_mime_type(mime_type='text/plain')
        FILTER_TXT.add_mime_type(mime_type='text/csv')

        FILTER_ALL = Gtk.FileFilter()
        FILTER_ALL.set_name(name='All Files')
        FILTER_ALL.add_pattern(pattern='*')

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(item=FILTER_TXT)
        filters.append(item=FILTER_ALL)

        dialog = Gtk.FileDialog.new()
        dialog.set_title(title='Open File')
        dialog.set_modal(True)
        dialog.set_filters(filters)

        print_log('Opening a file dialog...', Log.DEBUG)
        dialog.open(parent=self.get_active_window(), callback=self.on_file_dialog_dismissed)

    def on_file_dialog_dismissed(self, dialog: Gtk.FileDialog, response: Gio.Task) -> None:
        """
        Handles the dismissal of the file dialog and processes the selected file.

        This method is invoked when the file dialog is dismissed. It attempts to
        retrieve the file selected by the user. If the file is successfully located,
        it checks if the file is already open in any existing window. If the file is
        already open, it brings that window to the foreground. Otherwise, it opens
        the file in a new window. Logs relevant status messages during the process.

        Args:
            dialog: The Gtk.FileDialog that was dismissed.
            response: The Gio.Task containing the result of the dialog operation.
        """
        def finish() -> None:
            print_log('File dialog dismissed', Log.DEBUG)

        file = None
        try:
            print_log('Trying to locate file...', Log.DEBUG)
            file = dialog.open_finish(response)
            print_log(f'Located file {file.get_path()}')
        except Exception as e:
            print_log(f'Failed to locate file: {e}', Log.WARNING)

        if file is None:
            finish()
            return

        for window in self.get_windows():
            if window.dbms.file and window.dbms.file.get_path() == file.get_path():
                print_log('File is already open in a window', Log.DEBUG)
                window.present()
                finish()
                return

        self.open_new_window(file)
        finish()

    def on_preferences_action(self, *args) -> None:
        """
        Opens the preferences dialog for the application.

        This method is triggered when the user selects the "Preferences"
        action, typically through a menu item or a keyboard shortcut.
        It is intended to present a dialog or window where users can
        configure application-specific settings.

        Args:
            *args: Variable length argument list. Currently unused.
        """
        raise NotImplementedError # TODO

    def on_column_sort_a_to_z_action(self, *args) -> None:
        """
        Sorts the selected column in ascending order.

        This method is triggered when the user selects the "Sort A to Z"
        action, typically through a menu item or a keyboard shortcut.
        It is intended to sort the selected column in ascending order.

        Args:
            *args: Variable length argument list. Currently unused.
        """
        window = self.get_active_window()
        window.dbms.sort_column_values(window.selection.get_previous_selected_column())
        window.action_set_enabled('app.sheet.column.reset-sort', True)
        window.renderer.invalidate_cache()
        window.main_canvas.queue_draw()

    def on_column_sort_z_to_a_action(self, *args) -> None:
        """
        Sorts the selected column in descending order.

        This method is triggered when the user selects the "Sort Z to A"
        action, typically through a menu item or a keyboard shortcut.
        It is intended to sort the selected column in descending order.

        Args:
            *args: Variable length argument list. Currently unused.
        """
        window = self.get_active_window()
        window.dbms.sort_column_values(window.selection.get_previous_selected_column(), descending=True)
        window.action_set_enabled('app.sheet.column.reset-sort', True)
        window.renderer.invalidate_cache()
        window.main_canvas.queue_draw()

    def on_column_reset_sort_action(self, *args) -> None:
        """
        Resets the sort order of the selected column.

        This method is triggered when the user selects the "Reset Sort"
        action, typically through a menu item or a keyboard shortcut.
        It is intended to reset the sort order of the selected column.

        Args:
            *args: Variable length argument list. Currently unused.
        """
        window = self.get_active_window()
        window.dbms.sort_column_values(-1)
        window.action_set_enabled('app.sheet.column.reset-sort', False)
        window.renderer.invalidate_cache()
        window.main_canvas.queue_draw()

    def on_column_apply_filter_action(self, *args) -> None:
        """
        Applies a filter to the selected column.

        This method is triggered when the user selects the "Apply Filter"
        action, typically through a menu item or a keyboard shortcut.
        It is intended to apply a filter to the selected column.

        Args:
            *args: Variable length argument list. Currently unused.
        """
        window = self.get_active_window()
        if not window.dbms.apply_filter():
            return
        window.dbms.summary_fill_counts()
        window.update_project_status()
        window.renderer.invalidate_cache()
        window.main_canvas.queue_draw()
        window.action_set_enabled('app.sheet.column.reset-filter', True)

    def on_column_reset_filter_action(self, *args) -> None:
        """
        Resets the filter applied to the selected column.

        This method is triggered when the user selects the "Reset Filter"
        action, typically through a menu item or a keyboard shortcut.
        It is intended to reset the filter applied to the selected column.

        Args:
            *args: Variable length argument list. Currently unused.
        """
        window = self.get_active_window()
        window.dbms.reset_filter()
        window.action_set_enabled('app.sheet.column.reset-filter', False)
        window.renderer.invalidate_cache()
        window.main_canvas.queue_draw()

    def on_column_convert_to_boolean_action(self, *args) -> None:
        """Converts the selected column to boolean values."""
        self.column_convert_to(polars.Boolean)

    def on_column_convert_to_int8_action(self, *args) -> None:
        """Converts the selected column to Int8 values."""
        self.column_convert_to(polars.Int8)

    def on_column_convert_to_int16_action(self, *args) -> None:
        """Converts the selected column to Int16 values."""
        self.column_convert_to(polars.Int16)

    def on_column_convert_to_int32_action(self, *args) -> None:
        """Converts the selected column to Int32 values."""
        self.column_convert_to(polars.Int32)

    def on_column_convert_to_int64_action(self, *args) -> None:
        """Converts the selected column to Int64 values."""
        self.column_convert_to(polars.Int64)

    def on_column_convert_to_uint8_action(self, *args) -> None:
        """Converts the selected column to UInt8 values."""
        self.column_convert_to(polars.UInt8)

    def on_column_convert_to_uint16_action(self, *args) -> None:
        """Converts the selected column to UInt16 values."""
        self.column_convert_to(polars.UInt16)

    def on_column_convert_to_uint32_action(self, *args) -> None:
        """Converts the selected column to UInt32 values."""
        self.column_convert_to(polars.UInt32)

    def on_column_convert_to_uint64_action(self, *args) -> None:
        """Converts the selected column to UInt64 values."""
        self.column_convert_to(polars.UInt64)

    def on_column_convert_to_float32_action(self, *args) -> None:
        """Converts the selected column to Float32 values."""
        self.column_convert_to(polars.Float32)

    def on_column_convert_to_float64_action(self, *args) -> None:
        """Converts the selected column to Float64 values."""
        self.column_convert_to(polars.Float64)

    def on_column_convert_to_decimal_action(self, *args) -> None:
        """Converts the selected column to Decimal values."""
        self.column_convert_to(polars.Decimal)

    def on_column_convert_to_string_action(self, *args) -> None:
        """Converts the selected column to String values."""
        self.column_convert_to(polars.Utf8)

    def on_column_convert_to_categorical_action(self, *args) -> None:
        """Converts the selected column to Categorical values."""
        self.column_convert_to(polars.Categorical)

    def on_column_convert_to_date_action(self, *args) -> None:
        """Converts the selected column to Date values."""
        self.column_convert_to(polars.Date)

    def on_column_convert_to_time_action(self, *args) -> None:
        """Converts the selected column to Time values."""
        self.column_convert_to(polars.Time)

    def on_column_convert_to_datetime_action(self, *args) -> None:
        """Converts the selected column to Datetime values."""
        self.column_convert_to(polars.Datetime)

    def column_convert_to(self, col_type: polars.DataType, *args) -> None:
        """
        Converts the selected column to the specified data type.

        This method is triggered when the user selects the "Convert to [data type]"
        action, typically through a menu item or a keyboard shortcut.
        It is intended to convert the selected column to the specified data type.

        Args:
            col_type: The data type to convert the column to.
            *args: Variable length argument list. Currently unused.
        """
        window = self.get_active_window()
        col_index = window.selection.get_previous_selected_column()
        if window.dbms.convert_column_to(col_index, col_type):
            window.renderer.invalidate_cache()
            window.main_canvas.queue_draw()
        else:
            col_name = window.dbms.get_columns()[col_index]
            if col_name.startswith('Categorical'):
                col_name = 'Categorical'
            elif col_name.startswith('Datetime'):
                col_name = 'Datetime'
            window.show_toast_message(f'Failed to convert column \'{col_name}\' to {col_type}')

    def create_action(self, name: str, callback: callable, shortcuts: list | None = None) -> None:
        """
        Creates an action for the application.

        This method creates a new action with the given name, connects the
        given callback to the action's activate signal, and adds the action
        to the application. If shortcuts are provided, the action is also
        associated with the given shortcuts.

        Args:
            name: The name of the action to create.
            callback: The callback to connect to the action's activate signal.
            shortcuts: An optional list of shortcuts to associate with the action.
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect('activate', callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f'app.{name}', shortcuts)

    def open_new_window(self, file: Gio.File | None) -> None:
        """
        Opens a new window for the application.

        This method opens a new window for the application, loading the given file
        if specified. If the application already has a window with no associated
        file, it will be reused instead of opening a new window.

        Args:
            file: An optional Gio.File object to load into the new window.
        """
        window = self.get_active_window()
        if window and not window.dbms.file:
            print_log('Reusing the active window...', Log.DEBUG)
            window.load_file(file)
            return

        print_log(f'Opening a new window...', Log.DEBUG)
        EruoDataStudioWindow(application=self, file=file).present()

def main(version):
    """The application's entry point."""
    app = EruoDataStudioApplication()
    return app.run(sys.argv)