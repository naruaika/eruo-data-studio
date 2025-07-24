# sheet_widget.py
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

from gi.repository import Gdk, GObject
import cairo

from .sheet_display import SheetDisplay

class SheetWidget(GObject.Object):
    __gtype_name__ = 'SheetWidget'

    def __init__(self, x: int, y: int, width: int, height: int, display: SheetDisplay) -> None:
        super().__init__()

        self.x = x
        self.y = y

        self.width = width
        self.height = height

        self.position: str = 'relative'
        self.cursor: Gdk.Cursor = Gdk.Cursor.new_from_name('default')

        self.display = display

    def get_x(self) -> int:
        if self.position == 'absolute':
            return self.x + self.display.scroll_x_position
        return self.x

    def get_y(self) -> int:
        if self.position == 'absolute':
            return self.y + self.display.scroll_y_position
        return self.y

    def get_rx(self) -> int:
        return self.x

    def get_ry(self) -> int:
        return self.y

    def get_width(self) -> int:
        return self.width

    def get_height(self) -> int:
        return self.height

    def contains(self, x: int, y: int) -> bool:
        return self.get_rx() <= x <= self.get_rx() + self.width and \
               self.get_ry() <= y <= self.get_ry() + self.height

    def do_on_enter(self, x: int, y: int) -> None:
        pass

    def do_on_leave(self, x: int, y: int) -> None:
        pass

    def do_on_click(self, x: int, y: int) -> None:
        pass

    def do_render(self, context: cairo.Context, width: int, height: int, display: SheetDisplay, prefers_dark: bool) -> None:
        if self.position == 'relative':
            context.translate(-display.scroll_x_position, -display.scroll_y_position)



class SheetAutoFilter(SheetWidget):
    __gtype_name__ = 'SheetAutoFilter'

    def __init__(self, x: int, y: int, width: int, height: int, display: SheetDisplay, callback: callable) -> None:
        super().__init__(x, y, width, height, display)

        self.callback = callback

        self.position = 'absolute'
        self.cursor = Gdk.Cursor.new_from_name('pointer', Gdk.Cursor.new_from_name('default'))

    def get_x(self) -> int:
        return self.x

    def get_rx(self) -> int:
        return self.x - self.display.scroll_x_position

    def get_ry(self) -> int:
        if self.display.scroll_y_position > 0:
            return self.y - self.display.column_header_height
        return self.y

    def contains(self, x: int, y: int) -> bool:
        if x < self.display.row_header_width:
            return False
        return self.get_rx() <= x <= self.get_rx() + self.width and \
               self.get_ry() <= y <= self.get_ry() + self.height

    def do_on_click(self, x: int, y: int) -> None:
        self.callback(x, y)

    def do_render(self, context: cairo.Context, width: int, height: int, prefers_dark: bool) -> None:
        context.rectangle(self.display.row_header_width, 0, width, height)
        context.clip()

        # TODO: implement render cache if possible

        x = self.get_rx()
        y = self.get_ry()

        background_color = (0.0, 0.0, 0.0)
        if prefers_dark:
            background_color = (1.0, 1.0, 1.0)

        context.set_source_rgb(*background_color)

        # Draw the background fill
        context.rectangle(x, y, self.width, self.height)
        context.fill()

        stroke_color = (1.0, 1.0, 1.0)
        if prefers_dark:
            stroke_color = (0.0, 0.0, 0.0)

        context.set_source_rgb(*stroke_color)
        context.set_hairline(True)

        # Draw the left diagonal line
        start_x = x + 3
        start_y = y + 4
        end_x = x + self.width / 2
        end_y = y + self.height - 4
        context.move_to(start_x, start_y)
        context.line_to(end_x, end_y)

        # Draw the right diagonal line
        start_x = x + self.width / 2
        start_y = y + self.height - 4
        end_x = x + self.width - 3
        end_y = y + 4
        context.move_to(start_x, start_y)
        context.line_to(end_x, end_y)

        context.stroke()