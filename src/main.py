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

from gi.repository import Adw, Gdk, Gio, GObject, Gtk

from . import globals
from .clipboard_manager import ClipboardManager
from .file_manager import FileManager
from .sheet_document import SheetDocument
from .window import Window

class Application(Adw.Application):
    """The main application singleton class."""

    def __init__(self) -> None:
        super().__init__(application_id='com.macipra.eruo',
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
                         resource_base_path='/com/macipra/eruo')

        self.file_manager = FileManager()
        self.file_manager.connect('file-opened', self.on_file_opened)
        self.file_manager.connect('file-saved', self.on_file_saved)

        self.clipboard = ClipboardManager()

        self.create_action('quit', self.on_quit_action, ['<primary>q'])
        self.create_action('about', self.on_about_action)
        self.create_action('preferences', self.on_preferences_action, ['<primary>comma'])
        self.create_action('toggle-sidebar', self.on_toggle_sidebar_action, ['<primary>b'])
        self.create_action('open', self.on_open_file_action, ['<primary>o'])
        self.create_action('save', self.on_save_file_action, ['<primary>s'])
        self.create_action('save-as', self.on_save_as_file_action, ['<shift><primary>s'])
        self.create_action('open-search', self.on_open_search_action, ['<primary>f'])
        self.create_action('open-sort-filter', self.on_open_sort_filter_action)
        self.create_action('toggle-replace', self.on_toggle_replace_action, ['<primary>h'])
        self.create_action('toggle-search-all', self.on_toggle_search_all_action, ['<primary><shift>f'])
        self.create_action('toggle-replace-all', self.on_toggle_replace_all_action, ['<primary><shift>h'])
        self.create_action('toggle-history', self.on_toggle_history_action)
        self.create_action('new-sheet', self.on_new_sheet_action, ['<primary>t'])
        self.create_action('close-sheet', self.on_close_sheet_action, ['<primary>w'])
        self.create_action('undo', self.on_undo_action, ['<primary>z'])
        self.create_action('redo', self.on_redo_action, ['<shift><primary>z'])
        self.create_action('cut', self.on_cut_action, ['<primary>x'])
        self.create_action('copy', self.on_copy_action, ['<primary>c'])
        self.create_action('paste', self.on_paste_action, ['<primary>v'])
        self.create_action('insert-row-above', self.on_insert_row_above_action)
        self.create_action('insert-row-below', self.on_insert_row_below_action)
        self.create_action('insert-column-left', self.on_insert_column_left_action)
        self.create_action('insert-column-right', self.on_insert_column_right_action)
        self.create_action('duplicate-to-above', self.on_duplicate_to_above_action)
        self.create_action('duplicate-to-below', self.on_duplicate_to_below_action)
        self.create_action('duplicate-to-left', self.on_duplicate_to_left_action)
        self.create_action('duplicate-to-right', self.on_duplicate_to_right_action)
        self.create_action('delete-row', self.on_delete_row_action)
        self.create_action('delete-column', self.on_delete_column_action)
        self.create_action('clear-contents', self.on_clear_contents_action, ['Delete'])
        self.create_action('filter-cell-value', self.on_filter_cell_value_action)
        # self.create_action('filter-cell-color', self.on_filter_cell_color_action)
        # self.create_action('filter-font-color', self.on_filter_font_color_action)
        self.create_action('filter-cell-values', self.on_filter_cell_values_action)
        self.create_action('reset-all-filters', self.on_reset_all_filters_action)
        self.create_action('sort-smallest-to-largest', self.on_sort_smallest_to_largest_action)
        self.create_action('sort-largest-to-smallest', self.on_sort_largest_to_smallest_action)
        self.create_action('convert-to-int8', self.on_convert_to_int8_action)
        self.create_action('convert-to-int16', self.on_convert_to_int16_action)
        self.create_action('convert-to-int32', self.on_convert_to_int32_action)
        self.create_action('convert-to-int64', self.on_convert_to_int64_action)
        self.create_action('convert-to-uint8', self.on_convert_to_uint8_action)
        self.create_action('convert-to-uint16', self.on_convert_to_uint16_action)
        self.create_action('convert-to-uint32', self.on_convert_to_uint32_action)
        self.create_action('convert-to-uint64', self.on_convert_to_uint64_action)
        self.create_action('convert-to-float32', self.on_convert_to_float32_action)
        self.create_action('convert-to-float64', self.on_convert_to_float64_action)
        self.create_action('convert-to-decimal', self.on_convert_to_decimal_action)
        self.create_action('convert-to-date', self.on_convert_to_date_action)
        self.create_action('convert-to-time', self.on_convert_to_time_action)
        self.create_action('convert-to-datetime', self.on_convert_to_datetime_action)
        self.create_action('convert-to-categorical', self.on_convert_to_categorical_action)
        self.create_action('convert-to-boolean', self.on_convert_to_boolean_action)
        self.create_action('convert-to-text', self.on_convert_to_text_action)

    def do_activate(self) -> None:
        if window := self.get_active_window():
            window.present()
            return
        self.create_new_window()

    def on_quit_action(self, action: Gio.SimpleAction, *args) -> None:
        window = self.get_active_window()

        # We do cleanup the history of all sheets in the current window, mainly
        # to free up disk space from the temporary files, usually .ersnap files
        # created for example when multiple cells or even the entire row(s) or
        # column(s) are edited so that the user can perform undo/redo operations.
        # At the moment, any previous states will be stored as a file on a disk,
        # not in memory to reduce the memory footprint. It's purely to support
        # handling of big datasets more possible.
        for page_index in range (window.tab_view.get_n_pages()):
            tab_page = window.tab_view.get_nth_page(page_index)
            sheet_view = tab_page.get_child()
            sheet_view.document.history.cleanup_all()

        # Instead of closing the whole application at once, we just close the current
        # window one by one until no more windows are open and the application will be
        # closed automatically by itself.
        window.close()

    def on_about_action(self, action: Gio.SimpleAction, *args) -> None:
        dialog = Adw.AboutDialog(application_name='Data Studio',
                                 application_icon='com.macipra.eruo',
                                 developer_name='Naufan Rusyda Faikar',
                                 version='0.1.0',
                                 developers=['Naufan Rusyda Faikar'],
                                 copyright='© 2025 Naufan Rusyda Faikar',
                                 issue_url='https://github.com/naruaika/eruo-data-studio/issues',
                                 support_url='https://github.com/naruaika/eruo-data-studio/discussions')
        dialog.set_translator_credits(_('translator-credits'))
        dialog.present(self.get_active_window())

    def on_preferences_action(self, action: Gio.SimpleAction, *args) -> None:
        raise NotImplementedError

    def on_toggle_sidebar_action(self, action: Gio.SimpleAction, *args) -> None:
        window = self.get_active_window()
        window.do_toggle_sidebar()

    def on_open_file_action(self, action: Gio.SimpleAction, *args) -> None:
        window = self.get_active_window()
        self.file_manager.open_file(window)

    def on_save_file_action(self, action: Gio.SimpleAction, *args) -> None:
        window = self.get_active_window()

        # Pre-check if there is any data to save
        sheets = list(window.sheet_manager.sheets.values())
        if len(sheets) == 0 or len(sheets[0].data.dfs) == 0:
            return

        self.file_manager.save_file(window)

    def on_save_as_file_action(self, action: Gio.SimpleAction, *args) -> None:
        window = self.get_active_window()

        # Pre-check if there is any data to save
        sheets = list(window.sheet_manager.sheets.values())
        if len(sheets) == 0 or len(sheets[0].data.dfs) == 0:
            return

        self.file_manager.save_as_file(window)

    def on_open_search_action(self, action: Gio.SimpleAction, *args) -> None:
        window = self.get_active_window()
        window.search_replace_overlay.open_search_box()

    def on_open_sort_filter_action(self, action: Gio.SimpleAction, *args) -> None:
        window = self.get_active_window()

        # Close all possible views on the sidebar to reveal the home view
        window.search_replace_all_view.close_search_view()

        # Open the home view
        window.sidebar_home_view.open_home_view()

    def on_toggle_replace_action(self, action: Gio.SimpleAction, *args) -> None:
        window = self.get_active_window()
        window.search_replace_overlay.toggle_replace_section()

    def on_toggle_search_all_action(self, action: Gio.SimpleAction, *args) -> None:
        window = self.get_active_window()

        tab_page = window.search_replace_all_page
        tab_view = window.search_replace_all_view

        if window.sidebar_tab_view.get_selected_page() == tab_page:
            tab_view.close_search_view()
            window.sidebar_home_view.open_home_view()
        else:
            tab_view.open_search_view()

    def on_toggle_replace_all_action(self, action: Gio.SimpleAction, *args) -> None:
        window = self.get_active_window()
        tab_view = window.search_replace_all_view
        tab_view.toggle_replace_section()

    def on_toggle_history_action(self, action: Gio.SimpleAction, *args) -> None:
        pass

    def on_file_opened(self, source: GObject.Object, file_path: str) -> None:
        if not file_path:
            return # shouldn't happen, but for completeness

        self.create_new_window(file_path)

    def on_file_saved(self, source: GObject.Object, file_path: str) -> None:
        pass # TODO: indicate the user when the file has been saved

    def on_new_sheet_action(self, action: Gio.SimpleAction, *args) -> None:
        window = self.get_active_window()
        sheet_view = window.sheet_manager.create_sheet(None)
        window.add_new_tab(sheet_view)

    def on_close_sheet_action(self, action: Gio.SimpleAction, *args) -> None:
        window = self.get_active_window()
        tab_page = window.tab_view.get_selected_page()
        window.tab_view.close_page(tab_page)

    def on_undo_action(self, action: Gio.SimpleAction, *args) -> None:
        window = self.get_active_window()
        focused_widget = window.get_focus()

        # Prevent from colliding with the undo action of editable widgets.
        if isinstance(focused_widget, Gtk.Text) \
                or isinstance(focused_widget, Gtk.TextView):
            focused_widget.activate_action('text.undo', None)
            return

        globals.history.undo()

    def on_redo_action(self, action: Gio.SimpleAction, *args) -> None:
        window = self.get_active_window()
        focused_widget = window.get_focus()

        # Prevent from colliding with the redo action of editable widgets
        if isinstance(focused_widget, Gtk.Text) \
                or isinstance(focused_widget, Gtk.TextView):
            focused_widget.activate_action('text.redo', None)
            return

        globals.history.redo()

    def on_cut_action(self, action: Gio.SimpleAction, *args) -> bool:
        window = self.get_active_window()

        # Prevent from colliding with the cut action of editable widgets
        focused_widget = window.get_focus()
        if isinstance(focused_widget, Gtk.Text) \
                or isinstance(focused_widget, Gtk.TextView):
            focused_widget.activate_action('clipboard.cut', None)
            return True

        document = self.get_current_active_document()
        document.cut_from_current_selection(self.clipboard)

        return True

    def on_copy_action(self, action: Gio.SimpleAction, *args) -> bool:
        window = self.get_active_window()

        # Prevent from colliding with the copy action of editable widgets
        focused_widget = window.get_focus()
        if isinstance(focused_widget, Gtk.Text) \
                or isinstance(focused_widget, Gtk.TextView):
            focused_widget.activate_action('clipboard.copy', None)
            return True

        document = self.get_current_active_document()
        document.copy_from_current_selection(self.clipboard)

        return True

    def on_paste_action(self, action: Gio.SimpleAction, *args) -> bool:
        window = self.get_active_window()

        # Prevent from colliding with the paste action of editable widgets
        focused_widget = window.get_focus()
        if isinstance(focused_widget, Gtk.Text) \
                or isinstance(focused_widget, Gtk.TextView):
            focused_widget.activate_action('clipboard.paste', None)
            return True

        def on_clipboard_text_received(clipboard: Gdk.Clipboard, result: Gio.Task) -> None:
            if result.had_error():
                document.paste_into_current_selection(self.clipboard, None)
                return False

            text = clipboard.read_text_finish(result)
            document.paste_into_current_selection(self.clipboard, text)

        document = self.get_current_active_document()
        self.clipboard.read_text_async(on_clipboard_text_received)

        return True

    def on_insert_row_above_action(self, action: Gio.SimpleAction, *args) -> None:
        document = self.get_current_active_document()
        document.insert_blank_from_current_rows(above=True)

    def on_insert_row_below_action(self, action: Gio.SimpleAction, *args) -> None:
        document = self.get_current_active_document()
        document.insert_blank_from_current_rows(above=False)

    def on_insert_column_left_action(self, action: Gio.SimpleAction, *args) -> None:
        document = self.get_current_active_document()
        document.insert_blank_from_current_columns(left=True)

    def on_insert_column_right_action(self, action: Gio.SimpleAction, *args) -> None:
        document = self.get_current_active_document()
        document.insert_blank_from_current_columns(left=False)

    def on_duplicate_to_above_action(self, action: Gio.SimpleAction, *args) -> None:
        document = self.get_current_active_document()
        document.duplicate_from_current_rows(above=True)

    def on_duplicate_to_below_action(self, action: Gio.SimpleAction, *args) -> None:
        document = self.get_current_active_document()
        document.duplicate_from_current_rows(above=False)

    def on_duplicate_to_left_action(self, action: Gio.SimpleAction, *args) -> None:
        document = self.get_current_active_document()
        document.duplicate_from_current_columns(left=True)

    def on_duplicate_to_right_action(self, action: Gio.SimpleAction, *args) -> None:
        document = self.get_current_active_document()
        document.duplicate_from_current_columns(left=False)

    def on_delete_row_action(self, action: Gio.SimpleAction, *args) -> None:
        document = self.get_current_active_document()
        document.delete_current_rows()

    def on_delete_column_action(self, action: Gio.SimpleAction, *args) -> None:
        document = self.get_current_active_document()
        document.delete_current_columns()

    def on_clear_contents_action(self, action: Gio.SimpleAction, *args) -> None:
        document = self.get_current_active_document()
        document.update_current_cells('')

    def on_filter_cell_value_action(self, action: Gio.SimpleAction, *args) -> None:
        document = self.get_current_active_document()
        document.filter_current_rows()

    def on_filter_cell_values_action(self, action: Gio.SimpleAction, *args) -> None:
        document = self.get_current_active_document()
        document.filter_current_rows(multiple=True)

    def on_reset_all_filters_action(self, action: Gio.SimpleAction, *args) -> None:
        document = self.get_current_active_document()
        document.reset_all_filters()

    def on_filter_cell_color_action(self, action: Gio.SimpleAction, *args) -> None:
        pass

    def on_filter_font_color_action(self, action: Gio.SimpleAction, *args) -> None:
        pass

    def on_sort_smallest_to_largest_action(self, action: Gio.SimpleAction, *args) -> None:
        document = self.get_current_active_document()
        document.sort_current_rows(descending=False)

    def on_sort_largest_to_smallest_action(self, action: Gio.SimpleAction, *args) -> None:
        document = self.get_current_active_document()
        document.sort_current_rows(descending=True)

    def on_convert_to_categorical_action(self, action: Gio.SimpleAction, *args) -> None:
        self.convert_to(polars.Categorical)

    def on_convert_to_int8_action(self, action: Gio.SimpleAction, *args) -> None:
        self.convert_to(polars.Int8)

    def on_convert_to_int16_action(self, action: Gio.SimpleAction, *args) -> None:
        self.convert_to(polars.Int16)

    def on_convert_to_int32_action(self, action: Gio.SimpleAction, *args) -> None:
        self.convert_to(polars.Int32)

    def on_convert_to_int64_action(self, action: Gio.SimpleAction, *args) -> None:
        self.convert_to(polars.Int64)

    def on_convert_to_uint8_action(self, action: Gio.SimpleAction, *args) -> None:
        self.convert_to(polars.UInt8)

    def on_convert_to_uint16_action(self, action: Gio.SimpleAction, *args) -> None:
        self.convert_to(polars.UInt16)

    def on_convert_to_uint32_action(self, action: Gio.SimpleAction, *args) -> None:
        self.convert_to(polars.UInt32)

    def on_convert_to_uint64_action(self, action: Gio.SimpleAction, *args) -> None:
        self.convert_to(polars.UInt64)

    def on_convert_to_float32_action(self, action: Gio.SimpleAction, *args) -> None:
        self.convert_to(polars.Float32)

    def on_convert_to_float64_action(self, action: Gio.SimpleAction, *args) -> None:
        self.convert_to(polars.Float64)

    def on_convert_to_decimal_action(self, action: Gio.SimpleAction, *args) -> None:
        self.convert_to(polars.Decimal)

    def on_convert_to_date_action(self, action: Gio.SimpleAction, *args) -> None:
        self.convert_to(polars.Date)

    def on_convert_to_time_action(self, action: Gio.SimpleAction, *args) -> None:
        self.convert_to(polars.Time)

    def on_convert_to_datetime_action(self, action: Gio.SimpleAction, *args) -> None:
        self.convert_to(polars.Datetime)

    def on_convert_to_boolean_action(self, action: Gio.SimpleAction, *args) -> None:
        self.convert_to(polars.Boolean)

    def on_convert_to_text_action(self, action: Gio.SimpleAction, *args) -> None:
        self.convert_to(polars.Utf8)

    def convert_to(self, dtype: polars.DataType) -> None:
        document = self.get_current_active_document()
        document.convert_current_columns_dtype(dtype)

    def get_current_active_document(self) -> SheetDocument:
        window = self.get_active_window()
        return window.get_current_active_document()

    def create_action(self,
                      name:      str,
                      callback:  callable,
                      shortcuts: list = None) -> None:
        action = Gio.SimpleAction.new(name, None)
        action.connect('activate', callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f'app.{name}', shortcuts)

    def create_new_window(self, file_path: str = '') -> None:
        file = None
        dataframe = None

        # By default, no file is loaded when creating a new window.
        # But later on, we can add support for file manager integration
        # as well as a command line interface. Maybe even adding support
        # for opening the last session automatically.
        if file_path:
            file = Gio.File.new_for_path(file_path)
            dataframe = self.file_manager.read_file(file_path)

        window = Window(application=self, file=file, dataframe=dataframe)
        window.present()

def main(version):
    """The application's entry point."""
    return Application().run(sys.argv)