# sheet_selection.py
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

from .sheet_document import SheetDocument
from .sheet_data import SheetCellMetadata

class SheetElement(GObject.Object):
    __gtype_name__ = 'SheetElement'

    x: int
    y: int

    def __init__(self, x: int, y: int) -> None:
        super().__init__()

        self.x = x
        self.y = y



class SheetCell(SheetElement):
    __gtype_name__ = 'SheetCell'

    column: int
    row: int

    column_span: int
    row_span: int

    width: int
    height: int

    metadata: SheetCellMetadata

    rtl: bool # right to left
    btt: bool # bottom to top

    def __init__(self, x: int, y: int, column: int, row: int, width: int, height: int, column_span: int, row_span: int,
                 metadata: SheetCellMetadata, rtl: bool = False, btt: bool = False) -> None:
        super().__init__(x, y)

        self.column = column
        self.row = row

        self.column_span = column_span
        self.row_span = row_span

        self.width = width
        self.height = height

        self.metadata = metadata

        self.rtl = rtl
        self.btt = btt



class SheetLocatorCell(SheetCell):
    __gtype_name__ = 'SheetLocatorCell'

class SheetTopLocatorCell(SheetLocatorCell):
    __gtype_name__ = 'SheetTopLocatorCell'

class SheetLeftLocatorCell(SheetLocatorCell):
    __gtype_name__ = 'SheetLeftLocatorCell'

class SheetCornerLocatorCell(SheetLocatorCell):
    __gtype_name__ = 'SheetCornerLocatorCell'



class SheetContentCell(SheetCell):
    __gtype_name__ = 'SheetContentCell'



class SheetSelection(GObject.Object):
    __gtype_name__ = 'SheetSelection'

    cell_name: str
    cell_data: str

    current_active_range: SheetCell
    previous_active_range: SheetCell

    current_active_cell: SheetCell
    current_cursor_cell: SheetCell

    current_search_range: SheetCell

    def __init__(self, document: SheetDocument) -> None:
        super().__init__()

        self.document = document

        self.current_active_range = SheetCell(0, 0, 0, 0, 0, 0, 0, 0, SheetCellMetadata(0, 0, 0))
        self.previous_active_range = self.current_active_range

        self.current_active_cell = self.current_active_range
        self.current_cursor_cell = self.current_active_range

        self.current_search_range = None