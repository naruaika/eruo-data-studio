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
from .sheet_document import SheetDocument
from .sheet_selection import SheetCornerLocatorCell, SheetTopLocatorCell, SheetLeftLocatorCell

@Gtk.Template(resource_path='/com/macipra/eruo/ui/sheet-view.ui')
class SheetView(Gtk.Box):
    __gtype_name__ = 'SheetView'

    __gsignals__ = {
        'select-by-keypress': (GObject.SIGNAL_RUN_FIRST, None, (int, int)),
        'select-by-motion': (GObject.SIGNAL_RUN_FIRST, None, (int, int)),
        'pointer-moved': (GObject.SIGNAL_RUN_FIRST, None, (int, int)),
        'pointer-released': (GObject.SIGNAL_RUN_FIRST, None, (int, int)),
        'open-inline-formula': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
        'open-context-menu': (GObject.SIGNAL_RUN_FIRST, None, (int, int, str)),
    }

    horizontal_scrollbar = Gtk.Template.Child()
    vertical_scrollbar = Gtk.Template.Child()

    main_canvas = Gtk.Template.Child()

    def __init__(self, document: SheetDocument, **kwargs) -> None:
        super().__init__(**kwargs)

        self.document = document

        scroll_event_controller = Gtk.EventControllerScroll()
        scroll_event_controller.set_flags(Gtk.EventControllerScrollFlags.BOTH_AXES)
        scroll_event_controller.connect('scroll', self.on_main_canvas_scrolled)
        self.main_canvas.add_controller(scroll_event_controller)

        drag_event_controller = Gtk.GestureDrag()
        drag_event_controller.connect('drag-update', self.on_main_canvas_drag_update)
        self.main_canvas.add_controller(drag_event_controller)

        motion_event_controller = Gtk.EventControllerMotion()
        motion_event_controller.connect('motion', self.on_main_canvas_motion)
        self.main_canvas.add_controller(motion_event_controller)

        focus_event_controller = Gtk.EventControllerFocus()
        focus_event_controller.connect('leave', self.on_main_canvas_unfocused)
        self.main_canvas.add_controller(focus_event_controller)

        click_event_controller = Gtk.GestureClick()
        click_event_controller.connect('pressed', self.on_main_canvas_lmb_pressed)
        click_event_controller.connect('released', self.on_main_canvas_lmb_released)
        self.main_canvas.add_controller(click_event_controller)

        click_event_controller = Gtk.GestureClick()
        click_event_controller.set_button(3)
        click_event_controller.connect('pressed', self.on_main_canvas_rmb_pressed)
        click_event_controller.connect('released', self.on_main_canvas_rmb_released)
        self.main_canvas.add_controller(click_event_controller)

        key_event_controller = Gtk.EventControllerKey()
        key_event_controller.connect('key-pressed', self.on_main_canvas_key_pressed)
        self.main_canvas.add_controller(key_event_controller)

        self.main_canvas_width = 0
        self.main_canvas_height = 0
        self.main_canvas.connect('resize', self.on_main_canvas_resized)

        self.default_cursor = Gdk.Cursor.new_from_name('cell', Gdk.Cursor.new_from_name('default'))
        self.main_canvas.set_cursor(self.default_cursor)

        motion_event_controller = Gtk.EventControllerMotion()
        motion_event_controller.connect('enter', self.on_scrollbar_entered)
        motion_event_controller.connect('leave', self.on_scrollbar_left)
        self.vertical_scrollbar.add_controller(motion_event_controller)

        motion_event_controller = Gtk.EventControllerMotion()
        motion_event_controller.connect('enter', self.on_scrollbar_entered)
        motion_event_controller.connect('leave', self.on_scrollbar_left)
        self.horizontal_scrollbar.add_controller(motion_event_controller)

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
        self.emit('pointer-moved', x, y)

    def on_main_canvas_unfocused(self, event: Gtk.EventControllerFocus) -> None:
        self.main_canvas.set_focusable(False)

    def on_main_canvas_lmb_pressed(self, event: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        # Request to open inline formula on double click
        if n_press >= 2:
            cell_data = self.document.selection.cell_data
            if cell_data is None:
                cell_data = ''
            cell_data = str(cell_data)

            self.emit('open-inline-formula', cell_data)

            return

        self.document.select_element_from_point(x, y, event.get_current_event_state())
        self.main_canvas.set_focusable(True)
        self.main_canvas.grab_focus()
        if self.document.check_selection_changed():
            self.main_canvas.queue_draw()

    def on_main_canvas_lmb_released(self, event: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        self.emit('pointer-released', x, y)

    def on_main_canvas_rmb_pressed(self, event: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        pass

    def on_main_canvas_rmb_released(self, event: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        if not self.document.check_selection_contains_point(x, y):
            self.document.select_element_from_point(x, y)
            self.main_canvas.queue_draw()

        cell_x = self.document.display.get_cell_x_from_point(x)
        cell_y = self.document.display.get_cell_y_from_point(y)

        if cell_x == 0 and cell_y == 0:
            return # no applicable context menu for corner locator

        self.emit('pointer-released', x, y)
        self.emit('open-context-menu', x, y, 'cell')

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
        if state == (Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.ALT_MASK) \
                or state == (Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK) \
                or state == (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.ALT_MASK) \
                or state == Gdk.ModifierType.CONTROL_MASK \
                or state == Gdk.ModifierType.ALT_MASK:
            return

        if Gdk.KEY_space <= keyval <= Gdk.KEY_asciitilde:
            self.emit('open-inline-formula', chr(keyval))
            return

        if keyval == Gdk.KEY_BackSpace:
            self.emit('open-inline-formula', '')
            return

    def on_scrollbar_entered(self, event: Gtk.EventControllerMotion, x: float, y: float) -> None:
        event.get_widget().add_css_class('hovering')

    def on_scrollbar_left(self, event: Gtk.EventControllerMotion) -> None:
        event.get_widget().remove_css_class('hovering')

    def on_main_canvas_resized(self, drawing_area: Gtk.DrawingArea, width: int, height: int) -> None:
        if self.main_canvas_width == width and self.main_canvas_height == height:
            return

        active = self.document.selection.current_active_range

        if isinstance(active, SheetCornerLocatorCell):
            active.width = width
            active.height = height
        if isinstance(active, SheetTopLocatorCell):
            active.height = height
        if isinstance(active, SheetLeftLocatorCell):
            active.width = width

        self.document.auto_adjust_scrollbars_by_scroll()

        # Invalidate some parts of the render cache
        if 'content' in self.document.renderer.render_caches and \
                (self.main_canvas_width < width or self.main_canvas_height < height):
            if (x_offset := width - self.main_canvas_width) != 0:
                self.document.renderer.render_caches['content']['x_pos'] -= x_offset
                self.document.renderer.render_caches['content']['x_trans'] = x_offset

            if (y_offset := height - self.main_canvas_height) != 0:
                self.document.renderer.render_caches['content']['y_pos'] -= y_offset
                self.document.renderer.render_caches['content']['y_trans'] = y_offset

            # We currently don't support resizing in diagonal axis,
            # so we force clear the entire cache instead
            if x_offset != 0 and y_offset != 0:
                self.document.renderer.render_caches = {}

        self.main_canvas_width = width
        self.main_canvas_height = height