# history_manager.py
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


from collections import deque
from gi.repository import GObject
from tempfile import NamedTemporaryFile
from typing import Any
import copy
import polars
import time

from . import globals
from .sheet_document import SheetDocument
from .sheet_selection import SheetCell
from .window import Window

class State(GObject.Object):
    __gtype_name__ = 'State'

    timestamp: float

    scroll_x: int
    scroll_y: int

    # Optionals
    arange: SheetCell
    active: SheetCell
    cursor: SheetCell

    search_range: SheetCell

    def __init__(self) -> None:
        super().__init__()

        self.timestamp = time.time()

        document = globals.history.document

        self.scroll_x = document.display.scroll_x_position
        self.scroll_y = document.display.scroll_y_position

        self.restore_scroll = False

    def save_selection(self, restore_scroll: bool = False) -> None:
        document = globals.history.document

        self.arange = document.selection.current_active_range
        self.active = document.selection.current_active_cell
        self.cursor = document.selection.current_cursor_cell

        self.search_range = document.selection.current_search_range

        self.restore_scroll = restore_scroll

    def restore_selection(self, notify: bool = True) -> None:
        document = globals.history.document

        # TODO: in some cases, no senses to restore the selection
        document.selection.current_active_range = self.arange
        document.selection.current_active_cell = self.active
        document.selection.current_cursor_cell = self.cursor

        document.selection.current_search_range = self.search_range

        if notify:
            document.notify_selection_changed(self.active.column,
                                              self.active.row,
                                              self.active.metadata)

    def write_snapshot(self, dataframe: polars.DataFrame) -> str:
        with NamedTemporaryFile(suffix='.ersnap', delete=False) as file_path:
            # TODO: we leave uncompressed for now, but we may want to determine
            # the compression level based on the size of the dataframe later.
            dataframe.write_parquet(file_path.name, compression='uncompressed', statistics=False)
            return file_path.name



class SelectionState(State):
    __gtype_name__ = 'SelectionState'

    col_1: int
    row_1: int
    col_2: int
    row_2: int

    keep_order: bool
    follow_cursor: bool
    auto_scroll: bool

    def __init__(self,
                 col_1:         int,
                 row_1:         int,
                 col_2:         int,
                 row_2:         int,
                 keep_order:    bool,
                 follow_cursor: bool,
                 auto_scroll:   bool) -> None:
        super().__init__()

        self.save_selection(restore_scroll=True)

        self.col_1 = col_1
        self.row_1 = row_1
        self.col_2 = col_2
        self.row_2 = row_2

        self.keep_order = keep_order
        self.follow_cursor = follow_cursor
        self.auto_scroll = auto_scroll

    def undo(self) -> None:
        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document
        document.update_selection_from_position(self.col_1, self.row_1,
                                                self.col_2, self.row_2,
                                                self.keep_order,
                                                self.follow_cursor,
                                                self.auto_scroll)



class InsertBlankRowState(State):
    __gtype_name__ = 'InsertBlankRowState'

    row_span: int
    above: bool
    on_border: int
    dfi: bool
    auto_range: bool

    def __init__(self,
                 above:      bool,
                 row_span:   int,
                 on_border:  bool,
                 dfi:        int,
                 auto_range: bool) -> None:
        super().__init__()

        self.save_selection()

        self.above = above
        self.row_span = row_span
        self.on_border = on_border
        self.dfi = dfi
        self.auto_range = auto_range

    def undo(self) -> None:
        document = globals.history.document

        arange = document.selection.current_active_range

        row_span = arange.row_span
        mrow = arange.metadata.row

        # This block won't affect anything if on_border set to True
        if self.auto_range:
            prow_span, self.arange.row_span = self.arange.row_span, self.row_span
            if not self.above:
                document.selection.current_active_range.metadata.row += self.arange.row_span
            else:
                document.selection.current_active_range = self.arange
        else:
            document.selection.current_active_range.metadata.row = self.arange.metadata.row
            document.selection.current_active_range.row_span = self.row_span

        document.delete_current_rows(self.above, self.row_span, self.on_border, self.dfi)

        if self.auto_range:
            self.arange.row_span = prow_span

        arange.metadata.row = mrow
        arange.row_span = row_span

        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document
        document.insert_blank_from_current_rows(self.above,
                                                self.row_span if not self.auto_range else -1,
                                                self.on_border,
                                                self.dfi)



class InsertBlankColumnState(State):
    __gtype_name__ = 'InsertBlankColumnState'

    left: bool
    column_span: int
    on_border: bool
    dfi: int
    auto_range: bool

    def __init__(self,
                 left:        bool,
                 column_span: int,
                 on_border:   bool,
                 dfi:         int,
                 auto_range:  bool) -> None:
        super().__init__()

        self.save_selection()

        self.left = left
        self.column_span = column_span
        self.on_border = on_border
        self.dfi = dfi
        self.auto_range = auto_range

    def undo(self) -> None:
        document = globals.history.document

        arange = document.selection.current_active_range

        column_span = arange.column_span
        mcolumn = arange.metadata.column

        # This block won't affect anything if on_border set to True
        if self.auto_range:
            pcolumn_span, self.arange.column_span = self.arange.column_span, self.column_span
            if not self.left:
                document.selection.current_active_range.metadata.column += self.arange.column_span
            else:
                document.selection.current_active_range = self.arange
        else:
            document.selection.current_active_range.metadata.column = self.arange.metadata.column
            document.selection.current_active_range.column_span = self.column_span

        document.delete_current_columns(self.left, self.column_span, self.on_border, self.dfi)

        if self.auto_range:
            self.arange.column_span = pcolumn_span

        arange.metadata.column = mcolumn
        arange.column_span = column_span

        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document
        document.insert_blank_from_current_columns(self.left,
                                                   self.column_span if not self.auto_range else -1,
                                                   self.on_border,
                                                   self.dfi)



class UpdateColumnDataFromDaxState(State):
    __gtype_name__ = 'UpdateColumnDataFromDaxState'

    file_path: str

    t_column_names: list[str] # targeted columns
    n_column_names: list[str] # added columns

    dfi: int
    query: str

    def __init__(self,
                 content:        Any,
                 t_column_names: list[str],
                 n_column_names: list[str],
                 dfi:            int,
                 query:          str) -> None:
        super().__init__()

        self.save_selection(restore_scroll=True)

        if content is not None:
            self.file_path = self.write_snapshot(content)
        else:
            self.file_path = None

        self.t_column_names = t_column_names
        self.n_column_names = n_column_names
        self.dfi = dfi
        self.query = query

    def undo(self) -> None:
        document = globals.history.document

        # Delete added columns
        bbox = document.data.bbs[self.dfi]
        for _ in self.n_column_names:
            document.move_selection_to_corner(bbox, 'bottom-right')
            document.delete_current_columns()

        # Restore targeted columns
        if self.file_path is not None:
            document.data.update_cell_data_blocks_from_metadata(self.t_column_names,
                                                                0,  # from the first row
                                                                -1, # to the last row
                                                                self.dfi,
                                                                polars.read_parquet(self.file_path))

        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document
        document.update_current_columns_from_dax(self.query)



class UpdateColumnDataFromSqlState(State):
    __gtype_name__ = 'UpdateColumnDataFromSqlState'

    file_path: str

    t_column_names: list[str] # targeted columns
    n_column_names: list[str] # added columns

    dfi: int
    query: str

    def __init__(self,
                 content:        Any,
                 t_column_names: list[str],
                 n_column_names: list[str],
                 dfi:            int,
                 query:          str) -> None:
        super().__init__()

        self.save_selection(restore_scroll=True)

        if content is not None:
            self.file_path = self.write_snapshot(content)
        else:
            self.file_path = None

        self.t_column_names = t_column_names
        self.n_column_names = n_column_names
        self.dfi = dfi
        self.query = query

    def undo(self) -> None:
        document = globals.history.document

        # Delete added columns
        bbox = document.data.bbs[self.dfi]
        for _ in self.n_column_names:
            document.move_selection_to_corner(bbox, 'bottom-right')
            document.delete_current_columns()

        # Restore targeted columns
        if self.file_path is not None:
            document.data.update_cell_data_blocks_from_metadata(self.t_column_names,
                                                                0,  # from the first row
                                                                -1, # to the last row
                                                                self.dfi,
                                                                polars.read_parquet(self.file_path))

        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document
        document.update_current_columns_from_sql(self.query)



class UpdateDataState(State):
    __gtype_name__ = 'UpdateDataState'

    column: int
    row: int
    column_span: int
    row_span: int
    dfi: int

    content: Any
    file_path: str

    new_value: Any

    include_header: bool

    def __init__(self,
                 column:         int,
                 row:            int,
                 column_span:    int,
                 row_span:       int,
                 dfi:            int,
                 content:        Any,
                 new_value:      Any,
                 include_header: bool) -> None:
        super().__init__()

        self.save_selection(restore_scroll=True)

        self.column = column
        self.row = row
        self.column_span = column_span
        self.row_span = row_span
        self.dfi = dfi

        self.file_path = self.write_snapshot(content)

        self.new_value = new_value

        self.include_header = include_header

    def undo(self) -> None:
        document = globals.history.document
        document.data.update_cell_data_block_from_metadata(self.column,
                                                           self.row,
                                                           self.column_span,
                                                           self.row_span,
                                                           self.dfi,
                                                           self.include_header,
                                                           polars.read_parquet(self.file_path))

        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document
        document.update_current_cells_from_literal(self.new_value)



class UpdateDataFromOperatorState(State):
    __gtype_name__ = 'UpdateDataFromOperatorState'

    column: int
    row: int
    column_span: int
    row_span: int
    dfi: int

    file_path: str
    include_header: bool

    operator_name: str
    operation_args: list
    on_column: bool

    def __init__(self,
                 column:         int,
                 row:            int,
                 column_span:    int,
                 row_span:       int,
                 dfi:            int,
                 content:        Any,
                 include_header: bool,
                 operator_name:  str,
                 operation_args: list,
                 on_column:      bool) -> None:
        super().__init__()

        self.save_selection(restore_scroll=True)

        self.column = column
        self.row = row
        self.column_span = column_span
        self.row_span = row_span
        self.dfi = dfi

        self.file_path = self.write_snapshot(content)
        self.include_header = include_header

        self.operator_name = operator_name
        self.operation_args = operation_args
        self.on_column = on_column

    def undo(self) -> None:
        document = globals.history.document
        document.data.update_cell_data_block_from_metadata(self.column,
                                                           self.row,
                                                           self.column_span,
                                                           self.row_span,
                                                           self.dfi,
                                                           self.include_header,
                                                           polars.read_parquet(self.file_path))

        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document
        document.update_current_cells_from_operator(self.operator_name,
                                                    self.operation_args,
                                                    self.on_column)



class UpdateDataFromDataTableState(State):
    __gtype_name__ = 'UpdateDataFromDataTableState'

    column: int
    row: int
    column_span: int
    row_span: int
    dfi: int

    before_path: str
    after_path: str

    include_header: bool

    def __init__(self,
                 column:         int,
                 row:            int,
                 column_span:    int,
                 row_span:       int,
                 dfi:            int,
                 include_header: bool,
                 before:         polars.DataFrame,
                 after:          polars.DataFrame) -> None:
        super().__init__()

        self.save_selection(restore_scroll=True)

        self.column = column
        self.row = row
        self.column_span = column_span
        self.row_span = row_span
        self.dfi = dfi

        self.before_path = self.write_snapshot(before)
        self.after_path = self.write_snapshot(after)

        self.include_header = include_header

    def undo(self) -> None:
        document = globals.history.document
        document.data.update_cell_data_block_from_metadata(self.column,
                                                           self.row,
                                                           self.column_span,
                                                           self.row_span,
                                                           self.dfi,
                                                           self.include_header,
                                                           polars.read_parquet(self.before_path))

        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document
        document.update_current_cells_from_datatable(polars.read_parquet(self.after_path))



class DuplicateRowState(State):
    __gtype_name__ = 'DuplicateRowState'

    row_span: int
    above: bool

    def __init__(self,
                 row_span: int,
                 above:    bool) -> None:
        super().__init__()

        self.save_selection()

        self.row_span = row_span
        self.above = above

    def undo(self) -> None:
        document = globals.history.document

        prow_span, self.arange.row_span = self.arange.row_span, self.row_span

        if not self.above:
            document.selection.current_active_range.metadata.row += self.arange.row_span
        else:
            document.selection.current_active_range = self.arange

        document.delete_current_rows()

        self.arange.row_span = prow_span

        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document
        document.duplicate_from_current_rows(self.above)



class DuplicateColumnState(State):
    __gtype_name__ = 'DuplicateColumnState'

    column_span: int
    left: bool

    def __init__(self,
                 column_span: int,
                 left:        bool) -> None:
        super().__init__()

        self.column_span = column_span
        self.left = left

        self.save_selection()

    def undo(self) -> None:
        document = globals.history.document

        pcolumn_span, self.arange.column_span = self.arange.column_span, self.column_span

        if not self.left:
            document.selection.current_active_range.metadata.column += self.arange.column_span
        else:
            document.selection.current_active_range = self.arange

        document.delete_current_columns()

        self.arange.column_span = pcolumn_span

        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document
        document.duplicate_from_current_columns(self.left)



class DeleteRowState(State):
    __gtype_name__ = 'DeleteRowState'

    file_path: str
    vflags_path: str
    rheights_path: str

    def __init__(self,
                 dataframe: polars.DataFrame,
                 vflags:    polars.Series,
                 rheights:  polars.Series) -> None:
        super().__init__()

        self.save_selection()

        self.file_path = self.write_snapshot(dataframe) if dataframe is not None \
                                                        else None

        self.vflags_path = self.write_snapshot(polars.DataFrame({'vflags': vflags})) if vflags is not None \
                                                                                     else None

        self.rheights_path = self.write_snapshot(polars.DataFrame({'rheights': rheights})) if rheights is not None \
                                                                                           else None

    def undo(self) -> None:
        document = globals.history.document

        self.restore_selection(False)

        document.insert_from_current_rows(polars.read_parquet(self.file_path),
                                          polars.read_parquet(self.vflags_path).to_series() if self.vflags_path is not None
                                                                                            else None,
                                          polars.read_parquet(self.rheights_path).to_series() if self.rheights_path is not None
                                                                                              else None)

    def redo(self) -> None:
        document = globals.history.document
        document.delete_current_rows()



class DeleteColumnState(State):
    __gtype_name__ = 'DeleteColumnState'

    file_path: str
    vflags_path: str
    cwidths_path: str

    def __init__(self,
                 dataframe: polars.DataFrame,
                 vflags:    polars.Series,
                 cwidths:   polars.Series) -> None:
        super().__init__()

        self.save_selection()

        self.file_path = self.write_snapshot(dataframe) if dataframe is not None \
                                                        else None

        self.vflags_path = self.write_snapshot(polars.DataFrame({'vflags': vflags})) if vflags is not None \
                                                                                     else None

        self.cwidths_path = self.write_snapshot(polars.DataFrame({'cwidths': cwidths})) if cwidths is not None \
                                                                                        else None

    def undo(self) -> None:
        document = globals.history.document

        self.restore_selection(False)

        document.insert_from_current_columns(polars.read_parquet(self.file_path),
                                             polars.read_parquet(self.vflags_path).to_series() if self.vflags_path is not None
                                                                                               else None,
                                             polars.read_parquet(self.cwidths_path).to_series() if self.cwidths_path is not None
                                                                                                else None)

    def redo(self) -> None:
        document = globals.history.document
        document.delete_current_columns()



class HideColumnState(State):
    __gtype_name__ = 'HideColumnState'

    def __init__(self) -> None:
        super().__init__()

        self.save_selection()

    def undo(self) -> None:
        document = globals.history.document

        self.restore_selection(False)

        document.unhide_current_columns()

        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document
        document.hide_current_columns()



class UnhideColumnState(State):
    __gtype_name__ = 'UnhideColumnState'

    column_span: int

    vflags_path: str

    def __init__(self, column_span: int, vflags: polars.Series) -> None:
        super().__init__()

        self.save_selection()

        self.column_span = column_span

        self.vflags_path = self.write_snapshot(polars.DataFrame({'vflags': vflags}))

    def undo(self) -> None:
        document = globals.history.document

        mdfi = self.arange.metadata.dfi
        mcolumn = self.arange.metadata.column

        # Update column visibility flags
        document.display.column_visibility_flags = polars.concat([document.display.column_visibility_flags[:mcolumn],
                                                                  polars.read_parquet(self.vflags_path).to_series(),
                                                                  document.display.column_visibility_flags[mcolumn + self.column_span:]])
        document.display.column_visible_series = document.display.column_visibility_flags.arg_true()
        document.data.bbs[mdfi].column_span = len(document.display.column_visible_series)

        document.repopulate_auto_filter_widgets()

        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document
        document.unhide_current_columns()



class UnhideAllColumnState(State):
    __gtype_name__ = 'UnhideAllColumnState'

    vflags_path: str

    def __init__(self, vflags: polars.Series) -> None:
        super().__init__()

        self.save_selection()

        self.vflags_path = self.write_snapshot(polars.DataFrame({'vflags': vflags}))

    def undo(self) -> None:
        document = globals.history.document

        mdfi = self.arange.metadata.dfi

        # Update column visibility flags
        document.display.column_visibility_flags = polars.read_parquet(self.vflags_path).to_series()
        document.display.column_visible_series = document.display.column_visibility_flags.arg_true()
        document.data.bbs[0].column_span = len(document.display.column_visible_series)

        # Update column widths
        if len(document.display.column_widths):
            column_widths_visible_only = document.display.column_widths
            if len(document.display.column_visibility_flags):
                column_widths_visible_only = column_widths_visible_only.filter(document.display.column_visibility_flags)
            document.display.cumulative_column_widths = polars.Series('ccwidths', column_widths_visible_only).cum_sum()

        document.repopulate_auto_filter_widgets()

        self.restore_selection()

        document.emit('columns-changed', mdfi)

    def redo(self) -> None:
        document = globals.history.document
        document.unhide_all_columns()



class FilterRowState(State):
    __gtype_name__ = 'FilterRowState'

    vflags_path: str
    rheights_path: str

    multiple: bool
    inverse: bool

    cfilters: dict
    pfilters: dict

    def __init__(self,
                 vflags:   polars.Series,
                 rheights: polars.Series,
                 multiple: bool,
                 inverse:  bool,
                 cfilters: dict,
                 pfilters: dict) -> None:
        super().__init__()

        self.save_selection()

        self.vflags_path = self.write_snapshot(polars.DataFrame({'vflags': vflags})) if vflags is not None \
                                                                                     else None

        self.rheights_path = self.write_snapshot(polars.DataFrame({'rheights': rheights})) if rheights is not None \
                                                                                           else None

        self.multiple = multiple
        self.inverse = inverse

        self.cfilters = cfilters
        self.pfilters = pfilters

    def undo(self) -> None:
        document = globals.history.document

        mdfi = self.arange.metadata.dfi

        # Update current filters
        document.current_filters = copy.deepcopy(self.cfilters)
        document.pending_filters = []

        # Update row visibility flags
        if self.vflags_path is not None:
            document.display.row_visibility_flags = polars.read_parquet(self.vflags_path).to_series()
            document.display.row_visible_series = document.display.row_visibility_flags.arg_true()
            document.data.bbs[mdfi].row_span = len(document.display.row_visible_series)
        else:
            document.display.row_visibility_flags = polars.Series(dtype=polars.Boolean)
            document.display.row_visible_series = polars.Series(dtype=polars.UInt32)
            document.data.bbs[mdfi].row_span = document.data.dfs[mdfi].height + 1

        # Update row heights
        if self.rheights_path is not None:
            document.display.row_heights = polars.read_parquet(self.rheights_path).to_series()
            row_heights_visible_only = document.display.row_heights
            if len(document.display.row_visibility_flags):
                row_heights_visible_only = row_heights_visible_only.filter(document.display.row_visibility_flags)
            document.display.cumulative_row_heights = polars.Series('crheights', row_heights_visible_only).cum_sum()
        else:
            document.display.row_heights = polars.Series(dtype=polars.UInt32)
            document.display.cumulative_row_heights = polars.Series(dtype=polars.UInt32)

        self.restore_selection()

        document.emit('filters-changed', mdfi)

    def redo(self) -> None:
        document = globals.history.document

        document.current_filters = copy.deepcopy(self.cfilters)
        document.pending_filters = copy.deepcopy(self.pfilters)

        document.filter_current_rows(self.multiple, self.inverse)



class ResetFilterRowState(State):
    __gtype_name__ = 'ResetFilterRowState'

    vflags_path: str
    rheights_path: str

    cfilters: dict

    def __init__(self,
                 vflags:   polars.Series,
                 rheights: polars.Series,
                 cfilters: dict) -> None:
        super().__init__()

        self.save_selection()

        self.vflags_path = self.write_snapshot(polars.DataFrame({'vflags': vflags})) if vflags is not None \
                                                                                     else None

        self.rheights_path = self.write_snapshot(polars.DataFrame({'rheights': rheights})) if rheights is not None \
                                                                                           else None

        self.cfilters = cfilters

    def undo(self) -> None:
        document = globals.history.document

        mdfi = self.arange.metadata.dfi

        # Update current filters
        document.current_filters = copy.deepcopy(self.cfilters)
        document.pending_filters = {}

        # Update row visibility flags
        if self.vflags_path is not None:
            document.display.row_visibility_flags = polars.read_parquet(self.vflags_path).to_series()
            document.display.row_visible_series = document.display.row_visibility_flags.arg_true()
            document.data.bbs[mdfi].row_span = len(document.display.row_visible_series)
        else:
            document.display.row_visibility_flags = polars.Series(dtype=polars.Boolean)
            document.display.row_visible_series = polars.Series(dtype=polars.UInt32)
            document.data.bbs[mdfi].row_span = document.data.dfs[mdfi].height + 1

        # Update row heights
        if self.rheights_path is not None:
            document.display.row_heights = polars.read_parquet(self.rheights_path).to_series()
            row_heights_visible_only = document.display.row_heights
            if len(document.display.row_visibility_flags):
                row_heights_visible_only = row_heights_visible_only.filter(document.display.row_visibility_flags)
            document.display.cumulative_row_heights = polars.Series('crheights', row_heights_visible_only).cum_sum()
        else:
            document.display.row_heights = polars.Series(dtype=polars.UInt32)
            document.display.cumulative_row_heights = polars.Series(dtype=polars.UInt32)

    def redo(self) -> None:
        document = globals.history.document
        document.reset_all_filters()



class SortRowState(State):
    __gtype_name__ = 'SortRowState'

    dfi: int
    descending: bool
    multiple: bool

    csorts: int
    psorts: int

    rindex_path: str
    vflags_path: str

    def __init__(self,
                 rindex:     polars.DataFrame,
                 vflags:     polars.Series,
                 dfi:        int,
                 descending: bool,
                 multiple:   bool,
                 csorts:     dict,
                 psorts:     dict) -> None:
        super().__init__()

        self.save_selection()

        self.dfi = dfi
        self.descending = descending
        self.multiple = multiple

        self.csorts = csorts
        self.psorts = psorts

        self.rindex_path = self.write_snapshot(polars.DataFrame(rindex))

        self.vflags_path = self.write_snapshot(polars.DataFrame({'vflags': vflags})) if vflags is not None \
                                                                                     else None

    def undo(self) -> None:
        document = globals.history.document

        document.data.dfs[self.dfi].insert_column(0, polars.read_parquet(self.rindex_path).to_series())
        document.data.sort_rows_from_metadata({'$ridx': {'descending': False}}, self.dfi)

        # Update row visibility flags
        if self.vflags_path is not None:
            document.display.row_visibility_flags = polars.read_parquet(self.vflags_path).to_series()
            document.display.row_visible_series = document.display.row_visibility_flags.arg_true()

        # Update row heights
        if len(document.display.row_heights):
            sorted_row_heights = polars.DataFrame({'rheights': document.display.row_heights[1:],
                                                   '$ridx': document.data.dfs[self.dfi]['$ridx']}).sort('$ridx').to_series()
            document.display.row_heights = polars.concat([polars.Series([True]), sorted_row_heights])
            row_heights_visible_only = document.display.row_heights
            if len(document.display.row_visibility_flags):
                row_heights_visible_only = row_heights_visible_only.filter(document.display.row_visibility_flags)
            document.display.cumulative_row_heights = polars.Series('crheights', row_heights_visible_only).cum_sum()

        document.data.dfs[self.dfi].drop_in_place('$ridx')

        # Update current sorts
        document.current_sorts = copy.deepcopy(self.csorts)
        document.pending_sorts = {}

        self.restore_selection()

        document.emit('sorts-changed', self.dfi)

    def redo(self) -> None:
        document = globals.history.document

        self.restore_selection(False)

        document.current_sorts = copy.deepcopy(self.csorts)
        document.pending_sorts = copy.deepcopy(self.psorts)

        document.sort_current_rows(self.descending, self.multiple)



class ReorderColumnState(State):
    __gtype_name__ = 'ReorderColumnState'

    before: list[str]
    after: list[str]

    def __init__(self,
                 before: list[str],
                 after:  list[str]) -> None:
        super().__init__()

        self.save_selection()

        self.before = before
        self.after = after

    def undo(self) -> None:
        document = globals.history.document
        document.reorder_current_columns(self.before)

        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document
        document.reorder_current_columns(self.after)



class ConvertColumnDataTypeState(State):
    __gtype_name__ = 'ConvertColumnDataTypeState'

    before: polars.DataType
    after: polars.DataType

    def __init__(self,
                 before: polars.DataType,
                 after:  polars.DataType) -> None:
        super().__init__()

        self.save_selection()

        self.before = before
        self.after = after

    def undo(self) -> None:
        document = globals.history.document
        document.convert_current_columns_dtype(self.before)

        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document
        document.convert_current_columns_dtype(self.after)



class KeepRowState(State):
    __gtype_name__ = 'KeepRowState'

    file_path: str
    vflags_path: str
    rheights_path: str

    strategy: str
    no_rows: int
    first_row: int

    def __init__(self,
                 content:   Any,
                 vflags:    polars.Series,
                 rheights:  polars.Series,
                 strategy:  str,
                 no_rows:   int,
                 first_row: int) -> None:
        super().__init__()

        self.save_selection(restore_scroll=True)

        self.file_path = self.write_snapshot(content)

        self.vflags_path = self.write_snapshot(polars.DataFrame({'vflags': vflags})) if vflags is not None \
                                                                                     else None

        self.rheights_path = self.write_snapshot(polars.DataFrame({'rheights': rheights})) if rheights is not None \
                                                                                           else None

        self.strategy = strategy
        self.no_rows = no_rows
        self.first_row = first_row

    def undo(self) -> None:
        document = globals.history.document

        document.data.dfs[0] = polars.read_parquet(self.file_path)

        # Update row visibility flags
        if self.vflags_path is not None:
            document.display.row_visibility_flags = polars.read_parquet(self.vflags_path).to_series()
            document.display.row_visible_series = document.display.row_visibility_flags.arg_true()
            document.data.bbs[0].row_span = len(document.display.row_visible_series)
        else:
            document.display.row_visibility_flags = polars.Series(dtype=polars.Boolean)
            document.display.row_visible_series = polars.Series(dtype=polars.UInt32)
            document.data.bbs[0].row_span = document.data.dfs[0].height + 1

        # Update row heights
        if self.rheights_path is not None:
            document.display.row_heights = polars.read_parquet(self.rheights_path).to_series()
            row_heights_visible_only = document.display.row_heights
            if len(document.display.row_visibility_flags):
                row_heights_visible_only = row_heights_visible_only.filter(document.display.row_visibility_flags)
            document.display.cumulative_row_heights = polars.Series('crheights', row_heights_visible_only).cum_sum()
        else:
            document.display.row_heights = polars.Series(dtype=polars.UInt32)
            document.display.cumulative_row_heights = polars.Series(dtype=polars.UInt32)

        document.auto_adjust_selections_by_crud(0, 0, False)

        # TODO: clear only for the related columns
        document.data.clear_cell_data_unique_cache(0)

    def redo(self) -> None:
        document = globals.history.document

        self.restore_selection()

        document.keep_n_rows(self.strategy,
                             self.no_rows,
                             self.first_row)



class FindReplaceDataState(State):
    __gtype_name__ = 'FindReplaceDataState'

    content: str
    replace_with: str
    search_pattern: str
    match_case: bool

    def __init__(self,
                 content:        str,
                 replace_with:   str,
                 search_pattern: str,
                 match_case:     bool) -> None:
        super().__init__()

        self.save_selection(restore_scroll=True)

        self.content = content
        self.replace_with = replace_with
        self.search_pattern = search_pattern
        self.match_case = match_case

    def undo(self) -> None:
        document = globals.history.document
        document.update_current_cells_from_literal(self.content)
        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document
        document.find_replace_in_current_cells(self.replace_with,
                                               self.search_pattern,
                                               self.match_case)



class FindReplaceAllDataState(State):
    __gtype_name__ = 'FindReplaceAllDataState'

    file_path: str

    column_names: list[str]
    row: int
    row_span: int
    dfi: int

    search_pattern: str
    replace_with: str
    match_case: bool
    match_cell: bool
    within_selection: bool
    use_regexp: bool

    def __init__(self,
                 content:          Any,
                 column_names:     list[str],
                 row:              int,
                 row_span:         int,
                 dfi:              int,
                 search_pattern:   str,
                 replace_with:     str,
                 match_case:       bool,
                 match_cell:       bool,
                 within_selection: bool,
                 use_regexp:       bool) -> None:
        super().__init__()

        self.save_selection(restore_scroll=True)

        self.file_path = self.write_snapshot(content)

        self.column_names = column_names
        self.row = row
        self.row_span = row_span
        self.dfi = dfi

        self.search_pattern = search_pattern
        self.replace_with = replace_with
        self.match_case = match_case
        self.match_cell = match_cell
        self.within_selection = within_selection
        self.use_regexp = use_regexp

    def undo(self) -> None:
        document = globals.history.document
        document.data.update_cell_data_blocks_from_metadata(self.column_names,
                                                            self.row,
                                                            self.row_span,
                                                            self.dfi,
                                                            polars.read_parquet(self.file_path))

    def redo(self) -> None:
        document = globals.history.document

        self.restore_selection()

        document.find_replace_all_in_current_cells(self.search_pattern,
                                                   self.replace_with,
                                                   self.match_case,
                                                   self.match_cell,
                                                   self.within_selection,
                                                   self.use_regexp)



class ToggleColumnVisibilityState(State):
    __gtype_name__ = 'ToggleColumnVisibilityState'

    column: int
    show: bool

    def __init__(self,
                 column: int,
                 show:   bool) -> None:
        super().__init__()

        self.save_selection()

        self.column = column
        self.show = show

    def undo(self) -> None:
        document = globals.history.document
        document.toggle_column_visibility(self.column, not self.show)

        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document
        document.toggle_column_visibility(self.column, self.show)



class UpdateColumnWidthState(State):
    __gtype_name__ = 'UpdateColumnWidthState'

    column: int
    before: int
    after: int

    def __init__(self,
                 column: int,
                 before: int,
                 after:  int) -> None:
        super().__init__()

        self.save_selection()

        self.column = column
        self.before = before
        self.after = after

    def undo(self) -> None:
        document = globals.history.document
        document.update_column_width(self.column, self.before)

        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document
        document.update_column_width(self.column, self.after)



class RenameSheetState(State):
    __gtype_name__ = 'RenameSheetState'

    window: Window

    before: str
    after: str

    def __init__(self,
                 window: Window,
                 before: str,
                 after:  str) -> None:
        super().__init__()

        self.window = window

        self.before = before
        self.after = after

    def undo(self) -> None:
        document = globals.history.document
        document.title = self.before

        self.window.emit('update-connection-list')

    def redo(self) -> None:
        document = globals.history.document
        document.title = self.after

        self.window.emit('update-connection-list')



class HistoryManager(GObject.Object):
    __gtype_name__ = 'HistoryManager'

    document: SheetDocument

    undo_stack: deque[State]
    redo_stack: deque[State]

    TIME_THRESHOLD = 1.0 # in seconds

    def __init__(self, document: SheetDocument) -> None:
        super().__init__()

        self.document = document

        self.undo_stack = deque()
        self.redo_stack = deque()

        from .file_manager import FileManager
        self.file_manager = FileManager()

    def setup_history(self) -> None:
        self.undo_stack.clear()

        # We need to save the current state at the beginning
        state = SelectionState(1, 1, 1, 1, True, True, True)
        self.undo_stack.append(state)

    def save(self, state: State) -> None:
        if len(self.undo_stack) > 1 \
                and type(state) is type(self.undo_stack[-1]) \
                and isinstance(state, SelectionState) \
                and state.col_1 == self.undo_stack[-1].col_1 \
                and state.row_1 == self.undo_stack[-1].row_1 \
                and state.col_2 == self.undo_stack[-1].col_2 \
                and state.row_2 == self.undo_stack[-1].row_2:
            return # skip duplicate selection states

        if len(self.undo_stack) > 1 \
                and type(state) is type(self.undo_stack[-1]) \
                and isinstance(state, SelectionState) \
                and abs(state.timestamp - self.undo_stack[-1].timestamp) < self.TIME_THRESHOLD:
            self.undo_stack[-1].col_1 = state.col_1
            self.undo_stack[-1].row_1 = state.row_1
            self.undo_stack[-1].col_2 = state.col_2
            self.undo_stack[-1].row_2 = state.row_2
            return # update last selection states

        self.undo_stack.append(state)
        self.cleanup_redo_stack()

    def undo(self) -> None:
        globals.is_changing_state = True

        if len(self.undo_stack) == 1:
            self.undo_stack[0].undo()
        else:
            state = self.undo_stack.pop()
            state.undo()
            self.redo_stack.append(state)

        scroll_y_position = self.undo_stack[-1].scroll_y
        scroll_x_position = self.undo_stack[-1].scroll_x

        if self.undo_stack[-1].restore_scroll:
            self.restore_scroll_position(scroll_y_position, scroll_x_position)

        self.redraw_main_canvas()

        globals.is_changing_state = False

    def redo(self) -> None:
        if len(self.redo_stack) == 0:
            return

        globals.is_changing_state = True

        state = self.redo_stack.pop()
        state.redo()
        self.undo_stack.append(state)

        if state.restore_scroll:
            self.restore_scroll_position(state.scroll_y, state.scroll_x)

        self.redraw_main_canvas()

        globals.is_changing_state = False

    def restore_scroll_position(self,
                                scroll_y: float,
                                scroll_x: float) -> None:
        if isinstance(self.document, SheetDocument):
            # TODO: don't restore if the target cell is already visible?
            canvas_height = self.document.view.main_canvas.get_height()
            canvas_width = self.document.view.main_canvas.get_width()

            vadjustment = self.document.view.vertical_scrollbar.get_adjustment()
            hadjustment = self.document.view.horizontal_scrollbar.get_adjustment()

            vadjustment.set_upper(scroll_y + canvas_height)
            hadjustment.set_upper(scroll_x + canvas_width)

            vadjustment.set_value(scroll_y)
            hadjustment.set_value(scroll_x)

            # Make sure that the cursor is visible in case the user has toggled some
            # UI elements causing the cursor to be hidden, for example the sidebar.
            self.document.auto_adjust_scrollbars_by_selection()
            self.document.auto_adjust_locators_size_by_scroll()
            self.document.auto_adjust_selections_by_scroll()
            self.document.repopulate_auto_filter_widgets()

    def redraw_main_canvas(self) -> None:
        if isinstance(self.document, SheetDocument):
            self.document.renderer.render_caches = {}
            self.document.view.main_canvas.queue_draw()

    def delete_snapshot(self, file_path: str) -> None:
        self.file_manager.delete_file(file_path)

    def cleanup_undo_stack(self) -> None:
        for state in self.undo_stack:
            for attribute in dir(state):
                if attribute.endswith('_path'):
                    file_path = getattr(state, attribute)
                    if file_path is not None:
                        self.delete_snapshot(file_path)
        self.undo_stack.clear()

    def cleanup_redo_stack(self) -> None:
        for state in self.redo_stack:
            for attribute in dir(state):
                if attribute.endswith('_path'):
                    file_path = getattr(state, attribute)
                    if file_path is not None:
                        self.delete_snapshot(file_path)
        self.redo_stack.clear()

    def cleanup_all(self) -> None:
        self.cleanup_undo_stack()
        self.cleanup_redo_stack()