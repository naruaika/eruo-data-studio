# selection.py
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

import re

from gi.repository import GObject

from .display import Display

class Selection(GObject.Object):
    __gtype_name__ = 'Selection'

    _display: Display

    _previous_selected_column: int = -1
    _selected_column: int = -1

    _previous_selected_locator: tuple[int, int] = (-1, -1)
    _selected_locator: tuple[int, int] = (-1, -1)

    _active_cell: tuple[int, int] = (0, 0)
    _selected_cells: tuple[tuple[int, int], tuple[int, int]] = ((0, 0), (0, 0))

    _opposite_active_cell: tuple[int, int] = (0, 0)

    def __init__(self, display: Display) -> None:
        """
        Initializes the Selection class.

        This class is responsible for managing the selection of cells in the Eruo Data Studio.
        It keeps track of the currently active cell and the set of selected cells.
        """
        super().__init__()
        self._display = display

    def get_previous_selected_column(self) -> int:
        """
        Returns the index of the previously selected column.

        Returns:
            An integer representing the index of the previously selected column.
        """
        return self._previous_selected_column

    def set_previous_selected_column(self, index: int) -> None:
        """
        Sets the previously selected column.

        Args:
            index: The index of the previously selected column.
        """
        self._previous_selected_column = index

    def get_selected_column(self) -> int:
        """
        Returns the index of the currently selected column.

        Returns:
            An integer representing the index of the selected column.
        """
        return self._selected_column

    def set_selected_column(self, index: int) -> None:
        """
        Sets the currently selected column.

        Args:
            index: The index of the selected column.
        """
        self._selected_column = index
    def get_previous_selected_locator(self) -> tuple[int, int]:
        """
        Returns the index of the previously selected locator.

        Returns:
            A tuple representing the index of the previously selected locator.
        """
        return self._previous_selected_locator

    def set_previous_selected_locator(self, index: tuple[int, int]) -> None:
        """
        Sets the previously selected locator.

        Args:
            index: The index of the previously selected locator.
        """
        self._previous_selected_locator = index

    def get_selected_locator(self) -> tuple[int, int]:
        """
        Returns the index of the currently selected locator.

        Returns:
            A tuple representing the index of the selected locator.
        """
        return self._selected_locator

    def set_selected_locator(self, index: tuple[int, int]) -> None:
        """
        Sets the currently selected locator.

        Args:
            index: The index of the selected locator.
        """
        self._selected_locator = index

    def get_active_cell(self) -> tuple[int, int]:
        """
        Returns the currently active cell.

        The active cell is represented as a tuple of (row, column) indices.

        Returns:
            A tuple containing the row and column indices of the active cell.
        """
        return self._active_cell

    def get_active_cell_name(self) -> str:
        """
        Returns the name of the currently active cell.

        The name is constructed based on the active cell's row and column indices.
        For example, if the active cell is at (0, 0), the name will be "A1".

        Returns:
            A string representing the name of the active cell.
        """
        return self.index_to_name(self._active_cell)

    def set_active_cell(self, index: tuple[int, int]) -> None:
        """
        Sets the currently active cell.

        This method updates the active cell and refreshes the name box to reflect the new active cell.

        Args:
            row: The row index of the active cell.
            col: The column index of the active cell.
        """
        self._active_cell = index

    def set_active_cell_by_name(self, name: str) -> bool:
        """
        Sets the currently active cell based on its name.

        The cell name should be in the format "A1", "AB12", "AAA333", etc.,
        where the letters represent the column and the number represents the row.

        Args:
            name: A string representing the name of the cell to be set as active.

        Returns:
            True if the cell name is valid and the active cell is set successfully,
            False if the cell name format is invalid.
        """
        match = re.match(r"([A-Za-z]+)(\d+)", name)
        if not match: # Invalid cell name format
            return False
        col_letters, row_str = match.groups()
        col = 0
        for c in col_letters.upper():
            col = col * 26 + (ord(c) - ord('A') + 1)
        col -= 1
        row = int(row_str) - 1
        self.set_active_cell((row, col))
        return True

    def set_active_cell_by_coordinate(self, coordinate: tuple[float, float]) -> bool:
        """
        Sets the currently active cell based on the provided coordinates.

        This method calculates the row and column indices based on the x and y coordinates
        relative to the display's cell dimensions. It then updates the active cell accordingly.

        Args:
            coordinate: A tuple containing the x and y coordinates of the cell.
        """
        row, col = self._display.coordinate_to_index(coordinate)
        if row < 0 or col < 0:
            return False
        self.set_active_cell((row, col))
        return True

    def get_opposite_active_cell(self) -> tuple[int, int]:
        """
        Returns the opposite active cell.

        The opposite active cell is the cell opposite the currently active cell,
        represented as a tuple of (row, column) indices.

        Returns:
            A tuple containing the row and column indices of the opposite active cell.
        """
        return self._opposite_active_cell

    def get_selected_cells(self) -> tuple[tuple[int, int], tuple[int, int]]:
        """
        Returns the set of currently selected cells.

        The selected cells are represented as a set of tuples, where each tuple contains
        the row and column indices of a selected cell.

        Returns:
            A tuple containing two tuples, each representing the start and end of the selected cell range.
            For example, ((start_row, start_col), (end_row, end_col)).
        """
        return self._selected_cells

    def set_selected_cells(self, range: tuple[tuple[int, int], tuple[int, int]]) -> None:
        """
        Sets the currently selected cells.

        This method updates the selected cells based on a range defined by two tuples, where each tuple
        contains the row and column indices of the start and end cells. The range is inclusive, meaning both
        the start and end cells are included in the selection, and normalizes the range to ensure the start is
        always less than or equal to the end.

        This method is also updates the active cell to the start of the selected range automatically.

        Args:
            range: A set of tuples representing the cells to be selected.
        """
        start = (min(range[0][0], range[1][0]), min(range[0][1], range[1][1]))
        end = (max(range[0][0], range[1][0]), max(range[0][1], range[1][1]))
        range = (start, end)
        self._selected_cells = range
        self.set_active_cell(start)

    def set_selected_cells_by_name(self, range: str) -> bool:
        """
        Sets the currently selected cells based on a range string.

        The range should be in the format "A1:B2", where the letters represent
        the column and the number represents the row. The range is inclusive.

        Args:
            range: A string representing the range of cells to be selected.

        Returns:
            True if the range is valid and the selected cells are set successfully,
            False if the format is invalid.
        """
        # Try to parse a range of cell names
        if match := re.match(r"([A-Za-z]+\d+):([A-Za-z]+\d+)", range):
            start_name, end_name = match.groups()
            start = self.name_to_index(start_name)
            end = self.name_to_index(end_name)
            if start is None or end is None:
                return False
            self.set_selected_cells((start, end))
            return True

        # Try to parse a single cell name
        if match := re.match(r"([A-Za-z]+\d+)", range):
            cell_name = match.group(1)
            index = self.name_to_index(cell_name)
            if index is None:
                return False
            self.set_selected_cells((index, index))
            return True

        return False

    def set_selected_cells_by_coordinates(self, range: tuple[tuple[float, float], tuple[float, float]]) -> None:
        """
        Sets the currently selected cells based on a range of coordinates.

        The range is defined by two tuples, each containing the x and y coordinates of the start and end cells.
        The selection is inclusive, meaning both the start and end cells are included in the selection.

        Args:
            range: A tuple containing two tuples, each representing the start and end coordinates of the selection.
        """
        start_coord, end_coord = range
        start_row, start_col = self._display.coordinate_to_index(start_coord)
        end_row, end_col = self._display.coordinate_to_index(end_coord)
        start_row = max(start_row, 0)
        start_col = max(start_col, 0)
        end_row = max(end_row, 0)
        end_col = max(end_col, 0)
        range = ((start_row, start_col), (end_row, end_col))
        self.set_selected_cells(range)
        self.set_active_cell(range[0])
        self._opposite_active_cell = range[1]

    def name_to_index(self, name: str) -> tuple[int, int]:
        """
        Converts a cell name to its corresponding row and column indices.

        The name should be in the format "A1", "AB12", "AAA333", etc.,
        where the letters represent the column and the number represents the row.

        Args:
            name: A string representing the name of the cell.

        Returns:
            A tuple containing the row and column indices of the cell.
            Returns None if the name format is invalid.
        """
        m = re.match(r"([A-Za-z]+)(\d+)", name)
        if not m:
            return None
        col_letters, row_str = m.groups()
        col = 0
        for c in col_letters.upper():
            col = col * 26 + (ord(c) - ord('A') + 1)
        col -= 1
        row = int(row_str) - 1
        return (row, col)

    def index_to_name(self, index: tuple[int, int]) -> str:
        """
        Returns the name of the currently active cell.

        The name is constructed based on the active cell's row and column indices.
        For example, if the active cell is at (0, 0), the name will be "A1"; at (0, 1)
        the name will be "B1"; and at (1, 0) the name will be "A2". When reaching
        the end of the alphabet, the next column will be prepended with a letter.
        For example, if the active cell is at (0, 26), the name will be "AA1". In other
        words, following this pattern: A ^ B ^ C ... Z ^ AA ... AZ ^ BA ... ZZ ^ AAA ...

        Args:
            index: A tuple containing the row and column indices of the active cell.

        Returns:
            A string representing the name of the active cell.
        """
        row, col = index
        name = ''
        while col >= 0:
            name = chr(65 + col % 26) + name
            col //= 26
            col -= 1
        return name + str(row + 1)