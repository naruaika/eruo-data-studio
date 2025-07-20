# search_replace_overlay.py
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


from gi.repository import Adw, Gdk, GLib, Gtk
import polars

from . import globals
from .window import Window

@Gtk.Template(resource_path='/com/macipra/eruo/ui/search-replace-overlay.ui')
class SearchReplaceOverlay(Adw.Bin):
    __gtype_name__ = 'SearchReplaceOverlay'

    search_box = Gtk.Template.Child()

    search_entry = Gtk.Template.Child()
    search_status = Gtk.Template.Child()

    search_options = Gtk.Template.Child()
    search_options_toggler = Gtk.Template.Child()

    search_match_case = Gtk.Template.Child()
    search_match_cell = Gtk.Template.Child()
    search_within_selection = Gtk.Template.Child()
    search_use_regexp = Gtk.Template.Child()

    replace_toggler = Gtk.Template.Child()
    replace_section = Gtk.Template.Child()
    replace_entry = Gtk.Template.Child()
    replace_button = Gtk.Template.Child()
    replace_all_button = Gtk.Template.Child()

    search_results = polars.DataFrame()
    search_results_length: int = 0
    search_cursor_position: int = 1
    search_cursor_coordinate: tuple[int, str] = (0, '')
    search_states: dict = {}

    def __init__(self, window: Window, **kwargs) -> None:
        super().__init__(**kwargs)

        self.window = window

        key_event_controller = Gtk.EventControllerKey()
        key_event_controller.connect('key-pressed', self.on_key_pressed)
        self.add_controller(key_event_controller)

        key_event_controller = Gtk.EventControllerKey()
        key_event_controller.connect('key-pressed', self.on_search_entry_key_pressed)
        self.search_entry.add_controller(key_event_controller)

        key_event_controller = Gtk.EventControllerKey()
        key_event_controller.connect('key-pressed', self.on_replace_entry_key_pressed)
        self.replace_entry.add_controller(key_event_controller)

    def on_key_pressed(self, event: Gtk.EventControllerKey, keyval: int, keycode: int, state: Gdk.ModifierType) -> None:
        if keyval == Gdk.KEY_Escape:
            self.close_search_box()
            return

    def on_search_entry_key_pressed(self, event: Gtk.EventControllerKey, keyval: int, keycode: int, state: Gdk.ModifierType) -> None:
        # Pressing enter/return key while holding shift key will
        # search for the previous search occurrence.
        if keyval == Gdk.KEY_Return and state == Gdk.ModifierType.SHIFT_MASK:
            if self.search_results_length == 0:
                self.on_search_entry_activated(self.search_entry)
                return

            self.find_previous_search_occurrence()
            return

    def on_replace_entry_key_pressed(self, event: Gtk.EventControllerKey, keyval: int, keycode: int, state: Gdk.ModifierType) -> None:
        # Pressing enter/return key while holding shift key will
        # search for the previous search occurrence.
        if keyval == Gdk.KEY_Return and state == (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.ALT_MASK):
            self.on_replace_all_button_clicked(self.replace_all_button)

    @Gtk.Template.Callback()
    def on_search_entry_activated(self, widget: Gtk.Widget) -> None:
        self.search_status.set_visible(True)

        text_value = self.search_entry.get_text()

        match_case = self.search_match_case.get_active()
        match_cell = self.search_match_cell.get_active()
        within_selection = self.search_within_selection.get_active()
        use_regexp = self.search_use_regexp.get_active()

        tab_page = self.window.tab_view.get_selected_page()
        sheet_view = tab_page.get_child()
        sheet_document = sheet_view.document

        # Reset the current search range
        if not within_selection:
            sheet_document.selection.current_search_range = None

        # Initialize the current search range
        elif sheet_document.selection.current_search_range is None:
            sheet_document.selection.current_search_range = sheet_document.selection.current_active_range

        if text_value == '':
            self.search_status.set_text('No results found')
            return # prevent empty search

        new_search_states = self.get_current_search_states()

        # Continue previous search
        if new_search_states == self.search_states and self.search_results_length > 0:
            vheight = sheet_document.view.main_canvas.get_height() - sheet_document.display.column_header_height
            vwidth = sheet_document.view.main_canvas.get_width() - sheet_document.display.row_header_width

            cell_name = sheet_view.document.selection.cell_name
            vcol_index, vrow_index = sheet_document.display.get_cell_position_from_name(cell_name)

            col_index = sheet_view.document.display.get_column_from_vcolumn(vcol_index)
            row_index = sheet_view.document.display.get_row_from_vrow(vrow_index)

            # Try to scroll to the search item first in case the user has scrolled.
            # In addition, we force to continue previous search if the user chose to search within the selection
            # when the user re-opens the search box.
            if not within_selection and sheet_document.display.scroll_to_position(col_index, row_index, vheight, vwidth):
                sheet_document.auto_adjust_scrollbars_by_selection(with_offset=True)
                sheet_document.renderer.render_caches = {}
                sheet_document.view.main_canvas.queue_draw()
                return

            # Go to the next search item
            self.find_next_search_occurrence()

            return

        self.search_states = new_search_states

        # Get the search results
        self.search_results, self.search_results_length = sheet_document.find_in_current_table(text_value,
                                                                                               match_case, match_cell,
                                                                                               within_selection, use_regexp)

        if self.search_results_length == 0:
            self.search_status.set_text('No results found')
            return # prevent empty search

        self.search_status.set_text(f'Showing 1 of {format(self.search_results_length, ',d')}')
        self.search_status.set_visible(True)

        # Set the search cursor to the first item
        first_column_name = self.search_results.columns[0]
        self.search_cursor_coordinate = (0, first_column_name)
        self.search_cursor_position = 0

        # Get the first occurrence of the search item index
        self.find_next_search_occurrence()

    @Gtk.Template.Callback()
    def on_find_all_button_clicked(self, button: Gtk.Button) -> None:
        pass

    @Gtk.Template.Callback()
    def on_find_previous_clicked(self, button: Gtk.Button) -> None:
        if self.get_current_search_states() != self.search_states \
                or self.search_results_length == 0:
            self.on_search_entry_activated(self.search_entry)
            return

        self.find_previous_search_occurrence()

    @Gtk.Template.Callback()
    def on_find_next_clicked(self, button: Gtk.Button) -> None:
        if self.get_current_search_states() != self.search_states \
                or self.search_results_length == 0:
            self.on_search_entry_activated(self.search_entry)
            return

        self.find_next_search_occurrence()

    @Gtk.Template.Callback()
    def on_replace_entry_activated(self, entry: Gtk.Entry) -> None:
        self.replace_current_search_result_item()

    @Gtk.Template.Callback()
    def on_replace_button_clicked(self, button: Gtk.Button) -> None:
        self.replace_current_search_result_item()

    @Gtk.Template.Callback()
    def on_replace_all_button_clicked(self, button: Gtk.Button) -> None:
        self.replace_all_search_occurences()

    @Gtk.Template.Callback()
    def on_search_options_toggled(self, button: Gtk.Button) -> None:
        if button.get_active():
            button.add_css_class('raised')
            self.search_options.set_visible(True)
        else:
            button.remove_css_class('raised')
            self.search_options.set_visible(False)

    @Gtk.Template.Callback()
    def on_search_close_clicked(self, button: Gtk.Button) -> None:
        self.close_search_box()

    def open_search_box(self) -> None:
        if self.get_visible():
            self.search_entry.grab_focus()
            return

        if self.search_results_length == 0:
            self.search_status.set_visible(False)

        self.set_visible(True)

        self.search_box.add_css_class('slide-up-dialog')
        GLib.timeout_add(200, self.search_box.remove_css_class, 'slide-up-dialog')

        # Selects all text on the search entry
        self.search_entry.select_region(0, len(self.search_entry.get_text()))
        self.search_entry.get_first_child().set_focus_on_click(True)
        self.search_entry.get_first_child().grab_focus()

        globals.is_searching_cells = True

        self.search_entry.grab_focus()

    def toggle_replace_section(self) -> None:
        overlay_visible = self.get_visible()
        overlay_in_focus = self.get_focus_child()
        search_entry_in_focus = self.search_entry.get_focus_child()
        replace_section_visible = self.replace_section.get_visible()

        # Open the search overlay
        if not overlay_visible:
            self.set_visible(True)
            self.search_box.add_css_class('slide-up-dialog')
            GLib.timeout_add(200, self.search_box.remove_css_class, 'slide-up-dialog')

            globals.is_searching_cells = True

            if self.search_results_length == 0:
                self.search_status.set_visible(False)

        # In case the user wants to jump between the search and replace entry
        if overlay_visible and replace_section_visible and overlay_in_focus and search_entry_in_focus:
            self.replace_toggler.set_icon_name('go-down-symbolic')
            self.replace_section.set_visible(True)

            # Selects all text on the replace entry
            self.replace_entry.select_region(0, len(self.replace_entry.get_text()))
            self.replace_entry.get_first_child().set_focus_on_click(True)
            self.replace_entry.get_first_child().grab_focus()

            self.replace_entry.grab_focus()

        # Hide the replace section and grab focus on the search entry
        elif overlay_visible and replace_section_visible and overlay_in_focus:
            self.replace_toggler.set_icon_name('go-next-symbolic')
            self.replace_section.set_visible(False)

            self.search_entry.grab_focus()

        # Show and grab focus on the replace entry
        else:
            self.replace_toggler.set_icon_name('go-down-symbolic')
            self.replace_section.set_visible(True)

            # Selects all text on the replace entry
            self.replace_entry.select_region(0, len(self.replace_entry.get_text()))
            self.replace_entry.get_first_child().set_focus_on_click(True)
            self.replace_entry.get_first_child().grab_focus()

            self.replace_entry.grab_focus()

    def close_search_box(self) -> None:
        self.search_box.add_css_class('slide-down-dialog')
        GLib.timeout_add(200, self.set_visible, False)
        GLib.timeout_add(200, self.search_box.remove_css_class, 'slide-down-dialog')

        # Hide the replace section
        self.replace_toggler.set_icon_name('go-next-symbolic')
        self.replace_section.set_visible(False)

        tab_page = self.window.tab_view.get_selected_page()
        sheet_view = tab_page.get_child()

        # Reset the current search range
        sheet_view.document.selection.current_search_range = None

        globals.is_searching_cells = False

        # Focus on the main canvas
        sheet_view.main_canvas.set_focusable(True)
        sheet_view.main_canvas.grab_focus()

    def get_current_search_states(self) -> bool:
        text_value = self.search_entry.get_text()

        match_case = self.search_match_case.get_active()
        match_cell = self.search_match_cell.get_active()
        within_selection = self.search_within_selection.get_active()
        use_regexp = self.search_use_regexp.get_active()

        tab_page = self.window.tab_view.get_selected_page()
        sheet_view = tab_page.get_child()
        sheet_document = sheet_view.document

        # I know right that this is a bit hacky, but it works for now.
        # My mission is to prevent from performing the same search again
        # when nothing has changed.
        search_states = {
            'query': text_value,
            'match_case': match_case,
            'match_cell': match_cell,
            'within_selection': within_selection,
            'use_regexp': use_regexp,

            # TODO: support multiple dataframes?
            'table_id': id(sheet_document.data.dfs[0]),
            'table_rvs_id': id(sheet_document.display.row_visible_series),
            'table_cvs_id': id(sheet_document.display.column_visible_series),
        }

        if within_selection:
            if sheet_document.selection.current_search_range is None:
                sheet_document.selection.current_search_range = sheet_document.selection.current_active_range

            csr_dict = sheet_document.selection.current_search_range.__dict__.copy()
            search_states['selection'] = {
                'column': csr_dict['column'],
                'row': csr_dict['row'],
                'column_span': csr_dict['column_span'],
                'row_span': csr_dict['row_span'],
            }

        return search_states

    def find_previous_search_occurrence(self) -> None:
        # Check if the cursor is at the end of the search results
        cursor_at_first_row = self.search_cursor_coordinate[0] == 0
        cursor_at_first_column = self.search_cursor_coordinate[1] == self.search_results.columns[1]

        # Reset the cursor when hitting the end of the search results
        if cursor_at_first_row and cursor_at_first_column:
            last_column_name = self.search_results.columns[-1]
            self.search_cursor_coordinate = (self.search_results.height - 1, last_column_name)
            self.search_cursor_position = self.search_results_length + 1
            self.find_previous_search_occurrence()
            return

        # Move the cursor to the previous row
        if cursor_at_first_column:
            last_column_name = self.search_results.columns[-1]
            next_row_index = self.search_cursor_coordinate[0] - 1
            self.search_cursor_coordinate = (next_row_index, last_column_name)

        # Move the cursor to previous column
        else:
            current_column_index = self.search_results.columns.index(self.search_cursor_coordinate[1])
            previous_column_name = self.search_results.columns[current_column_index - 1]
            self.search_cursor_coordinate = (self.search_cursor_coordinate[0], previous_column_name)

        # Check if the current cursor position is a search result
        found_search_result_item = self.search_results[self.search_cursor_coordinate[1]][self.search_cursor_coordinate[0]]

        # Continue to search if the current cursor position is not a search result
        if not found_search_result_item:
            self.find_previous_search_occurrence()

        # Update the search states
        else:
            self.search_cursor_position -= 1
            self.show_current_search_result_item()

    def find_next_search_occurrence(self) -> None:
        # Check if the cursor is at the end of the search results
        cursor_at_last_row = self.search_cursor_coordinate[0] == self.search_results.height - 1
        cursor_at_last_column = self.search_cursor_coordinate[1] == self.search_results.columns[-1]

        # Reset the cursor when hitting the end of the search results
        if cursor_at_last_column and cursor_at_last_row:
            first_column_name = self.search_results.columns[0]
            self.search_cursor_coordinate = (0, first_column_name)
            self.search_cursor_position = 0
            self.find_next_search_occurrence()
            return

        # Move the cursor to the next row
        if cursor_at_last_column:
            first_column_name = self.search_results.columns[1]
            next_row_index = self.search_cursor_coordinate[0] + 1
            self.search_cursor_coordinate = (next_row_index, first_column_name)

        # Move the cursor to next column
        else:
            current_column_index = self.search_results.columns.index(self.search_cursor_coordinate[1])
            next_column_name = self.search_results.columns[current_column_index + 1]
            self.search_cursor_coordinate = (self.search_cursor_coordinate[0], next_column_name)

        # Check if the current cursor position is a search result
        found_search_result_item = self.search_results[self.search_cursor_coordinate[1]][self.search_cursor_coordinate[0]]

        # Continue to search if the current cursor position is not a search result
        if not found_search_result_item:
            self.find_next_search_occurrence()

        # Update the search states
        else:
            self.search_cursor_position += 1
            self.show_current_search_result_item()

    def show_current_search_result_item(self) -> None:
        tab_page = self.window.tab_view.get_selected_page()
        sheet_view = tab_page.get_child()
        sheet_document = sheet_view.document

        # TODO: re-adjust the viewport scroll to account the search box

        # TODO: support multiple dataframes?
        vcol_index = sheet_view.document.data.dfs[0].columns.index(self.search_cursor_coordinate[1]) + 1 # +1 for the locator
        vrow_index = self.search_results['$ridx'][self.search_cursor_coordinate[0]] + 2 # +2 for the locator and the header

        col_index = sheet_view.document.display.get_column_from_vcolumn(vcol_index)
        row_index = sheet_view.document.display.get_row_from_vrow(vrow_index)

        search_range = sheet_document.selection.current_search_range

        sheet_view.document.update_selection_from_position(col_index, row_index, col_index, row_index, with_offset=True)

        sheet_document.selection.current_search_range = search_range

        self.search_status.set_text(f'Showing {format(self.search_cursor_position, ',d')} of {format(self.search_results_length, ',d')}')
        self.search_status.set_visible(True)

    def replace_current_search_result_item(self) -> None:
        if self.get_current_search_states() != self.search_states \
                or self.search_results_length == 0:
            self.on_search_entry_activated(self.search_entry)

        if self.search_results_length == 0:
            return

        tab_page = self.window.tab_view.get_selected_page()
        sheet_view = tab_page.get_child()

        sheet_view.document.update_current_cells(self.replace_entry.get_text(),
                                                 self.search_entry.get_text(),
                                                 self.search_match_case.get_active())

        self.find_next_search_occurrence()

        self.search_status.set_text(f'{self.search_status.get_text()} (Out of sync)')

    def replace_all_search_occurences(self) -> None:
        search_pattern = self.search_entry.get_text()
        replace_with = self.replace_entry.get_text()

        match_case = self.search_match_case.get_active()
        match_cell = self.search_match_cell.get_active()
        within_selection = self.search_within_selection.get_active()
        use_regexp = self.search_use_regexp.get_active()

        tab_page = self.window.tab_view.get_selected_page()
        sheet_view = tab_page.get_child()
        sheet_document = sheet_view.document

        # Reset the current search range
        if not within_selection:
            sheet_document.selection.current_search_range = None

        # Initialize the current search range
        elif sheet_document.selection.current_search_range is None:
            sheet_document.selection.current_search_range = sheet_document.selection.current_active_range

        sheet_document.replace_all_in_current_table(search_pattern, replace_with, match_case, match_cell, within_selection, use_regexp)

        self.search_status.set_visible(False)