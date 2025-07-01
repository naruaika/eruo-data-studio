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

import polars

from gi.repository import GObject

from .dbms import WITH_ROW_INDEX
from .utils import print_log, Log

class Display(GObject.Object):
    __gtype_name__ = 'Display'

    ROW_HEADER_WIDTH: int = 40
    COLUMN_HEADER_HEIGHT: int = 20
    CELL_DEFAULT_HEIGHT: int = 20
    CELL_DEFAULT_WIDTH: int = 65
    CELL_DEFAULT_PADDING: int = 6
    ICON_DEFAULT_SIZE: int = 10

    scroll_vertical_position: int = 0
    scroll_horizontal_position: int = 0

    column_widths: list[int] = []
    cumulative_column_widths: polars.Series = polars.Series()

    def __init__(self) -> None:
        """
        Initializes the Display class.

        This class is responsible for managing the display settings of the Eruo Data Studio.
        It defines constants for row header width, cell dimensions, scroll positions, and other
        display-related properties.
        """
        super().__init__()

    def scroll_to_cell(self, cell: tuple[int, int], viewport_height: int, viewport_width: int) -> bool:
        """
        Scrolls the display to a specific cell.

        This method sets the scroll positions to the appropriate values to display the specified
        cell within the viewport.

        Args:
            cell: A tuple containing the row and column indices of the cell to scroll to.
            viewport_height: The height of the viewport excluding the column header.
            viewport_width: The width of the viewport excluding the row header.
        """
        print_log(f'Scrolling to the target cell at index ({format(cell[0], ",d")}, {format(cell[1], ",d")})...')

        bottom_offset = (cell[0] + 1) * self.CELL_DEFAULT_HEIGHT
        top_offset = cell[0] * self.CELL_DEFAULT_HEIGHT
        right_offset = (cell[1] + 1) * self.CELL_DEFAULT_WIDTH
        left_offset = cell[1] * self.CELL_DEFAULT_WIDTH

        if not self.cumulative_column_widths.is_empty():
            right_offset = self.get_column_position(cell[1] + 1)
            left_offset = self.get_column_position(cell[1])

        # Skip if the target cell is already visible
        if self.scroll_vertical_position <= top_offset and bottom_offset <= self.scroll_vertical_position + viewport_height and \
                self.scroll_horizontal_position <= left_offset and right_offset <= self.scroll_horizontal_position + viewport_width:
            print_log('Target cell is already visible in the viewport', Log.DEBUG)
            return False

        # Scroll down when the target cell is below the viewport so that the target cell is near the bottom of the viewport
        if bottom_offset > self.scroll_vertical_position + viewport_height:
            self.scroll_vertical_position = top_offset - (viewport_height - (viewport_height % self.CELL_DEFAULT_HEIGHT)) + self.CELL_DEFAULT_HEIGHT

        # Scroll up when the target cell is above the viewport so that the target cell is exactly at the top of the viewport
        if top_offset < self.scroll_vertical_position:
            self.scroll_vertical_position = top_offset

        # Scroll to the right when the target cell is to the right of the viewport so that the target cell is near the right of the viewport
        if right_offset > self.scroll_horizontal_position + viewport_width:
            self.scroll_horizontal_position = left_offset - (viewport_width - (viewport_width % self.CELL_DEFAULT_WIDTH)) + self.get_column_width(cell[1])

        # Scroll to the left when the target cell is to the left of the viewport so that the target cell is exactly at the left of the viewport
        if left_offset < self.scroll_horizontal_position:
            self.scroll_horizontal_position = left_offset

        return True

    def get_column_position(self, col_index: int) -> int:
        """Calculates the x-coordinate for the start of a given column."""
        if col_index == 0:
            return 0
        elif col_index < self.cumulative_column_widths.shape[0]:
            return self.cumulative_column_widths[col_index - 1]
        else:
            return self.cumulative_column_widths[-1] + (col_index - self.cumulative_column_widths.shape[0]) * self.CELL_DEFAULT_WIDTH

    def get_column_width(self, col_index: int) -> int:
        """Retrieves the width of a single column."""
        if col_index < len(self.column_widths):
            return self.column_widths[col_index]
        else:
            return self.CELL_DEFAULT_WIDTH

    def coordinate_to_column(self, x: int) -> int:
        """
        Returns the index of the column at the specified x-coordinate.

        Args:
            x: The x-coordinate of the column.

        Returns:
            int: The index of the column at the specified x-coordinate.
        """
        if self.cumulative_column_widths.is_empty():
            return x // self.CELL_DEFAULT_WIDTH

        if x >= self.cumulative_column_widths[-1]:
            return len(self.cumulative_column_widths) + (x - self.cumulative_column_widths[-1] + WITH_ROW_INDEX) // self.CELL_DEFAULT_WIDTH

        return self.cumulative_column_widths.search_sorted(x, 'left')

    def coordinate_to_index(self, coordinate: tuple[float, float]) -> tuple[int, int]:
        """
        Converts a coordinate to its corresponding row and column indices.

        The coordinate is expected to be in the format (x, y), where x is the horizontal position
        and y is the vertical position relative to the display's cell dimensions.

        Args:
            coordinate: A tuple containing the x and y coordinates of the cell.

        Returns:
            A tuple containing the row and column indices of the cell.
        """
        x, y = coordinate
        row = int((y - self.COLUMN_HEADER_HEIGHT) // self.CELL_DEFAULT_HEIGHT)
        col = self.coordinate_to_column(int(x) - self.ROW_HEADER_WIDTH)
        return (row, col)