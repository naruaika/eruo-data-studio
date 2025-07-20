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
from .sheet_view import SheetView

@Gtk.Template(resource_path='/com/macipra/eruo/ui/window.ui')
class Window(Adw.ApplicationWindow):
    __gtype_name__ = 'Window'

    split_view = Gtk.Template.Child()
    toggle_sidebar = Gtk.Template.Child()
    window_title = Gtk.Template.Child()

    toggle_search = Gtk.Template.Child()
    toggle_history = Gtk.Template.Child()

    content_overlay = Gtk.Template.Child()

    name_box = Gtk.Template.Child()
    formula_bar = Gtk.Template.Child()

    toast_overlay = Gtk.Template.Child()
    tab_view = Gtk.Template.Child()
    tab_bar = Gtk.Template.Child()

    def __init__(self, file: Gio.File, dataframe: polars.DataFrame, **kwargs) -> None:
        super().__init__(**kwargs)

        self.file = file

        from .sheet_manager import SheetManager
        self.sheet_manager = SheetManager()

        from .search_replace_overlay import SearchReplaceOverlay
        self.search_overlay = SearchReplaceOverlay(self)
        self.content_overlay.add_overlay(self.search_overlay)

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

    def show_toast_message(self, message: str) -> None:
        self.toast_overlay.add_toast(Adw.Toast.new(message))