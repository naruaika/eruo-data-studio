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


import cairo
import polars
import re
import threading
import time

from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango, PangoCairo

from .utils import Log, print_log
from .dbms import DBMS, WITH_ROW_INDEX
from .display import Display
from .renderer import Renderer
from .selection import Selection

from .widgets.sheet_column_header_menu import SheetColumnHeaderMenu
from .widgets.sheet_column_locator_menu import SheetColumnLocatorMenu

@Gtk.Template(resource_path='/com/macipra/Eruo/gtk/window.ui')
class EruoDataStudioWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'EruoDataStudioWindow'

    SCROLL_X_MULTIPLIER: int = 20
    SCROLL_Y_MULTIPLIER: int = 20

    name_box: Gtk.Widget = Gtk.Template.Child()
    formula_bar: Gtk.Widget = Gtk.Template.Child()
    toast_container: Gtk.Widget = Gtk.Template.Child()
    main_container: Gtk.Widget = Gtk.Template.Child()
    main_canvas: Gtk.Widget = Gtk.Template.Child()
    vertical_scrollbar: Gtk.Widget = Gtk.Template.Child()
    horizontal_scrollbar: Gtk.Widget = Gtk.Template.Child()
    status_message: Gtk.Widget = Gtk.Template.Child()

    dbms: DBMS
    display: Display
    selection: Selection
    renderer: Renderer

    _main_canvas_size: tuple[int, int] = (0, 0)
    _main_canvas_cursor_name: str = 'cell'

    def __init__(self, file: Gio.File | None = None, **kwargs) -> None:
        """
        Creates a new EruoDataStudioWindow.

        The constructor takes an optional Gio.File argument, which if present,
        initiates the loading and parsing of the file. The file is loaded
        asynchronously using a background thread to keep the UI responsive.

        Args:
            file: An optional Gio.File object specifying the file to be loaded.
        """
        super().__init__(**kwargs)

        self.dbms = DBMS()
        self.display = Display()
        self.selection = Selection(self.display)
        self.renderer = Renderer(self.display, self.selection, self.dbms)

        self.SCROLL_X_MULTIPLIER = 1 * self.display.CELL_DEFAULT_WIDTH
        self.SCROLL_Y_MULTIPLIER = 3 * self.display.CELL_DEFAULT_HEIGHT

        self.formula_bar.connect('changed', self.on_formula_bar_changed)
        self.formula_bar.x_is_dirty = False

        self.main_canvas.connect('resize', self.on_main_canvas_resized)
        self.main_canvas.set_cursor(Gdk.Cursor.new_from_name(self._main_canvas_cursor_name, Gdk.Cursor.new_from_name('default')))
        self.main_canvas.set_draw_func(self.renderer.draw)
        self.main_canvas.set_focusable(True)
        self.main_canvas.grab_focus()

        # Setup the application initial states
        self.selection.set_active_cell((0, 0))
        self.selection.set_selected_cells(((0, 0), (0, 0)))
        self.name_box.set_text(self.selection.index_to_name((0, 0)))

        self.vertical_adjustment = Gtk.Adjustment.new(0, 0, 100, 3, 33, 75)
        self.horizontal_adjustment = Gtk.Adjustment.new(0, 0, 100, 3, 33, 75)
        self.vertical_scrollbar.set_adjustment(self.vertical_adjustment)
        self.horizontal_scrollbar.set_adjustment(self.horizontal_adjustment)

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

        click_event_controller = Gtk.GestureClick()
        click_event_controller.connect('pressed', self.on_main_canvas_lmb_pressed)
        self.main_canvas.add_controller(click_event_controller)
        click_event_controller = Gtk.GestureClick()
        click_event_controller.set_button(3)
        click_event_controller.connect('released', self.on_main_canvas_rmb_released)
        self.main_canvas.add_controller(click_event_controller)
        focus_event_controller = Gtk.EventControllerFocus()
        focus_event_controller.connect('leave', self.on_main_canvas_unfocused)
        self.main_canvas.add_controller(focus_event_controller)

        drag_event_controller = Gtk.GestureDrag()
        drag_event_controller.connect('drag_update', self.on_main_canvas_drag_update)
        self.main_canvas.add_controller(drag_event_controller)

        key_event_controller = Gtk.EventControllerKey()
        key_event_controller.connect('key-pressed', self.on_main_canvas_key_pressed)
        self.main_canvas.add_controller(key_event_controller)

        scroll_event_controller = Gtk.EventControllerScroll()
        scroll_event_controller.set_flags(Gtk.EventControllerScrollFlags.BOTH_AXES)
        scroll_event_controller.connect('scroll', self.on_main_canvas_scrolled)
        self.main_canvas.add_controller(scroll_event_controller)

        motion_event_controller = Gtk.EventControllerMotion()
        motion_event_controller.connect('motion', self.on_main_canvas_motion)
        self.main_canvas.add_controller(motion_event_controller)

        motion_event_controller = Gtk.EventControllerMotion()
        motion_event_controller.connect('enter', self.on_scrollbar_entered)
        motion_event_controller.connect('leave', self.on_scrollbar_left)
        self.vertical_scrollbar.add_controller(motion_event_controller)

        motion_event_controller = Gtk.EventControllerMotion()
        motion_event_controller.connect('enter', self.on_scrollbar_entered)
        motion_event_controller.connect('leave', self.on_scrollbar_left)
        self.horizontal_scrollbar.add_controller(motion_event_controller)

        self.connect('close-request', self.on_close_request)

        if file is not None:
            self.load_file(file)

    def do_focus(self, direction: Gtk.DirectionType) -> bool:
        if self.main_canvas.has_focus():
            # When focusing on the main canvas, pressing tab key will keep the focus
            # on the main canvas
            return False
        return Gtk.Window.do_focus(self, direction)

    @Gtk.Template.Callback()
    def on_name_box_activated(self, widget: Gtk.Widget) -> None:
        """
        Callback function for when the name box is activated (e.g. when the user presses Enter).

        This function validates the input in the name box to ensure it follows the expected format
        and updates the selection accordingly. If the input is invalid, it resets the name box to
        the currently active cell's name.

        The expected format for the input is either a single cell name (e.g. "A1") or a range of cells
        (e.g. "A1:B2"). The input is case-insensitive and will be converted to uppercase.

        If the input is valid, it updates the selection to the specified cell(s) and schedule the main
        canvas to redraw.
        """
        if not re.fullmatch(r'([A-Za-z]+\d+):([A-Za-z]+\d+)|([A-Za-z]+\d+)', widget.get_text()):
            widget.set_text(self.selection.get_active_cell_name())
            widget.set_position(len(widget.get_text()))
            return

        self.selection.set_selected_cells_by_name(widget.get_text())
        widget.set_text(self.selection.get_active_cell_name().upper())
        widget.set_position(len(widget.get_text()))
        self.formula_bar.set_text(self.get_cell_data())

        active_cell = self.selection.get_active_cell()
        self.scroll_to_cell(active_cell)
        self.renderer.invalidate_cache()
        self.main_canvas.set_focusable(True)
        self.main_canvas.grab_focus()
        self.main_canvas.queue_draw()

    def on_name_box_pressed(self, event: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        """
        Callback function for when the name box is pressed.

        This function selects all text in the name box and sets it to be focused for editing.
        """
        self.name_box.select_region(0, len(self.name_box.get_text()))
        self.name_box.get_first_child().set_focus_on_click(True)
        self.name_box.get_first_child().grab_focus()

    def on_name_box_unfocused(self, event: Gtk.EventControllerFocus) -> None:
        """
        Callback function for when the name box loses focus.

        This function sets the position of the cursor in the name box to the end of the text
        when it loses focus, allowing the user to continue editing from the end of the text.
        """
        self.name_box.get_first_child().set_focus_on_click(False)

    def on_name_box_key_pressed(self, event: Gtk.EventControllerKey, keyval: int, keycode: int, state: Gdk.ModifierType) -> None:
        """Callback function for when a key is pressed on the name box."""
        if keyval == Gdk.KEY_Tab:
            self.on_name_box_activated(self.name_box)
        elif keyval == Gdk.KEY_Escape:
            self.name_box.set_text(self.selection.get_active_cell_name())
            self.main_canvas.set_focusable(True)
            self.main_canvas.grab_focus()

    @Gtk.Template.Callback()
    def on_formula_bar_activated(self, widget: Gtk.Widget, direction: Gtk.DirectionType = Gtk.DirectionType.DOWN) -> None:
        """
        Callback function for when the formula bar is activated (e.g., when the user presses Enter).

        This function sets the data in the selected cell to the value in the formula bar,
        advances the selection to the next cell, and redraws the main canvas.
        """
        row, col = self.selection.get_active_cell()
        self.set_cell_data(row, col, widget.get_text())
        if direction == Gtk.DirectionType.DOWN:
            active_cell = (row + 1, col)
        else:
            active_cell = (row, col + 1)
        self.selection.set_selected_cells(((active_cell), (active_cell)))
        self.name_box.set_text(self.selection.get_active_cell_name())
        self.formula_bar.set_text(self.get_cell_data())
        self.formula_bar.x_is_dirty = False

        active_cell = self.selection.get_active_cell()
        self.scroll_to_cell(active_cell)
        self.renderer.invalidate_cache()
        self.main_canvas.set_focusable(True)
        self.main_canvas.grab_focus()
        self.main_canvas.queue_draw()

    def on_formula_bar_changed(self, widget: Gtk.Widget) -> None:
        self.formula_bar.x_is_dirty = True

    def on_formula_bar_key_pressed(self, event: Gtk.EventControllerKey, keyval: int, keycode: int, state: Gdk.ModifierType) -> None:
        """Callback function for when a key is pressed on the formula bar."""
        if keyval == Gdk.KEY_Tab:
            if not self.formula_bar.x_is_dirty or self.get_cell_data() == self.formula_bar.get_text():
                return
            self.on_formula_bar_activated(self.formula_bar, Gtk.DirectionType.RIGHT)
        elif keyval == Gdk.KEY_Escape:
            self.formula_bar.set_text(self.get_cell_data())
            self.formula_bar.x_is_dirty = False
            self.main_canvas.set_focusable(True)
            self.main_canvas.grab_focus()

    def on_main_canvas_resized(self, widget: Gtk.Widget, width: int, height: int) -> None:
        """
        Callback function for when the main canvas is resized.

        This function resets the renderer cache if necessary.
        """
        if self._main_canvas_size == (0, 0):
            self._main_canvas_size = (width, height)
            return

        if self._main_canvas_size[0] < width or self._main_canvas_size[1] < height:
            self.renderer.invalidate_cache()

    def on_main_canvas_lmb_pressed(self, event: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        """
        Callback function for when the main canvas is pressed with the left mouse button.

        This function checks if the click coordinates are within the bounds of the main canvas.
        It sets the active cell based on the clicked coordinates and updates the name box with
        the name of the active cell. It also updates the selection to include the active cell
        and schedules the main canvas to redraw.
        """
        if x <= self.display.ROW_HEADER_WIDTH or y <= self.display.COLUMN_HEADER_HEIGHT:
            return

        # Set active cell
        self.selection.set_active_cell_by_coordinate((x + self.display.scroll_horizontal_position, y + self.display.scroll_vertical_position))
        self.selection.set_selected_cells(((self.selection.get_active_cell()), (self.selection.get_active_cell())))
        self.name_box.set_text(self.selection.get_active_cell_name())
        self.formula_bar.set_text(self.get_cell_data())
        self.main_canvas.set_focusable(True)
        self.main_canvas.grab_focus()
        self.main_canvas.queue_draw()

    def on_main_canvas_rmb_released(self, event: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        """
        Callback function for when the main canvas is released with the right mouse button.

        This function checks if the click coordinates are within the bounds of the main canvas.
        It triggers the context menu at the clicked coordinates.
        """
        def on_context_menu_closed(widget: Gtk.Widget) -> None:
            """Callback function for when the context menu is closed."""
            self.selection.set_selected_column(-1)
            self.selection.set_selected_locator((-1, -1))
            self.main_canvas.set_focusable(True)
            self.main_canvas.grab_focus()

        def find_popover_menu(type: type[Gtk.PopoverMenu]) -> Gtk.PopoverMenu | None:
            """Find an instance of target type of popover menu."""
            widget = self.main_container.get_last_child()
            while widget is not None:
                if isinstance(widget, type):
                    return widget
                widget = widget.get_prev_sibling()
            return None

        if x <= self.display.ROW_HEADER_WIDTH or y <= self.display.COLUMN_HEADER_HEIGHT:
            if x <= self.display.ROW_HEADER_WIDTH and y <= self.display.COLUMN_HEADER_HEIGHT:
                raise NotImplementedError # TODO: handle clicking on the top left corner area

            if x <= self.display.ROW_HEADER_WIDTH and self.display.CELL_DEFAULT_HEIGHT <= y:
                raise NotImplementedError # TODO: handle clicking on the row index cell

            if y <= self.display.CELL_DEFAULT_HEIGHT and self.display.ROW_HEADER_WIDTH <= x:
                # Get hovered locator index
                row_index, col_index = self.display.coordinate_to_index((x + self.display.scroll_horizontal_position, self.display.CELL_DEFAULT_HEIGHT))
                self.selection.set_selected_locator((-1, col_index))
                self.selection.set_previous_selected_locator((-1, col_index))

                # Find or create context menu
                if (context_menu := find_popover_menu(SheetColumnLocatorMenu)) is not None:
                    context_menu.set_colid(col_index)
                else:
                    context_menu = SheetColumnLocatorMenu(col_index, self.dbms)
                    context_menu.set_parent(self.main_container)
                context_menu.connect('closed', on_context_menu_closed)

                # Position context menu
                x_menu = self.display.get_column_position(col_index) + self.display.get_column_width(col_index) // 2 + self.display.ROW_HEADER_WIDTH - self.display.scroll_horizontal_position
                if x_menu < self.display.ROW_HEADER_WIDTH:
                    x_menu = self.display.ROW_HEADER_WIDTH + 1
                elif x_menu > self._main_canvas_size[0]:
                    x_menu = self.main_canvas.get_width() - 1
                rectangle = Gdk.Rectangle()
                rectangle.x = int(x_menu)
                rectangle.y = self.display.CELL_DEFAULT_HEIGHT
                rectangle.height = 1
                rectangle.width = 1
                context_menu.set_pointing_to(rectangle)

                # Show context menu
                context_menu.popup()
                self.main_canvas.queue_draw()

                return

            if self.display.CELL_DEFAULT_HEIGHT <= y \
                    and not self.display.cumulative_column_widths.is_empty() \
                    and x + self.display.scroll_horizontal_position <= self.display.cumulative_column_widths[-1] + self.display.ROW_HEADER_WIDTH:
                # Get hovered column index
                row_index, col_index = self.display.coordinate_to_index((x + self.display.scroll_horizontal_position, self.display.CELL_DEFAULT_HEIGHT))
                self.selection.set_selected_column(col_index)
                self.selection.set_previous_selected_column(col_index)

                # Find or create context menu
                if (context_menu := find_popover_menu(SheetColumnHeaderMenu)) is not None:
                    context_menu.set_colid(col_index)
                else:
                    context_menu = SheetColumnHeaderMenu(col_index, self.dbms)
                    context_menu.set_parent(self.main_container)
                    context_menu.action_set_enabled('app.sheet.column.reset-sort', False)
                    context_menu.action_set_enabled('app.sheet.column.reset-filter', False)
                context_menu.connect('closed', on_context_menu_closed)
                context_menu.update_filters()

                # Position context menu
                x_menu = self.display.get_column_position(col_index) + self.display.get_column_width(col_index) // 2 + self.display.ROW_HEADER_WIDTH - self.display.scroll_horizontal_position
                if x_menu < self.display.ROW_HEADER_WIDTH:
                    x_menu = self.display.ROW_HEADER_WIDTH + 1
                elif x_menu > self._main_canvas_size[0]:
                    x_menu = self.main_canvas.get_width() - 1
                rectangle = Gdk.Rectangle()
                rectangle.x = int(x_menu)
                rectangle.y = self.display.COLUMN_HEADER_HEIGHT
                rectangle.height = 1
                rectangle.width = 1
                context_menu.set_pointing_to(rectangle)

                # Show context menu
                context_menu.popup()
                self.main_canvas.queue_draw()

                return

    def on_main_canvas_unfocused(self, event: Gtk.EventControllerFocus) -> None:
        """
        Callback function for when the main canvas loses focus.

        This function prevents the main canvas from being focused by keyboard navigation when it loses focus.
        """
        self.main_canvas.set_focusable(False)

    def on_main_canvas_drag_update(self, event: Gtk.GestureDrag, offset_x: float, offset_y: float) -> None:
        """
        Callback function for when the main canvas is dragged.

        This function updates the selection based on the drag offset from the initial click position.
        It calculates the new selection range based on the initial click coordinates and the drag offsets.
        """
        _, *start_coord = event.get_start_point()
        if start_coord[0] <= self.display.ROW_HEADER_WIDTH or start_coord[1] <= self.display.COLUMN_HEADER_HEIGHT:
            return # prevent from dragging the worksheet header cells
        start_coord = (start_coord[0] + self.display.scroll_horizontal_position, start_coord[1] + self.display.scroll_vertical_position)
        end_coord = (start_coord[0] + offset_x, start_coord[1] + offset_y)
        if (self.selection.get_opposite_cell() == self.display.coordinate_to_index(end_coord)):
            return # skip redraw if the opposite active cell is being selected
        self.selection.set_selected_cells_by_coordinates((start_coord, end_coord))
        self.main_canvas.queue_draw()

    def on_main_canvas_key_pressed(self, event: Gtk.EventControllerKey, keyval: int, keycode: int, state: Gdk.ModifierType) -> None:
        """
        Callback function for when a key is pressed on the main canvas.

        This function defines the behavior when a key is pressed on the main canvas.
        It updates the active cell based on the pressed key and modifier keys.
        It also updates the selection to include the active cell and schedules the main canvas to redraw.
        """
        active_cell = self.selection.get_active_cell()
        opposite_cell = self.selection.get_opposite_cell()
        target_cell = active_cell

        match keyval:
            case Gdk.KEY_Tab | Gdk.KEY_ISO_Left_Tab:
                if state == Gdk.ModifierType.SHIFT_MASK:
                    target_cell = (active_cell[0], max(0, active_cell[1] - 1))
                else:
                    target_cell = (active_cell[0], active_cell[1] + 1)

            case Gdk.KEY_Return:
                if state == Gdk.ModifierType.SHIFT_MASK:
                    target_cell = (max(0, active_cell[0] - 1), active_cell[1])
                else:
                    target_cell = (active_cell[0] + 1, active_cell[1])

            case Gdk.KEY_Left:
                if state == Gdk.ModifierType.CONTROL_MASK:
                    target_cell = (active_cell[0], 0)
                elif state == Gdk.ModifierType.SHIFT_MASK:
                    target_cell = (active_cell, (opposite_cell[0], max(0, opposite_cell[1] - 1)))
                elif state == (Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK):
                    target_cell = (active_cell, (opposite_cell[0], 0))
                else:
                    target_cell = (active_cell[0], max(0, active_cell[1] - 1))

            case Gdk.KEY_Right:
                if state == Gdk.ModifierType.CONTROL_MASK:
                    target_cell = (active_cell[0], max(0, self.dbms.get_shape()[1] - 1))
                elif state == Gdk.ModifierType.SHIFT_MASK:
                    target_cell = (active_cell, (opposite_cell[0], opposite_cell[1] + 1))
                elif state == (Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK):
                    target_cell = (active_cell, (opposite_cell[0], max(0, self.dbms.get_shape()[1] - 1)))
                else:
                    target_cell = (active_cell[0], active_cell[1] + 1)

            case Gdk.KEY_Up:
                if state == Gdk.ModifierType.CONTROL_MASK:
                    target_cell = (0, active_cell[1])
                elif state == Gdk.ModifierType.SHIFT_MASK:
                    target_cell = (active_cell, (max(0, opposite_cell[0] - 1), opposite_cell[1]))
                elif state == (Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK):
                    target_cell = (active_cell, (0, opposite_cell[1]))
                else:
                    target_cell = (max(0, active_cell[0] - 1), active_cell[1])

            case Gdk.KEY_Down:
                if state == Gdk.ModifierType.CONTROL_MASK:
                    target_cell = (max(0, self.dbms.get_shape()[0] - 1), active_cell[1])
                elif state == Gdk.ModifierType.SHIFT_MASK:
                    target_cell = (active_cell, (opposite_cell[0] + 1, opposite_cell[1]))
                elif state == (Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK):
                    target_cell = (active_cell, (max(0, self.dbms.get_shape()[0] - 1), opposite_cell[1]))
                else:
                    target_cell = (active_cell[0] + 1, active_cell[1])

            case _:
                if state == Gdk.ModifierType.CONTROL_MASK \
                        or state == (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK):
                    return
                if Gdk.KEY_space <= keyval <= Gdk.KEY_asciitilde:
                    self.formula_bar.grab_focus()
                    self.formula_bar.set_text(chr(keyval))
                    self.formula_bar.set_position(1)
                elif keyval == Gdk.KEY_BackSpace:
                    self.formula_bar.grab_focus()
                    self.formula_bar.set_text('')
                    self.formula_bar.set_position(1)
                elif keyval == Gdk.KEY_Delete:
                    # TODO: add support for multiple cells
                    self.set_cell_data(*target_cell, None)
                    self.formula_bar.set_text('')
                    self.renderer.invalidate_cache()
                    self.main_canvas.queue_draw()
                return

        if single_target := all(isinstance(i, int) for i in target_cell):
            self.selection.set_selected_cells((target_cell, target_cell))
        else:
            self.selection.set_selected_cells(target_cell)
        self.name_box.set_text(self.selection.get_active_cell_name())
        self.formula_bar.set_text(self.get_cell_data())

        active_cell = self.selection.get_active_cell()
        opposite_cell = self.selection.get_opposite_cell()
        if (single_target and self.scroll_to_cell(active_cell)) or self.scroll_to_cell(opposite_cell):
            self.renderer.invalidate_cache()
        self.main_canvas.queue_draw()

    def on_main_canvas_scrolled(self, event: Gtk.EventControllerScroll, dx: float, dy: float) -> bool:
        """
        Callback function for when the main canvas is scrolled.

        This function updates the scroll positions based on the scroll offsets and modifier keys.
        """
        if event.get_current_event_state() == Gdk.ModifierType.SHIFT_MASK and (dy > 0 or dy < 0):
            dx, dy = dy, 0
        elif event.get_current_event_state() == Gdk.ModifierType.SHIFT_MASK and (dx > 0 or dx < 0):
            dy, dx = dx, 0
        dx = int(dx * self.SCROLL_X_MULTIPLIER)
        dy = int(dy * self.SCROLL_Y_MULTIPLIER)

        if dy < 0 and self.display.scroll_vertical_position == 0:
            return False
        if dx < 0 and self.display.scroll_horizontal_position == 0:
            return False

        self.display.scroll_vertical_position = max(0, self.display.scroll_vertical_position + dy)
        self.display.scroll_horizontal_position = max(0, self.display.scroll_horizontal_position + dx)
        self.renderer.invalidate_cache()
        self.main_canvas.queue_draw()

        return True

    def on_main_canvas_motion(self, event: Gtk.EventControllerMotion, x: float, y: float) -> None:
        """Callback function for when the main canvas is hovered."""
        cursor_name = 'cell'
        if x <= self.display.ROW_HEADER_WIDTH or y <= self.display.COLUMN_HEADER_HEIGHT:
            if x <= self.display.ROW_HEADER_WIDTH and y <= self.display.COLUMN_HEADER_HEIGHT:
                cursor_name = 'cell'
            elif \
                (
                    not self.display.cumulative_column_widths.is_empty()
                    and x + self.display.scroll_horizontal_position <= self.display.cumulative_column_widths[-1] + self.display.ROW_HEADER_WIDTH
                    and y <= self.display.CELL_DEFAULT_HEIGHT
                ) \
                    or x <= self.display.ROW_HEADER_WIDTH:
                cursor_name = 'pointer'
            else:
                cursor_name = 'default'
        else:
            cursor_name = 'cell'

        if cursor_name != self._main_canvas_cursor_name:
            print_log(f'Changing main canvas cursor to: {cursor_name}', Log.DEBUG)
            self.main_canvas.set_cursor(Gdk.Cursor.new_from_name(cursor_name, Gdk.Cursor.new_from_name('default')))
            self._main_canvas_cursor_name = cursor_name

    def on_scrollbar_entered(self, event: Gtk.EventControllerMotion, x: float, y: float) -> None:
        """Callback function for when the scrollbar is entered."""
        event.get_widget().add_css_class('hovering')

    def on_scrollbar_left(self, event: Gtk.EventControllerMotion) -> None:
        """Callback function for when the scrollbar is left."""
        event.get_widget().remove_css_class('hovering')

    def on_close_request(self, window: Gtk.Window) -> bool:
        """
        Callback function for when the window is closed.

        This function removes the temporary data files and destroys the window.
        It also checks if the .erquet file exists in the temporary directory and
        deletes it in case the program crashed or exited unexpectedly last time.

        Returns:
            bool: True if the window should be closed, False otherwise.
        """
        import os
        for temp_file_path in self.dbms.temp_data_file_paths:
            print_log(f'Removing temporary file: {temp_file_path}', Log.DEBUG)
            os.remove(temp_file_path)

        import tempfile
        for file in os.listdir(tempfile.gettempdir()):
            if file.endswith('.erquet'):
                print_log(f'Removing temporary file: {file}', Log.DEBUG)
                os.remove(os.path.join(os.getcwd(), 'temp', file))

        self.destroy()
        return True

    def get_cell_data(self) -> str:
        """
        Retrieve the data from the selected cell.

        Returns:
            str: The data from the selected cell, or an empty string if the selected cell is out of bounds.
        """
        df_shape = self.dbms.get_shape()
        row, col = self.selection.get_active_cell()
        if df_shape[0] <= row or df_shape[1] <= col:
            return ''
        cell_data = self.dbms.get_data(row, col)
        return str('' if cell_data is None else cell_data)

    def set_cell_data(self, row: int, col: int, value: any) -> bool:
        """
        Set the data in the selected cell.

        Args:
            row: The row index of the cell.
            col: The column index of the cell.
            value: The value to be set in the cell.

        Returns:
            bool: True if the cell data is successfully set, False otherwise.
        """
        print_log(f"Updating cell data at index ({format(row, ",d")}, {format(col, ",d")}) to: {value}")
        df_shape = self.dbms.get_shape()
        if df_shape[0] <= row or df_shape[1] <= col:
            print_log(f"Cannot update cell data at index ({format(row, ",d")}, {format(col, ",d")}) due to out of bounds", Log.NOTICE)
            return False # TODO: implement dynamic data frame(?)
        if self.dbms.set_data(row, col, value):
            self.dbms.summary_fill_counts(col)
        else:
            col_type = self.dbms.get_dtypes()[col]
            cell_name = self.selection.index_to_name((row, col))
            if str(col_type).startswith('Categorical'):
                col_type = 'Categorical'
            self.show_toast_message(f'Incorrect {col_type} value: \'{value}\' at {cell_name}')
            return False
        return True

    def scroll_to_cell(self, target_cell: tuple[int, int]) -> bool:
        """Scroll the main canvas to the active cell."""
        viewport_height = self.main_canvas.get_height() - self.display.COLUMN_HEADER_HEIGHT
        viewport_width = self.main_canvas.get_width() - self.display.ROW_HEADER_WIDTH
        return self.display.scroll_to_cell(target_cell, viewport_height, viewport_width)

    def load_file(self, file: Gio.File) -> None:
        """
        Load a file asynchronously using a background thread.

        This method initiates the loading and parsing of a CSV file specified
        by the 'file' argument. It provides real-time feedback by updating the
        status message while the file is being processed. The actual parsing
        is done in a separate thread to keep the UI responsive, and upon
        successful parsing, the resulting DataFrame is stored in data_frame.
        The method also handles any exceptions during the process and logs
        relevant information and errors.

        TODO: Implement data selection feature before loading the entire file.
              See https://docs.pola.rs/api/python/stable/reference/api/polars.scan_csv.html
        TODO: Handle parsing errors, e.g. if some rows are not complete or consistent

        Args:
            file: A Gio.File object representing the file to be loaded.
        """
        def assign_file() -> None:
            """Assigns the given file to the window's file attribute."""
            self.dbms.file = file

        def expand_column_header_height() -> None:
            """Expands the column header height to fit the header of the data frame."""
            print_log('Calculating column header height...', Log.DEBUG)
            self.display.COLUMN_HEADER_HEIGHT += self.display.CELL_DEFAULT_HEIGHT * 2

        def load_file_thread() -> None:
            """
            A background thread to load and parse a file.

            This method is responsible for loading a CSV file specified by the
            'file' argument in a separate thread, providing real-time feedback by
            updating the status message while the file is being processed. The
            actual parsing is done in a separate thread to keep the UI responsive,
            and upon successful parsing, the resulting DataFrame is stored in
            dbms.data_frame. The method also handles any exceptions during the
            process and logs relevant information and errors.
            """
            try:
                start_time = time.time()
                if WITH_ROW_INDEX:
                    self.dbms.data_frame = polars.read_csv(file.get_path()).with_row_index(offset=1)
                else:
                    self.dbms.data_frame = polars.read_csv(file.get_path())
                end_time = time.time()
                file_size = file.query_info('standard::size', Gio.FileQueryInfoFlags.NONE, None).get_size() / (1024 * 1024)
                print_log(f'Loaded and parsed file {file.get_path()} of size {format(file_size, ",.2f")} MB in {end_time - start_time:.6f} seconds')
                print_log(f'Quick preview of the file: {self.dbms.data_frame.head()}', Log.DEBUG)
            except Exception as e:
                print_log(f'Failed to load file: {e}', Log.WARNING)

            if self.dbms.data_frame.is_empty():
                self.show_toast_message('We\'re sorry, we couldn\'t load your workbook.')
            else:
                assign_file()
                expand_column_header_height()
                GLib.idle_add(self.calculate_column_widths)
                GLib.idle_add(self.calculate_cumulative_column_widths)
                GLib.idle_add(self.update_project_status)
                GLib.idle_add(self.dbms.summary_fill_counts)
                GLib.idle_add(self.renderer.invalidate_cache)
                GLib.idle_add(self.main_canvas.queue_draw)

        threading.Thread(target=load_file_thread, daemon=True).start()
        print_log(f'Loading file {file.get_path()} in background...', Log.DEBUG)
        GLib.idle_add(self.status_message.set_text, 'Loading your workbook...')

    def calculate_column_widths(self) -> None:
        """
        Automatically fits the column header width to the content.

        It starts by reading the first 200 rows of the data frame, using Cairo to measure
        the width of the longest column header, and stores the result in display.cell_sizes.
        """
        display = Gdk.Display.get_default()
        monitor = display.get_monitors()[0]
        max_width = monitor.get_geometry().width // 8
        sample_data = self.dbms.data_frame.head(200)
        self.display.column_widths = [0] * self.dbms.get_shape()[1]

        font_desc = Gtk.Widget.create_pango_context(self.main_canvas).get_font_description()
        system_font = font_desc.get_family() if font_desc else 'Sans'
        font_desc = Pango.font_description_from_string(f'{system_font} Normal Bold {self.renderer.FONT_SIZE}')
        context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 0, 0))
        layout = PangoCairo.create_layout(context)
        layout.set_font_description(font_desc)

        print_log('Calculating preferred column widths...', Log.DEBUG)
        for index, col_name in enumerate(self.dbms.get_columns()):
            sample_data = sample_data.with_columns(polars.col(col_name).cast(polars.Utf8))
            max_length = sample_data.select(polars.col(col_name).str.len_chars().max()).item()
            if max_length is not None:
                layout.set_text('0' * max_length, -1)
            else:
                layout.set_text('0', -1)
            text_width = layout.get_size()[0] / Pango.SCALE
            preferred_width = text_width + 2 * self.display.CELL_DEFAULT_PADDING
            self.display.column_widths[index] = max(self.display.CELL_DEFAULT_WIDTH, min(max_width, int(preferred_width)))

    def calculate_cumulative_column_widths(self) -> None:
        """Calculates the cumulative column widths."""
        print_log('Calculating cumulative column widths...', Log.DEBUG)
        self.display.cumulative_column_widths = polars.Series('cumulative_column_widths', self.display.column_widths).cum_sum()

    def update_project_status(self) -> None:
        """Updates the project status."""
        print_log('Updating project status...', Log.DEBUG)
        self.set_title(f'{self.dbms.file.get_basename()} – Eruo Data Studio')
        self.formula_bar.set_text(self.get_cell_data())
        file_size = self.dbms.file.query_info('standard::size', Gio.FileQueryInfoFlags.NONE, None).get_size() / (1024 * 1024)
        self.status_message.set_text(f'File: {self.dbms.file.get_basename()} | Size: {format(file_size, ",.2f")}MB | '
                                     f'Rows: {format(self.dbms.get_shape()[0], ",d")} | Columns: {format(self.dbms.get_shape()[1], ",d")} | '
                                     f'Memory: {format(self.dbms.data_frame.estimated_size("mb"), ",.2f")}MB')

    def show_toast_message(self, message: str) -> None:
        """Shows a toast message."""
        print_log(f'Showing toast message: {message}', Log.DEBUG)
        self.toast_container.add_toast(Adw.Toast.new(message))