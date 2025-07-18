# window.py
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


from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk
import os
import polars
import re

from . import globals
from .sheet_view import SheetView

@Gtk.Template(resource_path='/com/macipra/eruo/ui/window.ui')
class Window(Adw.ApplicationWindow):
    __gtype_name__ = 'Window'

    split_view = Gtk.Template.Child()
    toggle_sidebar = Gtk.Template.Child()
    window_title = Gtk.Template.Child()

    toggle_search = Gtk.Template.Child()
    toggle_history = Gtk.Template.Child()

    search_overlay = Gtk.Template.Child()
    search_box = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    search_status = Gtk.Template.Child()
    search_navigation = Gtk.Template.Child()
    search_options = Gtk.Template.Child()
    search_options_toggler = Gtk.Template.Child()

    search_match_case = Gtk.Template.Child()
    search_match_cell = Gtk.Template.Child()
    search_within_selection = Gtk.Template.Child()
    search_use_regexp = Gtk.Template.Child()

    name_box = Gtk.Template.Child()
    formula_bar = Gtk.Template.Child()

    toast_overlay = Gtk.Template.Child()
    tab_view = Gtk.Template.Child()
    tab_bar = Gtk.Template.Child()

    search_results = polars.DataFrame()
    search_results_length: int = 0
    search_cursor_position: int = 1
    search_cursor_coordinate: tuple[int, str] = (0, '')
    search_states: dict = {}

    def __init__(self, file: Gio.File, dataframe: polars.DataFrame, **kwargs) -> None:
        super().__init__(**kwargs)

        self.file = file

        from .sheet_manager import SheetManager
        self.sheet_manager = SheetManager()

        key_event_controller = Gtk.EventControllerKey()
        key_event_controller.connect('key-pressed', self.on_search_overlay_key_pressed)
        self.search_overlay.add_controller(key_event_controller)

        key_event_controller = Gtk.EventControllerKey()
        key_event_controller.connect('key-pressed', self.on_search_entry_key_pressed)
        self.search_entry.add_controller(key_event_controller)

        # We override the default behavior of the Gtk.Entry for the name box,
        # so that it'll select all text when the user clicks on it for the first
        # time in a while (when the widget is currently not in focus, to be precise).
        self.name_box.get_first_child().set_focus_on_click(False)

        click_event_controller = Gtk.GestureClick()
        click_event_controller.connect('pressed', self.on_name_box_pressed)
        self.name_box.add_controller(click_event_controller)

        focus_event_controller = Gtk.EventControllerFocus()
        focus_event_controller.connect('leave', self.on_name_box_unfocused)
        self.name_box.add_controller(focus_event_controller)

        key_event_controller = Gtk.EventControllerKey()
        key_event_controller.connect('key-pressed', self.on_name_box_key_pressed)
        self.name_box.add_controller(key_event_controller)

        key_event_controller = Gtk.EventControllerKey()
        key_event_controller.connect('key-pressed', self.on_formula_bar_key_pressed)
        self.formula_bar.add_controller(key_event_controller)

        self.tab_view.connect('notify::selected-page', self.on_selected_page_changed)
        self.tab_view.connect('close-page', self.on_page_closed)

        focus_event_controller = Gtk.EventControllerFocus()
        focus_event_controller.connect('enter', self.on_focus_received)
        self.add_controller(focus_event_controller)

        # Add a new sheet for the user to start with
        sheet_name = 'Sheet 1'
        if file is not None:
            sheet_name = os.path.basename(file.get_path())
        sheet_view = self.sheet_manager.create_sheet(dataframe, sheet_name)
        self.add_new_tab(sheet_view)

    def do_focus(self, direction: Gtk.DirectionType) -> bool:
        # When focusing on the main canvas, pressing tab key
        # will keep the focus on the main canvas.
        tab_page = self.tab_view.get_selected_page()
        if tab_page is not None:
            sheet_view = tab_page.get_child()
            if sheet_view.main_canvas.has_focus():
                return False

        # Otherwise, let the default behavior happen. Usually,
        # cycling focus between widgets, excluding the main canvas,
        # because the main canvas shouldn't receive the focus when
        # the user leaves it (clicking on another widget).
        return Gtk.Window.do_focus(self, direction)

    def on_focus_received(self, event: Gtk.EventControllerFocus) -> None:
        tab_page = self.tab_view.get_selected_page()
        sheet_view = tab_page.get_child()

        # We use a global state to reference to the current history
        # manager and some other things too. This may be an indication
        # of the wrong design, but I can't think of a better way. What we
        # do here is to reset any window-related references anytime the focus
        # is received. Performing for example an undo operation will only
        # affect the currently focused sheet. Gtk does have signals and slots
        # mechanisms, but in my personal experience, it's not easy to manage
        # them especially for a very depth nested hierarchy; often times they
        # can be hard to track and debug. Gtk also has the property binding
        # for different use cases. TODO: is there any better/safer way?
        globals.history = sheet_view.document.history

        # I'd prefer that we can also have system-level notification for any
        # background operations. I assume this approach will show notifications
        # from other windows on the current active window which can be misleading
        # for the user. We can add a verification to avoid that though.
        globals.send_notification = self.show_toast_message

    def on_search_overlay_key_pressed(self, event: Gtk.EventControllerKey, keyval: int, keycode: int, state: Gdk.ModifierType) -> None:
        if keyval == Gdk.KEY_Escape:
            self.close_search_box()
            return

    def on_search_entry_key_pressed(self, event: Gtk.EventControllerKey, keyval: int, keycode: int, state: Gdk.ModifierType) -> None:
        if keyval == Gdk.KEY_Escape:
            self.close_search_box()
            return

    @Gtk.Template.Callback()
    def on_search_entry_activated(self, widget: Gtk.Widget) -> None:
        self.search_entry.set_size_request(-1, -1)
        self.search_navigation.set_visible(True)
        self.search_status.set_visible(True)

        if not self.search_options_toggler.get_active():
            self.search_options.set_visible(False)

        self.search_overlay.remove_css_class('floating-sheet')
        self.search_overlay.set_valign(Gtk.Align.END)
        self.search_overlay.set_halign(Gtk.Align.CENTER)
        self.search_overlay.set_margin_bottom(80)

        self.search_box.remove_css_class('big-search-box')
        self.search_box.add_css_class('slide-up-dialog')

        text_value = widget.get_text()

        match_case = self.search_match_case.get_active()
        match_cell = self.search_match_cell.get_active()
        within_selection = self.search_within_selection.get_active()
        use_regexp = self.search_use_regexp.get_active()

        tab_page = self.tab_view.get_selected_page()
        sheet_view = tab_page.get_child()
        sheet_document = sheet_view.document

        # Reset the current search range
        if not within_selection:
            sheet_document.selection.current_search_range = None

        # Initialize the current search range
        elif sheet_document.selection.current_search_range is None:
            sheet_document.selection.current_search_range = sheet_document.selection.current_active_range

        if text_value == '':
            self.search_status.set_text('Showing 0 of 0')
            return # prevent empty search

        # I know right that this is a bit hacky, but it works for now.
        # My mission is to prevent from performing the same search again
        # when nothing has changed.
        new_search_states = {
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
            csr_dict = sheet_document.selection.current_search_range.__dict__.copy()
            new_search_states['selection'] = {
                'column': csr_dict['column'],
                'row': csr_dict['row'],
                'column_span': csr_dict['column_span'],
                'row_span': csr_dict['row_span'],
            }

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
                sheet_document.auto_adjust_scrollbars_by_selection()
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
            self.search_status.set_text('Showing 0 of 0')
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
    def on_find_previous_clicked(self, button: Gtk.Button) -> None:
        self.find_previous_search_occurrence()

    @Gtk.Template.Callback()
    def on_find_next_clicked(self, button: Gtk.Button) -> None:
        self.find_next_search_occurrence()

    @Gtk.Template.Callback()
    def on_search_close_clicked(self, button: Gtk.Button) -> None:
        self.close_search_box()

    @Gtk.Template.Callback()
    def on_search_options_toggled(self, button: Gtk.Button) -> None:
        if button.get_active():
            button.add_css_class('raised')
            self.search_options.set_visible(True)
        else:
            button.remove_css_class('raised')
            self.search_options.set_visible(False)

    @Gtk.Template.Callback()
    def on_name_box_activated(self, widget: Gtk.Widget) -> None:
        # Normalize the input
        input_text = widget.get_text().strip()
        input_text = input_text.replace(';', ':')
        if input_text in ['', ':']:
            input_text = 'A1'
        if input_text.startswith(':'):
            input_text = input_text[1:]
            input_text = f'{input_text}:{input_text}'
        if input_text.endswith(':'):
            input_text = input_text[:-1]
            input_text = f'{input_text}:{input_text}'

        # Basic check if the input is a valid cell name.
        # Here we accept a wide range of cell name patterns and some
        # non-standard ones that I think will be of use somehow, e.g.
        # "A:1" (any letter:any number) to select the whole sheet.
        # Well, it's not supposed to be useful, maybe I only wanted to
        # be a bit playful or just being lazy :)
        single_part_pattern = r"[A-Za-z]*\d*|[A-Za-z]*\d*"
        full_range_pattern = fr"{single_part_pattern}(?:[:]{single_part_pattern})?"
        if not re.fullmatch(full_range_pattern, input_text, re.IGNORECASE):
            self.reset_inputbar()
            return

        # Activating (pressing enter/return key) the name box will update
        # the selection accordingly and move the focus back to the main canvas.
        tab_page = self.tab_view.get_selected_page()
        sheet_view = tab_page.get_child()
        sheet_view.document.update_selection_from_name(input_text)
        sheet_view.main_canvas.set_focusable(True)
        sheet_view.main_canvas.grab_focus()

    @Gtk.Template.Callback()
    def on_formula_bar_activated(self, entry: Gtk.Entry) -> None:
        # It requests the sheet document to update the current selected cells
        # with the user input and move the focus back to the main canvas. But
        # we still miss to tell the user when the update isn't successful.
        # Looking at other applications, it should always commit the update,
        # but make the cells appear in some way e.g. "######" whenever there's
        # an error or something that the user should do in response.
        tab_page = self.tab_view.get_selected_page()
        sheet_view = tab_page.get_child()
        sheet_view.document.update_current_cells(entry.get_text())
        sheet_view.main_canvas.set_focusable(True)
        sheet_view.main_canvas.grab_focus()

    @Gtk.Template.Callback()
    def on_new_sheet_clicked(self, button: Gtk.Button) -> None:
        sheet_view = self.sheet_manager.create_sheet(None)
        self.add_new_tab(sheet_view)

    def on_name_box_pressed(self, event: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        # Selects all text when the user clicks on the name box
        # when it's currently not in focus.
        self.name_box.select_region(0, len(self.name_box.get_text()))
        self.name_box.get_first_child().set_focus_on_click(True)
        self.name_box.get_first_child().grab_focus()

    def on_name_box_unfocused(self, event: Gtk.EventControllerFocus) -> None:
        self.name_box.get_first_child().set_focus_on_click(False)

    def on_name_box_key_pressed(self, event: Gtk.EventControllerKey, keyval: int, keycode: int, state: Gdk.ModifierType) -> None:
        # Pressing tab key will reset the input bar instead of activating
        # the input bar to prevent undesired behavior. I've seen other
        # applications don't do this, but I prefer this for consistency.
        if keyval == Gdk.KEY_Tab:
            self.reset_inputbar()
            return

        # Pressing escape key will reset the input bar and
        # return the focus to the main canvas back.
        if keyval == Gdk.KEY_Escape:
            self.reset_inputbar()
            tab_page = self.tab_view.get_selected_page()
            sheet_view = tab_page.get_child()
            sheet_view.main_canvas.set_focusable(True)
            sheet_view.main_canvas.grab_focus()
            return

    def on_formula_bar_key_pressed(self, event: Gtk.EventControllerKey, keyval: int, keycode: int, state: Gdk.ModifierType) -> None:
        # Pressing escape key will reset the input bar and
        # return the focus to the main canvas back.
        if keyval == Gdk.KEY_Escape:
            self.reset_inputbar()
            tab_page = self.tab_view.get_selected_page()
            sheet_view = tab_page.get_child()
            sheet_view.main_canvas.set_focusable(True)
            sheet_view.main_canvas.grab_focus()
            return

    def on_selected_page_changed(self, tab_view: Adw.TabView, pspec: GObject.ParamSpec) -> None:
        tab_page = tab_view.get_selected_page()
        if tab_page is None:
            return
        sheet_view = tab_page.get_child()

        # Update the global references to the current active document
        globals.history = sheet_view.document.history

        # TODO: should be possible to continue the editing session
        # For now, we just reset the flag because we don't want to
        # see visual glitches.
        globals.is_editing_cells = False

        # Reset the input bar to represent the current selection
        self.reset_inputbar()

    def on_page_closed(self, tab_view: Adw.TabView, tab_page: Adw.TabPage) -> None:
        sheet_view = tab_page.get_child()

        # Clean up the history, mainly to free up disk space
        # from the temporary files created for undo/redo operations.
        sheet_view.document.history.cleanup_all()

        self.sheet_manager.delete_sheet(sheet_view)

        # Disable the input bar when no sheet is open
        # just to add more emphasize.
        if len(self.sheet_manager.sheets) == 0:
            self.name_box.set_sensitive(False)
            self.formula_bar.set_sensitive(False)
            self.update_inputbar('', '')
            self.grab_focus()

    def on_selection_changed(self, source: GObject.Object, sel_name: str, sel_value: str) -> None:
        self.update_inputbar(sel_name, sel_value)

    def add_new_tab(self, sheet_view: SheetView) -> None:
        tab_page = self.tab_view.append(sheet_view)
        tab_page.set_title(sheet_view.document.title)

        # Setup proper handling of signals and bindings
        tab_page.bind_property('title', sheet_view.document, 'title', GObject.BindingFlags.BIDIRECTIONAL)
        sheet_view.document.connect('selection-changed', self.on_selection_changed)

        # Switch to the new tab automatically
        self.tab_view.set_selected_page(tab_page)

        # Reset the focus and input bar
        sheet_view.main_canvas.set_focusable(True)
        sheet_view.main_canvas.grab_focus()
        self.name_box.set_sensitive(True)
        self.formula_bar.set_sensitive(True)

    def reset_inputbar(self) -> None:
        tab_page = self.tab_view.get_selected_page()

        # Empty the input bar when no sheet is open
        if tab_page is None:
            self.update_inputbar('', '')
            return

        # Reset the input bar to represent the current selection
        sheet_view = tab_page.get_child()
        cell_name = sheet_view.document.selection.cell_name
        cell_data = sheet_view.document.selection.cell_data
        if cell_data is None:
            cell_data = ''
        cell_data = str(cell_data)
        self.update_inputbar(cell_name, cell_data)

    def update_inputbar(self, sel_name: str, sel_value: str) -> None:
        self.name_box.set_text(sel_name)
        self.formula_bar.set_text(sel_value)

    def close_search_box(self) -> None:
        # Close the search box
        self.search_box.remove_css_class('zoom-in-dialog')
        if 'slide-up-dialog' in self.search_box.get_css_classes():
            self.search_box.remove_css_class('slide-up-dialog')
            self.search_box.add_css_class('slide-down-dialog')
            GLib.timeout_add(200, self.search_overlay.set_visible, False)
        else:
            self.search_overlay.set_visible(False)

        tab_page = self.tab_view.get_selected_page()
        sheet_view = tab_page.get_child()

        # Reset the current search range
        sheet_view.document.selection.current_search_range = None

        # Focus on the main canvas
        sheet_view.main_canvas.set_focusable(True)
        sheet_view.main_canvas.grab_focus()

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
        tab_page = self.tab_view.get_selected_page()
        sheet_view = tab_page.get_child()

        # TODO: re-adjust the viewport scroll to account the search box

        # TODO: support multiple dataframes?
        vcol_index = sheet_view.document.data.dfs[0].columns.index(self.search_cursor_coordinate[1]) + 1 # +1 for the locator
        vrow_index = self.search_results['$ridx'][self.search_cursor_coordinate[0]] + 2 # +2 for the locator and the header

        col_index = sheet_view.document.display.get_column_from_vcolumn(vcol_index)
        row_index = sheet_view.document.display.get_row_from_vrow(vrow_index)

        sheet_view.document.update_selection_from_position(col_index, row_index, col_index, row_index)
        self.search_status.set_text(f'Showing {format(self.search_cursor_position, ',d')} of {format(self.search_results_length, ',d')}')

    def show_toast_message(self, message: str) -> None:
        self.toast_overlay.add_toast(Adw.Toast.new(message))