# sheet_display.py
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
import polars
import re

from .sheet_document import SheetDocument

class SheetDisplay(GObject.Object):
    __gtype_name__ = 'SheetDisplay'

    DEFAULT_CELL_HEIGHT: int = 20
    DEFAULT_CELL_WIDTH: int = 65
    DEFAULT_CELL_PADDING: int = 6

    ICON_SIZE: float = 12
    FONT_SIZE: float = 12

    row_header_width: int = 40
    column_header_height: int = 20

    scroll_increment: int = 3
    page_increment: int = 20

    scroll_y_position: int = 0
    scroll_x_position: int = 0

    row_visibility_flags: polars.Series = polars.Series(dtype=polars.Boolean)
    column_visibility_flags: polars.Series = polars.Series(dtype=polars.Boolean)

    row_visible_series: polars.Series = polars.Series(dtype=polars.UInt32)
    column_visible_series: polars.Series = polars.Series(dtype=polars.UInt32)

    row_heights: polars.Series = polars.Series(dtype=polars.UInt32)
    column_widths: polars.Series = polars.Series(dtype=polars.UInt32)

    cumulative_row_heights: polars.Series = polars.Series(dtype=polars.UInt32)
    cumulative_column_widths: polars.Series = polars.Series(dtype=polars.UInt32)

    def __init__(self, document: SheetDocument) -> None:
        super().__init__()

        self.document = document

    # FIXME: functions don't share their coordinate system

    def get_vcolumn_from_column(self, column: int) -> int:
        if column < len(self.column_visible_series):
            return self.column_visible_series[column - 1] + 1
        if len(self.column_visible_series):
            return self.column_visible_series[-1] + column - len(self.column_visible_series) + 1
        return column

    def get_vrow_from_row(self, row: int) -> int:
        if row < len(self.row_visible_series):
            return self.row_visible_series[row - 1] + 1
        if len(self.row_visible_series):
            return self.row_visible_series[-1] + row - len(self.row_visible_series) + 1
        return row

    def get_column_from_vcolumn(self, vcolumn: int, side = 'left') -> int:
        if len(self.column_visible_series):
            if vcolumn - 1 <= self.column_visible_series[-1]:
                return self.column_visible_series.search_sorted(vcolumn - 1, side) + 1
            else:
                return len(self.column_visible_series) + vcolumn - self.column_visible_series[-1] - 1
        return vcolumn

    def get_row_from_vrow(self, vrow: int, side = 'left') -> int:
        if len(self.row_visible_series):
            if vrow - 1 <= self.row_visible_series[-1]:
                return self.row_visible_series.search_sorted(vrow - 1, side) + 1
            else:
                return len(self.row_visible_series) + vrow - self.row_visible_series[-1] - 1
        return vrow

    def get_starting_column(self, offset: int = None, side = 'right') -> int:
        if offset is None:
            offset = self.scroll_x_position
        if len(self.cumulative_column_widths) == 0:
            return int(offset // self.DEFAULT_CELL_WIDTH)
        if self.cumulative_column_widths[-1] <= offset:
            return len(self.cumulative_column_widths) + (offset - self.cumulative_column_widths[-1]) // self.DEFAULT_CELL_WIDTH
        return self.cumulative_column_widths.search_sorted(offset, side)

    def get_starting_row(self, offset: int = None, side = 'right') -> int:
        if offset is None:
            offset = self.scroll_y_position
        if len(self.cumulative_row_heights) == 0:
            return int(offset // self.DEFAULT_CELL_HEIGHT)
        if self.cumulative_row_heights[-1] <= offset:
            return len(self.cumulative_row_heights) + (offset - self.cumulative_row_heights[-1]) // self.DEFAULT_CELL_HEIGHT
        return self.cumulative_row_heights.search_sorted(offset, side)

    def get_n_hidden_columns(self, col_1: int, col_2: int) -> int:
        if len(self.column_visible_series):
            vcol_1 = self.get_column_from_vcolumn(col_1)
            vcol_2 = self.get_column_from_vcolumn(col_2)
            return (col_2 - col_1) - (vcol_2 - vcol_1)
        return 0

    def get_n_all_hidden_columns(self) -> int:
        return len(self.column_visibility_flags) - len(self.column_visible_series)

    def get_n_hidden_rows(self, row_1: int, row_2: int) -> int:
        if len(self.row_visible_series):
            vrow_1 = self.get_row_from_vrow(row_1)
            vrow_2 = self.get_row_from_vrow(row_2)
            return (row_2 - row_1) - (vrow_2 - vrow_1)
        return 0

    def get_n_all_hidden_rows(self) -> int:
        return len(self.row_visibility_flags) - len(self.row_visible_series)

    def get_right_cell_name(self, name: str) -> str:
        i = len(name) - 1
        while i >= 0 and name[i] == 'Z':
            i -= 1
        if i == -1:
            return 'A' * (len(name) + 1)
        return name[:i] + chr(ord(name[i]) + 1) + 'A' * (len(name) - i - 1)

    def get_bottom_cell_name(self, name: str) -> str:
        i = len(name) - 1
        while i >= 0 and name[i] == '9':
            i -= 1
        if i == -1:
            return 'A' * (len(name) + 1)
        return name[:i] + str(int(name[i]) + 1) + 'A' * (len(name) - i - 1)

    def get_column_from_point(self, x: int = 0, side = 'left') -> int:
        if x <= self.row_header_width:
            return 0
        x = int(x + self.scroll_x_position - self.row_header_width)
        if len(self.cumulative_column_widths):
            if x <= self.cumulative_column_widths[-1]:
                return self.cumulative_column_widths.search_sorted(x, side) + 1
            return len(self.cumulative_column_widths) + (x - self.cumulative_column_widths[-1]) // self.DEFAULT_CELL_WIDTH + 1
        return x // self.DEFAULT_CELL_WIDTH + 1

    def get_row_from_point(self, y: int = 0, side = 'left') -> int:
        if y <= self.column_header_height:
            return 0
        y = int(y + self.scroll_y_position - self.column_header_height)
        if len(self.cumulative_row_heights):
            if y <= self.cumulative_row_heights[-1]:
                return self.cumulative_row_heights.search_sorted(y, side) + 1
            return len(self.cumulative_row_heights) + (y - self.cumulative_row_heights[-1]) // self.DEFAULT_CELL_HEIGHT + 1
        return y // self.DEFAULT_CELL_HEIGHT + 1

    def get_cell_x_from_point(self, x: int = 0) -> int:
        column = self.get_column_from_point(x)
        return self.get_cell_x_from_column(column)

    def get_cell_y_from_point(self, y: int = 0) -> int:
        row = self.get_row_from_point(y)
        return self.get_cell_y_from_row(row)

    def get_cell_x_from_column(self, column: int) -> int:
        if column == 0:
            return 0
        x = self.row_header_width - self.scroll_x_position
        if column == 1:
            return x
        df_width = len(self.cumulative_column_widths)
        if df_width:
            if column <= df_width:
                return x + self.cumulative_column_widths[column - 2]
            return x + self.cumulative_column_widths[-1] + (column - 1 - df_width) * self.DEFAULT_CELL_WIDTH
        return x + (column - 1) * self.DEFAULT_CELL_WIDTH

    def get_cell_y_from_row(self, row: int) -> int:
        if row == 0:
            return 0
        y = self.column_header_height - self.scroll_y_position
        if row == 1:
            return y
        df_height = len(self.cumulative_row_heights)
        if df_height:
            if row <= df_height:
                return y + self.cumulative_row_heights[row - 2]
            return y + self.cumulative_row_heights[-1] + (row - 1 - df_height) * self.DEFAULT_CELL_HEIGHT
        return y + (row - 1) * self.DEFAULT_CELL_HEIGHT

    def get_cell_width_from_point(self, x: int = 0) -> int:
        column = self.get_column_from_point(x)
        return self.get_cell_width_from_column(column)

    def get_cell_height_from_point(self, y: int = 0) -> int:
        row = self.get_row_from_point(y)
        return self.get_cell_height_from_row(row)

    def get_cell_width_from_column(self, column: int) -> int:
        vcolumn = self.get_vcolumn_from_column(column)
        if vcolumn == 0:
            return self.row_header_width
        if vcolumn <= len(self.column_widths):
            return self.column_widths[vcolumn - 1]
        return self.DEFAULT_CELL_WIDTH

    def get_cell_height_from_row(self, row: int) -> int:
        vrow = self.get_vrow_from_row(row)
        if vrow == 0:
            return self.column_header_height
        if vrow <= len(self.row_heights):
            return self.row_heights[vrow - 1]
        return self.DEFAULT_CELL_HEIGHT

    def get_column_name_from_column(self, column: int = 0) -> str:
        if column == 0:
            return 'A'

        column -= 1

        name = ''
        while column >= 0:
            name = chr(65 + column % 26) + name
            column //= 26
            column -= 1

        return name

    def get_cell_name_from_position(self, column: int = 0, row: int = 0) -> str:
        column_name = self.get_column_name_from_column(column)
        row_name = str(row) if row >= 0 else ''
        return column_name + row_name

    def get_cell_position_from_name(self, name: str) -> tuple[int, int]:
        """
        Parses a cell name (e.g., 'A10', 'ABC123', '5', 'H') into a (column, row) tuple.

        Disclaimer: this function was written by genAI under my own supervision.
        I've tested over all the potential cases, but there's no guarantee.

        Interpretation of inputs:
        - For 'A10', 'AA5', 'ABC123': column is 1-based (A=1, AA=27), row is 1-based.
        - For '5', '10': column is 0, row is 1-based.
        - For 'h', 'H', 'HIJ': column is 1-based (H=8, HIJ=...), row is 0.

        Returns None if the name cannot be parsed into a valid position.
        """
        cell_part_pattern = r"([A-Za-z]+\d*|[A-Za-z]*\d+)"
        m = re.match(cell_part_pattern, name, re.IGNORECASE)

        if not m:
            return None

        cell_part = m.group(1)
        col = 0 # Default for column index
        row = 0 # Default for row index

        # Check the composition of the cell_part
        has_letters = bool(re.search(r"[A-Za-z]", cell_part))
        has_digits = bool(re.search(r"\d", cell_part))

        if has_letters and has_digits:
            # Case 1: Contains both letters and digits (e.g., 'A10', 'AA5', 'ABC123')
            # This is a standard column-row reference.
            col_letters_match = re.search(r"([A-Za-z]+)", cell_part)
            row_str_match = re.search(r"(\d+)", cell_part)

            if not (col_letters_match and row_str_match):
                return None # Should theoretically not happen if regex `m` matched, but for safety

            col_letters = col_letters_match.group(1)
            row_str = row_str_match.group(1)

            # Convert column letters to 1-based index
            for c in col_letters.upper():
                col = col * 26 + (ord(c) - ord('A') + 1)
            # Convert row string to 1-based integer
            row = int(row_str)

        elif has_digits:
            # Case 2: Contains only digits (e.g., '5', '10')
            # As per requirement: this implies a specific row with column 0.
            col = 0 # Explicitly set column to 0
            row = int(cell_part) # Row is the number itself (1-based)

        elif has_letters:
            # Case 3: Contains only letters (e.g., 'h', 'H', 'HIJ')
            # As per requirement: this implies a specific column with row 0.
            # Convert column letters to 1-based index
            for c in cell_part.upper(): # cell_part is entirely letters here
                col = col * 26 + (ord(c) - ord('A') + 1)
            row = 0 # Explicitly set row to 0

        else:
            return None # Should not be reached if the initial regex is robust, but for completeness

        # Basic validation for sensible results (col/row shouldn't be negative).
        # A (0, 0) result is valid but is not possible to achieve from the input bar.
        if col < 0 and row < 0:
            return None

        return (col, row)

    def get_cell_range_from_name(self, name: str) -> tuple[int, int, int, int]:
        """
        Parses a cell range (e.g., 'A10:a20', 'AA5:BB20', '5:10', 'h:H') or a single cell
        (e.g., 'a10', '123', 'HIJ', 'ABC123') into a tuple of (start_col, start_row, end_col, end_row).

        Disclaimer: this function was written by genAI under my own supervision.
        I've tested over all the potential cases, but there's no guarantee.

        Returns (-1, -1, -1, -1) if the name cannot be parsed.
        """
        cell_part_pattern = r"([A-Za-z]*\d*|[A-Za-z]*\d*)"
        pattern = fr"{cell_part_pattern}(:{cell_part_pattern})?"
        match = re.match(pattern, name, re.IGNORECASE)

        if not match:
            return (-1, -1, -1, -1)

        start_name_part = match.group(1)
        end_name_part = match.group(3)

        start_pos = self.get_cell_position_from_name(start_name_part)

        if start_pos is None:
            return (-1, -1, -1, -1)

        if end_name_part: # If a second part exists (it's a range)
            end_pos = self.get_cell_position_from_name(end_name_part)
            if end_pos is None:
                return (-1, -1, -1, -1)
            return (*start_pos, *end_pos)
        else: # It's a single cell name
            return (*start_pos, *start_pos)

    def check_cell_position_near_edges(self, column: int, row: int, viewport_height: int, viewport_width: int) -> list[str]:
        cell_y = self.get_cell_y_from_row(row)
        cell_x = self.get_cell_x_from_column(column)
        cell_width = self.get_cell_width_from_column(column)
        cell_height = self.get_cell_height_from_row(row)

        x_offset = self.row_header_width - self.scroll_x_position
        y_offset = self.column_header_height - self.scroll_y_position

        top_offset = cell_y - y_offset
        left_offset = cell_x - x_offset

        top_limit = top_offset - (viewport_height - (viewport_height % self.DEFAULT_CELL_HEIGHT)) + cell_height
        left_limit = left_offset - (viewport_width - (viewport_width % self.DEFAULT_CELL_WIDTH)) + cell_width

        near_edges = []

        # Check if the target cell is near the bottom of the viewport
        if abs(self.scroll_y_position - top_limit) <= self.DEFAULT_CELL_HEIGHT:
            near_edges.append('bottom')

        # Check if the target cell is near the top of the viewport
        if abs(self.scroll_y_position - top_offset) <= self.DEFAULT_CELL_HEIGHT:
            near_edges.append('top')

        # Check if the target cell is near the right of the viewport
        if abs(self.scroll_x_position - left_limit) <= self.DEFAULT_CELL_WIDTH:
            near_edges.append('right')

        # Check if the target cell is near the left of the viewport
        if abs(self.scroll_x_position - left_offset) <= self.DEFAULT_CELL_WIDTH:
            near_edges.append('left')

        return near_edges

    def scroll_to_position(self, column: int, row: int, viewport_height: int, viewport_width: int, scroll_axis: str = 'both',
                           with_offset: bool = False, offset_size: int = 0) -> bool:
        cell_y = self.get_cell_y_from_row(row)
        cell_x = self.get_cell_x_from_column(column)
        cell_width = self.get_cell_width_from_column(column)
        cell_height = self.get_cell_height_from_row(row)

        x_offset = self.row_header_width - self.scroll_x_position
        y_offset = self.column_header_height - self.scroll_y_position

        bottom_offset = cell_y + cell_height - y_offset
        top_offset = cell_y - y_offset
        right_offset = cell_x + cell_width - x_offset
        left_offset = cell_x - x_offset

        # Skip if the target cell is already visible
        if self.scroll_y_position <= top_offset and bottom_offset <= self.scroll_y_position + viewport_height and \
                self.scroll_x_position <= left_offset and right_offset <= self.scroll_x_position + viewport_width:
            return False

        # Scroll down when the target cell is below the viewport so that the target cell is near the bottom of the viewport
        if scroll_axis in ['both', 'vertical'] and bottom_offset > self.scroll_y_position + viewport_height:
            self.scroll_y_position = top_offset - (viewport_height - (viewport_height % self.DEFAULT_CELL_HEIGHT)) + cell_height
            if with_offset:
                self.scroll_y_position += offset_size or self.DEFAULT_CELL_HEIGHT

        # Scroll up when the target cell is above the viewport so that the target cell is exactly at the top of the viewport
        if scroll_axis in ['both', 'vertical'] and top_offset < self.scroll_y_position:
            self.scroll_y_position = top_offset
            if with_offset:
                self.scroll_y_position -= offset_size or self.DEFAULT_CELL_HEIGHT

        # Scroll to the right when the target cell is to the right of the viewport so that the target cell is near the right of the viewport
        if scroll_axis in ['both', 'horizontal'] and right_offset > self.scroll_x_position + viewport_width:
            self.scroll_x_position = left_offset - (viewport_width - (viewport_width % self.DEFAULT_CELL_WIDTH)) + cell_width
            if with_offset:
                self.scroll_x_position += offset_size or self.DEFAULT_CELL_WIDTH

        # Scroll to the left when the target cell is to the left of the viewport so that the target cell is exactly at the left of the viewport
        if scroll_axis in ['both', 'horizontal'] and left_offset < self.scroll_x_position:
            self.scroll_x_position = left_offset
            if with_offset:
                self.scroll_x_position -= offset_size or self.DEFAULT_CELL_WIDTH

        self.scroll_y_position = max(0, self.scroll_y_position)
        self.scroll_x_position = max(0, self.scroll_x_position)

        if with_offset:
            self.discretize_scroll_position()

        return True

    def discretize_scroll_position(self) -> None:
        self.scroll_y_position = round(self.scroll_y_position / self.DEFAULT_CELL_HEIGHT) * self.DEFAULT_CELL_HEIGHT
        self.scroll_x_position = round(self.scroll_x_position / self.DEFAULT_CELL_WIDTH) * self.DEFAULT_CELL_WIDTH