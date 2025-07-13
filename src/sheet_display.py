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

    ICON_SIZE: int = 10
    FONT_SIZE: float = 12

    row_header_width: int = 40
    column_header_height: int = 20

    scroll_increment: int = 3
    page_increment: int = 20

    scroll_y_position: int = 0
    scroll_x_position: int = 0

    # We don't need to fill these upfront because everything will be visible
    # by default. It'll be filled up on demand, usually when the user performs
    # a filter to any dataframe. Whenever possible, we should try to avoid
    # having these series with the same length as the number of rows/columns;
    # I think it's best to have them as short as possible, i.e. truncating
    # all the true values at the end.
    row_visibility_flags: polars.Series = polars.Series(dtype=polars.Boolean)
    column_visibility_flags: polars.Series = polars.Series(dtype=polars.Boolean)

    # These are the cumulative heights/widths of the visible cells, a helper
    # for the renderer to know which cells will be on the very top left of
    # the viewport regarding the current scroll position. It's useful for
    # two scenarios at least: 1) when some rows/columns are hidden, and 2)
    # when the width/height of some rows/columns have been adjusted. It's
    # also useful to calculate the total width/height of the visible cells
    # so that the user can go to the edges of the table, for example by
    # pressing the arrow keys with the ctrl[+shift] modifier. Most of the
    # time when accessing these values, a binary search will be involved.
    cumulative_visible_heights: polars.Series = polars.Series(dtype=polars.UInt32)
    cumulative_visible_widths: polars.Series = polars.Series(dtype=polars.UInt32)

    def __init__(self, document: SheetDocument) -> None:
        super().__init__()

        self.document = document

    def get_starting_column(self, offset: int = 0) -> int:
        if offset == 0:
            offset = self.scroll_x_position
        return int(offset // self.DEFAULT_CELL_WIDTH)

    def get_starting_row(self, offset: int = 0) -> int:
        if offset == 0:
            offset = self.scroll_y_position
        return int(offset // self.DEFAULT_CELL_HEIGHT)

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

    def get_column_from_point(self, x: int = 0) -> int:
        if x <= self.row_header_width:
            return 0
        return int(x + self.scroll_x_position - self.row_header_width) // self.DEFAULT_CELL_WIDTH + 1

    def get_row_from_point(self, y: int = 0) -> int:
        if y <= self.column_header_height:
            return 0
        return int(y + self.scroll_y_position - self.column_header_height) // self.DEFAULT_CELL_HEIGHT + 1

    def get_cell_x_from_point(self, x: int = 0) -> int:
        if (column := self.get_column_from_point(x)) == 0:
            return 0
        return (column - 1) * self.DEFAULT_CELL_WIDTH + self.row_header_width - self.scroll_x_position

    def get_cell_y_from_point(self, y: int = 0) -> int:
        if (row := self.get_row_from_point(y)) == 0:
            return 0
        return (row - 1) * self.DEFAULT_CELL_HEIGHT + self.column_header_height - self.scroll_y_position

    def get_cell_x_from_column(self, column: int) -> int:
        if column == 0:
            return 0
        return (column - 1) * self.DEFAULT_CELL_WIDTH + self.row_header_width - self.scroll_x_position

    def get_cell_y_from_row(self, row: int) -> int:
        if row == 0:
            return 0
        return (row - 1) * self.DEFAULT_CELL_HEIGHT + self.column_header_height - self.scroll_y_position

    def get_cell_width_from_point(self, x: int = 0) -> int:
        if self.get_column_from_point(x) == 0:
            return self.row_header_width
        return self.DEFAULT_CELL_WIDTH

    def get_cell_height_from_point(self, y: int = 0) -> int:
        if self.get_row_from_point(y) == 0:
            return self.column_header_height
        return self.DEFAULT_CELL_HEIGHT

    def get_cell_width_from_column(self, column: int) -> int:
        if column == 0:
            return self.row_header_width
        return self.DEFAULT_CELL_WIDTH

    def get_cell_height_from_row(self, row: int) -> int:
        if row == 0:
            return self.column_header_height
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
        if column == 0 and row == 0:
            return 'A1'

        column_name = self.get_column_name_from_column(column)
        row_name = str(row) if row >= 0 else ''

        return column_name + row_name

    def get_cell_position_from_name(self, name: str) -> tuple[int, int]:
        """
        Parses a cell name (e.g., 'A10', 'ABC123', '5', 'H') into a (column, row) tuple.

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

    def get_dtype_symbol(self, dtype: polars.DataType, short: bool = True) -> str:
        symbol_map = {
            polars.Categorical: {'short': 'cat.',     'long': 'categorical'},
            polars.Int8:        {'short': 'int8',     'long': 'integer8'},
            polars.Int16:       {'short': 'int16',    'long': 'integer16'},
            polars.Int32:       {'short': 'int32',    'long': 'integer32'},
            polars.Int64:       {'short': 'int64',    'long': 'integer64'},
            polars.UInt8:       {'short': 'uint8',    'long': 'unsigned integer8'},
            polars.UInt16:      {'short': 'uint16',   'long': 'unsigned integer16'},
            polars.UInt32:      {'short': 'uint32',   'long': 'unsigned integer32'},
            polars.UInt64:      {'short': 'uint64',   'long': 'unsigned integer64'},
            polars.Float32:     {'short': 'float32',  'long': 'float32'},
            polars.Float64:     {'short': 'float64',  'long': 'float64'},
            polars.Decimal:     {'short': 'decimal',  'long': 'decimal'},
            polars.Date:        {'short': 'date',     'long': 'date'},
            polars.Time:        {'short': 'time',     'long': 'time'},
            polars.Datetime:    {'short': 'datetime', 'long': 'datetime'},
            polars.Boolean:     {'short': 'bool.',    'long': 'boolean'},
            polars.Utf8:        {'short': 'str.',     'long': 'string'},
            polars.Null:        {'short': 'null',     'long': 'null'},
        }
        for dt, symbol in symbol_map.items():
            if dtype == dt or isinstance(dtype, dt):
                return symbol['short'] if short else symbol['long']
        return '?'

    def scroll_to_position(self, column: int, row: int, viewport_height: int, viewport_width: int) -> bool:
        bottom_offset = row * self.DEFAULT_CELL_HEIGHT
        top_offset = (row - 1) * self.DEFAULT_CELL_HEIGHT
        right_offset = column * self.DEFAULT_CELL_WIDTH
        left_offset = (column - 1) * self.DEFAULT_CELL_WIDTH

        # Skip if the target cell is already visible
        if self.scroll_y_position <= top_offset and bottom_offset <= self.scroll_y_position + viewport_height and \
                self.scroll_x_position <= left_offset and right_offset <= self.scroll_x_position + viewport_width:
            return False

        # Scroll down when the target cell is below the viewport so that the target cell is near the bottom of the viewport
        if bottom_offset > self.scroll_y_position + viewport_height:
            self.scroll_y_position = top_offset - (viewport_height - (viewport_height % self.DEFAULT_CELL_HEIGHT)) + self.DEFAULT_CELL_HEIGHT

        # Scroll up when the target cell is above the viewport so that the target cell is exactly at the top of the viewport
        if top_offset < self.scroll_y_position:
            self.scroll_y_position = top_offset

        # Scroll to the right when the target cell is to the right of the viewport so that the target cell is near the right of the viewport
        if right_offset > self.scroll_x_position + viewport_width:
            self.scroll_x_position = left_offset - (viewport_width - (viewport_width % self.DEFAULT_CELL_WIDTH)) + self.get_cell_width_from_column(column)

        # Scroll to the left when the target cell is to the left of the viewport so that the target cell is exactly at the left of the viewport
        if left_offset < self.scroll_x_position:
            self.scroll_x_position = left_offset

        return True