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
import copy
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

    # Optionals
    range: SheetCell
    active: SheetCell
    cursor: SheetCell

    search_range: SheetCell

    def __init__(self) -> None:
        super().__init__()

        self.timestamp = time.time()

        # TODO: should we also store the scrollbar uppers?
        document = globals.history.document
        self.scroll_x = document.display.scroll_x_position
        self.scroll_y = document.display.scroll_y_position

    def save_selection(self) -> None:
        document = globals.history.document

        self.range = document.selection.current_active_range
        self.active = document.selection.current_active_cell
        self.cursor = document.selection.current_cursor_cell

        self.search_range = document.selection.current_search_range

    def restore_selection(self, notify: bool = True) -> None:
        document = globals.history.document

        document.selection.current_active_range = self.range
        document.selection.current_active_cell = self.active
        document.selection.current_cursor_cell = self.cursor

        document.selection.current_search_range = self.search_range

        if notify:
            document.notify_selection_changed(self.active.column, self.active.row, self.active.metadata)

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

    def __init__(self, col_1: int, row_1: int, col_2: int, row_2: int,
                 keep_order: bool, follow_cursor: bool, auto_scroll: bool) -> None:
        super().__init__()

        self.save_selection()

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
        document.update_selection_from_position(self.col_1, self.row_1, self.col_2, self.row_2,
                                                self.keep_order, self.follow_cursor, self.auto_scroll)



class InsertBlankRowState(State):
    __gtype_name__ = 'InsertBlankRowState'

    row_span: int
    above: bool

    def __init__(self, row_span: int, above: bool) -> None:
        super().__init__()

        self.save_selection()

        self.row_span = row_span
        self.above = above

    def undo(self) -> None:
        document = globals.history.document

        prow_span, self.range.row_span = self.range.row_span, self.row_span

        if not self.above:
            document.selection.current_active_range.metadata.row += self.range.row_span
        else:
            document.selection.current_active_range = self.range

        document.delete_current_rows()

        self.range.row_span = prow_span

        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document
        document.insert_blank_from_current_rows(self.above)



class InsertBlankColumnState(State):
    __gtype_name__ = 'InsertBlankColumnState'

    column_span: int
    left: bool

    def __init__(self, column_span: int, left: bool) -> None:
        super().__init__()

        self.save_selection()

        self.column_span = column_span
        self.left = left

    def undo(self) -> None:
        document = globals.history.document

        pcolumn_span, self.range.column_span = self.range.column_span, self.column_span

        if not self.left:
            document.selection.current_active_range.metadata.column += self.range.column_span
        else:
            document.selection.current_active_range = self.range

        document.delete_current_columns()

        self.range.column_span = pcolumn_span

        self.restore_selection()

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

    # It can be a single value or a polars.DataFrame
    # TODO: for now only single value is supported.
    replace_with: any

    # It can be None when there is no search pattern in case
    # the user wants to replace all the cell contents.
    search_pattern: str
    match_case: bool

    def __init__(self, header: any, content: any, replace_with: any, search_pattern: str, match_case: bool) -> None:
        super().__init__()

        self.save_selection()

        self.header = header

        self.replace_with = replace_with
        self.search_pattern = search_pattern
        self.match_case = match_case

        if isinstance(content, polars.DataFrame):
            if content.height == 0:
                self.content = None
                self.file_path = None
            else:
                self.content = None
                self.file_path = self.write_snapshot(content)
        else:
            self.content = content
            self.file_path = None

    def undo(self) -> None:
        document = globals.history.document

        if self.file_path is not None:
            document.update_current_cells([self.header, polars.read_parquet(self.file_path)])
        else:
            document.update_current_cells([self.header, self.content])

        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document
        document.update_current_cells(self.replace_with, self.search_pattern, self.match_case)



class DuplicateRowState(State):
    __gtype_name__ = 'DuplicateRowState'

    row_span: int
    above: bool

    def __init__(self, row_span: int, above: bool) -> None:
        super().__init__()

        self.save_selection()

        self.row_span = row_span
        self.above = above

    def undo(self) -> None:
        document = globals.history.document

        prow_span, self.range.row_span = self.range.row_span, self.row_span

        if not self.above:
            document.selection.current_active_range.metadata.row += self.range.row_span
        else:
            document.selection.current_active_range = self.range

        document.delete_current_rows()

        self.range.row_span = prow_span

        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document
        document.duplicate_from_current_rows(self.above)



class DuplicateColumnState(State):
    __gtype_name__ = 'DuplicateColumnState'

    column_span: int
    left: bool

    def __init__(self, column_span: int, left: bool) -> None:
        super().__init__()

        self.column_span = column_span
        self.left = left

        self.save_selection()

    def undo(self) -> None:
        document = globals.history.document

        pcolumn_span, self.range.column_span = self.range.column_span, self.column_span

        if not self.left:
            document.selection.current_active_range.metadata.column += self.range.column_span
        else:
            document.selection.current_active_range = self.range

        document.delete_current_columns()

        self.range.column_span = pcolumn_span

        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document
        document.duplicate_from_current_columns(self.left)



class DeleteRowState(State):
    __gtype_name__ = 'DeleteRowState'

    file_path: str
    vflags_path: str
    rheights_path: str

    def __init__(self, dataframe: polars.DataFrame, vflags: polars.Series, rheights: polars.Series) -> None:
        super().__init__()

        self.save_selection()

        self.file_path = self.write_snapshot(dataframe) if dataframe is not None else None

        self.vflags_path = self.write_snapshot(polars.DataFrame({'vflags': vflags})) if vflags is not None else None

        self.rheights_path = self.write_snapshot(polars.DataFrame({'rheights': rheights})) if rheights is not None else None

    def undo(self) -> None:
        document = globals.history.document

        self.restore_selection(False)

        document.insert_from_current_rows(polars.read_parquet(self.file_path),
                                          polars.read_parquet(self.vflags_path).to_series(0) if self.vflags_path is not None else None,
                                          polars.read_parquet(self.rheights_path).to_series(0) if self.rheights_path is not None else None)

    def redo(self) -> None:
        document = globals.history.document
        document.delete_current_rows()



class DeleteColumnState(State):
    __gtype_name__ = 'DeleteColumnState'

    file_path: str
    vflags_path: str
    cwidths_path: str

    def __init__(self, dataframe: polars.DataFrame, vflags: polars.Series, cwidths: polars.Series) -> None:
        super().__init__()

        self.save_selection()

        self.file_path = self.write_snapshot(dataframe) if dataframe is not None else None

        self.vflags_path = self.write_snapshot(polars.DataFrame({'vflags': vflags})) if vflags is not None else None

        self.cwidths_path = self.write_snapshot(polars.DataFrame({'cwidths': cwidths})) if cwidths is not None else None

    def undo(self) -> None:
        document = globals.history.document

        self.restore_selection(False)

        document.insert_from_current_columns(polars.read_parquet(self.file_path),
                                             polars.read_parquet(self.vflags_path).to_series(0) if self.vflags_path is not None else None,
                                             polars.read_parquet(self.cwidths_path).to_series(0) if self.cwidths_path is not None else None)

    def redo(self) -> None:
        document = globals.history.document
        document.delete_current_columns()



class FilterRowState(State):
    __gtype_name__ = 'FilterRowState'

    vflags_path: str
    rheights_path: str

    multiple: bool
    cfilters: dict
    pfilters: dict

    def __init__(self, vflags: polars.Series, rheights: polars.Series, multiple: bool, cfilters: dict, pfilters: dict) -> None:
        super().__init__()

        self.save_selection()

        self.vflags_path = self.write_snapshot(polars.DataFrame({'vflags': vflags})) if vflags is not None else None

        self.rheights_path = self.write_snapshot(polars.DataFrame({'rheights': rheights})) if rheights is not None else None

        self.multiple = multiple
        self.cfilters = cfilters
        self.pfilters = pfilters

    def undo(self) -> None:
        document = globals.history.document

        # Update current filters
        document.current_filters = copy.deepcopy(self.cfilters)
        document.pending_filters = []

        # Update row visibility flags
        if self.vflags_path is not None:
            document.display.row_visibility_flags = polars.read_parquet(self.vflags_path).to_series(0)
            document.display.row_visible_series = document.display.row_visibility_flags.arg_true()
            document.data.bbs[self.range.metadata.dfi].row_span = len(document.display.row_visible_series)
        else:
            document.display.row_visibility_flags = polars.Series(dtype=polars.Boolean)
            document.display.row_visible_series = polars.Series(dtype=polars.UInt32)
            document.data.bbs[self.range.metadata.dfi].row_span = document.data.dfs[self.range.metadata.dfi].height + 1

        # Update row heights
        if self.rheights_path is not None:
            document.display.row_heights = polars.read_parquet(self.rheights_path).to_series(0)
            row_heights_visible_only = document.display.row_heights
            if len(document.display.row_visibility_flags):
                row_heights_visible_only = row_heights_visible_only.filter(document.display.row_visibility_flags)
            document.display.cumulative_row_heights = polars.Series('crheights', row_heights_visible_only).cum_sum()
        else:
            document.display.row_heights = polars.Series(dtype=polars.UInt32)
            document.display.cumulative_row_heights = polars.Series(dtype=polars.UInt32)

        document.emit('filters-changed', self.range.metadata.dfi)

        self.restore_selection()

    def redo(self) -> None:
        document = globals.history.document

        self.restore_selection(False)

        document.current_filters = copy.deepcopy(self.cfilters)
        document.pending_filters = copy.deepcopy(self.pfilters)

        document.filter_current_rows(self.multiple)



class ResetFilterRowState(State):
    __gtype_name__ = 'ResetFilterRowState'

    vflags_path: str
    rheights_path: str

    cfilters: dict

    def __init__(self, vflags: polars.Series, rheights: polars.Series, cfilters: dict) -> None:
        super().__init__()

        self.save_selection()

        self.vflags_path = self.write_snapshot(polars.DataFrame({'vflags': vflags})) if vflags is not None else None

        self.rheights_path = self.write_snapshot(polars.DataFrame({'rheights': rheights})) if rheights is not None else None

        self.cfilters = cfilters

    def undo(self) -> None:
        document = globals.history.document

        # Update current filters
        document.current_filters = copy.deepcopy(self.cfilters)
        document.pending_filters = {}

        # Update row visibility flags
        if self.vflags_path is not None:
            document.display.row_visibility_flags = polars.read_parquet(self.vflags_path).to_series(0)
            document.display.row_visible_series = document.display.row_visibility_flags.arg_true()
            document.data.bbs[self.range.metadata.dfi].row_span = len(document.display.row_visible_series)
        else:
            document.display.row_visibility_flags = polars.Series(dtype=polars.Boolean)
            document.display.row_visible_series = polars.Series(dtype=polars.UInt32)
            document.data.bbs[self.range.metadata.dfi].row_span = document.data.dfs[self.range.metadata.dfi].height + 1

        # Update row heights
        if self.rheights_path is not None:
            document.display.row_heights = polars.read_parquet(self.rheights_path).to_series(0)
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

    def __init__(self, rindex: polars.DataFrame, vflags: polars.Series, dfi: int, descending: bool, multiple: bool, csorts: dict, psorts: dict) -> None:
        super().__init__()

        self.save_selection()

        self.dfi = dfi
        self.descending = descending
        self.multiple = multiple

        self.csorts = csorts
        self.psorts = psorts

        self.rindex_path = self.write_snapshot(polars.DataFrame(rindex))

        self.vflags_path = self.write_snapshot(polars.DataFrame({'vflags': vflags})) if vflags is not None else None

    def undo(self) -> None:
        document = globals.history.document

        document.data.dfs[self.dfi].insert_column(0, polars.read_parquet(self.rindex_path).to_series(0))
        document.data.sort_rows_from_metadata({'$ridx': {'descending': False}}, self.dfi)

        # Update row visibility flags
        if self.vflags_path is not None:
            document.display.row_visibility_flags = polars.read_parquet(self.vflags_path).to_series(0)
            document.display.row_visible_series = document.display.row_visibility_flags.arg_true()

        # Update row heights
        if len(document.display.row_heights):
            sorted_row_heights = polars.DataFrame({'rheights': document.display.row_heights[1:],
                                                   '$ridx': document.data.dfs[self.dfi]['$ridx']}).sort('$ridx').to_series(0)
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



class ConvertColumnDataTypeState(State):
    __gtype_name__ = 'ConvertColumnDataTypeState'

    before: polars.DataType
    after: polars.DataType

    def __init__(self, before: polars.DataType, after: polars.DataType) -> None:
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



class ReplaceAllState(State):
    __gtype_name__ = 'ReplaceAllState'

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

    def __init__(self, content: any, column_names: list[str], row: int, row_span: int, dfi: int,
                 search_pattern: str, replace_with: str, match_case: bool,
                 match_cell: bool, within_selection: bool, use_regexp: bool) -> None:
        super().__init__()

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

        self.save_selection()

    def undo(self) -> None:
        document = globals.history.document
        document.data.update_cell_data_with_chunk_from_metadata(self.column_names, self.row, self.row_span, self.dfi,
                                                                polars.read_parquet(self.file_path))

    def redo(self) -> None:
        document = globals.history.document

        self.restore_selection()

        document.replace_all_in_current_table(self.search_pattern, self.replace_with, self.match_case,
                                              self.match_cell, self.within_selection, self.use_regexp)



class ToggleColumnVisibilityState(State):
    __gtype_name__ = 'ToggleColumnVisibilityState'

    column: int
    show: bool

    def __init__(self, column: int, show: bool) -> None:
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

    def __init__(self, column: int, before: int, after: int) -> None:
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

        # FIXME: this is problematic, because it's too easy to jump to unexpected places
        #        from the user perspective
        scroll_y_position = globals.history.undo_stack[-1].scroll_y
        scroll_x_position = globals.history.undo_stack[-1].scroll_x

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

        self.restore_scroll_position(state.scroll_y, state.scroll_x)

        self.redraw_main_canvas()

        globals.is_changing_state = False

    def restore_scroll_position(self, scroll_y: float, scroll_x: float) -> None:
        # TODO: if the target element is already visible, I don't think we need to scroll

        canvas_height = self.document.view.main_canvas.get_height()
        canvas_width = self.document.view.main_canvas.get_width()

        self.document.view.vertical_scrollbar.get_adjustment().set_upper(scroll_y + canvas_height)
        self.document.view.horizontal_scrollbar.get_adjustment().set_upper(scroll_x + canvas_width)

        self.document.view.vertical_scrollbar.get_adjustment().set_value(scroll_y)
        self.document.view.horizontal_scrollbar.get_adjustment().set_value(scroll_x)

    def redraw_main_canvas(self) -> None:
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