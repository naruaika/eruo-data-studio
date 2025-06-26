# display.py
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

from gi.repository import GObject

from .utils import print_log, Log

class Display(GObject.Object):
    __gtype_name__ = 'Display'

    ROW_HEADER_WIDTH: int = 40
    CELL_DEFAULT_HEIGHT: int = 20
    CELL_DEFAULT_WIDTH: int = 60

    scroll_vertical_position: int = 0
    scroll_horizontal_position: int = 0

    def __init__(self) -> None:
        """
        Initializes the Display class.

        This class is responsible for managing the display settings of the Eruo Data Studio.
        It defines constants for row header width, cell dimensions, scroll positions, and other
        display-related properties.
        """
        super().__init__()

    def scroll_to_cell(self, cell: tuple[int, int], viewport_height: int, viewport_width: int) -> None:
        """
        Scrolls the display to a specific cell.

        This method sets the scroll positions to the appropriate values to display the specified
        cell within the viewport.

        Args:
            cell: A tuple containing the row and column indices of the cell to scroll to.
            viewport_height: The height of the viewport excluding the column header.
            viewport_width: The width of the viewport excluding the row header.
        """
        print_log(f'Scrolling to the target cell at index {cell}...')

        # Skip if the target cell is already visible
        if self.scroll_vertical_position < cell[0] * self.CELL_DEFAULT_HEIGHT + self.CELL_DEFAULT_HEIGHT < self.scroll_vertical_position + viewport_height and \
                self.scroll_horizontal_position < cell[1] * self.CELL_DEFAULT_WIDTH + self.CELL_DEFAULT_WIDTH < self.scroll_horizontal_position + viewport_width:
            print_log('Target cell is already visible in the viewport', Log.DEBUG)
            return

        # Scroll down when the target cell is below the viewport so that the target cell is near the bottom of the viewport
        if cell[0] * self.CELL_DEFAULT_HEIGHT + self.CELL_DEFAULT_HEIGHT > self.scroll_vertical_position + viewport_height:
            self.scroll_vertical_position = cell[0] * self.CELL_DEFAULT_HEIGHT - (viewport_height - (viewport_height % self.CELL_DEFAULT_HEIGHT)) + self.CELL_DEFAULT_HEIGHT

        # Scroll up when the target cell is above the viewport so that the target cell is exactly at the top of the viewport
        if cell[0] * self.CELL_DEFAULT_HEIGHT < self.scroll_vertical_position:
            self.scroll_vertical_position = cell[0] * self.CELL_DEFAULT_HEIGHT

        # Scroll to the right when the target cell is to the right of the viewport so that the target cell is near the right of the viewport
        if cell[1] * self.CELL_DEFAULT_WIDTH + self.CELL_DEFAULT_WIDTH > self.scroll_horizontal_position + viewport_width:
            self.scroll_horizontal_position = cell[1] * self.CELL_DEFAULT_WIDTH - (viewport_width - (viewport_width % self.CELL_DEFAULT_WIDTH)) + self.CELL_DEFAULT_WIDTH

        # Scroll to the left when the target cell is to the left of the viewport so that the target cell is exactly at the left of the viewport
        if cell[1] * self.CELL_DEFAULT_WIDTH < self.scroll_horizontal_position:
            self.scroll_horizontal_position = cell[1] * self.CELL_DEFAULT_WIDTH
