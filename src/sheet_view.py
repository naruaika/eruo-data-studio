# sheet_view.py
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


from gi.repository import Gdk, GObject, Gtk

from . import globals
from .sheet_cell_menu import SheetCellMenu
from .sheet_document import SheetDocument

@Gtk.Template(resource_path='/com/macipra/eruo/ui/sheet-view.ui')
class SheetView(Gtk.Box):
    __gtype_name__ = 'SheetView'

    __gsignals__ = {
        'select-by-keypress': (GObject.SIGNAL_RUN_FIRST, None, (int, int,)),
        'select-by-motion': (GObject.SIGNAL_RUN_FIRST, None, (int, int,)),
        'update-cell-data': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
    }

    main_overlay = Gtk.Template.Child()

    horizontal_scrollbar = Gtk.Template.Child()
    vertical_scrollbar = Gtk.Template.Child()

    main_canvas = Gtk.Template.Child()
    inline_formula = Gtk.Template.Child()

    def __init__(self, document: SheetDocument, **kwargs) -> None:
        super().__init__(**kwargs)

        self.document = document

        scroll_event_controller = Gtk.EventControllerScroll()
        scroll_event_controller.set_flags(Gtk.EventControllerScrollFlags.BOTH_AXES)
        scroll_event_controller.connect('scroll', self.on_main_canvas_scrolled)
        self.main_canvas.add_controller(scroll_event_controller)
        motion_event_controller = Gtk.EventControllerMotion()
        drag_event_controller = Gtk.GestureDrag()
        drag_event_controller.connect('drag-update', self.on_main_canvas_drag_update)
        self.main_canvas.add_controller(drag_event_controller)

        motion_event_controller.connect('motion', self.on_main_canvas_motion)
        self.main_canvas.add_controller(motion_event_controller)
        focus_event_controller = Gtk.EventControllerFocus()
        focus_event_controller.connect('leave', self.on_main_canvas_unfocused)
        self.main_canvas.add_controller(focus_event_controller)

        click_event_controller = Gtk.GestureClick()
        click_event_controller.connect('pressed', self.on_main_canvas_lmb_pressed)
        self.main_canvas.add_controller(click_event_controller)
        click_event_controller = Gtk.GestureClick()
        click_event_controller.set_button(3)
        click_event_controller.connect('released', self.on_main_canvas_rmb_released)
        self.main_canvas.add_controller(click_event_controller)
        key_event_controller = Gtk.EventControllerKey()
        key_event_controller.connect('key-pressed', self.on_main_canvas_key_pressed)
        self.main_canvas.add_controller(key_event_controller)

        self.main_canvas_width = 0
        self.main_canvas_height = 0
        self.main_canvas.connect('resize', self.on_main_canvas_resized)

        self.main_canvas.set_cursor(Gdk.Cursor.new_from_name('cell', Gdk.Cursor.new_from_name('default')))

        motion_event_controller = Gtk.EventControllerMotion()
        motion_event_controller.connect('enter', self.on_scrollbar_entered)
        motion_event_controller.connect('leave', self.on_scrollbar_left)
        self.vertical_scrollbar.add_controller(motion_event_controller)

        motion_event_controller = Gtk.EventControllerMotion()
        motion_event_controller.connect('enter', self.on_scrollbar_entered)
        motion_event_controller.connect('leave', self.on_scrollbar_left)
        self.horizontal_scrollbar.add_controller(motion_event_controller)

        focus_event_controller = Gtk.EventControllerFocus()
        focus_event_controller.connect('leave', self.on_inline_formula_unfocused)
        self.inline_formula.add_controller(focus_event_controller)
        key_event_controller = Gtk.EventControllerKey()
        key_event_controller.connect('key-pressed', self.on_inline_formula_key_pressed)
        self.inline_formula.add_controller(key_event_controller)

        self.inline_formula_x = 0
        self.inline_formula_y = 0
        self.inline_formula.get_buffer().connect('changed', self.on_inline_formula_buffer_changed)

        self.main_overlay.connect('get-child-position', self.on_main_overlay_get_child_position)

        self.context_menu = None

    def on_main_canvas_scrolled(self, event: Gtk.EventControllerScroll, dx: float, dy: float) -> bool:
        # Change direction of scroll based on shift key
        if event.get_current_event_state() == Gdk.ModifierType.SHIFT_MASK and (dy < 0 or 0 < dy):
            dx, dy = dy, 0
        elif event.get_current_event_state() == Gdk.ModifierType.SHIFT_MASK and (dx < 0 or 0 < dx):
            dy, dx = dx, 0

        # Convert to scroll unit (in pixels)
        dx = int(dx * self.document.display.DEFAULT_CELL_WIDTH) # cell width is usually 2-3x the cell height
        dy = int(dy * self.document.display.DEFAULT_CELL_HEIGHT * self.document.display.scroll_increment)

        scroll_y_position = self.vertical_scrollbar.get_adjustment().get_value()
        scroll_x_position = self.horizontal_scrollbar.get_adjustment().get_value()

        if dy < 0 and scroll_y_position == 0:
            return False
        if dx < 0 and scroll_x_position == 0:
            return False

        self.vertical_scrollbar.get_adjustment().set_upper(scroll_y_position + dy + self.main_canvas_height)
        self.horizontal_scrollbar.get_adjustment().set_upper(scroll_x_position + dx + self.main_canvas_width)

        self.vertical_scrollbar.get_adjustment().set_value(max(0, scroll_y_position + dy))
        self.horizontal_scrollbar.get_adjustment().set_value(max(0, scroll_x_position + dx))

        return True

    def on_main_canvas_drag_update(self, event: Gtk.GestureDrag, offset_x: float, offset_y: float) -> None:
        if globals.is_editing_cells:
            return # prevent dragging while inline editing

        _, *start_coord = event.get_start_point()
        end_coord = (start_coord[0] + offset_x, start_coord[1] + offset_y)
        self.emit('select-by-motion', *end_coord)

    def on_main_canvas_motion(self, event: Gtk.EventControllerMotion, x: float, y: float) -> None:
        pass

    def on_main_canvas_unfocused(self, event: Gtk.EventControllerFocus) -> None:
        self.main_canvas.set_focusable(False)

    def on_main_canvas_lmb_pressed(self, event: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        if n_press >= 2:
            globals.is_editing_cells = True
            self.document.auto_adjust_scrollbars_by_selection()

            cell_data = self.document.selection.cell_data
            if cell_data is None:
                cell_data = ''
            cell_data = str(cell_data)

            self.inline_formula_x = self.document.selection.current_active_cell.x
            self.inline_formula_y = self.document.selection.current_active_cell.y

            self.inline_formula.get_buffer().set_text(cell_data)
            self.inline_formula.set_visible(True)
            self.inline_formula.grab_focus()

            return

        self.document.select_element_from_point(x, y)
        self.main_canvas.set_focusable(True)
        self.main_canvas.grab_focus()
        if self.document.check_selection_changed():
            self.main_canvas.queue_draw()

    def on_main_canvas_rmb_released(self, event: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        if not self.document.check_selection_contains_point(x, y):
            self.document.select_element_from_point(x, y)
            self.main_canvas.queue_draw()

        cell_x = self.document.display.get_cell_x_from_point(x)
        cell_y = self.document.display.get_cell_y_from_point(y)

        if cell_x == 0 and cell_y == 0:
            return # no applicable context menu for corner locator

        cursor_cell = self.document.selection.current_cursor_cell
        active_cell = self.document.selection.current_active_cell

        col_1 = self.document.display.get_vcolumn_from_column(cursor_cell.column)
        row_1 = self.document.display.get_vrow_from_row(cursor_cell.row)
        col_2 = self.document.display.get_vcolumn_from_column(active_cell.column)
        row_2 = self.document.display.get_vrow_from_row(active_cell.row)

        col_1, col_2 = min(col_1, col_2), max(col_1, col_2)
        row_1, row_2 = min(row_1, row_2), max(row_1, row_2)

        start_column = self.document.display.get_column_name_from_column(col_1)
        start_row = str(row_1)
        end_column = self.document.display.get_column_name_from_column(col_2)
        end_row = str(row_2)

        n_hidden_columns = self.document.display.get_n_hidden_columns(col_1, col_2)
        n_hidden_rows = self.document.display.get_n_hidden_rows(row_1, row_2)

        n_all_hidden_columns = self.document.display.get_n_all_hidden_columns()
        n_all_hidden_rows = self.document.display.get_n_all_hidden_rows()

        ctype = type(self.document.selection.current_active_range)

        x = self.document.display.get_cell_x_from_point(x + 1)
        y = self.document.display.get_cell_y_from_point(y + 1)
        width = self.document.display.get_cell_width_from_point(x + 1)
        height = self.document.display.get_cell_height_from_point(y + 1)

        # Create context menu
        if self.context_menu is not None:
            self.context_menu.unparent()
            del self.context_menu
        self.context_menu = SheetCellMenu(start_column, start_row, end_column, end_row, n_hidden_columns, n_hidden_rows,
                                          n_all_hidden_columns, n_all_hidden_rows, ctype)
        self.context_menu.set_parent(self.main_overlay)

        def on_context_menu_closed(widget: Gtk.Widget) -> None:
            self.main_canvas.set_focusable(True)
            self.main_canvas.grab_focus()
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

    def on_main_canvas_key_pressed(self, event: Gtk.EventControllerKey, keyval: int, keycode: int, state: Gdk.ModifierType) -> None:
        if keyval in [
            Gdk.KEY_Tab,
            Gdk.KEY_ISO_Left_Tab,
            Gdk.KEY_Return,
            Gdk.KEY_Left,
            Gdk.KEY_Right,
            Gdk.KEY_Up,
            Gdk.KEY_Down,
        ]:
            self.emit('select-by-keypress', keyval, state)
            return

        # Prevent from interrupting any application actions
        if state == Gdk.ModifierType.CONTROL_MASK or state == (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK):
            return

        self.inline_formula_x = self.document.selection.current_active_cell.x
        self.inline_formula_y = self.document.selection.current_active_cell.y

        if Gdk.KEY_space <= keyval <= Gdk.KEY_asciitilde:
            self.inline_formula.get_buffer().set_text(chr(keyval))
            self.inline_formula.set_visible(True)
            self.inline_formula.grab_focus()
            return
        if keyval == Gdk.KEY_BackSpace:
            self.inline_formula.get_buffer().set_text('')
            self.inline_formula.set_visible(True)
            self.inline_formula.grab_focus()
            return

    def on_scrollbar_entered(self, event: Gtk.EventControllerMotion, x: float, y: float) -> None:
        event.get_widget().add_css_class('hovering')

    def on_scrollbar_left(self, event: Gtk.EventControllerMotion) -> None:
        event.get_widget().remove_css_class('hovering')

    def on_inline_formula_key_pressed(self, event: Gtk.EventControllerKey, keyval: int, keycode: int, state: Gdk.ModifierType) -> None:
        if keyval == Gdk.KEY_Escape:
            globals.is_editing_cells = False
            self.inline_formula.set_visible(False)
            self.main_canvas.set_focusable(True)
            self.main_canvas.grab_focus()
            self.main_canvas.queue_draw()
            return

        if keyval == Gdk.KEY_Return:
            globals.is_editing_cells = False
            self.inline_formula.set_visible(False)
            self.main_canvas.set_focusable(True)
            self.main_canvas.grab_focus()

            start_iter = self.inline_formula.get_buffer().get_start_iter()
            end_iter = self.inline_formula.get_buffer().get_end_iter()
            text = self.inline_formula.get_buffer().get_text(start_iter, end_iter, True)
            self.emit('update-cell-data', text)

            return

    def on_inline_formula_unfocused(self, event: Gtk.EventControllerFocus) -> None:
        globals.is_editing_cells = False
        self.inline_formula.set_visible(False)
        self.main_canvas.queue_draw()

    def on_inline_formula_buffer_changed(self, buffer):
        self.inline_formula.queue_resize()

    def on_main_canvas_resized(self, drawing_area: Gtk.DrawingArea, width: int, height: int) -> None:
        if self.main_canvas_width == width and self.main_canvas_height == height:
            return
        self.main_canvas_width = width
        self.main_canvas_height = height
        self.document.auto_adjust_scrollbars_by_scroll()
        self.document.renderer.render_caches = {}

    def on_main_overlay_get_child_position(self, overlay: Gtk.Overlay, widget: Gtk.Widget, allocation: Gdk.Rectangle) -> bool:
        if widget == self.inline_formula:
            new_x = self.inline_formula_x - 1
            new_y = self.inline_formula_y - 1
            new_width = self.document.display.DEFAULT_CELL_WIDTH * 3 + 2
            new_height = self.document.display.DEFAULT_CELL_HEIGHT * 7 + 2

            if self.main_canvas_width < new_x + new_width:
                new_x = new_x - new_width / 3 * 2 + 2
            if self.main_canvas_height < new_y + new_height:
                new_y = new_y - new_height / 7 * 6 + 2

            allocation.x = new_x
            allocation.y = new_y
            allocation.width = new_width
            allocation.height = new_height

            widget.set_size_request(allocation.width, allocation.height)

            return True

        return False