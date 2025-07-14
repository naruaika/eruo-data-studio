# history_manager.py
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


from collections import deque
from gi.repository import GObject
from tempfile import NamedTemporaryFile
import polars
import time

from . import globals
from .sheet_document import SheetDocument
from .sheet_selection import SheetCell

class State(GObject.Object):
    __gtype_name__ = 'State'

    timestamp: float

    scroll_x: int
    scroll_y: int

    def __init__(self) -> None:
        super().__init__()

        self.timestamp = time.time()

        document = globals.history.document
        self.scroll_x = document.display.scroll_x_position
        self.scroll_y = document.display.scroll_y_position



class SelectionState(State):
    __gtype_name__ = 'SelectionState'

    col_1: int
    row_1: int
    col_2: int
    row_2: int

    keep_order: bool
    follow_cursor: bool
    auto_scroll: bool

    range: SheetCell
    active: SheetCell
    cursor: SheetCell

    def __init__(self, col_1: int, row_1: int, col_2: int, row_2: int,
                 keep_order: bool, follow_cursor: bool, auto_scroll: bool) -> None:
        super().__init__()

        self.col_1 = col_1
        self.row_1 = row_1
        self.col_2 = col_2
        self.row_2 = row_2

        self.keep_order = keep_order
        self.follow_cursor = follow_cursor
        self.auto_scroll = auto_scroll

        document = globals.history.document
        self.range = document.selection.current_active_range
        self.active = document.selection.current_active_cell
        self.cursor = document.selection.current_cursor_cell

    def undo(self) -> None:
        document = globals.history.document

        document.selection.current_active_range = self.range
        document.selection.current_active_cell = self.active
        document.selection.current_cursor_cell = self.cursor

        document.notify_selection_changed(self.active.column, self.active.row, self.active.metadata)

    def redo(self) -> None:
        document = globals.history.document
        document.update_selection_from_position(self.col_1, self.row_1, self.col_2, self.row_2,
                                                self.keep_order, self.follow_cursor, self.auto_scroll)



class InsertBlankRowState(State):
    __gtype_name__ = 'InsertBlankRowState'

    row_span: int
    above: bool

    range: SheetCell
    active: SheetCell
    cursor: SheetCell

    def __init__(self, row_span: int, above: bool) -> None:
        super().__init__()

        self.row_span = row_span
        self.above = above

        document = globals.history.document
        self.range = document.selection.current_active_range
        self.active = document.selection.current_active_cell
        self.cursor = document.selection.current_cursor_cell

    def undo(self) -> None:
        document = globals.history.document

        prow_span, self.range.row_span = self.range.row_span, self.row_span

        if not self.above:
            document.selection.current_active_range.metadata.row += self.range.row_span
        else:
            document.selection.current_active_range = self.range

        document.delete_current_rows()

        self.range.row_span = prow_span

        document.selection.current_active_range = self.range
        document.selection.current_active_cell = self.active
        document.selection.current_cursor_cell = self.cursor

        document.notify_selection_changed(self.active.column, self.active.row, self.active.metadata)

    def redo(self) -> None:
        document = globals.history.document
        document.insert_blank_from_current_rows(self.above)



class InsertBlankColumnState(State):
    __gtype_name__ = 'InsertBlankColumnState'

    above: bool

    range: SheetCell
    active: SheetCell
    cursor: SheetCell

    def __init__(self, left: bool) -> None:
        super().__init__()

        self.left = left

        document = globals.history.document
        self.range = document.selection.current_active_range
        self.active = document.selection.current_active_cell
        self.cursor = document.selection.current_cursor_cell

    def undo(self) -> None:
        document = globals.history.document

        if not self.left:
            document.selection.current_active_range.metadata.column += self.range.column_span
        else:
            document.selection.current_active_range = self.range

        document.delete_current_columns()

        document.selection.current_active_range = self.range
        document.selection.current_active_cell = self.active
        document.selection.current_cursor_cell = self.cursor

    def redo(self) -> None:
        document = globals.history.document
        document.insert_blank_from_current_columns(self.left)



class UpdateDataState(State):
    __gtype_name__ = 'UpdateDataState'

    # When header is None, it means the header is not changed.
    # The header can be a list or a single value.
    header: any

    # When content is None, it means the content is not changed.
    # The header can only be a DataFrame and when it is, we'll
    # store the content as a parquet file, assign None to content,
    # and store the file path.
    content: any
    file_path: str

    # The replacer is an object that'll be used to replace the data.
    # It can be a single value or a numpy array. TODO: For now, only
    # single value is supported.
    replacer: any

    def __init__(self, header: any, content: any, replacer: any) -> None:
        super().__init__()

        self.header = header
        self.replacer = replacer

        if isinstance(content, polars.DataFrame):
            if content.height == 0:
                self.content = None
                self.file_path = None
            else:
                with NamedTemporaryFile(suffix='.ersnap', delete=False) as file_path:
                    # TODO: we leave uncompressed for now, but we may want to determine
                    # the compression level based on the size of the dataframe later.
                    content.write_parquet(file_path.name, compression='uncompressed', statistics=False)
                    self.content = None
                    self.file_path = file_path.name
        else:
            self.content = content
            self.file_path = None

    def undo(self) -> None:
        document = globals.history.document
        if self.file_path is not None:
            document.update_current_cells([self.header, polars.read_parquet(self.file_path)])
        else:
            document.update_current_cells([self.header, self.content])

    def redo(self) -> None:
        document = globals.history.document
        document.update_current_cells(self.replacer)



class DuplicateRowState(State):
    __gtype_name__ = 'DuplicateRowState'

    row_span: int
    above: bool

    range: SheetCell
    active: SheetCell
    cursor: SheetCell

    def __init__(self, row_span: int, above: bool) -> None:
        super().__init__()

        self.row_span = row_span
        self.above = above

        document = globals.history.document
        self.range = document.selection.current_active_range
        self.active = document.selection.current_active_cell
        self.cursor = document.selection.current_cursor_cell

    def undo(self) -> None:
        document = globals.history.document

        prow_span, self.range.row_span = self.range.row_span, self.row_span

        if not self.above:
            document.selection.current_active_range.metadata.row += self.range.row_span
        else:
            document.selection.current_active_range = self.range

        document.delete_current_rows()

        self.range.row_span = prow_span

        document.selection.current_active_range = self.range
        document.selection.current_active_cell = self.active
        document.selection.current_cursor_cell = self.cursor

        document.notify_selection_changed(self.active.column, self.active.row, self.active.metadata)

    def redo(self) -> None:
        document = globals.history.document
        document.duplicate_from_current_rows(self.above)



class DuplicateColumnState(State):
    __gtype_name__ = 'DuplicateColumnState'

    above: bool

    range: SheetCell
    active: SheetCell
    cursor: SheetCell

    def __init__(self, left: bool) -> None:
        super().__init__()

        self.left = left

        document = globals.history.document
        self.range = document.selection.current_active_range
        self.active = document.selection.current_active_cell
        self.cursor = document.selection.current_cursor_cell

    def undo(self) -> None:
        document = globals.history.document

        if not self.left:
            document.selection.current_active_range.metadata.column += self.range.column_span
        else:
            document.selection.current_active_range = self.range

        document.delete_current_columns()

        document.selection.current_active_range = self.range
        document.selection.current_active_cell = self.active
        document.selection.current_cursor_cell = self.cursor

    def redo(self) -> None:
        document = globals.history.document
        document.duplicate_from_current_columns(self.left)



class DeleteRowState(State):
    __gtype_name__ = 'DeleteRowState'

    file_path: str
    vflags_path: str

    range: SheetCell
    active: SheetCell
    cursor: SheetCell

    def __init__(self, dataframe: polars.DataFrame, vflags: polars.Series) -> None:
        super().__init__()

        if dataframe is None:
            self.file_path = None
            return

        document = globals.history.document
        self.range = document.selection.current_active_range
        self.active = document.selection.current_active_cell
        self.cursor = document.selection.current_cursor_cell

        with NamedTemporaryFile(suffix='.ersnap', delete=False) as file_path:
            # TODO: we leave uncompressed for now, but we may want to determine
            # the compression level based on the size of the dataframe later.
            dataframe.write_parquet(file_path.name, compression='uncompressed', statistics=False)
            self.file_path = file_path.name

        if vflags is None:
            self.vflags_path = None
            return

        with NamedTemporaryFile(suffix='.ersnap', delete=False) as file_path:
            # TODO: we leave uncompressed for now, but we may want to determine
            # the compression level based on the size of the dataframe later.
            polars.DataFrame({'vflags': vflags}).write_parquet(file_path.name, compression='uncompressed', statistics=False)
            self.vflags_path = file_path.name

    def undo(self) -> None:
        document = globals.history.document

        document.selection.current_active_range = self.range
        document.selection.current_active_cell = self.active
        document.selection.current_cursor_cell = self.cursor

        document.insert_from_current_rows(polars.read_parquet(self.file_path),
                                          polars.read_parquet(self.vflags_path).to_series(0) if self.vflags_path is not None else None)

    def redo(self) -> None:
        document = globals.history.document
        document.delete_current_rows()



class DeleteColumnState(State):
    __gtype_name__ = 'DeleteColumnState'

    file_path: str

    range: SheetCell
    active: SheetCell
    cursor: SheetCell

    def __init__(self, dataframe: polars.DataFrame) -> None:
        super().__init__()

        if dataframe is None:
            self.file_path = None
            return

        with NamedTemporaryFile(suffix='.ersnap', delete=False) as file_path:
            # TODO: we leave uncompressed for now, but we may want to determine
            # the compression level based on the size of the dataframe later.
            dataframe.write_parquet(file_path.name, compression='uncompressed', statistics=False)
            self.file_path = file_path.name

        document = globals.history.document
        self.range = document.selection.current_active_range
        self.active = document.selection.current_active_cell
        self.cursor = document.selection.current_cursor_cell

    def undo(self) -> None:
        document = globals.history.document
        document.selection.current_active_range = self.range
        document.selection.current_active_cell = self.active
        document.selection.current_cursor_cell = self.cursor
        document.insert_from_current_columns(polars.read_parquet(self.file_path))

    def redo(self) -> None:
        document = globals.history.document
        document.delete_current_columns()



class SortRowState(State):
    __gtype_name__ = 'SortRowState'

    descending: bool
    dfi: int

    file_path: str
    vflags_path: str

    def __init__(self, descending: bool, dfi: int, rindex: polars.DataFrame, vflags: polars.Series) -> None:
        super().__init__()

        self.descending = descending
        self.dfi = dfi

        with NamedTemporaryFile(suffix='.ersnap', delete=False) as file_path:
            # TODO: we leave uncompressed for now, but we may want to determine
            # the compression level based on the size of the dataframe later.
            polars.DataFrame(rindex).write_parquet(file_path.name, compression='uncompressed', statistics=False)
            self.file_path = file_path.name

        if vflags is None:
            self.vflags_path = None
            return

        with NamedTemporaryFile(suffix='.ersnap', delete=False) as file_path:
            # TODO: we leave uncompressed for now, but we may want to determine
            # the compression level based on the size of the dataframe later.
            polars.DataFrame({'vflags': vflags}).write_parquet(file_path.name, compression='uncompressed', statistics=False)
            self.vflags_path = file_path.name

    def undo(self) -> None:
        document = globals.history.document

        document.data.dfs[self.dfi].insert_column(0, polars.read_parquet(self.file_path).to_series(0))
        document.data.sort_rows_from_metadata(0, self.dfi, False)
        document.data.dfs[self.dfi].drop_in_place('$ridx')

        if self.vflags_path is not None:
            document.display.row_visibility_flags = polars.read_parquet(self.vflags_path).to_series(0)
            document.display.row_visible_series = document.display.row_visibility_flags.arg_true()

    def redo(self) -> None:
        document = globals.history.document
        document.sort_current_rows(self.descending)



class FilterRowState(State):
    __gtype_name__ = 'FilterRowState'

    dfi: int

    expression: polars.Expr

    range: SheetCell
    active: SheetCell
    cursor: SheetCell

    def __init__(self, dfi: int, expression: polars.Expr) -> None:
        super().__init__()

        self.dfi = dfi

        self.expression = expression

        document = globals.history.document
        self.range = document.selection.current_active_range
        self.active = document.selection.current_active_cell
        self.cursor = document.selection.current_cursor_cell

    def undo(self) -> None:
        document = globals.history.document
        document.data.fes[self.dfi] = self.expression

        document.selection.current_active_range = self.range
        document.selection.current_active_cell = self.active
        document.selection.current_cursor_cell = self.cursor

        if self.expression is not None:
            document.display.row_visibility_flags = polars.concat([polars.Series([True]), # for header row
                                                                   document.data.dfs[self.dfi].with_columns(self.expression.alias('$vrow'))['$vrow']])
        else:
            document.display.row_visibility_flags = polars.Series(dtype=polars.Boolean)

        document.display.row_visible_series = document.display.row_visibility_flags.arg_true()

        if self.expression is not None:
            document.data.bbs[self.dfi].row_span = len(document.display.row_visible_series)
        else:
            document.data.bbs[self.dfi].row_span = document.data.dfs[self.dfi].height

    def redo(self) -> None:
        document = globals.history.document
        document.data.fes[self.dfi] = self.expression

        document.selection.current_active_range = self.range
        document.selection.current_active_cell = self.active
        document.selection.current_cursor_cell = self.cursor

        document.filter_current_rows()



class ConvertDataState(State):
    __gtype_name__ = 'ConvertDataState'

    before: polars.DataType
    after: polars.DataType

    def __init__(self, before: polars.DataType, after: polars.DataType) -> None:
        super().__init__()

        self.before = before
        self.after = after

    def undo(self) -> None:
        document = globals.history.document
        document.convert_current_columns_dtype(self.before)

    def redo(self) -> None:
        document = globals.history.document
        document.convert_current_columns_dtype(self.after)



class HistoryManager(GObject.Object):
    __gtype_name__ = 'HistoryManager'

    document: SheetDocument

    undo_stack: deque[State]
    redo_stack: deque[State]

    TIME_THRESHOLD = 0.5 # in seconds

    def __init__(self, document: SheetDocument) -> None:
        super().__init__()

        self.document = document

        self.undo_stack = deque()
        self.redo_stack = deque()

        from .file_manager import FileManager
        self.file_manager = FileManager()

    def setup(self) -> None:
        # We need to save the current state at the beginning
        state = SelectionState(0, 0, 0, 0, True, True, True)
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
                and (state.timestamp - self.undo_stack[-1].timestamp) < self.TIME_THRESHOLD:
            self.undo_stack.pop() # replace the last state

        self.undo_stack.append(state)
        self.cleanup_redo_stack()

    def undo(self) -> None:
        if len(self.undo_stack) == 1:
            return # initial state isn't undoable

        globals.is_changing_state = True

        state = self.undo_stack.pop()
        state.undo()
        self.redo_stack.append(state)

        scroll_x_position = globals.history.undo_stack[-1].scroll_x
        scroll_y_position = globals.history.undo_stack[-1].scroll_y

        self.auto_adjust_scrollbars(scroll_y_position, scroll_x_position)

        globals.is_changing_state = False

    def redo(self) -> None:
        if len(self.redo_stack) == 0:
            return

        globals.is_changing_state = True

        state = self.redo_stack.pop()
        state.redo()
        self.undo_stack.append(state)

        self.auto_adjust_scrollbars(state.scroll_y, state.scroll_x)

        globals.is_changing_state = False

    def auto_adjust_scrollbars(self, scroll_y: float, scroll_x: float) -> None:
        vertical_adjustment = self.document.view.vertical_scrollbar.get_adjustment()
        horizontal_adjustment = self.document.view.horizontal_scrollbar.get_adjustment()

        vertical_adjustment.set_value(scroll_y)
        horizontal_adjustment.set_value(scroll_x)

        self.document.renderer.render_caches = {}
        self.document.view.main_canvas.queue_draw()

    def write_snapshot(self, dfi: int = 0) -> str:
        with NamedTemporaryFile(suffix='.ersnap', delete=False) as file_path:
            if self.file_manager.write_file(file_path.name, self.document.data, dfi):
                return file_path
        return None

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