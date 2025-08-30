# window.py
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


from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk
import duckdb
import os
import polars
import re
import threading

from . import globals
from .sheet_data import SheetCellBoundingBox
from .sheet_document import SheetDocument
from .sheet_notebook import SheetNotebook
from .sheet_functions import register_sql_functions
from .sheet_notebook_view import SheetNotebookView
from .sheet_view import SheetView

@Gtk.Template(resource_path='/com/macipra/eruo/ui/window.ui')
class Window(Adw.ApplicationWindow):
    __gtype_name__ = 'Window'

    __gsignals__ = {
        'update-connection-list'   : (GObject.SIGNAL_RUN_FIRST, None, ()),
        'toggle-connection-active' : (GObject.SIGNAL_RUN_FIRST, None, (str, bool)),
    }

    root_overlay = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    content_overlay = Gtk.Template.Child()

    split_view = Gtk.Template.Child()
    window_title = Gtk.Template.Child()

    sidebar_toggle_button = Gtk.Template.Child()

    sidebar_tab_view = Gtk.Template.Child()

    search_all_toggle_button = Gtk.Template.Child()
    history_toggle_button = Gtk.Template.Child()

    toolbar_tab_view = Gtk.Template.Child()
    toolbar_tab_bar = Gtk.Template.Child()

    home_toggle_button = Gtk.Template.Child()
    insert_toggle_button = Gtk.Template.Child()
    formulas_toggle_button = Gtk.Template.Child()
    data_toggle_button = Gtk.Template.Child()
    view_toggle_button = Gtk.Template.Child()

    name_formula_box = Gtk.Template.Child()
    name_box = Gtk.Template.Child()
    formula_bar = Gtk.Template.Child()
    formula_bar_dtype = Gtk.Template.Child()

    multiline_formula_bar_box = Gtk.Template.Child()
    multiline_formula_bar = Gtk.Template.Child()
    formula_bar_toggle_button = Gtk.Template.Child()

    inline_formula_box = Gtk.Template.Child()
    inline_formula = Gtk.Template.Child()

    tab_view = Gtk.Template.Child()
    tab_bar = Gtk.Template.Child()

    def __init__(self,
                 commands: list[dict],
                 **kwargs) -> None:
        super().__init__(**kwargs)

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

        self.toolbar_buttons = [
            self.home_toggle_button,
            self.insert_toggle_button,
            self.formulas_toggle_button,
            self.data_toggle_button,
            self.view_toggle_button,
        ]

        from .command_palette_overlay import CommandPaletteOverlay
        self.command_palette_overlay = CommandPaletteOverlay(self, commands)
        self.root_overlay.add_overlay(self.command_palette_overlay)

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

        # Removing the tab view shortcuts from the toolbar and the siderbar so that we can get them
        # to work on the content tab view instead
        self.toolbar_tab_view.remove_shortcuts(Adw.TabViewShortcuts.ALL_SHORTCUTS)
        self.sidebar_tab_view.remove_shortcuts(Adw.TabViewShortcuts.ALL_SHORTCUTS)

        self.tab_view.set_menu_model(Gio.Menu())
        self.tab_view.connect('setup-menu', self.setup_tab_menu)

        # Early instantiate the list items pool
        def instantiate_list_items_pool() -> None:
            from . import sheet_header_menu
            from . import search_replace_all_view
        threading.Thread(target=instantiate_list_items_pool).start()

        # We override the default behavior of the Gtk.Entry for the name box,
        # so that it'll select all text when the user clicks on it for the first
        # time in a while (when the widget is currently not in focus, to be precise).
        self.name_box.get_first_child().set_focus_on_click(False)

        # We add some margin to the formula bar to prevent its content from being hidden
        # by the dtype indicator widget.
        self.formula_bar.get_first_child().set_margin_end(40)

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

        key_event_controller = Gtk.EventControllerKey()
        key_event_controller.connect('key-pressed', self.on_multiline_formula_bar_key_pressed)
        self.multiline_formula_bar.add_controller(key_event_controller)

        self.content_overlay.connect('get-child-position', self.on_content_overlay_get_child_position)

        focus_event_controller = Gtk.EventControllerFocus()
        focus_event_controller.connect('leave', self.on_inline_formula_unfocused)
        self.inline_formula.add_controller(focus_event_controller)

        key_event_controller = Gtk.EventControllerKey()
        key_event_controller.connect('key-pressed', self.on_inline_formula_key_pressed)
        self.inline_formula.add_controller(key_event_controller)

        self.tab_view.connect('notify::selected-page', self.on_selected_page_changed)
        self.tab_view.connect('page-attached', self.on_page_attached)
        self.tab_view.connect('page-detached', self.on_page_detached)
        self.tab_view.connect('page-reordered', self.on_page_reordered)
        self.tab_view.connect('close-page', self.on_before_page_closed)

        focus_event_controller = Gtk.EventControllerFocus()
        focus_event_controller.connect('enter', self.on_focus_received)
        self.add_controller(focus_event_controller)

        # This is a file signature used to identify if the window
        # is already linked to a document
        self.file = None

        self.context_menu = None

        self.inline_formula_box_x = 0
        self.inline_formula_box_y = 0

    def setup_new_document(self,
                           file:      Gio.File,
                           dataframe: polars.DataFrame) -> None:
        # Set the first file as the signature
        if self.file is None:
            self.file = file

        # Specify the sheet name
        sheet_name = 'Sheet 1'
        if file is not None:
            file_path = file.get_path()
            sheet_name = os.path.basename(file_path)

        # Create a new sheet
        sheet_view = self.sheet_manager.create_sheet(dataframe, sheet_name)
        self.add_new_tab(sheet_view)

        # Synchronize the sidebar
        self.sidebar_home_view.repopulate_field_list()
        self.emit('update-connection-list')

    def setup_loaded_document(self, schema: dict) -> None:
        dataframe = None
        stype = schema['stype']
        sheet_name = schema['title']

        if stype == 'worksheet':
            dataframe = schema['data']['dataframes'][0]

        # Create a new sheet
        configs = {'auto-adjust-column-widths': False}
        sheet_view = self.sheet_manager.create_sheet(dataframe, sheet_name, stype, configs)
        self.add_new_tab(sheet_view)

        # Update the document
        sheet_document = sheet_view.document

        if stype == 'worksheet':
            bounding_boxes = [
                SheetCellBoundingBox(
                    bbox['column'],
                    bbox['row'],
                    bbox['column-span'],
                    bbox['row-span']
                )
                for bbox in schema['data']['bounding-boxes']
            ]

            sheet_document.data.bbs                        = bounding_boxes
            sheet_document.data.dfs                        = schema['data']['dataframes']
            sheet_document.data.has_main_dataframe         = schema['data']['has-main-dataframe']

            sheet_document.current_sorts                   = schema['current-sorts']
            sheet_document.current_filters                 = schema['current-filters']

            sheet_document.display.row_visibility_flags    = polars.Series(schema['display']['row-visibility-flags'], dtype=polars.Boolean)
            sheet_document.display.column_visibility_flags = polars.Series(schema['display']['column-visibility-flags'], dtype=polars.Boolean)
            sheet_document.display.row_heights             = polars.Series(schema['display']['row-heights'], dtype=polars.UInt32)
            sheet_document.display.column_widths           = polars.Series(schema['display']['column-widths'], dtype=polars.UInt32)

            sheet_document.display.row_visible_series = sheet_document.display.row_visibility_flags.arg_true()
            sheet_document.display.column_visible_series = sheet_document.display.column_visibility_flags.arg_true()

            row_heights_visible_only = sheet_document.display.row_heights
            if len(sheet_document.display.row_heights) and len(sheet_document.display.row_visibility_flags):
                row_heights_visible_only = row_heights_visible_only.filter(sheet_document.display.row_visibility_flags)
            sheet_document.display.cumulative_row_heights = polars.Series('crheights', row_heights_visible_only).cum_sum()

            column_widths_visible_only = sheet_document.display.column_widths
            if len(sheet_document.display.column_widths) and len(sheet_document.display.column_visibility_flags):
                column_widths_visible_only = column_widths_visible_only.filter(sheet_document.display.column_visibility_flags)
            sheet_document.display.cumulative_column_widths = polars.Series('ccwidths', column_widths_visible_only).cum_sum()

            sheet_document.setup_document()

        if stype == 'notebook':
            for list_item in schema['list-items']:
                if list_item['ctype'] == 'sql':
                    value = list_item['value']
                    sheet_document.view.add_new_sql_cell(value)
            # TODO: should we automatically run the notebook?

    def setup_tab_menu(self,
                       tab_view: Adw.TabView,
                       tab_page: Adw.TabPage) -> None:
        if tab_page is None:
            return

        menu = tab_view.get_menu_model()
        menu.remove_all()

        tab_view = tab_page.get_child()
        document_id = tab_view.document.document_id

        section = Gio.Menu.new()
        section.append(_('Move Tab to Start'), f"app.move-tab-to-start('{document_id}')")
        section.append(_('Move Tab to End'), f"app.move-tab-to-end('{document_id}')")
        menu.append_section(None, section)

        section = Gio.Menu.new()
        section.append(_('Close Tab'), f"app.close-tab('{document_id}')")
        section.append(_('Close Other Tabs'), f"app.close-other-tabs('{document_id}')")
        section.append(_('Close Tabs to Left'), f"app.close-tabs-to-left('{document_id}')")
        section.append(_('Close Tabs to Right'), f"app.close-tabs-to-right('{document_id}')")
        menu.append_section(None, section)

        section = Gio.Menu.new()
        if tab_page.get_pinned():
            section.append(_('Unpin Tab'), f"app.unpin-tab('{document_id}')")
        else:
            section.append(_('Pin Tab'), f"app.pin-tab('{document_id}')")
        section.append(_('Duplicate Tab'), f"app.duplicate-tab('{document_id}')")
        section.append(_('Rename Tab...'), f"app.rename-tab('{document_id}')")
        menu.append_section(None, section)

    def get_current_active_view(self) -> SheetView:
        tab_page = self.tab_view.get_selected_page()
        if tab_page is None:
            return None
        return tab_page.get_child()

    def get_current_active_document(self) -> SheetDocument:
        sheet_view = self.get_current_active_view()
        if sheet_view is None:
            return None
        return sheet_view.document

    def do_focus(self, direction: Gtk.DirectionType) -> bool:
        sheet_view = self.get_current_active_view()

        # When focusing on the main canvas, pressing tab key
        # will keep the focus on the main canvas.
        if sheet_view is not None \
                and isinstance(sheet_view.document, SheetDocument) \
                and sheet_view.main_canvas.has_focus():
            return False

        self.grab_focus()

        # Otherwise, let the default behavior happen. Usually,
        # cycling focus between widgets, excluding the main canvas,
        # because the main canvas shouldn't receive the focus when
        # the user leaves it (clicking on another widget).
        return Gtk.Window.do_focus(self, direction)

    def on_focus_received(self, event: Gtk.EventControllerFocus) -> None:
        # I'd prefer that we can also have system-level notification for any
        # background operations. I assume this approach will show notifications
        # from other windows on the current active window which can be misleading
        # for the user. We can add a verification to avoid that though.
        globals.send_notification = self.show_toast_message

        # We use a global state to reference to the current history
        # manager and some other things too. This may be an indication
        # of the wrong design, but I can't think of a better way. What we
        # do here is to reset any window-related references anytime the focus
        # is received. Performing for example an undo operation will only
        # affect the currently focused sheet. Gtk does have signals and slots
        # mechanisms, but in my personal experience, it's not easy to manage
        # them especially for a very depth nested hierarchy; often times they
        # can be hard to track and debug. TODO: is there any better/safer way?
        if sheet_document := self.get_current_active_document():
            globals.history = sheet_document.history

    def do_close_request(self) -> bool:
        # TODO: check for unsaved changes and show confirmation dialog if needed
        # TODO: switch to the previous active tab after closing the current one

        # We do cleanup the history of all sheets in the current window, mainly
        # to free up disk space from the temporary files, usually .ersnap files
        # created for example when multiple cells or even the entire row(s) or
        # column(s) are edited so that the user can perform undo/redo operations.
        # At the moment, any previous states will be stored as a file on a disk,
        # not in memory to reduce the memory footprint. It's purely to support
        # handling of big datasets more possible.
        for page_index in range(self.tab_view.get_n_pages()):
            tab_page = self.tab_view.get_nth_page(page_index)
            sheet_view = tab_page.get_child()
            sheet_view.document.history.cleanup_all()

        # Force an update of the connection list for other windows
        GLib.timeout_add(200, self.emit, 'update-connection-list')

        return False

    def on_inline_formula_key_pressed(self,
                                      event:   Gtk.EventControllerKey,
                                      keyval:  int,
                                      keycode: int,
                                      state:   Gdk.ModifierType) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.close_inline_formula()
            return True

        if keyval == Gdk.KEY_Return:
            if state == Gdk.ModifierType.ALT_MASK:
                return False # prevent from executing the inline formula
                             # when pressing Return key with any modifier

            entry_buffer = self.inline_formula.get_buffer()
            start_iter = entry_buffer.get_start_iter()
            end_iter = entry_buffer.get_end_iter()
            text = entry_buffer.get_text(start_iter, end_iter, True)

            # Update the current cells
            if not self.execute_pending_formula(text):
                self.show_toast_message('Cannot edit out of bound cells')
                return True

            self.close_inline_formula()

            return True

    def on_inline_formula_unfocused(self, event: Gtk.EventControllerFocus) -> None:
        sheet_view = self.get_current_active_view()

        if sheet_view is None:
            return # inline formula should be closed when there's no active view,
                   # but this is for completeness.

        self.close_inline_formula() # TODO: should hide instead of resetting all?

    def on_content_overlay_get_child_position(self,
                                              overlay:    Gtk.Overlay,
                                              widget:     Gtk.Widget,
                                              allocation: Gdk.Rectangle) -> bool:
        if widget == self.inline_formula_box:
            sheet_view = self.get_current_active_view()
            sheet_document = sheet_view.document

            if globals.current_document_id != '' \
                    and self.inline_formula_box_x > 0 \
                    and self.inline_formula_box_y > 0:
                allocation.x = self.inline_formula_box_x
                allocation.y = self.inline_formula_box_y
                return True

            if sheet_document is None:
                return False

            # I had been trying to make it intelligently resize itself, but sadly I didn't succeed.
            # My PangoCairo calculation is always different than what I perceived on the GtkEntry,
            # even after setting the right font size and some other things. The problem with the
            # current implementation is that it's too big for cells with small sizes and it can be
            # too small for cells with large sizes.
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

            canvas_width = sheet_view.main_canvas.get_width()
            canvas_height = sheet_view.main_canvas.get_height()

            if canvas_width < new_x + new_width:
                new_x = new_x - new_width + cell_width + 2
            if canvas_height < new_y + new_height:
                new_y = new_y - new_height + cell_height + 2

            new_x = min(canvas_width - new_width, new_x)
            new_y = min(canvas_height - new_height, new_y)

            allocation.x = new_x
            allocation.y = new_y
            allocation.width = new_width
            allocation.height = new_height

            self.inline_formula_box_x = new_x
            self.inline_formula_box_y = new_y

            widget.set_size_request(new_width, new_height)

            return True

        return False

    @Gtk.Template.Callback()
    def on_toolbar_tab_button_toggled(self, toggle_button: Gtk.ToggleButton) -> None:
        if not toggle_button.get_active():
            return

        # Show the corresponding toolbar view
        tab_view_name = toggle_button.get_label().lower()
        selected_view = getattr(self, f'toolbar_{tab_view_name}_page', None)
        if selected_view is not None:
            self.toolbar_tab_view.set_selected_page(selected_view)

    @Gtk.Template.Callback()
    def on_toggle_formula_bar_toggled(self, toggle_button: Gtk.ToggleButton) -> None:
        if toggle_button.get_active():
            self.formula_bar.set_visible(False)
            self.formula_bar_dtype.set_visible(False)
            self.multiline_formula_bar_box.set_visible(True)

            text = self.formula_bar.get_text()
            self.multiline_formula_bar.get_buffer().set_text(text)

        else:
            self.formula_bar.set_visible(True)
            self.formula_bar_dtype.set_visible(True)
            self.multiline_formula_bar_box.set_visible(False)

            entry_buffer = self.multiline_formula_bar.get_buffer()
            start_iter = entry_buffer.get_start_iter()
            end_iter = entry_buffer.get_end_iter()
            text = entry_buffer.get_text(start_iter, end_iter, True)
            self.formula_bar.set_text(text)

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

        sheet_view = self.get_current_active_view()

        if sheet_view is None:
            return # name box should be insensitive when there's no active view,
                   # but this is for completeness.

        # Update the selection accordingly
        sheet_view.document.update_selection_from_name(input_text)

        # Move the focus back to the main canvas
        sheet_view.main_canvas.set_focusable(True)
        sheet_view.main_canvas.grab_focus()

    @Gtk.Template.Callback()
    def on_formula_bar_activated(self, entry: Gtk.Entry) -> None:
        sheet_view = self.get_current_active_view()

        if sheet_view is None:
            return # formula bar should be insensitive when there's no active view,
                   # but this is for completeness.

        input_text = entry.get_text()
        if not self.execute_pending_formula(input_text):
            return

        # Move the focus back to the main canvas
        sheet_view.main_canvas.set_focusable(True)
        sheet_view.main_canvas.grab_focus()

    @Gtk.Template.Callback()
    def on_new_sheet_clicked(self, button: Gtk.Button) -> None:
        sheet_view = self.sheet_manager.create_sheet(None)

        if sheet_view is None:
            return # in case something goes wrong, it's not likely though

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
                                state:   Gdk.ModifierType) -> bool:
        # Pressing tab key will reset the input bar instead of activating
        # the input bar to prevent undesired behavior. I've seen other
        # applications don't do this, but I prefer this for consistency.
        if keyval == Gdk.KEY_Tab:
            self.reset_inputbar()
            return True

        # Pressing escape key will reset the input bar and
        # return the focus to the main canvas back.
        if keyval == Gdk.KEY_Escape:
            self.reset_inputbar()
            sheet_view = self.get_current_active_view()
            if sheet_view is None:
                return False # name box should be insensitive when there's no active view,
                             # but this is for completeness.
            sheet_view.main_canvas.set_focusable(True)
            sheet_view.main_canvas.grab_focus()
            return True

    def on_formula_bar_key_pressed(self,
                                   event:   Gtk.EventControllerKey,
                                   keyval:  int,
                                   keycode: int,
                                   state:   Gdk.ModifierType) -> bool:
        # Pressing escape key will reset the input bar
        # and return the focus to the main canvas back.
        if keyval == Gdk.KEY_Escape:
            self.reset_inputbar()
            sheet_view = self.get_current_active_view()
            if sheet_view is None:
                return False # formula bar should be insensitive when there's no active view,
                             # but this is for completeness.
            sheet_view.main_canvas.set_focusable(True)
            sheet_view.main_canvas.grab_focus()
            return True

        if keyval in {Gdk.KEY_Up, Gdk.KEY_Down}:
            return True # keep the focus on the formula bar

        return False

    def on_multiline_formula_bar_key_pressed(self,
                                             event:   Gtk.EventControllerKey,
                                             keyval:  int,
                                             keycode: int,
                                             state:   Gdk.ModifierType) -> bool:
        # Pressing escape key will reset the input bar
        # and return the focus to the main canvas back.
        if keyval == Gdk.KEY_Escape:
            self.reset_inputbar()

            sheet_view = self.get_current_active_view()

            if sheet_view is None:
                return False

            sheet_view.main_canvas.set_focusable(True)
            sheet_view.main_canvas.grab_focus()

            return True

        if keyval == Gdk.KEY_Return:
            if state != Gdk.ModifierType.CONTROL_MASK:
                return False

            entry_buffer = self.multiline_formula_bar.get_buffer()
            start_iter = entry_buffer.get_start_iter()
            end_iter = entry_buffer.get_end_iter()
            text = entry_buffer.get_text(start_iter, end_iter, True)

            # Update the current cells
            if not self.execute_pending_formula(text):
                return True

            return True

    def on_selected_page_changed(self,
                                 tab_view: Adw.TabView,
                                 pspec:    GObject.ParamSpec) -> None:
        sheet_view = self.get_current_active_view()

        if sheet_view is None:
            return

        if isinstance(sheet_view, SheetView):
            self.toolbar_home_view.worksheet_1_section.set_visible(True)
            self.toolbar_home_view.worksheet_2_section.set_visible(True)
            self.toolbar_insert_view.worksheet_1_section.set_visible(True)

            self.formulas_toggle_button.set_visible(True)
            self.data_toggle_button.set_visible(True)

            self.name_formula_box.set_visible(True)

            self.sidebar_home_view.fields_section.set_visible(True)
            self.sidebar_home_view.sorts_section.set_visible(True)
            self.sidebar_home_view.filters_section.set_visible(True)

        if isinstance(sheet_view, SheetNotebookView):
            self.toolbar_home_view.worksheet_1_section.set_visible(False)
            self.toolbar_home_view.worksheet_2_section.set_visible(False)
            self.toolbar_insert_view.worksheet_1_section.set_visible(False)

            self.formulas_toggle_button.set_visible(False)
            self.data_toggle_button.set_visible(False)

            self.name_formula_box.set_visible(False)

            self.sidebar_home_view.fields_section.set_visible(False)
            self.sidebar_home_view.sorts_section.set_visible(False)
            self.sidebar_home_view.filters_section.set_visible(False)

        # Reset the active toolbar tab if needed
        active_toolbar_tab_button = None
        for button in self.toolbar_buttons:
            if button.get_active():
                active_toolbar_tab_button = button
                break
        if not active_toolbar_tab_button.get_visible():
            self.home_toggle_button.set_active(True)

        sheet_document = sheet_view.document

        if isinstance(sheet_document, SheetDocument):
            sheet_document.view.main_canvas.set_focusable(True)
            sheet_document.view.main_canvas.grab_focus()

        if isinstance(sheet_document, SheetNotebook) \
                and len(sheet_document.view.list_items) > 0:
            sheet_document.view.list_items[0]['source_view'].grab_focus()

        globals.history = sheet_document.history

        if isinstance(sheet_document, SheetDocument):
            sheet_document.notify_selected_table_changed(force=True)
            self.reset_inputbar()

    def on_page_attached(self,
                         tab_view: Adw.TabView,
                         tab_page: Adw.TabPage,
                         position: int) -> None:
        self.emit('update-connection-list')

    def on_page_detached(self,
                         tab_view: Adw.TabView,
                         tab_page: Adw.TabPage,
                         position: int) -> None:
        self.emit('update-connection-list')

    def on_page_reordered(self,
                          tab_view: Adw.TabView,
                          tab_page: Adw.TabPage,
                          position: int) -> None:
        # Reorder the sheets in the sheet manager
        new_sheets = {}
        for page_index in range(self.tab_view.get_n_pages()):
            tab_page = self.tab_view.get_nth_page(page_index)
            sheet_view = tab_page.get_child()
            sheet_document = sheet_view.document
            document_id = sheet_document.document_id
            new_sheets[document_id] = sheet_document
        self.sheet_manager.sheets = new_sheets

        # Repopulate the connection list
        self.emit('update-connection-list')

    def on_before_page_closed(self,
                              tab_view: Adw.TabView,
                              tab_page: Adw.TabPage) -> bool:
        sheet_view = tab_page.get_child()

        if sheet_view is None:
            return True

        # Close the inline formula box if it references the closed sheet
        if sheet_view.document.document_id == globals.current_document_id:
            globals.is_editing_cells = False
            globals.current_document_id = ''
            self.inline_formula_box.set_visible(False)

            self.inline_formula_box_x = 0
            self.inline_formula_box_y = 0

        # Clean up the history, mainly to free up disk space
        # from the temporary files created for undo/redo operations.
        sheet_view.document.history.cleanup_all()

        self.sheet_manager.delete_sheet(sheet_view)

        # Disable some UIs when no sheet remains
        if len(self.sheet_manager.sheets) == 0:
            self.name_box.set_sensitive(False)
            self.formula_bar.set_sensitive(False)
            self.multiline_formula_bar.set_sensitive(False)
            self.formula_bar_toggle_button.set_sensitive(False)

            # TODO: connection list section shouldn't be disabled
            self.toolbar_tab_view.set_sensitive(False)
            self.sidebar_tab_view.set_sensitive(False)

            self.update_inputbar()
            self.grab_focus()

            globals.history = None

        # FIXME: clicking on the tab close button should trigger
        #        the confirmation dialog as well
        return False

    def on_operation_cancelled(self, source: GObject.Object) -> None:
        self.close_inline_formula()

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
        self.open_inline_formula(sel_value)

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

        if sheet_document is None:
            return # impossible to happen, but for safety

        active_cell = sheet_document.selection.current_active_cell
        mcolumn = active_cell.metadata.column
        mdfi = active_cell.metadata.dfi

        x = sheet_document.display.get_cell_x_from_point(x + 1)
        y = sheet_document.display.get_cell_y_from_point(y + 1)
        width = sheet_document.display.get_cell_width_from_point(x + 1)
        height = sheet_document.display.get_cell_height_from_point(y + 1)

        from .sheet_header_menu import SheetHeaderMenu

        # Create context menu
        if self.context_menu is not None:
            self.context_menu.unparent()
        self.context_menu = SheetHeaderMenu(self, mcolumn, mdfi)
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
        rectangle.x = min(max(1, int(x + width - 10)), self.content_overlay.get_width() - 1)
        rectangle.y = min(max(1, int(y + height)), self.content_overlay.get_height() - 1)
        rectangle.height = 1
        rectangle.width = 1
        self.context_menu.set_pointing_to(rectangle)

        # Show context menu
        self.context_menu.popup()

    def open_cell_context_menu(self,
                               x: int,
                               y: int) -> None:
        sheet_document = self.get_current_active_document()

        if sheet_document is None:
            return # impossible to happen, but for safety

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
        mdfi = active_cell.metadata.dfi

        n_hidden_columns = sheet_document.display.get_n_hidden_columns(col_1, col_2)
        n_all_hidden_columns = sheet_document.display.get_n_all_hidden_columns()

        from .sheet_cell_menu import SheetCellMenu

        # Create context menu
        if self.context_menu is not None:
            self.context_menu.unparent()
        self.context_menu = SheetCellMenu(start_column, start_row,
                                          end_column,   end_row,
                                          column_span,  row_span,
                                          n_hidden_columns,
                                          n_all_hidden_columns,
                                          ctype, mdfi)
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
        rectangle.x = min(max(1, int(x)), self.content_overlay.get_width() - 1)
        rectangle.y = min(max(1, int(y)), self.content_overlay.get_height() - 1)
        rectangle.height = 1
        rectangle.width = 1
        self.context_menu.set_pointing_to(rectangle)

        # Show context menu
        self.context_menu.popup()

    def add_new_tab(self, sheet_view: SheetView | SheetNotebookView) -> None:
        sheet_document = sheet_view.document

        tab_page = self.tab_view.append(sheet_view)
        tab_page.set_title(sheet_document.title)

        if isinstance(sheet_view, SheetView):
            tab_page.set_indicator_icon(Gio.ThemedIcon.new('table-symbolic'))
        if isinstance(sheet_view, SheetNotebookView):
            tab_page.set_indicator_icon(Gio.ThemedIcon.new('terminal-symbolic'))

        # Shrink the tab box size
        # self.tab_bar.get_first_child().get_first_child().get_first_child() \
        #             .get_next_sibling().get_next_sibling().get_first_child() \
        #             .set_halign(Gtk.Align.START)

        # Setup proper handling of signals and bindings
        tab_page.bind_property('title', sheet_document,
                               'title', GObject.BindingFlags.BIDIRECTIONAL)

        from .sheet_document import SheetDocument

        if isinstance(sheet_document, SheetDocument):
            sheet_document.connect('cancel-operation', self.on_operation_cancelled)
            sheet_document.connect('selection-changed', self.on_selection_changed)
            sheet_document.connect('columns-changed', self.on_columns_changed)
            sheet_document.connect('sorts-changed', self.on_sorts_changed)
            sheet_document.connect('filters-changed', self.on_filters_changed)
            sheet_document.connect('open-context-menu', self.on_context_menu_opened)
            sheet_document.view.connect('open-inline-formula', self.on_inline_formula_opened)
            sheet_document.view.connect('open-context-menu', self.on_context_menu_opened)

        # Switch to the new tab automatically
        self.tab_view.set_selected_page(tab_page)

        if isinstance(sheet_document, SheetDocument):
            # Re-enable the input bar
            self.name_box.set_sensitive(True)
            self.formula_bar.set_sensitive(True)
            self.multiline_formula_bar.set_sensitive(True)
            self.formula_bar_toggle_button.set_sensitive(True)
            self.toolbar_tab_view.set_sensitive(True)
            self.sidebar_tab_view.set_sensitive(True)

            # Focus the main canvas
            sheet_view.main_canvas.set_focusable(True)
            sheet_view.main_canvas.grab_focus()

    def duplicate_sheet(self,
                        document_id: str,
                        materialize: bool = False,
                        filter_by:   dict = {}) -> None:
        sheet_view = self.sheet_manager.duplicate_sheet(document_id)

        sheet_document = sheet_view.document

        if isinstance(sheet_document, SheetDocument):
            match filter_by.get('operator-name'):
                case 'current-selection':
                    sheet_document.filter_current_rows()
                case 'inverse-selection':
                    sheet_document.filter_current_rows(inverse=True)
                case 'query-builder':
                    sheet_document.pending_filters = filter_by['operator-args']
                    sheet_document.filter_current_rows(multiple=True)

            if materialize:
                sheet_document.materialize_view()

            if 'operator-name' in filter_by:
                sheet_document.setup_document()
                sheet_document.setup_history()

        self.add_new_tab(sheet_view)

    def rename_sheet(self, tab_page: Adw.TabPage) -> None:
        from .sheet_rename_dialog import SheetRenameDialog
        from .history_manager import RenameSheetState

        old_name = tab_page.get_title()

        def _rename_sheet(new_name: str) -> None:
            state = RenameSheetState(self, old_name, new_name)
            globals.history.save(state)

            tab_page.set_title(new_name)

            self.emit('update-connection-list')

        dialog = SheetRenameDialog(old_name, _rename_sheet)
        dialog.present(self)

    def reset_inputbar(self) -> None:
        sheet_document = self.get_current_active_document()

        # Empty the input bar when no sheet is open
        if sheet_document is None:
            self.update_inputbar()
            return

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
        self.multiline_formula_bar.get_buffer().set_text(sel_value)

        if sel_dtype is None:
            self.formula_bar_dtype.set_visible(False)
            return

        self.formula_bar_dtype.set_text(sel_dtype)

        if self.formula_bar.get_visible():
            self.formula_bar_dtype.set_visible(True)

        if not self.formula_bar_toggle_button.get_active():
            self.formula_bar_dtype.set_visible(sel_dtype is not None)

    def open_inline_formula(self, sel_value: str = None) -> None:
        sheet_document = self.get_current_active_document()

        if sheet_document is None:
            return

        if not isinstance(sheet_document, SheetDocument):
            return

        globals.is_editing_cells = True
        globals.current_document_id = sheet_document.document_id

        self.inline_formula_box.get_vadjustment().set_value(0)
        self.inline_formula_box.set_visible(True)

        if sel_value is None:
            sel_value = self.formula_bar.get_text()

        self.inline_formula.get_buffer().set_text(sel_value)

        self.inline_formula.grab_focus()

    def close_inline_formula(self) -> None:
        globals.is_editing_cells = False
        globals.current_document_id = ''

        self.inline_formula_box_x = 0
        self.inline_formula_box_y = 0

        self.inline_formula_box.set_visible(False)

        sheet_view = self.get_current_active_view()

        if sheet_view is None:
            return # inline formula should be closed when there's no active view,
                   # but this is for completeness.

        sheet_view.main_canvas.set_focusable(True)
        sheet_view.main_canvas.grab_focus()
        sheet_view.main_canvas.queue_draw()

    def apply_pending_table(self, action_data_id: str) -> None:
        dataframe = None
        if action_data_id is not None:
            dataframe = globals.pending_action_data[action_data_id]

        sheet_view = self.sheet_manager.create_sheet(dataframe)

        self.add_new_tab(sheet_view)

        self.sidebar_home_view.repopulate_field_list()
        self.emit('update-connection-list')

        del globals.pending_action_data[action_data_id]

    def toggle_sidebar(self) -> None:
        sheet_document = self.get_current_active_document()

        # Close the sidebar when it's already open
        if self.sidebar_toggle_button.get_active():
            self.sidebar_toggle_button.set_active(False)
            self.split_view.set_collapsed(True)

            if sheet_document is None:
                return

            # Hide the search range selection box if necessary
            if sheet_document.search_range_performer == 'search-all':
                sheet_document.is_searching_cells = False

                if isinstance(sheet_document, SheetDocument):
                    sheet_document.selection.current_search_range = None

            return

        # Open the sidebar
        self.sidebar_toggle_button.set_active(True)
        self.split_view.set_collapsed(False)

        if sheet_document is None:
            return

        selected_page = self.sidebar_tab_view.get_selected_page()

        if selected_page == self.search_replace_all_page:
            sheet_document.is_searching_cells = True

    def show_toast_message(self,
                           message: str,
                           action:  tuple = ()) -> None:

        def on_dismissed(toast: Adw.Toast, action_data_id: str) -> None:
            if action_data_id in globals.pending_action_data:
                del globals.pending_action_data[action_data_id]

        # Replace line breaks with spaces
        message = message.replace('\n', ' ')

        toast = Adw.Toast.new(message)

        if len(action) >= 2:
            toast.set_button_label(action[0])
            toast.set_detailed_action_name(action[1])

        if len(action) >= 3:
            toast.connect('dismissed', on_dismissed, action[2])

        self.toast_overlay.add_toast(toast)

    def execute_pending_formula(self, formula: str) -> bool:
        sheet_view = self.get_current_active_view()

        if sheet_view is None:
            return False

        # Check if the input is an SQL syntax but for DDL
        query_pattern = r"(\r\n|\r|\n|\s)*[A-Za-z0-9]+.*=(\r\n|\r|\n|\s)*" \
                        r"[SELECT|WITH](\r\n|\r|\n|.)*"
        if re.fullmatch(query_pattern, formula, re.IGNORECASE):
            return self.create_table_from_sql(formula)

        # Check if the input is an SQL syntax
        query_pattern = r"(\r\n|\r|\n|\s)*=(\r\n|\r|\n|\s)*" \
                        r"[SELECT|WITH](\r\n|\r|\n|.)*"
        if re.fullmatch(query_pattern, formula, re.IGNORECASE):
            return sheet_view.document.update_current_columns_from_sql(formula)

        # Check if the input is an DAX-like syntax
        expression_pattern = r"(\r\n|\r|\n|\s)*[A-Za-z0-9]+.*=.*"
        if re.fullmatch(expression_pattern, formula, re.IGNORECASE):
            return sheet_view.document.update_current_columns_from_dax(formula)

        # Check if the input is a formula
        formula_pattern = r"(\r\n|\r|\n|\s)*=.*"
        if re.fullmatch(formula_pattern, formula, re.IGNORECASE):
            return sheet_view.document.update_current_cells_from_formula(formula)

        # TODO: add support for Python code

        # Update the current cells
        return sheet_view.document.update_current_cells_from_literal(formula)

    def create_table_from_sql(self, query: str) -> bool:
        sheet_document = self.get_current_active_document()

        if sheet_document is None:
            return False # shouldn't happen

        table_name, query = query.split('=', 1)

        table_name = table_name.strip()
        query = query.strip()

        # Add "FROM self" if needed
        if 'from' not in query.lower():
            if 'where' in query.lower():
                query = query.replace('where', 'FROM self WHERE', 1)
            else:
                query += ' FROM self'

        connection = duckdb.connect()

        # Register all the data sources
        if sheet_document.data.has_main_dataframe:
            connection.register('self', sheet_document.data.dfs[0])
        connection_strings = globals.register_connection(connection)
        query = connection_strings + query

        register_sql_functions(connection)

        try:
            new_dataframe = connection.sql(query).pl()

            sheet_view = self.sheet_manager.create_sheet(new_dataframe, table_name)
            self.add_new_tab(sheet_view)

            connection.close()
            return True

        except Exception as e:
            print(e)
            message = str(e)
            self.show_toast_message(message)

        connection.close()
        return False