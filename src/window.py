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


from gi.repository import Adw, Gdk, Gio, GObject, Gtk
import os
import polars
import re

from . import globals
from .sheet_document import SheetDocument
from .sheet_view import SheetView

@Gtk.Template(resource_path='/com/macipra/eruo/ui/window.ui')
class Window(Adw.ApplicationWindow):
    __gtype_name__ = 'Window'

    split_view = Gtk.Template.Child()
    window_title = Gtk.Template.Child()

    toggle_sidebar = Gtk.Template.Child()
    sidebar_tab_view = Gtk.Template.Child()

    toggle_search_all = Gtk.Template.Child()
    toggle_history = Gtk.Template.Child()

    toolbar_tab_view = Gtk.Template.Child()

    name_box = Gtk.Template.Child()
    formula_bar = Gtk.Template.Child()
    formula_bar_dtype = Gtk.Template.Child()

    inline_formula_box = Gtk.Template.Child()
    inline_formula = Gtk.Template.Child()

    toast_overlay = Gtk.Template.Child()
    content_overlay = Gtk.Template.Child()

    tab_view = Gtk.Template.Child()
    tab_bar = Gtk.Template.Child()

    def __init__(self,
                 file:        Gio.File,
                 dataframe:   polars.DataFrame,
                 **kwargs) -> None:
        super().__init__(**kwargs)

        self.file = file

        from .sheet_manager import SheetManager
        self.sheet_manager = SheetManager()

        from .toolbar_home_view import ToolbarHomeView
        self.toolbar_home_view = ToolbarHomeView(self)
        self.toolbar_home_page = self.toolbar_tab_view.append(self.toolbar_home_view)
        self.toolbar_tab_view.set_selected_page(self.toolbar_home_page)

        from .toolbar_insert_view import ToolbarInsertView
        self.toolbar_insert_view = ToolbarInsertView(self)
        self.toolbar_insert_page = self.toolbar_tab_view.append(self.toolbar_insert_view)

        from .toolbar_formulas_view import ToolbarFormulasView
        self.toolbar_formulas_view = ToolbarFormulasView(self)
        self.toolbar_formulas_page = self.toolbar_tab_view.append(self.toolbar_formulas_view)

        from .toolbar_data_view import ToolbarDataView
        self.toolbar_data_view = ToolbarDataView(self)
        self.toolbar_data_page = self.toolbar_tab_view.append(self.toolbar_data_view)

        from .toolbar_view_view import ToolbarViewView
        self.toolbar_view_view = ToolbarViewView(self)
        self.toolbar_view_page = self.toolbar_tab_view.append(self.toolbar_view_view)

        from .search_replace_overlay import SearchReplaceOverlay
        self.search_replace_overlay = SearchReplaceOverlay(self)
        self.content_overlay.add_overlay(self.search_replace_overlay)

        from .sidebar_home_view import SidebarHomeView
        self.sidebar_home_view = SidebarHomeView(self)
        self.sidebar_home_page = self.sidebar_tab_view.append(self.sidebar_home_view)
        self.sidebar_tab_view.set_selected_page(self.sidebar_home_page)

        from .search_replace_all_view import SearchReplaceAllView
        self.search_replace_all_view = SearchReplaceAllView(self)
        self.search_replace_all_page = self.sidebar_tab_view.append(self.search_replace_all_view)

        # We override the default behavior of the Gtk.Entry for the name box,
        # so that it'll select all text when the user clicks on it for the first
        # time in a while (when the widget is currently not in focus, to be precise).
        self.name_box.get_first_child().set_focus_on_click(False)

        # We add some margin to the formula bar to prevent its content from being hidden
        # by the dtype indicator widget.
        self.formula_bar.get_first_child().set_margin_end(45)

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

        self.content_overlay.connect('get-child-position', self.on_content_overlay_get_child_position)

        focus_event_controller = Gtk.EventControllerFocus()
        focus_event_controller.connect('leave', self.on_inline_formula_unfocused)
        self.inline_formula.add_controller(focus_event_controller)

        key_event_controller = Gtk.EventControllerKey()
        key_event_controller.connect('key-pressed', self.on_inline_formula_key_pressed)
        self.inline_formula.add_controller(key_event_controller)

        self.inline_formula.get_buffer().connect('changed', self.on_inline_formula_buffer_changed)

        self.tab_view.connect('notify::selected-page', self.on_selected_page_changed)
        self.tab_view.connect('close-page', self.on_page_closed)

        focus_event_controller = Gtk.EventControllerFocus()
        focus_event_controller.connect('enter', self.on_focus_received)
        self.add_controller(focus_event_controller)

        self.context_menu = None

        # Add a new sheet for the user to start with
        sheet_name = 'Sheet 1'
        if file is not None:
            sheet_name = os.path.basename(file.get_path())
        sheet_view = self.sheet_manager.create_sheet(dataframe, sheet_name)
        self.add_new_tab(sheet_view)

        # Populate the field list
        if file is not None:
            self.sidebar_home_view.repopulate_field_list()

    def get_current_active_view(self) -> SheetView:
        tab_page = self.tab_view.get_selected_page()
        return tab_page.get_child()

    def get_current_active_document(self) -> SheetDocument:
        tab_page = self.tab_view.get_selected_page()
        sheet_view = tab_page.get_child()
        return sheet_view.document

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
        if tab_page is None:
            return
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

    def on_inline_formula_key_pressed(self,
                                      event:   Gtk.EventControllerKey,
                                      keyval:  int,
                                      keycode: int,
                                      state:   Gdk.ModifierType) -> None:
        sheet_view = self.get_current_active_view()

        if keyval == Gdk.KEY_Escape:
            globals.is_editing_cells = False
            self.inline_formula_box.set_visible(False)
            sheet_view.main_canvas.set_focusable(True)
            sheet_view.main_canvas.grab_focus()
            sheet_view.main_canvas.queue_draw()
            return

        if keyval == Gdk.KEY_Return:
            globals.is_editing_cells = False
            self.inline_formula_box.set_visible(False)
            sheet_view.main_canvas.set_focusable(True)
            sheet_view.main_canvas.grab_focus()

            start_iter = self.inline_formula.get_buffer().get_start_iter()
            end_iter = self.inline_formula.get_buffer().get_end_iter()
            text = self.inline_formula.get_buffer().get_text(start_iter, end_iter, True)
            sheet_view.document.update_current_cells(text)

            return

    def on_inline_formula_unfocused(self, event: Gtk.EventControllerFocus) -> None:
        globals.is_editing_cells = False
        self.inline_formula_box.set_visible(False)

        sheet_view = self.get_current_active_view()
        sheet_view.main_canvas.queue_draw()

    def on_inline_formula_buffer_changed(self, buffer):
        self.inline_formula_box.queue_resize()

    def on_content_overlay_get_child_position(self,
                                              overlay:    Gtk.Overlay,
                                              widget:     Gtk.Widget,
                                              allocation: Gdk.Rectangle) -> bool:
        if widget == self.inline_formula_box:
            sheet_view = self.get_current_active_view()
            sheet_document = sheet_view.document

            # I had been trying to make it intelligently resize itself, but sadly I didn't succeed.
            # My PangoCairo calculation is always different than what I perceived on the GtkEntry,
            # even after setting the right font size and some other things. The problem with the
            # current implementation is that it's too big for cells with small sizes and it can be
            # too small for cells with large sizes. Plus, the scroll functionality isn't really
            # working as I expected.
            active_cell = sheet_document.selection.current_active_cell
            cell_width = sheet_document.display.get_cell_width_from_column(active_cell.column)
            cell_height = sheet_document.display.get_cell_height_from_row(active_cell.row)

            new_x = active_cell.x - 1
            new_y = active_cell.y - 1
            new_width = sheet_document.display.DEFAULT_CELL_WIDTH * 3 + 2
            new_height = sheet_document.display.DEFAULT_CELL_HEIGHT * 7 + 2

            if new_width < cell_width:
                new_width = cell_width + 2
            if new_height < cell_height:
                new_height = cell_height + 2

            new_x = max(0, new_x)
            new_y = max(0, new_y)

            if sheet_view.main_canvas.get_width() < new_x + new_width:
                new_x = new_x - new_width + cell_width + 2
            if sheet_view.main_canvas.get_height() < new_y + new_height:
                new_y = new_y - new_height + cell_height + 2

            new_x = min(sheet_view.main_canvas.get_width() - new_width, new_x)
            new_y = min(sheet_view.main_canvas.get_height() - new_height, new_y)

            allocation.x = new_x
            allocation.y = new_y
            allocation.width = new_width
            allocation.height = new_height

            widget.set_size_request(new_width, new_height)

            return True

        return False

    @Gtk.Template.Callback()
    def on_toolbar_tab_button_toggled(self, toggle_button: Gtk.ToggleButton) -> None:
        if toggle_button.get_active():
            tv_name = toggle_button.get_label().lower()
            selected_view = getattr(self, f'toolbar_{tv_name}_page', None)
            if selected_view is not None:
                self.toolbar_tab_view.set_selected_page(selected_view)

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
        sheet_view = self.get_current_active_view()
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
        sheet_view = self.get_current_active_view()
        sheet_view.document.update_current_cells(entry.get_text())
        sheet_view.main_canvas.set_focusable(True)
        sheet_view.main_canvas.grab_focus()

    @Gtk.Template.Callback()
    def on_new_sheet_clicked(self, button: Gtk.Button) -> None:
        sheet_view = self.sheet_manager.create_sheet(None)
        self.add_new_tab(sheet_view)

    def on_name_box_pressed(self,
                            event:   Gtk.GestureClick,
                            n_press: int,
                            x:       float,
                            y:       float) -> None:
        # Selects all text when the user clicks on the name box
        # when it's currently not in focus.
        self.name_box.select_region(0, len(self.name_box.get_text()))
        self.name_box.get_first_child().set_focus_on_click(True)
        self.name_box.get_first_child().grab_focus()

    def on_name_box_unfocused(self, event: Gtk.EventControllerFocus) -> None:
        self.name_box.get_first_child().set_focus_on_click(False)

    def on_name_box_key_pressed(self,
                                event:   Gtk.EventControllerKey,
                                keyval:  int,
                                keycode: int,
                                state:   Gdk.ModifierType) -> None:
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
            sheet_view = self.get_current_active_view()
            sheet_view.main_canvas.set_focusable(True)
            sheet_view.main_canvas.grab_focus()
            return

    def on_formula_bar_key_pressed(self,
                                   event:   Gtk.EventControllerKey,
                                   keyval:  int,
                                   keycode: int,
                                   state:   Gdk.ModifierType) -> None:
        # Pressing escape key will reset the input bar
        # and return the focus to the main canvas back.
        if keyval == Gdk.KEY_Escape:
            self.reset_inputbar()
            sheet_view = self.get_current_active_view()
            sheet_view.main_canvas.set_focusable(True)
            sheet_view.main_canvas.grab_focus()
            return

    def on_selected_page_changed(self,
                                 tab_view: Adw.TabView,
                                 pspec:    GObject.ParamSpec) -> None:
        tab_page = tab_view.get_selected_page()
        if tab_page is None:
            return
        sheet_view = tab_page.get_child()

        # Force the sidebar to update its content based on the current
        # active selection
        sheet_view.document.notify_selected_table_changed(force=True)

        # Update the global references to the current active document
        globals.history = sheet_view.document.history

        # TODO: should be possible to continue the editing session
        # For now, we just reset the flag because we don't want to
        # see visual glitches.
        globals.is_editing_cells = False

        # Reset the input bar to represent the current selection
        self.reset_inputbar()

    def on_page_closed(self,
                       tab_view: Adw.TabView,
                       tab_page: Adw.TabPage) -> None:
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
            self.update_inputbar()
            self.grab_focus()

    def on_selection_changed(self, source: GObject.Object) -> None:
        self.reset_inputbar()

    def on_columns_changed(self,
                           source: GObject.Object,
                           dfi:    int) -> None:
        self.sidebar_home_view.repopulate_field_list(dfi)

    def on_sorts_changed(self,
                         source: GObject.Object,
                         dfi:    int) -> None:
        self.sidebar_home_view.repopulate_sort_list(dfi)

    def on_filters_changed(self,
                           source: GObject.Object,
                           dfi:    int) -> None:
        self.sidebar_home_view.repopulate_filter_list(dfi)

    def on_inline_formula_opened(self,
                                 source:    GObject.Object,
                                 sel_value: str) -> None:
        globals.is_editing_cells = True
        self.inline_formula_box.get_vadjustment().set_value(0)
        self.inline_formula_box.set_visible(True)
        self.inline_formula.get_buffer().set_text(sel_value)
        self.inline_formula.grab_focus()

    def on_context_menu_opened(self,
                               source: GObject.Object,
                               x:      int,
                               y:      int,
                               type:   str) -> None:
        if type == 'header':
            self.open_header_context_menu(x, y)
            return

        if type == 'cell':
            self.open_cell_context_menu(x, y)
            return

    def open_header_context_menu(self,
                                 x: int,
                                 y: int) -> None:
        sheet_document = self.get_current_active_document()

        active_cell = sheet_document.selection.current_active_cell

        column = active_cell.metadata.column

        x = sheet_document.display.get_cell_x_from_point(x + 1)
        y = sheet_document.display.get_cell_y_from_point(y + 1)
        width = sheet_document.display.get_cell_width_from_point(x + 1)
        height = sheet_document.display.get_cell_height_from_point(y + 1)

        from .sheet_header_menu import SheetHeaderMenu

        # Create context menu
        if self.context_menu is not None:
            self.context_menu.unparent()
        self.context_menu = SheetHeaderMenu(self, column)
        self.context_menu.set_parent(self.content_overlay)

        def on_context_menu_closed(widget: Gtk.Widget) -> None:
            sheet_document.focused_widget = None
            sheet_document.view.main_canvas.set_sensitive(True)
            sheet_document.view.main_canvas.set_focusable(True)
            sheet_document.view.main_canvas.grab_focus()
        sheet_document.view.main_canvas.set_sensitive(False)
        self.context_menu.connect('closed', on_context_menu_closed)

        # Position context menu
        rectangle = Gdk.Rectangle()
        rectangle.x = int(x + width / 2)
        rectangle.y = y + height
        rectangle.height = 1
        rectangle.width = 1
        self.context_menu.set_pointing_to(rectangle)

        # Show context menu
        self.context_menu.popup()

    def open_cell_context_menu(self,
                               x: int,
                               y: int) -> None:
        sheet_document = self.get_current_active_document()

        cursor_cell = sheet_document.selection.current_cursor_cell
        active_cell = sheet_document.selection.current_active_cell

        col_1 = sheet_document.display.get_vcolumn_from_column(cursor_cell.column)
        row_1 = sheet_document.display.get_vrow_from_row(cursor_cell.row)
        col_2 = sheet_document.display.get_vcolumn_from_column(active_cell.column)
        row_2 = sheet_document.display.get_vrow_from_row(active_cell.row)

        col_1, col_2 = min(col_1, col_2), max(col_1, col_2)
        row_1, row_2 = min(row_1, row_2), max(row_1, row_2)

        start_column = sheet_document.display.get_column_name_from_column(col_1)
        start_row = str(row_1)
        end_column = sheet_document.display.get_column_name_from_column(col_2)
        end_row = str(row_2)

        column_span = col_2 - col_1 + 1
        row_span = row_2 - row_1 + 1

        ctype = type(sheet_document.selection.current_active_range)

        x = sheet_document.display.get_cell_x_from_point(x + 1)
        y = sheet_document.display.get_cell_y_from_point(y + 1)
        width = sheet_document.display.get_cell_width_from_point(x + 1)
        height = sheet_document.display.get_cell_height_from_point(y + 1)

        from .sheet_cell_menu import SheetCellMenu

        # Create context menu
        if self.context_menu is not None:
            self.context_menu.unparent()
        self.context_menu = SheetCellMenu(start_column,start_row,
                                          end_column,  end_row,
                                          column_span, row_span,
                                          ctype)
        self.context_menu.set_parent(self.content_overlay)

        def on_context_menu_closed(widget: Gtk.Widget) -> None:
            sheet_document.focused_widget = None
            sheet_document.view.main_canvas.set_sensitive(True)
            sheet_document.view.main_canvas.set_focusable(True)
            sheet_document.view.main_canvas.grab_focus()
        sheet_document.view.main_canvas.set_sensitive(False)
        self.context_menu.connect('closed', on_context_menu_closed)

        # Position context menu
        rectangle = Gdk.Rectangle()
        rectangle.x = int(x + width / 2)
        rectangle.y = y + height
        rectangle.height = 1
        rectangle.width = 1
        self.context_menu.set_pointing_to(rectangle)

        # Show context menu
        self.context_menu.popup()

    def add_new_tab(self, sheet_view: SheetView) -> None:
        tab_page = self.tab_view.append(sheet_view)
        tab_page.set_title(sheet_view.document.title)

        # Shrink the tab box size
        # self.tab_bar.get_first_child().get_first_child().get_first_child() \
        #             .get_next_sibling().get_next_sibling().get_first_child() \
        #             .set_halign(Gtk.Align.START)

        # Setup proper handling of signals and bindings
        tab_page.bind_property('title', sheet_view.document, 'title', GObject.BindingFlags.BIDIRECTIONAL)
        sheet_view.document.connect('selection-changed', self.on_selection_changed)
        sheet_view.document.connect('columns-changed', self.on_columns_changed)
        sheet_view.document.connect('sorts-changed', self.on_sorts_changed)
        sheet_view.document.connect('filters-changed', self.on_filters_changed)
        sheet_view.document.connect('open-context-menu', self.on_context_menu_opened)
        sheet_view.document.view.connect('open-inline-formula', self.on_inline_formula_opened)
        sheet_view.document.view.connect('open-context-menu', self.on_context_menu_opened)

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
            self.update_inputbar()
            return

        sheet_document = self.get_current_active_document()

        # Reset the input bar to represent the current selection
        cell_name = sheet_document.selection.cell_name
        cell_data = sheet_document.selection.cell_data
        cell_dtype = sheet_document.selection.cell_dtype
        if cell_data is None:
            cell_data = ''
        cell_data = str(cell_data)
        self.update_inputbar(cell_name, cell_data, cell_dtype)

    def update_inputbar(self,
                        sel_name:  str = '',
                        sel_value: str = '',
                        sel_dtype: str = None) -> None:
        self.name_box.set_text(sel_name)
        self.formula_bar.set_text(sel_value)

        if sel_dtype is not None:
            self.formula_bar_dtype.set_text(sel_dtype)
            self.formula_bar_dtype.set_visible(True)
        else:
            self.formula_bar_dtype.set_visible(False)

    def do_toggle_sidebar(self) -> None:
        sheet_document = self.get_current_active_document()

        # Close the sidebar when it's already open
        if self.toggle_sidebar.get_active():
            self.toggle_sidebar.set_active(False)
            self.split_view.set_collapsed(True)
            sheet_document.selection.current_search_range = None
            sheet_document.is_searching_cells = False
            return

        # Open the sidebar
        self.toggle_sidebar.set_active(True)
        self.split_view.set_collapsed(False)

        selected_page = self.sidebar_tab_view.get_selected_page()

        if selected_page == self.search_replace_all_page:
            sheet_document.is_searching_cells = True

    def show_toast_message(self, message: str) -> None:
        self.toast_overlay.add_toast(Adw.Toast.new(message))