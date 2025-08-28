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

        globals.register_connection = self._register_connection

        self._register_expressions()

        self.settings = Gio.Settings.new('com.macipra.eruo')

        # Load the recently opened connection list
        saved_connection_list = self.settings.get_string('connection-list')
        deserialized_connection_list = json.loads(saved_connection_list)
        self.connection_list: list[dict] = deserialized_connection_list

        self.file_manager = FileManager()
        self.file_manager.connect('file-cancel', self.on_file_cancel)
        self.file_manager.connect('file-opened', self.on_file_opened)
        self.file_manager.connect('file-saved', self.on_file_saved)
        self.file_manager.connect('file-exported', self.on_file_exported)

        self.clipboard = ClipboardManager()

        self.application_commands = []

        #
        # Register general actions
        #
        # FIXME: when the display language isn't English, we should provide a way so that
        #        the user can still querying the commands in both languages.
        self.create_action('add-connection',                                                _('Add New Connection...'),
                                                                                            self.on_add_new_connection_action)
        self.create_action('cut',                                                           _('Cut'),
                                                                                            self.on_cut_action,
                                                                                            shortcuts=['<control>x'])
        self.create_action('copy',                                                          _('Copy'),
                                                                                            self.on_copy_action,
                                                                                            shortcuts=['<control>c'])
        self.create_action('paste',                                                         _('Paste'),
                                                                                            self.on_paste_action,
                                                                                            shortcuts=['<control>v'])
        self.create_action('undo',                                                          _('Undo'),
                                                                                            self.on_undo_action,
                                                                                            shortcuts=['<control>z'])
        self.create_action('redo',                                                          _('Redo'),
                                                                                            self.on_redo_action,
                                                                                            shortcuts=['<shift><control>z', '<control>y'])

        #
        # Register create actions
        #
        self.create_action('duplicate-selected-tab',                                        _('Create: Duplicate Sheet Into New Worksheet'),
                                                                                            self.on_duplicate_selected_tab_action)
        self.create_action('import-table',                                                  _('Create: Import Table Into New Worksheet'),
                                                                                            self.on_import_table_action)
        self.create_action('new-worksheet-from-view',                                       _('Create: Materialize View Into New Worksheet'),
                                                                                            self.on_new_worksheet_from_view_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('new-notebook',                                                  _('Create: New Blank Notebook'),
                                                                                            self.on_new_notebook_action,
                                                                                            shortcuts=['<control>n'])
        self.create_action('new-worksheet',                                                 _('Create: New Blank Worksheet'),
                                                                                            self.on_new_worksheet_action,
                                                                                            shortcuts=['<control>t'])

        #
        # Register file actions
        #
        self.create_action('open-file',                                                     _('File: Open File...'),
                                                                                            self.on_open_file_action,
                                                                                            shortcuts=['<control>o'])
        self.create_action('save',                                                          _('File: Save'),
                                                                                            self.on_save_file_action,
                                                                                            shortcuts=['<control>s'])
        self.create_action('save-as',                                                       _('File: Save As...'),
                                                                                            self.on_save_file_as_action,
                                                                                            shortcuts=['<shift><control>s'])
        self.create_action('export-as',                                                     _('File: Export As...'),
                                                                                            self.on_export_file_as_action,
                                                                                            shortcuts=['<control><alt>s'])

        #
        # Register help actions
        #
        self.create_action('about',                                                         _('Help: About'),
                                                                                            self.on_about_action)
        self.create_action('preferences',                                                   _('Help: Open Settings'),
                                                                                            self.on_preferences_action,
                                                                                            shortcuts=['<control>comma'])

        #
        # Register search actions
        #
        self.create_action('open-search',                                                   _('Search: Quick Search'),
                                                                                            self.on_open_search_action,
                                                                                            shortcuts=['<control>f'])
        self.create_action('toggle-replace',                                                _('Search: Quick Replace'),
                                                                                            self.on_toggle_replace_action,
                                                                                            shortcuts=['<control>h'])
        self.create_action('toggle-search-all',                                             _('Search: Search All'),
                                                                                            self.on_toggle_search_all_action,
                                                                                            shortcuts=['<control><shift>f'])
        self.create_action('toggle-replace-all',                                            _('Search: Replace All'),
                                                                                            self.on_toggle_replace_all_action,
                                                                                            shortcuts=['<control><shift>h'])

        #
        # Register view actions
        #
        self.create_action('close-selected-tab',                                            _('View: Close Tab'),
                                                                                            self.on_close_selected_tab_action,
                                                                                            shortcuts=['<control>w'])
        self.create_action('quit',                                                          _('View: Close Window'),
                                                                                            self.on_quit_action,
                                                                                            shortcuts=['<control>q'])
        self.create_action('toggle-history',                                                _('View: Toggle History Panel'),
                                                                                            self.on_toggle_history_action)
        self.create_action('toggle-sidebar',                                                _('View: Toggle Sidebar Panel'),
                                                                                            self.on_toggle_sidebar_action,
                                                                                            shortcuts=['<control>b'])

        #
        # Register worksheet actions
        #
        self.create_action('clear-contents',                                                _('Cell: Clear Contents'),
                                                                                            self.on_clear_contents_action,
                                                                                            shortcuts=['Delete'],
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-to-boolean',                                            _('Column: Convert to Boolean'),
                                                                                            self.on_convert_to_boolean_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-to-categorical',                                        _('Column: Convert to Categorical'),
                                                                                            self.on_convert_to_categorical_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-to-date',                                               _('Column: Convert to Date'),
                                                                                            self.on_convert_to_date_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-to-datetime',                                           _('Column: Convert to Datetime'),
                                                                                            self.on_convert_to_datetime_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-to-decimal',                                            _('Column: Convert to Decimal Number'),
                                                                                            self.on_convert_to_decimal_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-to-float32',                                            _('Column: Convert to Float (32-Bit)'),
                                                                                            self.on_convert_to_float32_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-to-float64',                                            _('Column: Convert to Float (64-Bit)'),
                                                                                            self.on_convert_to_float64_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-to-int8',                                               _('Column: Convert to Integer (8-Bit)'),
                                                                                            self.on_convert_to_int8_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-to-int16',                                              _('Column: Convert to Integer (16-Bit)'),
                                                                                            self.on_convert_to_int16_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-to-int32',                                              _('Column: Convert to Integer (32-Bit)'),
                                                                                            self.on_convert_to_int32_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-to-int64',                                              _('Column: Convert to Integer (64-Bit)'),
                                                                                            self.on_convert_to_int64_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-to-text',                                               _('Column: Convert to Text'),
                                                                                            self.on_convert_to_text_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-to-time',                                               _('Column: Convert to Time'),
                                                                                            self.on_convert_to_time_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-to-uint8',                                              _('Column: Convert to Unsigned Integer (8-Bit)'),
                                                                                            self.on_convert_to_uint8_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-to-uint16',                                             _('Column: Convert to Unsigned Integer (16-Bit)'),
                                                                                            self.on_convert_to_uint16_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-to-uint32',                                             _('Column: Convert to Unsigned Integer (32-Bit)'),
                                                                                            self.on_convert_to_uint32_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-to-uint64',                                             _('Column: Convert to Unsigned Integer (64-Bit)'),
                                                                                            self.on_convert_to_uint64_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-to-whole-number',                                       _('Column: Convert to Whole Number'),
                                                                                            self.on_convert_to_int64_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('delete-column',                                                 _('Column: Delete Columns'),
                                                                                            self.on_delete_column_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('delete-row',                                                    _('Row: Delete Rows'),
                                                                                            self.on_delete_row_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('duplicate-to-above',                                            _('Row: Duplicate Rows to Above'),
                                                                                            self.on_duplicate_to_above_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('duplicate-to-below',                                            _('Row: Duplicate Rows to Below'),
                                                                                            self.on_duplicate_to_below_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('duplicate-to-left',                                             _('Column: Duplicate Columns to Left'),
                                                                                            self.on_duplicate_to_left_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('duplicate-to-right',                                            _('Column: Duplicate Columns to Right'),
                                                                                            self.on_duplicate_to_right_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('go-to-cell',                                                    _('View: Go to Cell...'),
                                                                                            self.on_go_to_cell_action,
                                                                                            shortcuts=['<control>g'],
                                                                                            steal_focus=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('hide-column',                                                   _('Column: Hide Columns'),
                                                                                            self.on_hide_column_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('insert-column-left',                                            _('Column: Insert Column to the Left'),
                                                                                            self.on_insert_column_left_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('insert-column-right',                                           _('Column: Insert Column to the Right'),
                                                                                            self.on_insert_column_right_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('insert-row-above',                                              _('Row: Insert Rows Above'),
                                                                                            self.on_insert_row_above_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('insert-row-below',                                              _('Row: Insert Rows Below'),
                                                                                            self.on_insert_row_below_action,
                                                                                            when_expression="document == 'worksheet'")
#       self.create_action('keep-duplicated-rows-only',                                     _('Filter: Keep Duplicated Rows Only'),
#                                                                                           self.on_keep_duplicated_rows_only_action,
#                                                                                           when_expression="document == 'worksheet'")
        self.create_action('keep-rows-only-including-selection',                            _('Filter: Keep Rows Only Including the Selection'),
                                                                                            self.on_keep_rows_only_including_selection,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('keep-rows-only-including-selection-into-new-worksheet',         _('Filter: Keep Rows Only Including the Selection Into a New Worksheet'),
                                                                                            self.on_keep_rows_only_including_selection_into_new_worksheet_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('keep-rows-only-including-case-insensitive-string',              _('Filter: Keep Rows Only Including a String (Case Insensitive)...'),
                                                                                            self.on_keep_rows_only_including_case_insensitive_string_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('keep-rows-only-including-case-sensitive-string',                _('Filter: Keep Rows Only Including a String (Case Sensitive)...'),
                                                                                            self.on_keep_rows_only_including_case_sensitive_string_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('keep-rows-only-including-insensitive-string-into-new-worksheet',_('Filter: Keep Rows Only Including a String Into a New Worksheet (Case Insensitive)...'),
                                                                                            self.on_keep_rows_only_including_case_insensitive_string_into_new_worksheet_action_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('keep-rows-only-including-sensitive-string-into-new-worksheet',  _('Filter: Keep Rows Only Including a String Into a New Worksheet (Case Sensitive)...'),
                                                                                            self.on_keep_rows_only_including_case_sensitive_string_into_new_worksheet_action_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('keep-rows-only-matching-regex-case-insensitive',                _('Filter: Keep Rows Only Matching a Regex (Case Insensitive)...'),
                                                                                            self.on_keep_rows_only_matching_regex_case_insensitive_string_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('keep-rows-only-matching-regex-case-sensitive',                  _('Filter: Keep Rows Only Matching a Regex (Case Sensitive)...'),
                                                                                            self.on_keep_rows_only_matching_regex_case_sensitive_string_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('keep-rows-only-matching-regex-insensitive-into-new-worksheet',  _('Filter: Keep Rows Only Matching a Regex Into a New Worksheet (Case Insensitive)...'),
                                                                                            self.on_keep_rows_only_matching_regex_case_insensitive_string_into_new_worksheet_action_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('keep-rows-only-matching-regex-sensitive-into-new-worksheet',    _('Filter: Keep Rows Only Matching a Regex Into a New Worksheet (Case Sensitive)...'),
                                                                                            self.on_keep_rows_only_matching_regex_case_sensitive_string_into_new_worksheet_action_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('rechunk-table',                                                 _('Sheet: Rechunk Table'),
                                                                                            self.on_rechunk_table_action,
                                                                                            when_expression="document == 'worksheet'")
#       self.create_action('reverse-rows',                                                  _('Sort: Reverse Rows'),
#                                                                                           self.on_reverse_rows_action,
#                                                                                           when_expression="document == 'worksheet'")
#       self.create_action('remove-blank-rows',                                             _('Remove Blank Rows'),
#                                                                                            self.on_remove_blank_rows_action,
#                                                                                           when_expression="document == 'worksheet'")
#       self.create_action('remove-duplicated-rows',                                        _('Remove Duplicated Rows'),
#                                                                                            self.on_remove_duplicated_rows_action,
#                                                                                           when_expression="document == 'worksheet'")
#       self.create_action('remove-empty-rows',                                             _('Remove Empty Rows'),
#                                                                                            self.on_remove_empty_rows_action,
#                                                                                           when_expression="document == 'worksheet'")
        self.create_action('remove-rows-including-selection',                               _('Filter: Remove Rows Including the Selection'),
                                                                                            self.on_remove_rows_including_selection,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('remove-rows-including-selection-into-new-worksheet',            _('Filter: Remove Rows Including the Selection Into a New Worksheet'),
                                                                                            self.on_remove_rows_including_selection_into_new_worksheet_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('remove-rows-including-case-insensitive-string',                 _('Filter: Remove Rows Including a String (Case Insensitive)...'),
                                                                                            self.on_remove_rows_including_case_insensitive_string_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('remove-rows-including-case-sensitive-string',                   _('Filter: Remove Rows Including a String (Case Sensitive)...'),
                                                                                            self.on_remove_rows_including_case_sensitive_string_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('remove-rows-including-insensitive-string-into-new-worksheet',   _('Filter: Remove Rows Including a String Into a New Worksheet (Case Insensitive)...'),
                                                                                            self.on_remove_rows_including_case_insensitive_string_into_new_worksheet_action_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('remove-rows-including-sensitive-string-into-new-worksheet',     _('Filter: Remove Rows Including a String Into a New Worksheet (Case Sensitive)...'),
                                                                                            self.on_remove_rows_including_case_sensitive_string_into_new_worksheet_action_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('remove-rows-matching-regex-case-insensitive',                   _('Filter: Remove Rows Matching a Regex (Case Insensitive)...'),
                                                                                            self.on_remove_rows_matching_regex_case_insensitive_string_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('remove-rows-matching-regex-case-sensitive',                     _('Filter: Remove Rows Matching a Regex (Case Sensitive)...'),
                                                                                            self.on_remove_rows_matching_regex_case_sensitive_string_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('remove-rows-matching-regex-insensitive-into-new-worksheet',     _('Filter: Remove Rows Matching a Regex Into a New Worksheet (Case Insensitive)...'),
                                                                                            self.on_remove_rows_matching_regex_case_insensitive_string_into_new_worksheet_action_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('remove-rows-matching-regex-sensitive-into-new-worksheet',       _('Filter: Remove Rows Matching a Regex Into a New Worksheet (Case Sensitive)...'),
                                                                                            self.on_remove_rows_matching_regex_case_sensitive_string_into_new_worksheet_action_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
#       self.create_action('remove-surplus-blank-rows',                                     _('Remove Surplus Blank Rows'),
#                                                                                            self.on_remove_surplus_blank_rows_action,
#                                                                                           when_expression="document == 'worksheet'")
#       self.create_action('remove-surplus-empty-rows',                                     _('Remove Surplus Empty Rows'),
#                                                                                            self.on_remove_surplus_empty_rows_action,
#                                                                                           when_expression="document == 'worksheet'")
        self.create_action('reset-all-filters',                                             _('Filter: Clear All Rows Filters'),
                                                                                            self.on_reset_all_filters_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('sort-by-ascending',                                             _('Sort: Sort Rows by Ascending'),
                                                                                            self.on_sort_by_ascending_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('sort-by-descending',                                            _('Sort: Sort Rows by Descending'),
                                                                                            self.on_sort_by_descending_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('unhide-all-columns',                                            _('Column: Unhide All Columns'),
                                                                                            self.on_unhide_all_columns_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('unhide-column',                                                 _('Column: Unhide Columns'),
                                                                                            self.on_unhide_column_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('focus-on-formula-editor',                                       _('View: Focus on Formula Editor'),
                                                                                            self.on_focus_on_formula_editor_action,
                                                                                            shortcuts=['<shift>F2'],
                                                                                            steal_focus=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('open-multiline-formula',                                        _('View: Focus on Multiple Line Formula Editor'),
                                                                                            self.on_focus_on_multiline_formula_editor_action,
                                                                                            steal_focus=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('open-inline-formula',                                           _('View: Open Inline Formula Editor'),
                                                                                            self.on_open_inline_formula_action,
                                                                                            shortcuts=['F2'],
                                                                                            steal_focus=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('open-sort-filter',                                              _('View: Open Sort &amp; Filter Panel'),
                                                                                            self.on_open_sort_filter_action,
                                                                                            when_expression="document == 'worksheet'")

        #
        # Register application non-command actions
        #
        self.create_action('apply-pending-table',                                           callback=self.on_apply_pending_table_action,
                                                                                            is_command=False,
                                                                                            param_type=GLib.VariantType('s'))
        self.create_action('delete-connection',                                             callback=self.on_delete_connection_action,
                                                                                            is_command=False,
                                                                                            param_type=GLib.VariantType('s'))
        self.create_action('open-command-palette',                                          callback=self.on_open_command_palette_action,
                                                                                            is_command=False,
                                                                                            shortcuts=['F1', '<shift><control>p'])
        self.create_action('rename-connection',                                             callback=self.on_rename_connection_action,
                                                                                            is_command=False,
                                                                                            param_type=GLib.VariantType('s'))

        #
        # Register worksheet non-command actions
        #
        self.create_action('filter-by-cell-value',                                          callback=self.on_filter_by_cell_value_action,
                                                                                            is_command=False)
        self.create_action('filter-by-unique-values',                                       callback=self.on_filter_by_unique_values_action,
                                                                                            is_command=False)

        #
        # Register window non-command actions
        #
        # TODO: make these actions commandable
        self.create_action('close-other-tabs',                                              callback=self.on_close_other_tabs_action,
                                                                                            is_command=False,
                                                                                            param_type=GLib.VariantType('s'))
        self.create_action('close-tab',                                                     callback=self.on_close_tab_action,
                                                                                            is_command=False,
                                                                                            param_type=GLib.VariantType('s'))
        self.create_action('close-tabs-to-left',                                            callback=self.on_close_tabs_to_left_action,
                                                                                            is_command=False,
                                                                                            param_type=GLib.VariantType('s'))
        self.create_action('close-tabs-to-right',                                           callback=self.on_close_tabs_to_right_action,
                                                                                            is_command=False,
                                                                                            param_type=GLib.VariantType('s'))
        self.create_action('duplicate-tab',                                                 callback=self.on_duplicate_tab_action,
                                                                                            is_command=False,
                                                                                            param_type=GLib.VariantType('s'))
        self.create_action('move-tab-to-end',                                               callback=self.on_move_tab_to_end_action,
                                                                                            is_command=False,
                                                                                            param_type=GLib.VariantType('s'))
        self.create_action('move-tab-to-start',                                             callback=self.on_move_tab_to_start_action,
                                                                                            is_command=False,
                                                                                            param_type=GLib.VariantType('s'))
        self.create_action('pin-tab',                                                       callback=self.on_pin_tab_action,
                                                                                            is_command=False,
                                                                                            param_type=GLib.VariantType('s'))
        self.create_action('rename-tab',                                                    callback=self.on_rename_tab_action,
                                                                                            is_command=False,
                                                                                            param_type=GLib.VariantType('s'))
        self.create_action('unpin-tab',                                                     callback=self.on_unpin_tab_action,
                                                                                            is_command=False,
                                                                                            param_type=GLib.VariantType('s'))

        #
        # Register new advanced worksheet actions
        #
        # Inspired by https://github.com/qcz/vscode-text-power-tools
        self.create_action('append-prefix-to-cell',                                         _('Cell: Append Prefix...'),
                                                                                            self.on_append_prefix_to_cell_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('append-prefix-to-column',                                       _('Column: Append Prefix...'),
                                                                                            self.on_append_prefix_to_column_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('append-suffix-to-cell',                                         _('Cell: Append Suffix...'),
                                                                                            self.on_append_suffix_to_cell_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('append-suffix-to-column',                                       _('Column: Append Suffix...'),
                                                                                            self.on_append_suffix_to_column_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-cell-case-to-camel-case',                                _('Cell: Change Case to Camel Case (camelCase)'),
                                                                                            self.on_change_case_cell_to_camel_case_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-cell-case-to-constant-case',                             _('Cell: Change Case to Constant Case (CONSTANT_CASE)'),
                                                                                            self.on_change_case_cell_to_constant_case_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-cell-case-to-dot-case',                                  _('Cell: Change Case to Dot Case (dot.case)'),
                                                                                            self.on_change_case_cell_to_dot_case_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-cell-case-to-kebab-case',                                _('Cell: Change Case to Kebab Case (kebab-case)'),
                                                                                            self.on_change_case_cell_to_kebab_case_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-cell-case-to-lowercase',                                 _('Cell: Change Case to Lowercase'),
                                                                                            self.on_change_case_cell_to_lowercase_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-cell-case-to-pascal-case',                               _('Cell: Change Case to Pascal Case (PascalCase)'),
                                                                                            self.on_change_case_cell_to_pascal_case_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-cell-case-to-snake-case',                                _('Cell: Change Case to Snake Case (snake_case)'),
                                                                                            self.on_change_case_cell_to_snake_case_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-cell-case-to-sentence-case',                             _('Cell: Change Case to Sentence Case (Sentence case)'),
                                                                                            self.on_change_case_cell_to_sentence_case_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-cell-case-to-sponge-case',                               _('Cell: Change Case to Sponge Case (RANdoM CAPiTAlizAtiON)'),
                                                                                            self.on_change_case_cell_to_sponge_case_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-cell-case-to-title-case',                                _('Cell: Change Case to Title Case (Capitalize Each Word)'),
                                                                                            self.on_change_case_cell_to_title_case_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-cell-case-to-uppercase',                                 _('Cell: Change Case to Uppercase'),
                                                                                            self.on_change_case_cell_to_uppercase_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-column-case-to-camel-case',                              _('Column: Change Case to Camel Case (camelCase)'),
                                                                                            self.on_change_case_column_to_camel_case_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-column-case-to-constant-case',                           _('Column: Change Case to Constant Case (CONSTANT_CASE)'),
                                                                                            self.on_change_case_column_to_constant_case_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-column-case-to-dot-case',                                _('Column: Change Case to Dot Case (dot.case)'),
                                                                                            self.on_change_case_column_to_dot_case_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-column-case-to-kebab-case',                              _('Column: Change Case to Kebab Case (kebab-case)'),
                                                                                            self.on_change_case_column_to_kebab_case_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-column-case-to-lowercase',                               _('Column: Change Case to Lowercase'),
                                                                                            self.on_change_case_column_to_lowercase_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-column-case-to-pascal-case',                             _('Column: Change Case to Pascal Case (PascalCase)'),
                                                                                            self.on_change_case_column_to_pascal_case_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-column-case-to-snake-case',                              _('Column: Change Case to Snake Case (snake_case)'),
                                                                                            self.on_change_case_column_to_snake_case_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-column-case-to-sentence-case',                           _('Column: Change Case to Sentence Case (Sentence case)'),
                                                                                            self.on_change_case_column_to_sentence_case_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-column-case-to-sponge-case',                             _('Column: Change Case to Sponge Case (RANdoM CAPiTAlizAtiON)'),
                                                                                            self.on_change_case_column_to_sponge_case_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-column-case-to-title-case',                              _('Column: Change Case to Title Case (Capitalize Each Word)'),
                                                                                            self.on_change_case_column_to_title_case_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('change-column-case-to-uppercase',                               _('Column: Change Case to Uppercase'),
                                                                                            self.on_change_case_column_to_uppercase_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-cell-to-unicode-normalization-nfc',                     _('Cell: Convert to NFC Unicode Normalization Form'),
                                                                                            self.on_convert_cell_to_unicode_normalization_nfc_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-cell-to-unicode-normalization-nfd',                     _('Cell: Convert to NFD Unicode Normalization Form'),
                                                                                            self.on_convert_cell_to_unicode_normalization_nfd_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-cell-to-unicode-normalization-nfkc',                    _('Cell: Convert to NFKC Unicode Normalization Form'),
                                                                                            self.on_convert_cell_to_unicode_normalization_nfkc_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-cell-to-unicode-normalization-nfkd',                    _('Cell: Convert to NFKD Unicode Normalization Form'),
                                                                                            self.on_convert_cell_to_unicode_normalization_nfkd_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-column-to-unicode-normalization-nfc',                   _('Column: Convert to NFC Unicode Normalization Form'),
                                                                                            self.on_convert_column_to_unicode_normalization_nfc_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-column-to-unicode-normalization-nfd',                   _('Column: Convert to NFD Unicode Normalization Form'),
                                                                                            self.on_convert_column_to_unicode_normalization_nfd_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-column-to-unicode-normalization-nfkc',                  _('Column: Convert to NFKC Unicode Normalization Form'),
                                                                                            self.on_convert_column_to_unicode_normalization_nfkc_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('convert-column-to-unicode-normalization-nfkd',                  _('Column: Convert to NFKD Unicode Normalization Form'),
                                                                                            self.on_convert_column_to_unicode_normalization_nfkd_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('decode-base64-cell-text',                                       _('Cell: Decode Base64 Text'),
                                                                                            self.on_decode_base64_cell_text_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('decode-base64-column-text',                                     _('Column: Decode Base64 Text'),
                                                                                            self.on_decode_base64_column_text_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('decode-hexadecimal-cell-text',                                  _('Cell: Decode Hexadecimal Text'),
                                                                                            self.on_decode_hexadecimal_cell_text_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('decode-hexadecimal-column-text',                                _('Column: Decode Hexadecimal Text'),
                                                                                            self.on_decode_hexadecimal_column_text_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('decode-url-cell-text',                                          _('Cell: Decode URL Text'),
                                                                                            self.on_decode_url_cell_text_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('decode-url-column-text',                                        _('Column: Decode URL Text'),
                                                                                            self.on_decode_url_column_text_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('encode-base64-cell-text',                                       _('Cell: Encode Base64 Text'),
                                                                                            self.on_encode_base64_cell_text_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('encode-base64-column-text',                                     _('Column: Encode Base64 Text'),
                                                                                            self.on_encode_base64_column_text_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('encode-hexadecimal-cell-text',                                  _('Cell: Encode Hexadecimal Text'),
                                                                                            self.on_encode_hexadecimal_cell_text_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('encode-hexadecimal-column-text',                                _('Column: Encode Hexadecimal Text'),
                                                                                            self.on_encode_hexadecimal_column_text_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('encode-url-cell-text',                                          _('Cell: Encode URL Text'),
                                                                                            self.on_encode_url_cell_text_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('encode-url-column-text',                                        _('Column: Encode URL Text'),
                                                                                            self.on_encode_url_column_text_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('pad-end-cell-with-custom-string',                               _('Cell: Pad End (Right) with Custom Character...'),
                                                                                            self.on_pad_end_cell_with_custom_string_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('pad-end-cell',                                                  _('Cell: Pad End (Right) with Whitespace'),
                                                                                            self.on_pad_end_cell_with_whitespace_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('pad-end-column-with-custom-string',                             _('Column: Pad End (Right) with Custom Character...'),
                                                                                            self.on_pad_end_column_with_custom_string_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('pad-end-column',                                                _('Column: Pad End (Right) with Whitespace'),
                                                                                            self.on_pad_end_column_with_whitespace_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('pad-start-cell-with-custom-string',                             _('Cell: Pad Start (Left) with Custom Character...'),
                                                                                            self.on_pad_start_cell_with_custom_string_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('pad-start-cell',                                                _('Cell: Pad Start (Left) with Whitespace'),
                                                                                            self.on_pad_start_cell_with_whitespace_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('pad-start-column-with-custom-string',                           _('Column: Pad Start (Left) with Custom Character...'),
                                                                                            self.on_pad_start_column_with_custom_string_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('pad-start-column',                                              _('Column: Pad Start (Left) with Whitespace'),
                                                                                            self.on_pad_start_column_with_whitespace_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('pig-latinnify-cell',                                            _('Cell: Pig Latinnify'),
                                                                                            self.on_pig_latinnify_cell_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('pig-latinnify-column',                                          _('Column: Pig Latinnify'),
                                                                                            self.on_pig_latinnify_column_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('remove-prefix-from-cell-case-insensitive',                      _('Cell: Remove Prefix (Case Insensitive)...'),
                                                                                            self.on_remove_prefix_from_cell_case_insensitive_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('remove-prefix-from-cell-case-sensitive',                        _('Cell: Remove Prefix (Case Sensitive)...'),
                                                                                            self.on_remove_prefix_from_cell_case_sensitive_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('remove-prefix-from-column-case-insensitive',                    _('Column: Remove Prefix (Case Insensitive)...'),
                                                                                            self.on_remove_prefix_from_column_case_insensitive_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('remove-prefix-from-column-case-sensitive',                      _('Column: Remove Prefix (Case Sensitive)...'),
                                                                                            self.on_remove_prefix_from_column_case_sensitive_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('remove-suffix-from-cell-case-insensitive',                      _('Cell: Remove Suffix (Case Insensitive)...'),
                                                                                            self.on_remove_suffix_from_cell_case_insensitive_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('remove-suffix-from-cell-case-sensitive',                        _('Cell: Remove Suffix (Case Sensitive)...'),
                                                                                            self.on_remove_suffix_from_cell_case_sensitive_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('remove-suffix-from-column-case-insensitive',                    _('Column: Remove Suffix (Case Insensitive)...'),
                                                                                            self.on_remove_suffix_from_column_case_insensitive_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('remove-suffix-from-column-case-sensitive',                      _('Column: Remove Suffix (Case Sensitive)...'),
                                                                                            self.on_remove_suffix_from_column_case_sensitive_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
#       self.create_action('remove-cell-ansi-escape-codes',                                 _('Cell: Remove ANSI Escape Codes'),
#                                                                                           self.on_remove_cell_ansi_escape_codes_action,
#                                                                                           when_expression="document == 'worksheet'")
#       self.create_action('remove-cell-control-characters',                                _('Cell: Remove Control Characters'),
#                                                                                           self.on_remove_cell_control_characters_action,
#                                                                                           when_expression="document == 'worksheet'")
        self.create_action('remove-cell-new-lines-characters',                              _('Cell: Remove New-Lines Characters'),
                                                                                            self.on_remove_cell_new_lines_characters_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('remove-cell-whitespace-characters',                             _('Cell: Remove Whitespace Characters'),
                                                                                            self.on_remove_cell_whitespace_characters_action,
                                                                                            when_expression="document == 'worksheet'")
#       self.create_action('remove-column-ansi-escape-codes',                               _('Cell: Remove ANSI Escape Codes'),
#                                                                                           self.on_remove_column_ansi_escape_codes_action,
#                                                                                           when_expression="document == 'worksheet'")
#       self.create_action('remove-column-control-characters',                              _('Column: Remove Control Characters'),
#                                                                                           self.on_remove_column_control_characters_action,
#                                                                                           when_expression="document == 'worksheet'")
        self.create_action('remove-column-new-lines-characters',                            _('Column: Remove New-Lines Characters'),
                                                                                            self.on_remove_column_new_lines_characters_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('remove-column-whitespace-characters',                           _('Column: Remove Whitespace Characters'),
                                                                                            self.on_remove_column_whitespace_characters_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('replace-cell-values-case-insensitive',                          _('Cell: Replace Text Value (Case Insensitive)...'),
                                                                                            self.on_replace_cell_text_value_case_insensitive_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('replace-cell-values-case-insensitive-with-regex',               _('Cell: Replace Text Value with Regex (Case Insensitive)...'),
                                                                                            self.on_replace_cell_text_value_case_insensitive_with_regex_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('replace-cell-values-case-sensitive',                            _('Cell: Replace Text Value (Case Sensitive)...'),
                                                                                            self.on_replace_cell_text_value_case_sensitive_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('replace-cell-values-case-sensitive-with-regex',                 _('Cell: Replace Text Value with Regex (Case Sensitive)...'),
                                                                                            self.on_replace_cell_text_value_case_sensitive_with_regex_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('replace-cell-whitespace-with-a-single-space',                   _('Cell: Replace Whitespace with a Single Space'),
                                                                                            self.on_replace_cell_whitespace_with_a_single_space_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('replace-cell-whitespace-and-new-lines-with-a-single-space',     _('Cell: Replace Whitespace &amp; New-Lines with a Single Space'),
                                                                                            self.on_replace_cell_whitespace_and_new_lines_with_a_single_space_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('replace-column-values-case-insensitive',                        _('Column: Replace Text Value (Case Insensitive)...'),
                                                                                            self.on_replace_column_text_value_case_insensitive_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('replace-column-values-case-insensitive-with-regex',             _('Column: Replace Text Value with Regex (Case Insensitive)...'),
                                                                                            self.on_replace_column_text_value_case_insensitive_with_regex_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('replace-column-values-case-sensitive',                          _('Column: Replace Text Value (Case Sensitive)...'),
                                                                                            self.on_replace_column_text_value_case_sensitive_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('replace-column-values-case-sensitive-with-regex',               _('Column: Replace Text Value with Regex (Case Sensitive)...'),
                                                                                            self.on_replace_column_text_value_case_sensitive_with_regex_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('replace-column-whitespace-with-a-single-space',                 _('Column: Replace Whitespace with a Single Space'),
                                                                                            self.on_replace_column_whitespace_with_a_single_space_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('replace-column-whitespace-and-new-lines-with-a-single-space',   _('Column: Replace Whitespace &amp; New-Lines with a Single Space'),
                                                                                            self.on_replace_column_whitespace_and_new_lines_with_a_single_space_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('reverse-text-cell',                                             _('Cell: Reverse Text'),
                                                                                            self.on_reverse_cell_text_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('reverse-text-column',                                           _('Column: Reverse Text'),
                                                                                            self.on_reverse_column_text_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('slugify-cell',                                                  _('Cell: Slugify'),
                                                                                            self.on_slugify_cells_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('slugify-column',                                                _('Column: Slugify'),
                                                                                            self.on_slugify_columns_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('split-cell-by-comma-into-new-worksheet',                        _('Cell: Split Text by Comma Into New Worksheet'),
                                                                                            self.on_split_cells_by_comma_into_new_worksheet_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('split-cell-by-characters-into-new-worksheet',                   _('Cell: Split Text by a Set of Characters Into New Worksheet...'),
                                                                                            self.on_split_cells_by_characters_into_new_worksheet_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('split-cell-by-pipe-into-new-worksheet',                         _('Cell: Split Text by Pipe Into New Worksheet'),
                                                                                            self.on_split_cells_by_pipe_into_new_worksheet_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('split-cell-by-semicolon-into-new-worksheet',                    _('Cell: Split Text by Semicolon Into New Worksheet'),
                                                                                            self.on_split_cells_by_semicolon_into_new_worksheet_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('split-cell-by-space-into-new-worksheet',                        _('Cell: Split Text by Space Into New Worksheet'),
                                                                                            self.on_split_cells_by_space_into_new_worksheet_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('split-column-by-comma-into-new-worksheet',                      _('Column: Split Text by Comma Into New Worksheet'),
                                                                                            self.on_split_columns_by_comma_into_new_worksheet_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('split-column-by-characters-into-new-worksheet',                 _('Column: Split Text by a Set of Characters Into New Worksheet...'),
                                                                                            self.on_split_columns_by_characters_into_new_worksheet_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('split-column-by-pipe-into-new-worksheet',                       _('Column: Split Text by Pipe Into New Worksheet'),
                                                                                            self.on_split_columns_by_pipe_into_new_worksheet_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('split-column-by-semicolon-into-new-worksheet',                  _('Column: Split Text by Semicolon Into New Worksheet'),
                                                                                            self.on_split_columns_by_semicolon_into_new_worksheet_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('split-column-by-space-into-new-worksheet',                      _('Column: Split Text by Space Into New Worksheet'),
                                                                                            self.on_split_columns_by_space_into_new_worksheet_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('swap-cell-text-case',                                           _('Cell: Swap Text Case'),
                                                                                            self.on_swap_cell_text_case_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('swap-column-text-case',                                         _('Column: Swap Text Case'),
                                                                                            self.on_swap_column_text_case_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('trim-cell-whitespace',                                          _('Cell: Trim Leading &amp; Trailing Whitespace'),
                                                                                            self.on_trim_cell_whitespace_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('trim-cell-whitespace-and-remove-new-lines',                     _('Cell: Trim Whitespace &amp; Remove Newlines'),
                                                                                            self.on_trim_cell_whitespace_and_remove_new_lines_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('trim-cell-start-whitespace',                                    _('Cell: Trim Leading Whitespace'),
                                                                                            self.on_trim_cell_start_whitespace_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('trim-cell-end-whitespace',                                      _('Cell: Trim Trailing Whitespace'),
                                                                                            self.on_trim_cell_end_whitespace_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('trim-column-whitespace',                                        _('Column: Trim Leading &amp; Trailing Whitespace'),
                                                                                            self.on_trim_column_whitespace_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('trim-column-whitespace-and-remove-new-lines',                   _('Column: Trim Whitespace &amp; Remove Newlines'),
                                                                                            self.on_trim_column_whitespace_and_remove_new_lines_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('trim-column-start-whitespace',                                  _('Column: Trim Leading Whitespace'),
                                                                                            self.on_trim_column_start_whitespace_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('trim-column-end-whitespace',                                    _('Column: Trim Trailing Whitespace'),
                                                                                            self.on_trim_column_end_whitespace_action,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('wrap-cell-with-text-different',                                 _('Cell: Wrap with Text (Different Prefix and Suffix)...'),
                                                                                            self.on_wrap_cell_with_text_different_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('wrap-cell-with-text-same',                                      _('Cell: Wrap with Text (Same Prefix and Suffix)...'),
                                                                                            self.on_wrap_cell_with_text_same_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('wrap-column-with-text-different',                               _('Column: Wrap with Text (Different Prefix and Suffix)...'),
                                                                                            self.on_wrap_column_with_text_different_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")
        self.create_action('wrap-column-with-text-same',                                    _('Column: Wrap with Text (Same Prefix and Suffix)...'),
                                                                                            self.on_wrap_column_with_text_same_action,
                                                                                            will_prompt=True,
                                                                                            when_expression="document == 'worksheet'")

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

        file_paths = [] # file paths to open

        for arg in args:
            if not arg.startswith('--'):
                try:
                    file = Gio.File.new_for_commandline_arg(arg)
                    if file_path := file.get_path():
                        file_paths.append(file_path)
                except Exception as e:
                    print(e)

        if file_paths:
            for file_path in file_paths:
                self._create_new_window(file_path)
            return 0

        self.activate()
        return 0

    def do_activate(self) -> None:
        if window := self.get_active_window():
            window.present()
            return
        self._create_new_window()

    def do_shutdown(self) -> None:
        for window in self.get_windows():
            window.close()

        serialized_connection_list = json.dumps(self.connection_list)
        self.settings.set_string('connection-list', serialized_connection_list)

        Gio.Application.do_shutdown(self)

    def create_action(self,
                      name:            str,
                      title:           str = '',
                      callback:        callable = None,
                      param_type:      GLib.VariantType = None,
                      shortcuts:       list = None,
                      is_command:      bool = True,
                      will_prompt:     bool = False,
                      steal_focus:     bool = False,
                      when_expression: str = '') -> None:
        action = Gio.SimpleAction.new(name, param_type)
        action.connect('activate', callback)
        self.add_action(action)

        if shortcuts:
            self.set_accels_for_action(f'app.{name}', shortcuts)

        if is_command:
            self.application_commands.append({
                'action-name'     : name,
                'title'           : title,
                'shortcuts'       : shortcuts,
                'steal-focus'     : steal_focus,
                'will-prompt'     : will_prompt,
                'when-expression' : when_expression,
            })
            self.application_commands.sort(key=lambda command: command['title'])

    def load_user_workspace(self, workspace_schema: dict) -> None:
        window = self._reuse_current_window()

        # Create a new window if needed
        if not window:
            window = self._create_new_window(skip_setup=True)

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
        self._return_focus_back(sheet_document)

        # Set the pinned tabs
        pinned_tabs = workspace_schema.get('pinned-tabs', [])
        for tab_index in pinned_tabs:
            tab_page = window.tab_view.get_nth_page(tab_index)
            window.tab_view.set_page_pinned(tab_page, True)

        self.on_update_connection_list(window)

        window.present()

    def on_about_action(self,
                        action: Gio.SimpleAction,
                        *args) -> None:
        window = self.get_active_window()
        dialog = Adw.AboutDialog(application_name='Data Studio',
                                 application_icon='com.macipra.eruo',
                                 developer_name='Naufan Rusyda Faikar',
                                 version='0.1.0',
                                 developers=['Naufan Rusyda Faikar'],
                                 copyright='© 2025 Naufan Rusyda Faikar',
                                 issue_url='https://github.com/naruaika/eruo-data-studio/issues',
                                 support_url='https://github.com/naruaika/eruo-data-studio/discussions')
        dialog.set_translator_credits(_('translator-credits'))
        dialog.present(window)

    def on_add_new_connection_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
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

    def on_append_prefix_to_cell_action(self,
                                        action: Gio.SimpleAction,
                                        *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_append_prefix(prefix: str) -> None:
            document.update_current_cells_from_operator('append-prefix', [prefix], on_column=False)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the prefix for the cells'),
                                                            callback=proceed_to_append_prefix)

    def on_append_prefix_to_column_action(self,
                                          action: Gio.SimpleAction,
                                          *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_append_prefix(prefix: str) -> None:
            document.update_current_cells_from_operator('append-prefix', [prefix], on_column=True)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the prefix for the columns'),
                                                            callback=proceed_to_append_prefix)

    def on_append_suffix_to_cell_action(self,
                                        action: Gio.SimpleAction,
                                        *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_append_suffix(suffix: str) -> None:
            document.update_current_cells_from_operator('append-suffix', [suffix], on_column=False)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the suffix for the cells'),
                                                            callback=proceed_to_append_suffix)

    def on_append_suffix_to_column_action(self,
                                          action: Gio.SimpleAction,
                                          *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_append_suffix(suffix: str) -> None:
            document.update_current_cells_from_operator('append-suffix', [suffix], on_column=True)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the suffix for the columns'),
                                                            callback=proceed_to_append_suffix)

    def on_apply_pending_table_action(self,
                                      action: Gio.SimpleAction,
                                      *args) -> None:
        action_data_id = args[0].get_string()
        window = self.get_active_window()
        window.apply_pending_table(action_data_id)

    def on_change_case_cell_to_camel_case_action(self,
                                                 action: Gio.SimpleAction,
                                                 *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('camel-case', on_column=False)

    def on_change_case_cell_to_constant_case_action(self,
                                                    action: Gio.SimpleAction,
                                                    *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('constant-case', on_column=False)

    def on_change_case_cell_to_dot_case_action(self,
                                               action: Gio.SimpleAction,
                                               *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('dot-case', on_column=False)

    def on_change_case_cell_to_kebab_case_action(self,
                                                 action: Gio.SimpleAction,
                                                 *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('kebab-case', on_column=False)

    def on_change_case_cell_to_lowercase_action(self,
                                                action: Gio.SimpleAction,
                                                *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('lowercase', on_column=False)

    def on_change_case_cell_to_pascal_case_action(self,
                                                  action: Gio.SimpleAction,
                                                  *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('pascal-case', on_column=False)

    def on_change_case_cell_to_snake_case_action(self,
                                                 action: Gio.SimpleAction,
                                                 *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('snake-case', on_column=False)

    def on_change_case_cell_to_sentence_case_action(self,
                                                    action: Gio.SimpleAction,
                                                    *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('sentence-case', on_column=False)

    def on_change_case_cell_to_sponge_case_action(self,
                                                  action: Gio.SimpleAction,
                                                  *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('sponge-case', on_column=False)

    def on_change_case_cell_to_title_case_action(self,
                                                 action: Gio.SimpleAction,
                                                 *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('title-case', on_column=False)

    def on_change_case_cell_to_uppercase_action(self,
                                                action: Gio.SimpleAction,
                                                *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('uppercase', on_column=False)

    def on_change_case_column_to_camel_case_action(self,
                                                   action: Gio.SimpleAction,
                                                   *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('camel-case', on_column=True)

    def on_change_case_column_to_dot_case_action(self,
                                                      action: Gio.SimpleAction,
                                                      *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('dot-case', on_column=True)

    def on_change_case_column_to_constant_case_action(self,
                                                      action: Gio.SimpleAction,
                                                      *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('constant-case', on_column=True)

    def on_change_case_column_to_kebab_case_action(self,
                                                   action: Gio.SimpleAction,
                                                   *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('kebab-case', on_column=True)

    def on_change_case_column_to_lowercase_action(self,
                                                  action: Gio.SimpleAction,
                                                  *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('lowercase', on_column=True)

    def on_change_case_column_to_pascal_case_action(self,
                                                    action: Gio.SimpleAction,
                                                    *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('pascal-case', on_column=True)

    def on_change_case_column_to_snake_case_action(self,
                                                   action: Gio.SimpleAction,
                                                   *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('snake-case', on_column=True)

    def on_change_case_column_to_sentence_case_action(self,
                                                      action: Gio.SimpleAction,
                                                      *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('sentence-case', on_column=True)

    def on_change_case_column_to_sponge_case_action(self,
                                                    action: Gio.SimpleAction,
                                                    *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('sponge-case', on_column=True)

    def on_change_case_column_to_title_case_action(self,
                                                   action: Gio.SimpleAction,
                                                   *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('title-case', on_column=True)

    def on_change_case_column_to_uppercase_action(self,
                                                  action: Gio.SimpleAction,
                                                  *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('uppercase', on_column=True)

    def on_convert_cell_to_unicode_normalization_nfc_action(self,
                                                            action: Gio.SimpleAction,
                                                            *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('unicode-normalization-nfc', on_column=False)

    def on_convert_cell_to_unicode_normalization_nfd_action(self,
                                                            action: Gio.SimpleAction,
                                                            *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('unicode-normalization-nfd', on_column=False)

    def on_convert_cell_to_unicode_normalization_nfkc_action(self,
                                                             action: Gio.SimpleAction,
                                                             *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('unicode-normalization-nfkc', on_column=False)

    def on_convert_cell_to_unicode_normalization_nfkd_action(self,
                                                             action: Gio.SimpleAction,
                                                             *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('unicode-normalization-nfkd', on_column=False)

    def on_convert_column_to_unicode_normalization_nfc_action(self,
                                                              action: Gio.SimpleAction,
                                                              *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('unicode-normalization-nfc', on_column=True)

    def on_convert_column_to_unicode_normalization_nfd_action(self,
                                                              action: Gio.SimpleAction,
                                                              *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('unicode-normalization-nfd', on_column=True)

    def on_convert_column_to_unicode_normalization_nfkc_action(self,
                                                               action: Gio.SimpleAction,
                                                               *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('unicode-normalization-nfkc', on_column=True)

    def on_convert_column_to_unicode_normalization_nfkd_action(self,
                                                               action: Gio.SimpleAction,
                                                               *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('unicode-normalization-nfkd', on_column=True)

    def on_clear_contents_action(self,
                                 action: Gio.SimpleAction,
                                 *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_literal('')

    def on_close_other_tabs_action(self,
                                   action: Gio.SimpleAction,
                                   *args) -> None:
        window = self.get_active_window()

        def close_selected_tabs() -> None:
            document_id = args[0].get_string()
            tab_page = self._get_current_tab_page(window, document_id)
            window.tab_view.close_other_pages(tab_page)

        self._show_close_tabs_confirmation(window, close_selected_tabs)

    def on_close_selected_tab_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        window = self.get_active_window()

        tab_page = window.tab_view.get_selected_page()
        document = window.get_current_active_document()

        def close_selected_tabs() -> None:
            window.tab_view.close_page(tab_page)

        if self._check_sheet_blanks(window, document.document_id):
            close_selected_tabs()
        else:
            self._show_close_tabs_confirmation(window, close_selected_tabs)

    def on_close_tab_action(self,
                            action: Gio.SimpleAction,
                            *args) -> None:
        window = self.get_active_window()
        document_id = args[0].get_string()

        def close_selected_tabs() -> None:
            tab_page = self._get_current_tab_page(window, document_id)
            window.tab_view.close_page(tab_page)

        if self._check_sheet_blanks(window, document_id):
            close_selected_tabs()
        else:
            self._show_close_tabs_confirmation(window, close_selected_tabs)

    def on_close_tabs_to_left_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        window = self.get_active_window()

        def close_selected_tabs() -> None:
            document_id = args[0].get_string()
            tab_page = self._get_current_tab_page(window, document_id)
            window.tab_view.close_pages_before(tab_page)

        self._show_close_tabs_confirmation(window, close_selected_tabs)

    def on_close_tabs_to_right_action(self,
                                      action: Gio.SimpleAction,
                                      *args) -> None:
        window = self.get_active_window()

        def close_selected_tabs() -> None:
            document_id = args[0].get_string()
            tab_page = self._get_current_tab_page(window, document_id)
            window.tab_view.close_pages_after(tab_page)

        self._show_close_tabs_confirmation(window, close_selected_tabs)

    def on_convert_to_boolean_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        self._convert_to(polars.Boolean)

    def on_convert_to_categorical_action(self,
                                         action: Gio.SimpleAction,
                                         *args) -> None:
        self._convert_to(polars.Categorical)

    def on_convert_to_date_action(self,
                                  action: Gio.SimpleAction,
                                  *args) -> None:
        self._convert_to(polars.Date)

    def on_convert_to_datetime_action(self,
                                      action: Gio.SimpleAction,
                                      *args) -> None:
        self._convert_to(polars.Datetime)

    def on_convert_to_decimal_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        self._convert_to(polars.Decimal)

    def on_convert_to_float32_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        self._convert_to(polars.Float32)

    def on_convert_to_float64_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        self._convert_to(polars.Float64)

    def on_convert_to_int8_action(self,
                                  action: Gio.SimpleAction,
                                  *args) -> None:
        self._convert_to(polars.Int8)

    def on_convert_to_int16_action(self,
                                   action: Gio.SimpleAction,
                                   *args) -> None:
        self._convert_to(polars.Int16)

    def on_convert_to_int32_action(self,
                                   action: Gio.SimpleAction,
                                   *args) -> None:
        self._convert_to(polars.Int32)

    def on_convert_to_int64_action(self,
                                   action: Gio.SimpleAction,
                                   *args) -> None:
        self._convert_to(polars.Int64)

    def on_convert_to_text_action(self,
                                  action: Gio.SimpleAction,
                                  *args) -> None:
        self._convert_to(polars.Utf8)

    def on_convert_to_time_action(self,
                                  action: Gio.SimpleAction,
                                  *args) -> None:
        self._convert_to(polars.Time)

    def on_convert_to_uint8_action(self,
                                   action: Gio.SimpleAction,
                                   *args) -> None:
        self._convert_to(polars.UInt8)

    def on_convert_to_uint16_action(self,
                                    action: Gio.SimpleAction,
                                    *args) -> None:
        self._convert_to(polars.UInt16)

    def on_convert_to_uint32_action(self,
                                    action: Gio.SimpleAction,
                                    *args) -> None:
        self._convert_to(polars.UInt32)

    def on_convert_to_uint64_action(self,
                                    action: Gio.SimpleAction,
                                    *args) -> None:
        self._convert_to(polars.UInt64)

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

        document = self._get_current_active_document()
        document.copy_from_current_selection(self.clipboard)

        return True

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

        document = self._get_current_active_document()
        document.cut_from_current_selection(self.clipboard)

        return True

    def on_decode_base64_cell_text_action(self,
                                          action: Gio.SimpleAction,
                                          *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('decode-base64', on_column=False)

    def on_decode_base64_column_text_action(self,
                                            action: Gio.SimpleAction,
                                            *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('decode-base64', on_column=True)

    def on_decode_hexadecimal_cell_text_action(self,
                                               action: Gio.SimpleAction,
                                               *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('decode-hexadecimal', on_column=False)

    def on_decode_hexadecimal_column_text_action(self,
                                                 action: Gio.SimpleAction,
                                                 *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('decode-hexadecimal', on_column=True)

    def on_decode_url_cell_text_action(self,
                                       action: Gio.SimpleAction,
                                       *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('decode-url', on_column=False)

    def on_decode_url_column_text_action(self,
                                         action: Gio.SimpleAction,
                                         *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('decode-url', on_column=True)

    def on_delete_column_action(self,
                                action: Gio.SimpleAction,
                                *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.delete_current_columns()

    def on_delete_connection_action(self,
                                    action: Gio.SimpleAction,
                                    *args) -> None:
        cname = args[0].get_string()
        self.connection_list = [connection for connection in self.connection_list
                                if connection['cname'] != cname]

        window = self.get_active_window()
        self.on_update_connection_list(window)

    def on_delete_row_action(self,
                             action: Gio.SimpleAction,
                             *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.delete_current_rows()

    def on_duplicate_selected_tab_action(self,
                                         action: Gio.SimpleAction,
                                         *args) -> None:
        window = self.get_active_window()
        document = window.get_current_active_document()
        window.duplicate_sheet(document.document_id)

    def on_duplicate_tab_action(self,
                                action: Gio.SimpleAction,
                                *args) -> None:
        window = self.get_active_window()
        document_id = args[0].get_string()
        window.duplicate_sheet(document_id)

    def on_duplicate_to_above_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.duplicate_from_current_rows(above=True)

    def on_duplicate_to_below_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.duplicate_from_current_rows(above=False)

    def on_duplicate_to_left_action(self,
                                    action: Gio.SimpleAction,
                                    *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.duplicate_from_current_columns(left=True)

    def on_duplicate_to_right_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.duplicate_from_current_columns(left=False)

    def on_encode_base64_cell_text_action(self,
                                          action: Gio.SimpleAction,
                                          *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('encode-base64', on_column=False)

    def on_encode_base64_column_text_action(self,
                                            action: Gio.SimpleAction,
                                            *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('encode-base64', on_column=True)

    def on_encode_hexadecimal_cell_text_action(self,
                                               action: Gio.SimpleAction,
                                               *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('encode-hexadecimal', on_column=False)

    def on_encode_hexadecimal_column_text_action(self,
                                                 action: Gio.SimpleAction,
                                                 *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('encode-hexadecimal', on_column=True)

    def on_encode_url_cell_text_action(self,
                                       action: Gio.SimpleAction,
                                       *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('encode-url', on_column=False)

    def on_encode_url_column_text_action(self,
                                         action: Gio.SimpleAction,
                                         *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('encode-url', on_column=True)

    def on_export_file_as_action(self,
                                 action: Gio.SimpleAction,
                                 *args) -> None:
        window = self.get_active_window()
        self.file_manager.export_as_file(window)

    def on_file_cancel(self, source: GObject.Object) -> None:
        self._return_focus_back()

    def on_file_exported(self,
                         source:    GObject.Object,
                         file_path: str) -> None:
        self._return_focus_back()

    def on_file_opened(self,
                       source:    GObject.Object,
                       file_path: str,
                       in_place:  bool) -> None:
        if not file_path:
            return # shouldn't happen, but for completeness

        # Insert the file content to a new tab
        if in_place:
            self._create_new_tab(file_path)
            return

        if self._reuse_current_window(file_path):
            return

        self._create_new_window(file_path)

    def on_file_saved(self,
                      source:    GObject.Object,
                      file_path: str) -> None:
        self._return_focus_back()

    def on_filter_by_cell_value_action(self,
                                       action: Gio.SimpleAction,
                                       *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.filter_current_rows(multiple=False)

    def on_filter_by_unique_values_action(self,
                                          action: Gio.SimpleAction,
                                          *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.filter_current_rows(multiple=True)

    def on_focus_on_formula_editor_action(self,
                                          action: Gio.SimpleAction,
                                          *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        window = self.get_active_window()

        editor_in_focus = window.name_formula_box.get_focus_child() and \
                          window.formula_bar.get_focus_child()
        multiline_editor_is_visible = not window.name_formula_box.get_focus_child() and \
                                      window.formula_bar_toggle_button.get_active()

        if editor_in_focus or multiline_editor_is_visible:
            self.on_focus_on_multiline_formula_editor_action(action, args)
            return

        window.formula_bar_toggle_button.set_active(False)
        window.formula_bar.grab_focus()

    def on_focus_on_multiline_formula_editor_action(self,
                                                    action: Gio.SimpleAction,
                                                    *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        window = self.get_active_window()

        if window.multiline_formula_bar.get_focus_child():
            self.on_focus_on_formula_editor_action(action, args)
            return

        window.formula_bar_toggle_button.set_active(True)
        window.multiline_formula_bar.grab_focus()

    def on_go_to_cell_action(self,
                             action: Gio.SimpleAction,
                             *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        window = self.get_active_window()
        window.on_name_box_pressed(Gtk.GestureClick(), 1, 0, 0)

    def on_hide_column_action(self,
                              action: Gio.SimpleAction,
                              *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.hide_current_columns()

    def on_import_table_action(self,
                               action: Gio.SimpleAction,
                               *args) -> None:
        window = self.get_active_window()
        self.file_manager.open_file(window, in_place=True)

    def on_insert_column_left_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.insert_blank_from_current_columns(left=True)

    def on_insert_column_right_action(self,
                                      action: Gio.SimpleAction,
                                      *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.insert_blank_from_current_columns(left=False)

    def on_insert_row_above_action(self,
                                   action: Gio.SimpleAction,
                                   *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.insert_blank_from_current_rows(above=True)

    def on_insert_row_below_action(self,
                                   action: Gio.SimpleAction,
                                   *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.insert_blank_from_current_rows(above=False)

    def on_keep_rows_only_including_selection(self,
                                              action: Gio.SimpleAction,
                                              *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.filter_current_rows()

    def on_keep_rows_only_including_selection_into_new_worksheet_action(self,
                                                                        action: Gio.SimpleAction,
                                                                        *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        filter_by = {'operator-name': 'current-selection'}

        window = self.get_active_window()
        window.duplicate_sheet(document.document_id,
                               materialize=True,
                               filter_by=filter_by)

    def on_keep_rows_only_including_case_insensitive_string_action(self,
                                                                   action: Gio.SimpleAction,
                                                                   *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_keep_rows(string: str) -> None:
            operator = 'contains'
            expression = polars.col(polars.String).str.contains_any([string], ascii_case_insensitive=True)
            expression = polars.any_horizontal()
            document.pending_filters = [self._construct_query_builder(operator, string, expression)]

            document.filter_current_rows(multiple=True)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the string to keep only'),
                                                            callback=proceed_to_keep_rows)

    def on_keep_rows_only_including_case_sensitive_string_action(self,
                                                                 action: Gio.SimpleAction,
                                                                 *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_keep_rows(string: str) -> None:
            operator = 'contains'
            expression = polars.col(polars.String).str.contains_any([string], ascii_case_insensitive=False)
            expression = polars.any_horizontal(expression)
            document.pending_filters = [self._construct_query_builder(operator, string, expression)]
            document.filter_current_rows(multiple=True)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the string to keep only'),
                                                            callback=proceed_to_keep_rows)

    def on_keep_rows_only_including_case_insensitive_string_into_new_worksheet_action_action(self,
                                                                                             action: Gio.SimpleAction,
                                                                                             *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_keep_rows(string: str) -> None:
            operator = 'contains'
            expression = polars.col(polars.String).str.contains_any([string], ascii_case_insensitive=True)
            expression = polars.any_horizontal(expression)
            pending_filters = [self._construct_query_builder(operator, string, expression)]

            filter_by = {'operator-name': 'query-builder',
                         'operator-args': pending_filters}

            window = self.get_active_window()
            window.duplicate_sheet(document.document_id,
                                   materialize=True,
                                   filter_by=filter_by)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the string to keep only'),
                                                            callback=proceed_to_keep_rows)

    def on_keep_rows_only_including_case_sensitive_string_into_new_worksheet_action_action(self,
                                                                                           action: Gio.SimpleAction,
                                                                                           *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_keep_rows(string: str) -> None:
            operator = 'contains'
            expression = polars.col(polars.String).str.contains_any([string], ascii_case_insensitive=False)
            expression = polars.any_horizontal(expression)
            pending_filters = [self._construct_query_builder(operator, string, expression)]

            filter_by = {'operator-name': 'query-builder',
                         'operator-args': pending_filters}

            window = self.get_active_window()
            window.duplicate_sheet(document.document_id,
                                   materialize=True,
                                   filter_by=filter_by)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the string to keep only'),
                                                            callback=proceed_to_keep_rows)

    def on_keep_rows_only_matching_regex_case_insensitive_string_action(self,
                                                                        action: Gio.SimpleAction,
                                                                        *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_keep_rows(pattern: str) -> None:
            operator = 'contains'
            expression = polars.col(polars.String).str.contains(f'(?i){pattern}')
            expression = polars.any_horizontal(expression)
            document.pending_filters = [self._construct_query_builder(operator, pattern, expression)]
            document.filter_current_rows(multiple=True)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the pattern to keep only'),
                                                            callback=proceed_to_keep_rows)

    def on_keep_rows_only_matching_regex_case_sensitive_string_action(self,
                                                                      action: Gio.SimpleAction,
                                                                      *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_keep_rows(pattern: str) -> None:
            operator = 'contains'
            expression = polars.col(polars.String).str.contains(pattern)
            expression = polars.any_horizontal(expression)
            document.pending_filters = [self._construct_query_builder(operator, pattern, expression)]
            document.filter_current_rows(multiple=True)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the pattern to keep only'),
                                                            callback=proceed_to_keep_rows)

    def on_keep_rows_only_matching_regex_case_insensitive_string_into_new_worksheet_action_action(self,
                                                                                                  action: Gio.SimpleAction,
                                                                                                  *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_keep_rows(pattern: str) -> None:
            operator = 'contains'
            expression = polars.col(polars.String).str.contains(f'(?i){pattern}')
            expression = polars.any_horizontal(expression)
            pending_filters = [self._construct_query_builder(operator, pattern, expression)]

            filter_by = {'operator-name': 'query-builder',
                         'operator-args': pending_filters}

            window = self.get_active_window()
            window.duplicate_sheet(document.document_id,
                                   materialize=True,
                                   filter_by=filter_by)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the pattern to keep only'),
                                                            callback=proceed_to_keep_rows)

    def on_keep_rows_only_matching_regex_case_sensitive_string_into_new_worksheet_action_action(self,
                                                                                                action: Gio.SimpleAction,
                                                                                                *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_keep_rows(pattern: str) -> None:
            operator = 'contains'
            expression = polars.col(polars.String).str.contains(pattern)
            expression = polars.any_horizontal(expression)
            pending_filters = [self._construct_query_builder(operator, pattern, expression)]

            filter_by = {'operator-name': 'query-builder',
                         'operator-args': pending_filters}

            window = self.get_active_window()
            window.duplicate_sheet(document.document_id,
                                   materialize=True,
                                   filter_by=filter_by)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the pattern to keep only'),
                                                            callback=proceed_to_keep_rows)

    def on_move_tab_to_end_action(self,
                                  action: Gio.SimpleAction,
                                  *args) -> None:
        window = self.get_active_window()
        document_id = args[0].get_string()
        tab_page = self._get_current_tab_page(window, document_id)
        n_pages = window.tab_view.get_n_pages()
        window.tab_view.reorder_page(tab_page, n_pages - 1)

    def on_move_tab_to_start_action(self,
                                    action: Gio.SimpleAction,
                                    *args) -> None:
        window = self.get_active_window()
        document_id = args[0].get_string()
        tab_page = self._get_current_tab_page(window, document_id)
        n_pinned_pages = window.tab_view.get_n_pinned_pages()
        window.tab_view.reorder_page(tab_page, n_pinned_pages)

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

    def on_open_command_palette_action(self,
                                       action: Gio.SimpleAction,
                                       *args) -> None:
        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay()

    def on_open_file_action(self,
                            action: Gio.SimpleAction,
                            *args) -> None:
        window = self.get_active_window()
        self.file_manager.open_file(window)

    def on_open_inline_formula_action(self,
                                      action: Gio.SimpleAction,
                                      *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        window = self.get_active_window()

        if window.inline_formula_box.get_focus_child():
            self.on_focus_on_formula_editor_action(action, args)
            return

        if window.formula_bar.get_focus_child():
            self.on_focus_on_multiline_formula_editor_action(action, args)
            return

        # This is maybe undesirable behaviour from the user perspectives,
        # but they would probably appreciate when they get used to XD.
        # TODO: let's have a discussion on this with our real users.
        window.formula_bar_toggle_button.set_active(False)

        window.open_inline_formula()

    def on_open_search_action(self,
                              action: Gio.SimpleAction,
                              *args) -> None:
        window = self.get_active_window()
        window.search_replace_overlay.open_search_overlay()

    def on_open_sort_filter_action(self,
                                   action: Gio.SimpleAction,
                                   *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        window = self.get_active_window()

        # Close all possible views on the sidebar to reveal the home view
        window.search_replace_all_view.close_search_view()

        # Open the home view
        window.sidebar_home_view.open_home_view()
        window.sidebar_home_view.open_sort_filter_sections()

    def on_pad_end_cell_with_custom_string_action(self,
                                                  action: Gio.SimpleAction,
                                                  *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_pad_end(fill_char: str, length: str) -> None:
            fill_char = fill_char[0] if len(fill_char) else ' '
            document.update_current_cells_from_operator('pad-end-custom', [length, fill_char], on_column=False)

        def ask_for_fill_char(length: str) -> None:
            length = int(length) if length.isnumeric() else 0
            window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                                prompt_text=_('Please enter the character used for padding the cells'),
                                                                callback=proceed_to_pad_end,
                                                                user_data=[length])

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the length of the padded string for the cells'),
                                                            callback=ask_for_fill_char,
                                                            more_prompt=True)

    def on_pad_end_cell_with_whitespace_action(self,
                                               action: Gio.SimpleAction,
                                               *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_pad_end(length: str) -> None:
            length = int(length) if length.isnumeric() else 0
            document.update_current_cells_from_operator('pad-end-default', [length], on_column=False)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the length of the padded string for the cells'),
                                                            callback=proceed_to_pad_end)

    def on_pad_end_column_with_custom_string_action(self,
                                                    action: Gio.SimpleAction,
                                                    *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_pad_end(fill_char: str, length: str) -> None:
            fill_char = fill_char[0] if len(fill_char) else ' '
            document.update_current_cells_from_operator('pad-end-custom', [length, fill_char], on_column=True)

        def ask_for_fill_char(length: str) -> None:
            length = int(length) if length.isnumeric() else 0
            window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                                prompt_text=_('Please enter the character used for padding the columns'),
                                                                callback=proceed_to_pad_end,
                                                                user_data=[length])

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the length of the padded string for the columns'),
                                                            callback=ask_for_fill_char,
                                                            more_prompt=True)

    def on_pad_end_column_with_whitespace_action(self,
                                                 action: Gio.SimpleAction,
                                                 *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_pad_end(length: str) -> None:
            length = int(length) if length.isnumeric() else 0
            document.update_current_cells_from_operator('pad-end-default', [length], on_column=True)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the length of the padded string for the columns'),
                                                            callback=proceed_to_pad_end)

    def on_pad_start_cell_with_custom_string_action(self,
                                                    action: Gio.SimpleAction,
                                                    *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_pad_start(fill_char: str, length: str) -> None:
            fill_char = fill_char[0] if len(fill_char) else ' '
            document.update_current_cells_from_operator('pad-start-custom', [length, fill_char], on_column=False)

        def ask_for_fill_char(length: str) -> None:
            length = int(length) if length.isnumeric() else 0
            window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                                prompt_text=_('Please enter the character used for padding the cells'),
                                                                callback=proceed_to_pad_start,
                                                                user_data=[length])

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the length of the padded string for the cells'),
                                                            callback=ask_for_fill_char,
                                                            more_prompt=True)

    def on_pad_start_cell_with_whitespace_action(self,
                                                 action: Gio.SimpleAction,
                                                 *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_pad_start(length: str) -> None:
            length = int(length) if length.isnumeric() else 0
            document.update_current_cells_from_operator('pad-start-default', [length], on_column=False)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the length of the padded string for the cells'),
                                                            callback=proceed_to_pad_start)

    def on_pad_start_column_with_custom_string_action(self,
                                                      action: Gio.SimpleAction,
                                                      *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_pad_start(fill_char: str, length: str) -> None:
            fill_char = fill_char[0] if len(fill_char) else ' '
            document.update_current_cells_from_operator('pad-start-custom', [length, fill_char], on_column=True)

        def ask_for_fill_char(length: str) -> None:
            length = int(length) if length.isnumeric() else 0
            window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                                prompt_text=_('Please enter the character used for padding the columns'),
                                                                callback=proceed_to_pad_start,
                                                                user_data=[length])

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the length of the padded string for the columns'),
                                                            callback=ask_for_fill_char,
                                                            more_prompt=True)

    def on_pad_start_column_with_whitespace_action(self,
                                                   action: Gio.SimpleAction,
                                                   *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_pad_start(length: str) -> None:
            length = int(length) if length.isnumeric() else 0
            document.update_current_cells_from_operator('pad-start-default', [length], on_column=True)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the length of the padded string for the columns'),
                                                            callback=proceed_to_pad_start)

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

        document = self._get_current_active_document()
        self.clipboard.read_text_async(on_clipboard_text_received)

        return True

    def on_pig_latinnify_cell_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('pig-latinnify', on_column=False)

    def on_pig_latinnify_column_action(self,
                                       action: Gio.SimpleAction,
                                       *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('pig-latinnify', on_column=True)

    def on_pin_tab_action(self,
                          action: Gio.SimpleAction,
                          *args) -> None:
        window = self.get_active_window()
        document_id = args[0].get_string()
        tab_page = self._get_current_tab_page(window, document_id)
        window.tab_view.set_page_pinned(tab_page, True)

    def on_preferences_action(self,
                              action: Gio.SimpleAction,
                              *args) -> None:
        raise NotImplementedError # TODO

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

    def on_rechunk_table_action(self,
                                action: Gio.SimpleAction,
                                *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.rechunk_table()

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

    def on_rename_tab_action(self,
                             action: Gio.SimpleAction,
                             *args) -> None:
        window = self.get_active_window()
        document_id = args[0].get_string()
        tab_page = self._get_current_tab_page(window, document_id)
        window.rename_sheet(tab_page)

    def on_remove_cell_new_lines_characters_action(self,
                                                   action: Gio.SimpleAction,
                                                   *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('remove-new-lines', on_column=False)

    def on_remove_cell_whitespace_characters_action(self,
                                                    action: Gio.SimpleAction,
                                                    *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('remove-whitespaces', on_column=False)

    def on_remove_column_new_lines_characters_action(self,
                                                     action: Gio.SimpleAction,
                                                     *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('remove-new-lines', on_column=True)

    def on_remove_column_whitespace_characters_action(self,
                                                      action: Gio.SimpleAction,
                                                      *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('remove-whitespaces', on_column=True)

    def on_remove_prefix_from_cell_case_insensitive_action(self,
                                                           action: Gio.SimpleAction,
                                                           *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_remove_prefix(prefix: str) -> None:
            document.update_current_cells_from_operator('remove-prefix-case-insensitive', [prefix], on_column=False)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the prefix for the cells'),
                                                            callback=proceed_to_remove_prefix)

    def on_remove_prefix_from_cell_case_sensitive_action(self,
                                                         action: Gio.SimpleAction,
                                                         *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_remove_prefix(prefix: str) -> None:
            document.update_current_cells_from_operator('remove-prefix-case-sensitive', [prefix], on_column=False)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the prefix for the cells'),
                                                            callback=proceed_to_remove_prefix)

    def on_remove_prefix_from_column_case_insensitive_action(self,
                                                             action: Gio.SimpleAction,
                                                             *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_remove_prefix(prefix: str) -> None:
            document.update_current_cells_from_operator('remove-prefix-case-insensitive', [prefix], on_column=True)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the prefix for the columns'),
                                                            callback=proceed_to_remove_prefix)

    def on_remove_prefix_from_column_case_sensitive_action(self,
                                                           action: Gio.SimpleAction,
                                                           *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_remove_prefix(prefix: str) -> None:
            document.update_current_cells_from_operator('remove-prefix-case-sensitive', [prefix], on_column=True)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the prefix for the columns'),
                                                            callback=proceed_to_remove_prefix)

    def on_remove_rows_including_selection(self,
                                           action: Gio.SimpleAction,
                                           *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.filter_current_rows(inverse=True)

    def on_remove_rows_including_selection_into_new_worksheet_action(self,
                                                                     action: Gio.SimpleAction,
                                                                     *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        filter_by = {'operator-name': 'inverse-selection'}

        window = self.get_active_window()
        window.duplicate_sheet(document.document_id,
                               materialize=True,
                               filter_by=filter_by)

    def on_remove_rows_including_case_insensitive_string_action(self,
                                                                action: Gio.SimpleAction,
                                                                *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_remove_rows(string: str) -> None:
            operator = 'does not contain'
            expression = polars.col(polars.String).str.contains_any([string], ascii_case_insensitive=True)
            expression = polars.any_horizontal(expression).not_()
            document.pending_filters = [self._construct_query_builder(operator, string, expression)]
            document.filter_current_rows(multiple=True)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the string to remove'),
                                                            callback=proceed_to_remove_rows)

    def on_remove_rows_including_case_sensitive_string_action(self,
                                                              action: Gio.SimpleAction,
                                                              *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_remove_rows(string: str) -> None:
            operator = 'does not contain'
            expression = polars.col(polars.String).str.contains_any([string], ascii_case_insensitive=False)
            expression = polars.any_horizontal(expression).not_()
            document.pending_filters = [self._construct_query_builder(operator, string, expression)]
            document.filter_current_rows(multiple=True)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the string to remove'),
                                                            callback=proceed_to_remove_rows)

    def on_remove_rows_including_case_insensitive_string_into_new_worksheet_action_action(self,
                                                                                          action: Gio.SimpleAction,
                                                                                          *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_remove_rows(string: str) -> None:
            operator = 'does not contain'
            expression = polars.col(polars.String).str.contains_any([string], ascii_case_insensitive=True)
            expression = polars.any_horizontal(expression).not_()
            pending_filters = [self._construct_query_builder(operator, string, expression)]

            filter_by = {'operator-name': 'query-builder',
                         'operator-args': pending_filters}

            window = self.get_active_window()
            window.duplicate_sheet(document.document_id,
                                   materialize=True,
                                   filter_by=filter_by)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the string to remove'),
                                                            callback=proceed_to_remove_rows)

    def on_remove_rows_including_case_sensitive_string_into_new_worksheet_action_action(self,
                                                                                        action: Gio.SimpleAction,
                                                                                        *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_remove_rows(string: str) -> None:
            operator = 'does not contain'
            expression = polars.col(polars.String).str.contains_any([string], ascii_case_insensitive=False)
            expression = polars.any_horizontal(expression).not_()
            pending_filters = [self._construct_query_builder(operator, string, expression)]

            filter_by = {'operator-name': 'query-builder',
                         'operator-args': pending_filters}

            window = self.get_active_window()
            window.duplicate_sheet(document.document_id,
                                   materialize=True,
                                   filter_by=filter_by)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the string to remove'),
                                                            callback=proceed_to_remove_rows)

    def on_remove_rows_matching_regex_case_insensitive_string_action(self,
                                                                        action: Gio.SimpleAction,
                                                                        *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_keep_rows(pattern: str) -> None:
            operator = 'does not contain'
            expression = polars.col(polars.String).str.contains(f'(?i){pattern}')
            expression = polars.any_horizontal(expression).not_()
            document.pending_filters = [self._construct_query_builder(operator, pattern, expression)]
            document.filter_current_rows(multiple=True)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the pattern to remove'),
                                                            callback=proceed_to_keep_rows)

    def on_remove_rows_matching_regex_case_sensitive_string_action(self,
                                                                      action: Gio.SimpleAction,
                                                                      *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_keep_rows(pattern: str) -> None:
            operator = 'does not contain'
            expression = polars.col(polars.String).str.contains(pattern)
            expression = polars.any_horizontal(expression).not_()
            document.pending_filters = [self._construct_query_builder(operator, pattern, expression)]
            document.filter_current_rows(multiple=True)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the pattern to remove'),
                                                            callback=proceed_to_keep_rows)

    def on_remove_rows_matching_regex_case_insensitive_string_into_new_worksheet_action_action(self,
                                                                                               action: Gio.SimpleAction,
                                                                                               *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_keep_rows(pattern: str) -> None:
            operator = 'does not contain'
            expression = polars.col(polars.String).str.contains(f'(?i){pattern}')
            expression = polars.any_horizontal(expression).not_()
            pending_filters = [self._construct_query_builder(operator, pattern, expression)]

            filter_by = {'operator-name': 'query-builder',
                         'operator-args': pending_filters}

            window = self.get_active_window()
            window.duplicate_sheet(document.document_id,
                                   materialize=True,
                                   filter_by=filter_by)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the pattern to remove'),
                                                            callback=proceed_to_keep_rows)

    def on_remove_rows_matching_regex_case_sensitive_string_into_new_worksheet_action_action(self,
                                                                                             action: Gio.SimpleAction,
                                                                                             *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_keep_rows(pattern: str) -> None:
            operator = 'does not contain'
            expression = polars.col(polars.String).str.contains(pattern)
            expression = polars.any_horizontal(expression).not_()
            pending_filters = [self._construct_query_builder(operator, pattern, expression)]

            filter_by = {'operator-name': 'query-builder',
                         'operator-args': pending_filters}

            window = self.get_active_window()
            window.duplicate_sheet(document.document_id,
                                   materialize=True,
                                   filter_by=filter_by)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the pattern to remove'),
                                                            callback=proceed_to_keep_rows)

    def on_remove_suffix_from_cell_case_insensitive_action(self,
                                                           action: Gio.SimpleAction,
                                                           *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_remove_suffix(suffix: str) -> None:
            document.update_current_cells_from_operator('remove-suffix-case-insensitive', [suffix], on_column=False)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the suffix for the cells'),
                                                            callback=proceed_to_remove_suffix)

    def on_remove_suffix_from_cell_case_sensitive_action(self,
                                                         action: Gio.SimpleAction,
                                                         *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_remove_suffix(suffix: str) -> None:
            document.update_current_cells_from_operator('remove-suffix-case-sensitive', [suffix], on_column=False)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the suffix for the cells'),
                                                            callback=proceed_to_remove_suffix)

    def on_remove_suffix_from_column_case_insensitive_action(self,
                                                             action: Gio.SimpleAction,
                                                             *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_remove_suffix(suffix: str) -> None:
            document.update_current_cells_from_operator('remove-suffix-case-insensitive', [suffix], on_column=True)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the suffix for the columns'),
                                                            callback=proceed_to_remove_suffix)

    def on_remove_suffix_from_column_case_sensitive_action(self,
                                                           action: Gio.SimpleAction,
                                                           *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_remove_suffix(suffix: str) -> None:
            document.update_current_cells_from_operator('remove-suffix-case-sensitive', [suffix], on_column=True)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the suffix for the columns'),
                                                            callback=proceed_to_remove_suffix)

    def on_replace_cell_text_value_case_insensitive_action(self,
                                                           action: Gio.SimpleAction,
                                                           *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        self._replace_text_value()

    def on_replace_cell_text_value_case_insensitive_with_regex_action(self,
                                                                      action: Gio.SimpleAction,
                                                                      *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        self._replace_text_value(use_regexp=True)

    def on_replace_cell_text_value_case_sensitive_action(self,
                                                         action: Gio.SimpleAction,
                                                         *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        self._replace_text_value(match_case=True)

    def on_replace_cell_text_value_case_sensitive_with_regex_action(self,
                                                                    action: Gio.SimpleAction,
                                                                    *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        self._replace_text_value(match_case=True,
                                 use_regexp=True)

    def on_replace_cell_whitespace_with_a_single_space_action(self,
                                                              action: Gio.SimpleAction,
                                                              *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('replace-whitespace-with-a-single-space', on_column=False)

    def on_replace_cell_whitespace_and_new_lines_with_a_single_space_action(self,
                                                                            action: Gio.SimpleAction,
                                                                            *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('replace-whitespace-and-new-lines-with-a-single-space', on_column=False)

    def on_replace_column_text_value_case_insensitive_action(self,
                                                             action: Gio.SimpleAction,
                                                             *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        self._replace_text_value(column_wise=True)

    def on_replace_column_text_value_case_insensitive_with_regex_action(self,
                                                                        action: Gio.SimpleAction,
                                                                        *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        self._replace_text_value(use_regexp=True,
                                 column_wise=True)

    def on_replace_column_text_value_case_sensitive_action(self,
                                                           action: Gio.SimpleAction,
                                                           *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        self._replace_text_value(match_case=True,
                                 column_wise=True)

    def on_replace_column_text_value_case_sensitive_with_regex_action(self,
                                                                      action: Gio.SimpleAction,
                                                                      *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        self._replace_text_value(match_case=True,
                                 use_regexp=True,
                                 column_wise=True)

    def on_replace_column_whitespace_with_a_single_space_action(self,
                                                                action: Gio.SimpleAction,
                                                                *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_columns_from_operator('replace-whitespace-with-a-single-space', on_column=True)

    def on_replace_column_whitespace_and_new_lines_with_a_single_space_action(self,
                                                                              action: Gio.SimpleAction,
                                                                              *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_columns_from_operator('replace-whitespace-and-new-lines-with-a-single-space', on_column=True)

    def on_reset_all_filters_action(self,
                                    action: Gio.SimpleAction,
                                    *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.reset_all_filters()

    def on_reverse_cell_text_action(self,
                                    action: Gio.SimpleAction,
                                    *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('reverse-text', on_column=False)

    def on_reverse_column_text_action(self,
                                      action: Gio.SimpleAction,
                                      *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('reverse-text', on_column=True)

    def on_save_file_action(self,
                            action: Gio.SimpleAction,
                            *args) -> None:
        window = self.get_active_window()
        self.file_manager.save_file(window)

    def on_save_file_as_action(self,
                               action: Gio.SimpleAction,
                               *args) -> None:
        window = self.get_active_window()
        self.file_manager.save_as_file(window)

    def on_slugify_cells_action(self,
                                action: Gio.SimpleAction,
                                *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('slugify', on_column=False)

    def on_slugify_columns_action(self,
                                  action: Gio.SimpleAction,
                                  *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('slugify', on_column=True)

    def on_sort_by_ascending_action(self,
                                    action: Gio.SimpleAction,
                                    *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.sort_current_rows(descending=False)

    def on_sort_by_descending_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.sort_current_rows(descending=True)

    def on_split_cells_by_comma_into_new_worksheet_action(self,
                                                          action: Gio.SimpleAction,
                                                          *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        dataframe = document.create_table_from_operator('split-by-characters', [','], on_column=False)
        self._create_new_tab(dataframe=dataframe)

    def on_split_cells_by_characters_into_new_worksheet_action(self,
                                                                  action: Gio.SimpleAction,
                                                                  *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_split_by_characters(characters: str) -> None:
            dataframe = document.create_table_from_operator('split-by-characters', [characters], on_column=False)
            self._create_new_tab(dataframe=dataframe)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter a set of characters to split the cells by'),
                                                            callback=proceed_to_split_by_characters)

    def on_split_cells_by_pipe_into_new_worksheet_action(self,
                                                         action: Gio.SimpleAction,
                                                         *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        dataframe = document.create_table_from_operator('split-by-characters', ['|'], on_column=False)
        self._create_new_tab(dataframe=dataframe)

    def on_split_cells_by_semicolon_into_new_worksheet_action(self,
                                                              action: Gio.SimpleAction,
                                                              *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        dataframe = document.create_table_from_operator('split-by-characters', [';'], on_column=False)
        self._create_new_tab(dataframe=dataframe)

    def on_split_cells_by_space_into_new_worksheet_action(self,
                                                          action: Gio.SimpleAction,
                                                          *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        dataframe = document.create_table_from_operator('split-by-characters', [' '], on_column=False)
        self._create_new_tab(dataframe=dataframe)

    def on_split_columns_by_comma_into_new_worksheet_action(self,
                                                            action: Gio.SimpleAction,
                                                            *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        dataframe = document.create_table_from_operator('split-by-characters', [','], on_column=True)
        self._create_new_tab(dataframe=dataframe)

    def on_split_columns_by_characters_into_new_worksheet_action(self,
                                                                    action: Gio.SimpleAction,
                                                                    *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_split_by_characters(characters: str) -> None:
            dataframe = document.create_table_from_operator('split-by-characters', [characters], on_column=True)
            self._create_new_tab(dataframe=dataframe)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter a set of characters to split the columns by'),
                                                            callback=proceed_to_split_by_characters)

    def on_split_columns_by_pipe_into_new_worksheet_action(self,
                                                           action: Gio.SimpleAction,
                                                           *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        dataframe = document.create_table_from_operator('split-by-characters', ['|'], on_column=True)
        self._create_new_tab(dataframe=dataframe)

    def on_split_columns_by_semicolon_into_new_worksheet_action(self,
                                                                action: Gio.SimpleAction,
                                                                *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        dataframe = document.create_table_from_operator('split-by-characters', [';'], on_column=True)
        self._create_new_tab(dataframe=dataframe)

    def on_split_columns_by_space_into_new_worksheet_action(self,
                                                            action: Gio.SimpleAction,
                                                            *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        dataframe = document.create_table_from_operator('split-by-characters', [' '], on_column=True)
        self._create_new_tab(dataframe=dataframe)

    def on_swap_cell_text_case_action(self,
                                      action: Gio.SimpleAction,
                                      *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('swap-text-case', on_column=False)

    def on_swap_column_text_case_action(self,
                                        action: Gio.SimpleAction,
                                        *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('swap-text-case', on_column=True)

    def on_toggle_connection_active(self,
                                    source:    GObject.Object,
                                    cname:     str,
                                    connected: bool) -> None:
        for connection in self.connection_list:
            if connection['cname'] == cname:
                connection['connected'] = connected
                break

        self.on_update_connection_list(source, skip_emitter=True)

    def on_toggle_history_action(self,
                                 action: Gio.SimpleAction,
                                 *args) -> None:
        pass # TODO

    def on_toggle_replace_action(self,
                                 action: Gio.SimpleAction,
                                 *args) -> None:
        window = self.get_active_window()
        window.search_replace_overlay.toggle_replace_section()

    def on_toggle_replace_all_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        window = self.get_active_window()
        tab_view = window.search_replace_all_view
        tab_view.toggle_replace_section()

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

    def on_toggle_sidebar_action(self,
                                 action: Gio.SimpleAction,
                                 *args) -> None:
        window = self.get_active_window()
        window.toggle_sidebar()

    def on_trim_cell_whitespace_action(self,
                                       action: Gio.SimpleAction,
                                       *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('trim-whitespace', on_column=False)

    def on_trim_cell_whitespace_and_remove_new_lines_action(self,
                                                            action: Gio.SimpleAction,
                                                            *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('trim-whitespace-and-remove-new-lines', on_column=False)

    def on_trim_cell_start_whitespace_action(self,
                                             action: Gio.SimpleAction,
                                             *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('trim-start-whitespace', on_column=False)

    def on_trim_cell_end_whitespace_action(self,
                                           action: Gio.SimpleAction,
                                           *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('trim-end-whitespace', on_column=False)

    def on_trim_column_whitespace_action(self,
                                         action: Gio.SimpleAction,
                                         *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('trim-whitespace', on_column=True)

    def on_trim_column_whitespace_and_remove_new_lines_action(self,
                                                              action: Gio.SimpleAction,
                                                              *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('trim-whitespace-and-remove-new-lines', on_column=True)

    def on_trim_column_start_whitespace_action(self,
                                               action: Gio.SimpleAction,
                                               *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('trim-start-whitespace', on_column=True)

    def on_trim_column_end_whitespace_action(self,
                                             action: Gio.SimpleAction,
                                             *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.update_current_cells_from_operator('trim-end-whitespace', on_column=True)

    def on_wrap_cell_with_text_different_action(self,
                                                action: Gio.SimpleAction,
                                                *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        window = self.get_active_window()

        def proceed_to_wrap_text(suffix: str, prefix: str) -> None:
            document.update_current_cells_from_operator('wrap-with-text-different', [prefix, suffix], on_column=False)

        def ask_for_suffix_text(search_pattern: str) -> None:
            window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                                prompt_text=_('Please enter the suffix for the cells'),
                                                                callback=proceed_to_wrap_text,
                                                                user_data=[search_pattern])

        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the prefix for the cells'),
                                                            callback=ask_for_suffix_text,
                                                            more_prompt=True)

    def on_wrap_cell_with_text_same_action(self,
                                           action: Gio.SimpleAction,
                                           *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_wrap_text(prefix: str) -> None:
            document.update_current_cells_from_operator('wrap-with-text-same', [prefix], on_column=False)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the text to wrap the cells with'),
                                                            callback=proceed_to_wrap_text)

    def on_wrap_column_with_text_different_action(self,
                                                  action: Gio.SimpleAction,
                                                  *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        window = self.get_active_window()

        def proceed_to_wrap_text(suffix: str, prefix: str) -> None:
            document.update_current_cells_from_operator('wrap-with-text-different', [prefix, suffix], on_column=True)

        def ask_for_suffix_text(prefix: str) -> None:
            window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                                prompt_text=_('Please enter the suffix for the columns'),
                                                                callback=proceed_to_wrap_text,
                                                                user_data=[prefix])

        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the prefix for the columns'),
                                                            callback=ask_for_suffix_text,
                                                            more_prompt=True)

    def on_wrap_column_with_text_same_action(self,
                                             action: Gio.SimpleAction,
                                             *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return

        def proceed_to_wrap_text(prefix: str) -> None:
            document.update_current_cells_from_operator('wrap-with-text-same', [prefix], on_column=True)

        window = self.get_active_window()
        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the text to wrap the columns with'),
                                                            callback=proceed_to_wrap_text)

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

    def on_unhide_all_columns_action(self,
                                     action: Gio.SimpleAction,
                                     *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.unhide_all_columns()

    def on_unhide_column_action(self,
                                action: Gio.SimpleAction,
                                *args) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.unhide_current_columns()

    def on_unpin_tab_action(self,
                            action: Gio.SimpleAction,
                            *args) -> None:
        window = self.get_active_window()
        document_id = args[0].get_string()
        tab_page = self._get_current_tab_page(window, document_id)
        window.tab_view.set_page_pinned(tab_page, False)

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
                if isinstance(sheet, SheetDocument) \
                        and sheet.data.has_main_dataframe:
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

    def _check_sheet_blanks(self,
                            window:      Window,
                            document_id: str) -> bool:
        sheet_document = window.sheet_manager.get_sheet(document_id)

        undo_stack_is_empty = len(sheet_document.history.undo_stack) <= 1
        redo_stack_is_empty = len(sheet_document.history.redo_stack) == 0

        worksheet_has_no_data = not (isinstance(sheet_document, SheetDocument) and
                                     sheet_document.data.has_main_dataframe)
        notebook_has_no_data = not (isinstance(sheet_document, SheetNotebook) and
                                    len(sheet_document.view.list_items) > 0)

        return undo_stack_is_empty and \
               redo_stack_is_empty and \
               worksheet_has_no_data and \
               notebook_has_no_data

    def _construct_query_builder(self,
                                 operator:   str,
                                 text_value: str,
                                 expression: polars.Expr) -> dict:
        query_builder = {
            'operator': 'and',
            'conditions': [{
                'findex': -1,
                'fdtype': 'undefined',
                'field': '$any',
                'operator': operator,
                'value': text_value,
            }],
        }
        return {
            'qhash': None,
            'qtype': 'primitive',
            'operator': 'and',
            'query-builder': query_builder,
            'expression': expression,
        }

    def _convert_to(self, dtype: polars.DataType) -> None:
        document = self._get_current_active_document()
        if not isinstance(document, SheetDocument):
            return
        document.convert_current_columns_dtype(dtype)

    def _create_new_tab(self,
                        file_path: str = '',
                        dataframe: polars.DataFrame = None) -> bool:
        file = None
        dataframe = dataframe

        if file_path:
            file = Gio.File.new_for_path(file_path)
            dataframe = self.file_manager.read_file(self, file_path)

        # Check for special return values
        if not isinstance(dataframe, polars.DataFrame) \
                and dataframe == 0:
            return False

        window = self.get_active_window()
        window.setup_new_document(file, dataframe)

        return True

    def _create_new_window(self,
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
        if not isinstance(dataframe, polars.DataFrame) \
                and dataframe == 0:
            return None

        window = Window(self.application_commands, application=self)
        window.connect('update-connection-list', self.on_update_connection_list)
        window.connect('toggle-connection-active', self.on_toggle_connection_active)
        window.present()

        if not skip_setup:
            window.setup_new_document(file, dataframe)

        return window

    def _get_current_active_document(self, window: Window = None) -> SheetDocument:
        if window is None:
            window = self.get_active_window()
        return window.get_current_active_document()

    def _get_current_tab_page(self,
                              window:      Window,
                              document_id: str) -> SheetDocument:
        sheet_document = window.sheet_manager.get_sheet(document_id)
        sheet_view = sheet_document.view
        return window.tab_view.get_page(sheet_view)

    def _register_connection(self, connection: duckdb.DuckDBPyConnection) -> list[str]:
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
                if isinstance(sheet, SheetDocument) \
                        and sheet.data.has_main_dataframe:
                    view_name = f'{view_prefix}{sheet.title}'
                    connection.register(view_name, sheet.data.dfs[0])

                    # Register with `self` prefix too for convenience
                    if window is active_window:
                        view_name = f'self:{sheet.title}'
                        connection.register(view_name, sheet.data.dfs[0])

        active_connections = [connection['curl'] for connection in self.connection_list
                                                 if connection['connected']]
        return ';'.join(active_connections)

    def _register_expressions(self) -> None:
        import eruo_strutil as strx

        @polars.api.register_expr_namespace('strx')
        class ExpandedStringExpr:
            def __init__(self, expr: polars.Expr) -> None:
                self._expr = expr

            def pig_latinnify(self) -> polars.Expr:
                return strx.pig_latinnify(self._expr)

            def split_by_chars(self, characters: str) -> polars.Expr:
                return strx.split_by_chars(self._expr, characters)

            def to_sentence_case(self) -> polars.Expr:
                return strx.to_sentence_case(self._expr)

            def to_sponge_case(self) -> polars.Expr:
                return strx.to_sponge_case(self._expr)

    def _replace_text_value(self,
                            match_case:  bool = False,
                            use_regexp:  bool = False,
                            column_wise: bool = False) -> None:
        window = self.get_active_window()

        def proceed_to_replace_value(replace_with: str, search_pattern: str) -> None:
            window = self.get_active_window()
            sheet_document = self._get_current_active_document(window)

            active = sheet_document.selection.current_active_range
            if column_wise:
                from .sheet_selection import SheetCell
                nactive = SheetCell(active.x, active.y, active.column, active.row,
                                    active.width, active.height, active.column_span,
                                    active.row_span, active.metadata,
                                    active.rtl, active.btt)
                nactive.row_span = -1 # select the entire column(s)
            else:
                nactive = active

            sheet_document.selection.current_search_range = nactive
            sheet_document.find_replace_all_in_current_cells(search_pattern,
                                                             replace_with,
                                                             match_case=match_case,
                                                             match_cell=False,
                                                             within_selection=True,
                                                             use_regexp=use_regexp)

            sheet_document.selection.current_search_range = None

        def ask_for_replace_value(search_pattern: str) -> None:
            window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                                prompt_text=_('Please enter the value to replace'),
                                                                callback=proceed_to_replace_value,
                                                                user_data=[search_pattern])

        window.command_palette_overlay.open_command_overlay(as_prompt=True,
                                                            prompt_text=_('Please enter the pattern to find'),
                                                            callback=ask_for_replace_value,
                                                            more_prompt=True)

    def _return_focus_back(self, document: Any = None) -> None:
        if document is None:
            document = self._get_current_active_document()

        if isinstance(document, SheetDocument):
            document.view.main_canvas.set_focusable(True)
            document.view.main_canvas.grab_focus()

        if isinstance(document, SheetNotebook) \
                and len(document.view.list_items) > 0:
            document.view.list_items[0]['source_view'].grab_focus()

    def _reuse_current_window(self, file_path: str = '') -> Any:
        window = self.get_active_window()

        if not window:
            return False

        no_linked_file = window.file is None
        no_opened_sheet = len(window.sheet_manager.sheets) == 0
        history_is_empty = globals.history is None or \
                           (len(globals.history.undo_stack) <= 1 and
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
        if not isinstance(dataframe, polars.DataFrame) \
                and dataframe == 0:
            return True

        window = self.get_active_window()

        # Close the current tab
        tab_page = window.tab_view.get_selected_page()
        if tab_page is not None:
            window.tab_view.close_page(tab_page)

        window.setup_new_document(file, dataframe)

        return window

    def _show_close_tabs_confirmation(self,
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

def main(version):
    """The application's entry point."""
    return Application().run(sys.argv)