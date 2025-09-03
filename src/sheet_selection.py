# sheet_selection.py
#
# Copyright (c) 2025 Naufan Rusyda Faikar
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


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

    def __init__(self,
                 x:           int,
                 y:           int,
                 column:      int,
                 row:         int,
                 width:       int,
                 height:      int,
                 column_span: int,
                 row_span:    int,
                 metadata:    SheetCellMetadata,
                 rtl:         bool = False,
                 btt:         bool = False) -> None:
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
    cell_dtype: str

    current_active_range: SheetCell
    previous_active_range: SheetCell

    current_active_cell: SheetCell
    current_cursor_cell: SheetCell

    current_search_range: SheetCell
    current_cutcopy_range: SheetCell

    def __init__(self, document: SheetDocument) -> None:
        super().__init__()

        self.document = document

        self.cell_name = ''
        self.cell_data = None
        self.cell_dtype = None

        self.current_active_range = SheetCell(0, 0, 0, 0, 0, 0, 0, 0,
                                              SheetCellMetadata(0, 0, 0))
        self.previous_active_range = self.current_active_range

        self.current_active_cell = self.current_active_range
        self.current_cursor_cell = self.current_active_range

        self.current_search_range = None
        self.current_cutcopy_range = None