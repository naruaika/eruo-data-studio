# search_replace_overlay.py
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


from gi.repository import Adw, Gdk, GLib, Gtk
import polars

from .sheet_document import SheetDocument
from .window import Window

@Gtk.Template(resource_path='/com/macipra/eruo/ui/search-replace-overlay.ui')
class SearchReplaceOverlay(Adw.Bin):
    __gtype_name__ = 'SearchReplaceOverlay'

    search_overlay = Gtk.Template.Child()

    search_entry = Gtk.Template.Child()
    search_status = Gtk.Template.Child()

    search_options = Gtk.Template.Child()

    search_match_case = Gtk.Template.Child()
    search_match_cell = Gtk.Template.Child()
    search_within_selection = Gtk.Template.Child()
    search_use_regexp = Gtk.Template.Child()

    replace_toggle_button = Gtk.Template.Child()
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

    def on_key_pressed(self,
                       event:   Gtk.EventControllerKey,
                       keyval:  int,
                       keycode: int,
                       state:   Gdk.ModifierType) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.close_search_overlay()
            return False

        return False

    def on_search_entry_key_pressed(self,
                                    event:   Gtk.EventControllerKey,
                                    keyval:  int,
                                    keycode: int,
                                    state:   Gdk.ModifierType) -> bool:
        # Pressing enter/return key while holding shift key will
        # search for the previous search occurrence.
        if keyval == Gdk.KEY_Return and state == Gdk.ModifierType.SHIFT_MASK:
            if self.search_results_length == 0:
                self.on_search_entry_activated(self.search_entry)
                return True

            self.find_previous_search_occurrence()
            return True

        return False

    def on_replace_entry_key_pressed(self,
                                     event:   Gtk.EventControllerKey,
                                     keyval:  int,
                                     keycode: int,
                                     state:   Gdk.ModifierType) -> bool:
        # Pressing enter/return key while holding shift key will
        # search for the previous search occurrence.
        if keyval == Gdk.KEY_Return \
                and state == (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.ALT_MASK):
            self.on_replace_all_button_clicked(self.replace_all_button)
            return True

        return False

    @Gtk.Template.Callback()
    def on_search_entry_activated(self, widget: Gtk.Widget) -> None:
        text_value = self.search_entry.get_text()

        match_case = self.search_match_case.get_active()
        match_cell = self.search_match_cell.get_active()
        within_selection = self.search_within_selection.get_active()
        use_regexp = self.search_use_regexp.get_active()

        sheet_document = self.window.get_current_active_document()

        if isinstance(sheet_document, SheetDocument):
            # Reset the current search range
            if not within_selection:
                sheet_document.selection.current_search_range = None

            # Initialize the current search range
            elif sheet_document.selection.current_search_range is None:
                arange = sheet_document.selection.current_active_range
                sheet_document.selection.current_search_range = arange

        self.search_status.set_visible(True)

        new_search_states = self.get_current_search_states()

        if isinstance(sheet_document, SheetDocument):
            # Continue previous search
            if new_search_states == self.search_states and self.search_results_length > 0:
                vheight = sheet_document.view.main_canvas.get_height() - sheet_document.display.top_locator_height
                vwidth = sheet_document.view.main_canvas.get_width() - sheet_document.display.left_locator_width

                cell_name = sheet_document.selection.cell_name
                vcol_index, vrow_index = sheet_document.display.get_cell_position_from_name(cell_name)

                col_index = sheet_document.display.get_column_from_vcolumn(vcol_index)
                row_index = sheet_document.display.get_row_from_vrow(vrow_index)

                # Try to scroll to the search item first in case the user has scrolled.
                # In addition, we force to continue previous search if the user chose to search within the selection
                # when the user re-opens the search box.
                if not within_selection and sheet_document.display.scroll_to_position(col_index, row_index, vheight, vwidth):
                    sheet_document.auto_adjust_scrollbars_by_selection()
                    sheet_document.renderer.render_caches = {}
                    sheet_document.view.main_canvas.queue_draw()
                    return

                # Go to the next search item
                self.find_next_search_occurrence()

                return

        self.search_states = new_search_states

        # Get the search results
        self.search_results, self.search_results_length = sheet_document.find_in_current_cells(text_value,
                                                                                               match_case,
                                                                                               match_cell,
                                                                                               within_selection,
                                                                                               use_regexp)

        if self.search_results_length == 0:
            self.search_status.set_text('No results found')
            return # prevent empty search

        self.search_status.set_text(f'Showing 1 of {format(self.search_results_length, ',d')} results')
        self.search_status.set_visible(True)

        if isinstance(sheet_document, SheetDocument):
            # Set the search cursor to the first item
            ridx_column_name = self.search_results.columns[0]
            self.search_cursor_coordinate = (0, ridx_column_name)

        self.search_cursor_position = 0

        # Get the first occurrence of the search item index
        self.find_next_search_occurrence()

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
        self.replace_current_search_occurence()

    @Gtk.Template.Callback()
    def on_replace_button_clicked(self, button: Gtk.Button) -> None:
        self.replace_current_search_occurence()

    @Gtk.Template.Callback()
    def on_replace_all_button_clicked(self, button: Gtk.Button) -> None:
        self.replace_all_search_occurences()

    @Gtk.Template.Callback()
    def on_find_all_button_clicked(self, button: Gtk.Button) -> None:
        search_text = self.search_entry.get_text()
        match_case = self.search_match_case.get_active()
        match_cell = self.search_match_cell.get_active()
        within_selection = self.search_within_selection.get_active()
        use_regexp = self.search_use_regexp.get_active()

        self.window.search_replace_all_view.search_entry.set_text(search_text)
        self.window.search_replace_all_view.search_match_case.set_active(match_case)
        self.window.search_replace_all_view.search_match_cell.set_active(match_cell)
        self.window.search_replace_all_view.search_within_selection.set_active(within_selection)
        self.window.search_replace_all_view.search_use_regexp.set_active(use_regexp)

        self.close_search_overlay()

        GLib.timeout_add(200, self.window.search_replace_all_view.open_search_view)

    @Gtk.Template.Callback()
    def on_search_options_toggled(self, button: Gtk.Button) -> None:
        if button.get_active():
            self.search_options.set_visible(True)
        else:
            self.search_options.set_visible(False)

    @Gtk.Template.Callback()
    def on_search_close_clicked(self, button: Gtk.Button) -> None:
        self.close_search_overlay()

    def open_search_overlay(self) -> None:
        if self.get_visible():
            self.search_entry.grab_focus()
            return

        if self.search_results_length == 0:
            self.search_status.set_visible(False)

        self.set_visible(True)

        self.search_overlay.add_css_class('slide-up-dialog')
        GLib.timeout_add(200, self.search_overlay.remove_css_class, 'slide-up-dialog')

        # Selects all text on the search entry
        search_text = self.search_entry.get_text()
        self.search_entry.select_region(0, len(search_text))
        self.search_entry.get_first_child().set_focus_on_click(True)
        self.search_entry.get_first_child().grab_focus()

        sheet_document = self.window.get_current_active_document()
        sheet_document.is_searching_cells = True

        self.search_entry.grab_focus()

    def toggle_replace_section(self) -> None:
        overlay_visible = self.get_visible()
        overlay_in_focus = self.get_focus_child()
        search_entry_in_focus = self.search_entry.get_focus_child()
        replace_section_visible = self.replace_section.get_visible()

        # Open the search overlay
        if not overlay_visible:
            self.open_search_overlay()

        # In case the user wants to jump between the search and replace entry
        if overlay_visible \
                and replace_section_visible \
                and overlay_in_focus \
                and search_entry_in_focus:
            self.replace_toggle_button.set_icon_name('go-down-symbolic')
            self.replace_section.set_visible(True)

            # Selects all text on the replace entry
            replace_text = self.replace_entry.get_text()
            self.replace_entry.select_region(0, len(replace_text))
            self.replace_entry.get_first_child().set_focus_on_click(True)
            self.replace_entry.get_first_child().grab_focus()

            self.replace_entry.grab_focus()

        # Hide the replace section and grab focus on the search entry
        elif overlay_visible and replace_section_visible and overlay_in_focus:
            self.replace_toggle_button.set_icon_name('go-next-symbolic')
            self.replace_section.set_visible(False)

            self.search_entry.grab_focus()

        # Show and grab focus on the replace entry
        else:
            self.replace_toggle_button.set_icon_name('go-down-symbolic')
            self.replace_section.set_visible(True)

            # Selects all text on the replace entry
            replace_text = self.replace_entry.get_text()
            self.replace_entry.select_region(0, len(replace_text))
            self.replace_entry.get_first_child().set_focus_on_click(True)
            self.replace_entry.get_first_child().grab_focus()

            self.replace_entry.grab_focus()

    def close_search_overlay(self) -> None:
        self.search_overlay.add_css_class('slide-down-dialog')
        GLib.timeout_add(200, self.set_visible, False)
        GLib.timeout_add(200, self.search_overlay.remove_css_class, 'slide-down-dialog')

        # Hide the replace section
        self.replace_toggle_button.set_icon_name('go-next-symbolic')
        self.replace_section.set_visible(False)

        sheet_view = self.window.get_current_active_view()

        if sheet_view is None:
            return

        # Focus on the main canvas
        if isinstance(sheet_view.document, SheetDocument):
            sheet_view.main_canvas.set_focusable(True)
            sheet_view.main_canvas.grab_focus()

        # Reset the search states
        if isinstance(sheet_view.document, SheetDocument):
            sheet_view.document.selection.current_search_range = None
        if self.search_within_selection.get_active():
            sheet_view.document.search_range_performer = ''
        sheet_view.document.is_searching_cells = False

    def get_current_search_states(self) -> bool:
        text_value = self.search_entry.get_text()

        match_case = self.search_match_case.get_active()
        match_cell = self.search_match_cell.get_active()
        within_selection = self.search_within_selection.get_active()
        use_regexp = self.search_use_regexp.get_active()

        sheet_document = self.window.get_current_active_document()

        # I know right that this is a bit hacky, but it works for now.
        # My mission is to prevent from performing the same search again
        # when nothing has changed.
        search_states = {
            'query': text_value,
            'match_case': match_case,
            'match_cell': match_cell,
            'within_selection': within_selection,
            'use_regexp': use_regexp,
        }

        if isinstance(sheet_document, SheetDocument):
            # TODO: support multiple dataframes?
            search_states['table_id'] = id(sheet_document.data.dfs[0]),
            search_states['table_rvs_id'] = id(sheet_document.display.row_visible_series),
            search_states['table_cvs_id'] = id(sheet_document.display.column_visible_series),

            if within_selection:
                if sheet_document.selection.current_search_range is None:
                    arange = sheet_document.selection.current_active_range
                    sheet_document.selection.current_search_range = arange

                csr_dict = sheet_document.selection.current_search_range.__dict__.copy()
                search_states['selection'] = {
                    'column': csr_dict['column'],
                    'row': csr_dict['row'],
                    'column_span': csr_dict['column_span'],
                    'row_span': csr_dict['row_span'],
                }

        return search_states

    def find_previous_search_occurrence(self) -> None:
        row_index, column_name = self.search_cursor_coordinate

        # Check if the cursor is at the end of the search results
        cursor_at_first_row = row_index == 0
        cursor_at_first_column = column_name == self.search_results.columns[1]

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
            next_row_index = row_index - 1
            self.search_cursor_coordinate = (next_row_index, last_column_name)

        # Move the cursor to previous column
        else:
            current_column_index = self.search_results.columns.index(column_name)
            previous_column_name = self.search_results.columns[current_column_index - 1]
            self.search_cursor_coordinate = (row_index, previous_column_name)

        # Check if the current cursor position is a search result
        row_index, column_name = self.search_cursor_coordinate
        found_search_result_item = self.search_results[column_name][row_index]

        # Update the search states
        if found_search_result_item is True:
            self.search_cursor_position -= 1
            self.show_current_search_result_item()

        # Continue to search if the current cursor position is not a search result
        else:
            self.find_previous_search_occurrence()

    def find_next_search_occurrence(self) -> None:
        row_index, column_name = self.search_cursor_coordinate

        # Check if the cursor is at the end of the search results
        cursor_at_last_row = row_index == self.search_results.height - 1
        cursor_at_last_column = column_name == self.search_results.columns[-1]

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
            next_row_index = row_index + 1
            self.search_cursor_coordinate = (next_row_index, first_column_name)

        # Move the cursor to next column
        else:
            current_column_index = self.search_results.columns.index(column_name)
            next_column_name = self.search_results.columns[current_column_index + 1]
            self.search_cursor_coordinate = (row_index, next_column_name)

        # Check if the current cursor position is a search result
        row_index, column_name = self.search_cursor_coordinate
        found_search_result_item = self.search_results[column_name][row_index]

        # Update the search states
        if found_search_result_item is True:
            self.search_cursor_position += 1
            self.show_current_search_result_item()

        # Continue to search if the current cursor position is not a search result
        else:
            self.find_next_search_occurrence()

    def show_current_search_result_item(self) -> None:
        sheet_document = self.window.get_current_active_document()

        row_index, column_name = self.search_cursor_coordinate

        if isinstance(sheet_document, SheetDocument):
            # TODO: support multiple dataframes?
            col_index = sheet_document.data.dfs[0].columns.index(column_name) + 1 # +1 for the $ridx column
            row_index = self.search_results['$ridx'][row_index] + 2 # +2 for the locator and the header
            cname = sheet_document.display.get_cell_name_from_position(col_index, row_index)

            search_range = sheet_document.selection.current_search_range

            sheet_document.update_selection_from_name(cname)

            column = sheet_document.selection.current_active_cell.column
            row = sheet_document.selection.current_active_cell.row
            viewport_height = sheet_document.view.main_canvas.get_height() - sheet_document.display.top_locator_height
            viewport_width = sheet_document.view.main_canvas.get_width() - sheet_document.display.left_locator_width

            # Scroll to account for the search box if necessary
            if 'bottom' in sheet_document.display.check_cell_position_near_edges(column, row, viewport_height, viewport_width):
                offset_size = self.get_height() + self.get_margin_bottom() + sheet_document.display.DEFAULT_CELL_HEIGHT
                sheet_document.display.scroll_y_position += offset_size
                cname = sheet_document.display.get_cell_name_from_position(col_index, row_index)
                sheet_document.update_selection_from_name(cname)

            sheet_document.selection.current_search_range = search_range

            sheet_document.renderer.render_caches = {}
            sheet_document.view.main_canvas.queue_draw()

        self.search_status.set_text(f'Showing {format(self.search_cursor_position, ',d')} of '
                                    f'{format(self.search_results_length, ',d')} results')
        self.search_status.set_visible(True)

        if self.search_within_selection.get_active():
            sheet_document.search_range_performer = 'quick-search'

    def replace_current_search_occurence(self) -> None:
        if self.get_current_search_states() != self.search_states \
                or self.search_results_length == 0:
            self.on_search_entry_activated(self.search_entry)
            return

        if self.search_results_length == 0:
            return

        replace_with = self.replace_entry.get_text()
        search_pattern = self.search_entry.get_text()
        match_case = self.search_match_case.get_active()

        sheet_document = self.window.get_current_active_document()
        sheet_document.find_replace_in_current_cells(replace_with, search_pattern, match_case)

        self.find_next_search_occurrence()

        self.search_status.set_text(f'{self.search_status.get_text()} (Out of sync)')

    def replace_all_search_occurences(self) -> None:
        search_pattern = self.search_entry.get_text()
        replace_with = self.replace_entry.get_text()

        match_case = self.search_match_case.get_active()
        match_cell = self.search_match_cell.get_active()
        within_selection = self.search_within_selection.get_active()
        use_regexp = self.search_use_regexp.get_active()

        sheet_document = self.window.get_current_active_document()

        if isinstance(sheet_document, SheetDocument):
            # Reset the current search range
            if not within_selection:
                sheet_document.selection.current_search_range = None

            # Initialize the current search range
            elif sheet_document.selection.current_search_range is None:
                arange = sheet_document.selection.current_active_range
                sheet_document.selection.current_search_range = arange

        sheet_document.find_replace_all_in_current_cells(search_pattern,
                                                         replace_with,
                                                         match_case,
                                                         match_cell,
                                                         within_selection,
                                                         use_regexp)

        self.search_status.set_visible(False)