# main.py
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


from typing import Any
import duckdb
import gi
import json
import os
import polars
import re
import sys

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('GtkSource', '5')

# 0: Disable debug mode entirely
# 1: Don't wait for the debugger
# 2: Should wait for the debugger
if (debug_mode := int(os.environ.get('EDS_DEBUG', '0') or '0')) > 0:
    try:
        import debugpy
        debugpy.listen(('127.0.0.1', 5678))
        if debug_mode > 1:
            debugpy.wait_for_client()
    except ModuleNotFoundError:
        pass

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, GtkSource

from . import globals
from .clipboard_manager import ClipboardManager
from .file_manager import FileManager
from .sheet_document import SheetDocument
from .sheet_notebook import SheetNotebook
from .window import Window

class Application(Adw.Application):
    """The main application singleton class."""

    def __init__(self) -> None:
        super().__init__(application_id='com.macipra.eruo',
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
                         resource_base_path='/com/macipra/eruo')
        # Register the GtkSource.View to be used in the GtkBuilder
        # See https://stackoverflow.com/a/10528052/8791891
        GObject.type_register(GtkSource.View)

        globals.register_connection = self.register_connection

        self.settings = Gio.Settings.new('com.macipra.eruo')

        # Load the recently opened connection list
        saved_connection_list = self.settings.get_string('connection-list')
        deserialized_connection_list = json.loads(saved_connection_list)
        self.connection_list: list[dict] = deserialized_connection_list

        self.file_manager = FileManager()
        self.file_manager.connect('file-opened', self.on_file_opened)
        self.file_manager.connect('file-saved', self.on_file_saved)

        self.clipboard = ClipboardManager()

        self.file_paths = [] # File paths to open,
                             # assigned from the command line

        self.create_action('about', self.on_about_action)
        self.create_action('add-connection', self.on_add_new_connection_action)
        self.create_action('apply-pending-table', self.on_apply_pending_table_action, param_type=GLib.VariantType('s'))
        self.create_action('clear-contents', self.on_clear_contents_action, ['Delete'])
        self.create_action('close-other-tabs', self.on_close_other_tabs_action, param_type=GLib.VariantType('s'))
        self.create_action('close-selected-tab', self.on_close_selected_tab_action, ['<primary>w'])
        self.create_action('close-tab', self.on_close_tab_action, param_type=GLib.VariantType('s'))
        self.create_action('close-tabs-to-left', self.on_close_tabs_to_left_action, param_type=GLib.VariantType('s'))
        self.create_action('close-tabs-to-right', self.on_close_tabs_to_right_action, param_type=GLib.VariantType('s'))
        self.create_action('convert-to-boolean', self.on_convert_to_boolean_action)
        self.create_action('convert-to-categorical', self.on_convert_to_categorical_action)
        self.create_action('convert-to-date', self.on_convert_to_date_action)
        self.create_action('convert-to-datetime', self.on_convert_to_datetime_action)
        self.create_action('convert-to-decimal', self.on_convert_to_decimal_action)
        self.create_action('convert-to-float32', self.on_convert_to_float32_action)
        self.create_action('convert-to-float64', self.on_convert_to_float64_action)
        self.create_action('convert-to-int16', self.on_convert_to_int16_action)
        self.create_action('convert-to-int32', self.on_convert_to_int32_action)
        self.create_action('convert-to-int64', self.on_convert_to_int64_action)
        self.create_action('convert-to-int8', self.on_convert_to_int8_action)
        self.create_action('convert-to-text', self.on_convert_to_text_action)
        self.create_action('convert-to-time', self.on_convert_to_time_action)
        self.create_action('convert-to-uint16', self.on_convert_to_uint16_action)
        self.create_action('convert-to-uint32', self.on_convert_to_uint32_action)
        self.create_action('convert-to-uint64', self.on_convert_to_uint64_action)
        self.create_action('convert-to-uint8', self.on_convert_to_uint8_action)
        self.create_action('copy', self.on_copy_action, ['<primary>c'])
        self.create_action('cut', self.on_cut_action, ['<primary>x'])
        self.create_action('delete-column', self.on_delete_column_action)
        self.create_action('delete-connection', self.on_delete_connection_action, param_type=GLib.VariantType('s'))
        self.create_action('delete-row', self.on_delete_row_action)
        self.create_action('duplicate-tab', self.on_duplicate_tab_action, param_type=GLib.VariantType('s'))
        self.create_action('duplicate-selected-tab', self.on_duplicate_selected_tab_action)
        self.create_action('duplicate-to-above', self.on_duplicate_to_above_action)
        self.create_action('duplicate-to-below', self.on_duplicate_to_below_action)
        self.create_action('duplicate-to-left', self.on_duplicate_to_left_action)
        self.create_action('duplicate-to-right', self.on_duplicate_to_right_action)
        self.create_action('filter-cell-value', self.on_filter_cell_value_action)
        self.create_action('filter-cell-values', self.on_filter_cell_values_action)
        self.create_action('hide-column', self.on_hide_column_action)
        self.create_action('import-table', self.on_import_table_action)
        self.create_action('insert-column-left', self.on_insert_column_left_action)
        self.create_action('insert-column-right', self.on_insert_column_right_action)
        self.create_action('insert-row-above', self.on_insert_row_above_action)
        self.create_action('insert-row-below', self.on_insert_row_below_action)
        self.create_action('move-tab-to-end', self.on_move_tab_to_end_action, param_type=GLib.VariantType('s'))
        self.create_action('move-tab-to-start', self.on_move_tab_to_start_action, param_type=GLib.VariantType('s'))
        self.create_action('new-notebook', self.on_new_notebook_action, ['<primary>n'])
        self.create_action('new-worksheet', self.on_new_worksheet_action, ['<primary>t'])
        self.create_action('new-worksheet-from-view', self.on_new_worksheet_from_view_action, ['<primary>t'])
        self.create_action('open-inline-formula', self.on_open_inline_formula_action, ['F2'])
        self.create_action('open-search', self.on_open_search_action, ['<primary>f'])
        self.create_action('open-sort-filter', self.on_open_sort_filter_action)
        self.create_action('open', self.on_open_file_action, ['<primary>o'])
        self.create_action('paste', self.on_paste_action, ['<primary>v'])
        self.create_action('pin-tab', self.on_pin_tab_action, param_type=GLib.VariantType('s'))
        self.create_action('preferences', self.on_preferences_action, ['<primary>comma'])
        self.create_action('quit', self.on_quit_action, ['<primary>q'])
        self.create_action('redo', self.on_redo_action, ['<shift><primary>z'])
        self.create_action('rename-connection', self.on_rename_connection_action, param_type=GLib.VariantType('s'))
        self.create_action('rename-tab', self.on_rename_tab_action, param_type=GLib.VariantType('s'))
        self.create_action('reset-all-filters', self.on_reset_all_filters_action)
        self.create_action('save-as', self.on_save_as_file_action, ['<shift><primary>s'])
        self.create_action('save', self.on_save_file_action, ['<primary>s'])
        self.create_action('sort-largest-to-smallest', self.on_sort_largest_to_smallest_action)
        self.create_action('sort-smallest-to-largest', self.on_sort_smallest_to_largest_action)
        self.create_action('toggle-history', self.on_toggle_history_action)
        self.create_action('toggle-replace-all', self.on_toggle_replace_all_action, ['<primary><shift>h'])
        self.create_action('toggle-replace', self.on_toggle_replace_action, ['<primary>h'])
        self.create_action('toggle-search-all', self.on_toggle_search_all_action, ['<primary><shift>f'])
        self.create_action('toggle-sidebar', self.on_toggle_sidebar_action, ['<primary>b'])
        self.create_action('undo', self.on_undo_action, ['<primary>z'])
        self.create_action('unhide-all-columns', self.on_unhide_all_columns_action)
        self.create_action('unhide-column', self.on_unhide_column_action)
        self.create_action('unpin-tab', self.on_unpin_tab_action, param_type=GLib.VariantType('s'))

    def do_command_line(self, command_line: Gio.ApplicationCommandLine) -> int:
        args = command_line.get_arguments()[1:]

        if '--h' in args or '--help' in args:
            print(
"""
Usage: eruo-data-studio [options] [paths...]

Options:
  -h, --help            show this help message and exit
"""
            )
            return 0

        for arg in args:
            if not arg.startswith('--'):
                try:
                    file = Gio.File.new_for_commandline_arg(arg)
                    if file_path := file.get_path():
                        self.file_paths.append(file_path)
                except Exception as e:
                    print(e)

        if self.file_paths:
            for file_path in self.file_paths:
                self.create_new_window(file_path)
            return 0

        self.activate()
        return 0

    def do_activate(self) -> None:
        if window := self.get_active_window():
            window.present()
            return
        self.create_new_window()

    def do_shutdown(self) -> None:
        for window in self.get_windows():
            window.close()

        serialized_connection_list = json.dumps(self.connection_list)
        self.settings.set_string('connection-list', serialized_connection_list)

        Gio.Application.do_shutdown(self)

    def on_quit_action(self,
                       action: Gio.SimpleAction,
                       *args) -> None:
        window = self.get_active_window()

        if window is None:
            return

        # Instead of closing the whole application at once, we just close the current
        # window one by one until no more windows are open and the application will be
        # closed automatically by itself.
        window.close()

    def on_about_action(self,
                        action: Gio.SimpleAction,
                        *args) -> None:
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

    def on_preferences_action(self,
                              action: Gio.SimpleAction,
                              *args) -> None:
        raise NotImplementedError # TODO

    def on_toggle_sidebar_action(self,
                                 action: Gio.SimpleAction,
                                 *args) -> None:
        window = self.get_active_window()
        window.toggle_sidebar()

    def on_open_file_action(self,
                            action: Gio.SimpleAction,
                            *args) -> None:
        window = self.get_active_window()
        self.file_manager.open_file(window)

    def on_save_file_action(self,
                            action: Gio.SimpleAction,
                            *args) -> None:
        window = self.get_active_window()

        # Pre-check if there is any data to save
        sheets = list(window.sheet_manager.sheets.values())
        if len(sheets) == 0 or len(sheets[0].data.dfs) == 0:
            return

        self.file_manager.save_file(window)

    def on_save_as_file_action(self,
                               action: Gio.SimpleAction,
                               *args) -> None:
        window = self.get_active_window()

        # Pre-check if there is any data to save
        sheets = list(window.sheet_manager.sheets.values())
        if len(sheets) == 0 or len(sheets[0].data.dfs) == 0:
            return

        self.file_manager.save_as_file(window)

    def on_open_search_action(self,
                              action: Gio.SimpleAction,
                              *args) -> None:
        window = self.get_active_window()
        window.search_replace_overlay.open_search_box()

    def on_open_sort_filter_action(self,
                                   action: Gio.SimpleAction,
                                   *args) -> None:
        window = self.get_active_window()

        # Close all possible views on the sidebar to reveal the home view
        window.search_replace_all_view.close_search_view()

        # Open the home view
        window.sidebar_home_view.open_home_view()

    def on_toggle_replace_action(self,
                                 action: Gio.SimpleAction,
                                 *args) -> None:
        window = self.get_active_window()
        window.search_replace_overlay.toggle_replace_section()

    def on_toggle_search_all_action(self,
                                    action: Gio.SimpleAction,
                                    *args) -> None:
        window = self.get_active_window()

        tab_page = window.search_replace_all_page
        tab_view = window.search_replace_all_view

        selected_page = window.sidebar_tab_view.get_selected_page()

        if selected_page == tab_page:
            tab_view.close_search_view()
            window.sidebar_home_view.open_home_view()
        else:
            tab_view.open_search_view()

    def on_toggle_replace_all_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        window = self.get_active_window()
        tab_view = window.search_replace_all_view
        tab_view.toggle_replace_section()

    def on_toggle_history_action(self,
                                 action: Gio.SimpleAction,
                                 *args) -> None:
        pass # TODO

    def on_file_opened(self,
                       source:    GObject.Object,
                       file_path: str,
                       in_place:  bool) -> None:
        if not file_path:
            return # shouldn't happen, but for completeness

        # Insert the file content to a new tab
        if in_place:
            self.create_new_tab(file_path)
            return

        if self.reuse_current_window(file_path):
            return

        self.create_new_window(file_path)

    def on_file_saved(self,
                      source:    GObject.Object,
                      file_path: str) -> None:
        pass # TODO: indicate the user when the file has been saved

    def on_new_notebook_action(self,
                               action: Gio.SimpleAction,
                               *args) -> None:
        window = self.get_active_window()
        sheet_view = window.sheet_manager.create_sheet(None, stype='notebook')
        window.add_new_tab(sheet_view)

    def on_new_worksheet_action(self,
                                action: Gio.SimpleAction,
                                *args) -> None:
        window = self.get_active_window()
        sheet_view = window.sheet_manager.create_sheet(None, stype='worksheet')
        window.add_new_tab(sheet_view)

    def on_new_worksheet_from_view_action(self,
                                          action: Gio.SimpleAction,
                                          *args) -> None:
        window = self.get_active_window()
        document = window.get_current_active_document()
        window.duplicate_sheet(document.document_id, materialize=True)

    def on_duplicate_tab_action(self,
                                action: Gio.SimpleAction,
                                *args) -> None:
        window = self.get_active_window()
        document_id = args[0].get_string()
        window.duplicate_sheet(document_id)

    def on_duplicate_selected_tab_action(self,
                                         action: Gio.SimpleAction,
                                         *args) -> None:
        window = self.get_active_window()
        document = window.get_current_active_document()
        window.duplicate_sheet(document.document_id)

    def on_rename_tab_action(self,
                             action: Gio.SimpleAction,
                             *args) -> None:
        window = self.get_active_window()
        document_id = args[0].get_string()
        tab_page = self.get_current_tab_page(window, document_id)
        window.rename_sheet(tab_page)

    def on_pin_tab_action(self,
                          action: Gio.SimpleAction,
                          *args) -> None:
        window = self.get_active_window()
        document_id = args[0].get_string()
        tab_page = self.get_current_tab_page(window, document_id)
        window.tab_view.set_page_pinned(tab_page, True)

    def on_unpin_tab_action(self,
                            action: Gio.SimpleAction,
                            *args) -> None:
        window = self.get_active_window()
        document_id = args[0].get_string()
        tab_page = self.get_current_tab_page(window, document_id)
        window.tab_view.set_page_pinned(tab_page, False)

    def on_move_tab_to_start_action(self,
                                    action: Gio.SimpleAction,
                                    *args) -> None:
        window = self.get_active_window()
        document_id = args[0].get_string()
        tab_page = self.get_current_tab_page(window, document_id)
        n_pinned_pages = window.tab_view.get_n_pinned_pages()
        window.tab_view.reorder_page(tab_page, n_pinned_pages)

    def on_move_tab_to_end_action(self,
                                  action: Gio.SimpleAction,
                                  *args) -> None:
        window = self.get_active_window()
        document_id = args[0].get_string()
        tab_page = self.get_current_tab_page(window, document_id)
        n_pages = window.tab_view.get_n_pages()
        window.tab_view.reorder_page(tab_page, n_pages - 1)

    def on_close_tab_action(self,
                            action: Gio.SimpleAction,
                            *args) -> None:
        window = self.get_active_window()
        document_id = args[0].get_string()

        def close_selected_tabs() -> None:
            tab_page = self.get_current_tab_page(window, document_id)
            window.tab_view.close_page(tab_page)

        if self.check_sheet_blanks(window, document_id):
            close_selected_tabs()
        else:
            self.show_close_tabs_confirmation(window, close_selected_tabs)

    def on_close_other_tabs_action(self,
                                   action: Gio.SimpleAction,
                                   *args) -> None:
        window = self.get_active_window()

        def close_selected_tabs() -> None:
            document_id = args[0].get_string()
            tab_page = self.get_current_tab_page(window, document_id)
            window.tab_view.close_other_pages(tab_page)

        self.show_close_tabs_confirmation(window, close_selected_tabs)

    def on_close_tabs_to_left_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        window = self.get_active_window()

        def close_selected_tabs() -> None:
            document_id = args[0].get_string()
            tab_page = self.get_current_tab_page(window, document_id)
            window.tab_view.close_pages_before(tab_page)

        self.show_close_tabs_confirmation(window, close_selected_tabs)

    def on_close_tabs_to_right_action(self,
                                      action: Gio.SimpleAction,
                                      *args) -> None:
        window = self.get_active_window()

        def close_selected_tabs() -> None:
            document_id = args[0].get_string()
            tab_page = self.get_current_tab_page(window, document_id)
            window.tab_view.close_pages_after(tab_page)

        self.show_close_tabs_confirmation(window, close_selected_tabs)

    def on_close_selected_tab_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        window = self.get_active_window()

        tab_page = window.tab_view.get_selected_page()
        document = window.get_current_active_document()

        def close_selected_tabs() -> None:
            window.tab_view.close_page(tab_page)

        if self.check_sheet_blanks(window, document.document_id):
            close_selected_tabs()
        else:
            self.show_close_tabs_confirmation(window, close_selected_tabs)

    def check_sheet_blanks(self,
                           window:      Window,
                           document_id: str) -> bool:
        sheet_document = window.sheet_manager.get_sheet(document_id)
        return len(sheet_document.history.undo_stack) <= 1 and \
               len(sheet_document.history.redo_stack) == 0

    def show_close_tabs_confirmation(self,
                                     window:   Window,
                                     callback: callable) -> None:
        alert_dialog = Adw.AlertDialog()

        alert_dialog.set_heading(_('Close Tabs?'))
        alert_dialog.set_body(_('All data on the selected tabs will be lost permanently. '
                                'This action cannot be undone.'))

        alert_dialog.add_response('cancel', _('_Cancel'))
        alert_dialog.add_response('close', _('_Close Tabs'))

        alert_dialog.set_response_appearance('close', Adw.ResponseAppearance.DESTRUCTIVE)
        alert_dialog.set_default_response('close')
        alert_dialog.set_close_response('cancel')

        def on_alert_dialog_dismissed(dialog: Adw.AlertDialog,
                                      result: Gio.Task) -> None:
            if result.had_error():
                return
            if dialog.choose_finish(result) != 'close':
                return
            callback()

        alert_dialog.choose(window, None, on_alert_dialog_dismissed)

    def on_undo_action(self,
                       action: Gio.SimpleAction,
                       *args) -> None:
        window = self.get_active_window()
        focused_widget = window.get_focus()

        # Prevent from colliding with the undo action of editable widgets.
        if isinstance(focused_widget, Gtk.Text) \
                or isinstance(focused_widget, Gtk.TextView):
            focused_widget.activate_action('text.undo', None)
            return

        globals.history.undo()

    def on_redo_action(self,
                       action: Gio.SimpleAction,
                       *args) -> None:
        window = self.get_active_window()
        focused_widget = window.get_focus()

        # Prevent from colliding with the redo action of editable widgets
        if isinstance(focused_widget, Gtk.Text) \
                or isinstance(focused_widget, Gtk.TextView):
            focused_widget.activate_action('text.redo', None)
            return

        globals.history.redo()

    def on_cut_action(self,
                      action: Gio.SimpleAction,
                      *args) -> bool:
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

    def on_copy_action(self,
                       action: Gio.SimpleAction,
                       *args) -> bool:
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

    def on_paste_action(self,
                        action: Gio.SimpleAction,
                        *args) -> bool:
        window = self.get_active_window()

        # Prevent from colliding with the paste action of editable widgets
        focused_widget = window.get_focus()
        if isinstance(focused_widget, Gtk.Text) \
                or isinstance(focused_widget, Gtk.TextView):
            focused_widget.activate_action('clipboard.paste', None)
            return True

        def on_clipboard_text_received(clipboard: Gdk.Clipboard,
                                       result: Gio.Task) -> None:
            if result.had_error():
                document.paste_into_current_selection(self.clipboard, None)
                return False

            text = clipboard.read_text_finish(result)
            document.paste_into_current_selection(self.clipboard, text)

        document = self.get_current_active_document()
        self.clipboard.read_text_async(on_clipboard_text_received)

        return True

    def on_insert_row_above_action(self,
                                   action: Gio.SimpleAction,
                                   *args) -> None:
        document = self.get_current_active_document()
        document.insert_blank_from_current_rows(above=True)

    def on_insert_row_below_action(self,
                                   action: Gio.SimpleAction,
                                   *args) -> None:
        document = self.get_current_active_document()
        document.insert_blank_from_current_rows(above=False)

    def on_insert_column_left_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        document = self.get_current_active_document()
        document.insert_blank_from_current_columns(left=True)

    def on_insert_column_right_action(self,
                                      action: Gio.SimpleAction,
                                      *args) -> None:
        document = self.get_current_active_document()
        document.insert_blank_from_current_columns(left=False)

    def on_duplicate_to_above_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        document = self.get_current_active_document()
        document.duplicate_from_current_rows(above=True)

    def on_duplicate_to_below_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        document = self.get_current_active_document()
        document.duplicate_from_current_rows(above=False)

    def on_duplicate_to_left_action(self,
                                    action: Gio.SimpleAction,
                                    *args) -> None:
        document = self.get_current_active_document()
        document.duplicate_from_current_columns(left=True)

    def on_duplicate_to_right_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        document = self.get_current_active_document()
        document.duplicate_from_current_columns(left=False)

    def on_delete_row_action(self,
                             action: Gio.SimpleAction,
                             *args) -> None:
        document = self.get_current_active_document()
        document.delete_current_rows()

    def on_delete_column_action(self,
                                action: Gio.SimpleAction,
                                *args) -> None:
        document = self.get_current_active_document()
        document.delete_current_columns()

    def on_clear_contents_action(self,
                                 action: Gio.SimpleAction,
                                 *args) -> None:
        document = self.get_current_active_document()
        document.update_current_cells('')

    def on_import_table_action(self,
                               action: Gio.SimpleAction,
                               *args) -> None:
        window = self.get_active_window()
        self.file_manager.open_file(window, in_place=True)

    def on_hide_column_action(self,
                              action: Gio.SimpleAction,
                              *args) -> None:
        document = self.get_current_active_document()
        document.hide_current_columns()

    def on_unhide_column_action(self,
                                action: Gio.SimpleAction,
                                *args) -> None:
        document = self.get_current_active_document()
        document.unhide_current_columns()

    def on_unhide_all_columns_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        document = self.get_current_active_document()
        document.unhide_all_columns()

    def on_filter_cell_value_action(self,
                                    action: Gio.SimpleAction,
                                    *args) -> None:
        document = self.get_current_active_document()
        document.filter_current_rows()

    def on_filter_cell_values_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        document = self.get_current_active_document()
        document.filter_current_rows(multiple=True)

    def on_reset_all_filters_action(self,
                                    action: Gio.SimpleAction,
                                    *args) -> None:
        document = self.get_current_active_document()
        document.reset_all_filters()

    def on_sort_smallest_to_largest_action(self,
                                           action: Gio.SimpleAction,
                                           *args) -> None:
        document = self.get_current_active_document()
        document.sort_current_rows(descending=False)

    def on_sort_largest_to_smallest_action(self,
                                           action: Gio.SimpleAction,
                                           *args) -> None:
        document = self.get_current_active_document()
        document.sort_current_rows(descending=True)

    def on_convert_to_categorical_action(self,
                                         action: Gio.SimpleAction,
                                         *args) -> None:
        self.convert_to(polars.Categorical)

    def on_convert_to_int8_action(self,
                                  action: Gio.SimpleAction,
                                  *args) -> None:
        self.convert_to(polars.Int8)

    def on_convert_to_int16_action(self,
                                   action: Gio.SimpleAction,
                                   *args) -> None:
        self.convert_to(polars.Int16)

    def on_convert_to_int32_action(self,
                                   action: Gio.SimpleAction,
                                   *args) -> None:
        self.convert_to(polars.Int32)

    def on_convert_to_int64_action(self,
                                   action: Gio.SimpleAction,
                                   *args) -> None:
        self.convert_to(polars.Int64)

    def on_convert_to_uint8_action(self,
                                   action: Gio.SimpleAction,
                                   *args) -> None:
        self.convert_to(polars.UInt8)

    def on_convert_to_uint16_action(self,
                                    action: Gio.SimpleAction,
                                    *args) -> None:
        self.convert_to(polars.UInt16)

    def on_convert_to_uint32_action(self,
                                    action: Gio.SimpleAction,
                                    *args) -> None:
        self.convert_to(polars.UInt32)

    def on_convert_to_uint64_action(self,
                                    action: Gio.SimpleAction,
                                    *args) -> None:
        self.convert_to(polars.UInt64)

    def on_convert_to_float32_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        self.convert_to(polars.Float32)

    def on_convert_to_float64_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        self.convert_to(polars.Float64)

    def on_convert_to_decimal_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        self.convert_to(polars.Decimal)

    def on_convert_to_date_action(self,
                                  action: Gio.SimpleAction,
                                  *args) -> None:
        self.convert_to(polars.Date)

    def on_convert_to_time_action(self,
                                  action: Gio.SimpleAction,
                                  *args) -> None:
        self.convert_to(polars.Time)

    def on_convert_to_datetime_action(self,
                                      action: Gio.SimpleAction,
                                      *args) -> None:
        self.convert_to(polars.Datetime)

    def on_convert_to_boolean_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        self.convert_to(polars.Boolean)

    def on_convert_to_text_action(self,
                                  action: Gio.SimpleAction,
                                  *args) -> None:
        self.convert_to(polars.Utf8)

    def convert_to(self, dtype: polars.DataType) -> None:
        document = self.get_current_active_document()
        document.convert_current_columns_dtype(dtype)

    def on_open_inline_formula_action(self,
                                      action: Gio.SimpleAction,
                                      *args) -> None:
        window = self.get_active_window()
        window.open_inline_formula()

    def on_apply_pending_table_action(self,
                                      action: Gio.SimpleAction,
                                      *args) -> None:
        action_data_id = args[0].get_string()
        window = self.get_active_window()
        window.apply_pending_table(action_data_id)

    def on_add_new_connection_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        window = self.get_active_window()
        self.on_update_connection_list(window)

    def on_add_new_connection(self, source: GObject.Object) -> None:
        window = self.get_active_window()

        from .database_add_connection_dialog import DatabaseAddConnectionDialog

        existing_cnames = [connection['cname'] for connection in self.connection_list]

        def generate_connection_name(cname: str) -> str:
            # Remove the number suffix if present
            cname = re.sub(r'\s+(\d+)$', '', cname)

            cnumber = 1
            for cname in existing_cnames:
                if match := re.match(cname + r'\s+(\d+)', cname):
                    cnumber = max(cnumber, int(match.group(1)) + 1)

            return f'{cname} {cnumber}'

        def _add_new_connection(connection_schema: dict) -> None:
            # Rename connection if it already exists
            incoming_cname = connection_schema['cname']
            if incoming_cname in existing_cnames:
                new_cname = generate_connection_name(incoming_cname)
                new_curl = connection_schema['curl'].replace(incoming_cname, new_cname)
                connection_schema.update({'cname': new_cname, 'curl': new_curl})

            # Set the connected flag to true
            connection_schema['connected'] = True

            self.connection_list.append(connection_schema)
            self.on_update_connection_list(window)

        dialog = DatabaseAddConnectionDialog(window, _add_new_connection)
        dialog.present(window)

    def on_rename_connection_action(self,
                                    action: Gio.SimpleAction,
                                    *args) -> None:
        from .database_rename_connection_dialog import DatabaseRenameConnectionDialog

        window = self.get_active_window()
        old_cname = args[0].get_string()

        def _rename_connection(new_cname: str) -> None:
            for connection in self.connection_list:
                if connection['cname'] == old_cname:
                    new_curl = connection['curl'].replace(old_cname, new_cname)
                    connection.update({'cname': new_cname, 'curl': new_curl})
                    break

            self.on_update_connection_list(window)

        dialog = DatabaseRenameConnectionDialog(old_cname, _rename_connection)
        dialog.present(window)

    def on_delete_connection_action(self,
                                    action: Gio.SimpleAction,
                                    *args) -> None:
        cname = args[0].get_string()
        self.connection_list = [connection for connection in self.connection_list
                                if connection['cname'] != cname]

        window = self.get_active_window()
        self.on_update_connection_list(window)

    def on_toggle_connection_active(self,
                                    source:    GObject.Object,
                                    cname:     str,
                                    connected: bool) -> None:
        for connection in self.connection_list:
            if connection['cname'] == cname:
                connection['connected'] = connected
                break

        self.on_update_connection_list(source, skip_emitter=True)

    def on_update_connection_list(self,
                                  emitter: GObject.Object,
                                  skip_emitter: bool = False) -> None:
        connection_list = []

        for connection in self.connection_list:
            # Introduce a new connected flag
            if 'connected' not in connection:
                connection['connected'] = True

            connection_list.append({
                'ctype'     : connection['ctype'],
                'cname'     : connection['cname'],
                'connected' : connection['connected'],
                'removable' : True,
            })

        for window in self.get_windows():
            if window.file is None:
                continue

            file_path = window.file.get_path()
            file_path = os.path.basename(file_path)
            file_name = os.path.splitext(file_path)[0]
            view_prefix = f'{file_name}:'

            for sheet in window.sheet_manager.sheets.values():
                if sheet.data.has_main_dataframe:
                    view_name = f'{view_prefix}{sheet.title}'
                    connection_list.append({
                        'ctype'     : 'Dataframe',
                        'cname'     : view_name,
                        'connected' : True,
                        'removable' : False,
                    })

        # Update connection list view in all the windows
        for window in self.get_windows():
            if window == emitter and skip_emitter:
                continue
            window.sidebar_home_view.repopulate_connection_list(connection_list)

    def register_connection(self, connection: duckdb.DuckDBPyConnection) -> list[str]:
        # With the assumption that the connection is always from the active window
        # so that all the available connections in the current active window won't
        # get any prefixes.
        active_window = self.get_active_window()

        for window in self.get_windows():
            # Define the view name prefix if necessary
            view_prefix = ''
            if window is not active_window:
                file_path = window.file.get_path()
                file_path = os.path.basename(file_path)
                file_name = os.path.splitext(file_path)[0]
                view_prefix = f'{file_name}:'

            # Register all the main dataframe from all the sheets
            for sheet in window.sheet_manager.sheets.values():
                if sheet.data.has_main_dataframe:
                    view_name = f'{view_prefix}{sheet.title}'
                    connection.register(view_name, sheet.data.dfs[0])

                    # Register with `self` prefix too for convenience
                    if window is active_window:
                        view_name = f'self:{sheet.title}'
                        connection.register(view_name, sheet.data.dfs[0])

        active_connections = [connection['curl'] for connection in self.connection_list
                                                 if connection['connected']]
        return ';'.join(active_connections)

    def get_current_active_document(self) -> SheetDocument:
        window = self.get_active_window()
        return window.get_current_active_document()

    def get_current_tab_page(self,
                             window:      Window,
                             document_id: str) -> SheetDocument:
        sheet_document = window.sheet_manager.get_sheet(document_id)
        sheet_view = sheet_document.view
        return window.tab_view.get_page(sheet_view)

    def create_action(self,
                      name:       str,
                      callback:   callable,
                      shortcuts:  list = None,
                      param_type: GLib.VariantType = None) -> None:
        action = Gio.SimpleAction.new(name, param_type)
        action.connect('activate', callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f'app.{name}', shortcuts)

    def create_new_window(self,
                          file_path:  str = '',
                          skip_setup: bool = False) -> Window:
        file = None
        dataframe = None

        # By default, no file is loaded when creating a new window.
        # But later on, we can add support for file manager integration
        # as well as a command line interface. Maybe even adding support
        # for opening the last session automatically.
        if not skip_setup and file_path:
            file = Gio.File.new_for_path(file_path)
            dataframe = self.file_manager.read_file(self, file_path)

        # Check for special return values
        if not isinstance(dataframe, polars.DataFrame) and dataframe == 0:
            return None

        window = Window(application=self)
        window.connect('add-new-connection', self.on_add_new_connection)
        window.connect('update-connection-list', self.on_update_connection_list)
        window.connect('toggle-connection-active', self.on_toggle_connection_active)
        window.present()

        if not skip_setup:
            window.setup_new_document(file, dataframe)

        return window

    def reuse_current_window(self, file_path: str = '') -> Any:
        window = self.get_active_window()

        if not window:
            return False

        no_linked_file = window.file is None
        no_opened_sheet = len(window.sheet_manager.sheets) == 0
        history_is_empty = globals.history is None or \
                           (len(globals.history.undo_stack) <= 1 and \
                            len(globals.history.redo_stack) == 0)

        # Reuse the current active window if the window references to no file
        # and there's not any sheet opened or the current active sheet has no
        # editing history
        if not (no_linked_file and (no_opened_sheet or history_is_empty)):
            return False

        file = None
        dataframe = None

        if file_path:
            file = Gio.File.new_for_path(file_path)
            dataframe = self.file_manager.read_file(self, file_path)

        # Check for special return values
        if not isinstance(dataframe, polars.DataFrame) and dataframe == 0:
            return True

        window = self.get_active_window()

        # Close the current tab
        tab_page = window.tab_view.get_selected_page()
        if tab_page is not None:
            window.tab_view.close_page(tab_page)

        window.setup_new_document(file, dataframe)

        return window

    def create_new_tab(self, file_path: str = '') -> bool:
        file = None
        dataframe = None

        if file_path:
            file = Gio.File.new_for_path(file_path)
            dataframe = self.file_manager.read_file(self, file_path)

        # Check for special return values
        if not isinstance(dataframe, polars.DataFrame) and dataframe == 0:
            return False

        window = self.get_active_window()
        window.setup_new_document(file, dataframe)

        return True

    def load_user_workspace(self, workspace_schema: dict) -> None:
        window = self.reuse_current_window()

        # Create a new window if needed
        if not window:
            window = self.create_new_window(skip_setup=True)

        # Close the first tab if exists
        tab_page = window.tab_view.get_selected_page()
        if tab_page is not None:
            window.tab_view.close_page(tab_page)

        # Load all the sheets to separate tabs
        for sheet in workspace_schema['sheets']:
            window.setup_loaded_document(sheet)

        # Set the file signature
        window.file = Gio.File.new_for_path(workspace_schema['signature'])

        # Restore the UI states
        sidebar_collapsed = workspace_schema.get('sidebar-collapsed', True)
        if not sidebar_collapsed:
            window.toggle_sidebar() # it's collapsed by default

        # Set the current active tab
        current_active_tab = workspace_schema.get('current-active-tab', 0)
        selected_page = window.tab_view.get_nth_page(current_active_tab)
        window.tab_view.set_selected_page(selected_page)

        # Set the focus to specific widgets
        sheet_view = selected_page.get_child()
        sheet_document = sheet_view.document
        if isinstance(sheet_document, SheetDocument):
            sheet_document.view.main_canvas.set_focusable(True)
            sheet_document.view.main_canvas.grab_focus()
        if isinstance(sheet_document, SheetNotebook) \
                and len(sheet_document.view.list_items) > 0:
            sheet_document.view.list_items[0]['source_view'].grab_focus()

        # Set the pinned tabs
        pinned_tabs = workspace_schema.get('pinned-tabs', [])
        for tab_index in pinned_tabs:
            tab_page = window.tab_view.get_nth_page(tab_index)
            window.tab_view.set_page_pinned(tab_page, True)

        self.on_update_connection_list(window)

        window.present()

def main(version):
    """The application's entry point."""
    return Application().run(sys.argv)