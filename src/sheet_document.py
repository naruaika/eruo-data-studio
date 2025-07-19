# sheet_document.py
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


from gi.repository import Gdk, GObject, Gtk, Pango, PangoCairo
import cairo
import polars

from . import globals

class SheetDocument(GObject.Object):
    __gtype_name__ = 'SheetDocument'

    __gsignals__ = {
        'selection-changed': (GObject.SIGNAL_RUN_FIRST, None, (str, str,)),
    }

    docid = GObject.Property(type=int, default=0)
    title = GObject.Property(type=str, default='Sheet')

    def __init__(self, docid: int, title: str, dataframe: polars.DataFrame = None) -> None:
        super().__init__()

        self.docid = docid
        self.title = title

        from .history_manager import HistoryManager
        self.history = HistoryManager(self)

        from .sheet_data import SheetData
        from .sheet_display import SheetDisplay
        from .sheet_renderer import SheetRenderer
        from .sheet_selection import SheetSelection
        from .sheet_view import SheetView

        self.data = SheetData(self, dataframe)
        self.display = SheetDisplay(self)
        self.renderer = SheetRenderer(self)
        self.selection = SheetSelection(self)
        self.view = SheetView(self)

        self.setup_history_manager()
        self.setup_main_canvas()
        self.setup_scrollbars()

        self.auto_adjust_column_widths()
        self.auto_adjust_scrollbars_by_scroll()

        self.setup_workspace()

    def setup_history_manager(self) -> None:
        globals.history = self.history
        self.history.setup()

    def setup_main_canvas(self) -> None:
        self.view.main_canvas.set_draw_func(self.renderer.render)
        self.view.connect('select-by-keypress', self.on_update_selection_by_keypress)
        self.view.connect('select-by-motion', self.on_update_selection_by_motion)
        self.view.connect('update-cell-data', self.on_update_inline_cell_data)

    def setup_scrollbars(self) -> None:
        vertical_adjustment = Gtk.Adjustment.new(0, 0, 0, self.display.scroll_increment, self.display.page_increment, 0)
        vertical_adjustment.connect('value-changed', self.on_sheet_view_scrolled)
        self.view.vertical_scrollbar.set_adjustment(vertical_adjustment)

        horizontal_adjustment = Gtk.Adjustment.new(0, 0, 0, self.display.scroll_increment, self.display.page_increment, 0)
        horizontal_adjustment.connect('value-changed', self.on_sheet_view_scrolled)
        self.view.horizontal_scrollbar.set_adjustment(horizontal_adjustment)

    def setup_workspace(self) -> None:
        globals.is_changing_state = True
        self.select_element_from_point(self.display.row_header_width + 1, self.display.column_header_height + 1)
        globals.is_changing_state = False

    def on_sheet_view_scrolled(self, source: GObject.Object) -> None:
        self.display.scroll_y_position = self.view.vertical_scrollbar.get_adjustment().get_value()
        self.display.scroll_x_position = self.view.horizontal_scrollbar.get_adjustment().get_value()

        # Transform continuous scroll position to discrete
        self.display.scroll_y_position = round(self.display.scroll_y_position / self.display.DEFAULT_CELL_HEIGHT) * self.display.DEFAULT_CELL_HEIGHT
        self.display.scroll_x_position = round(self.display.scroll_x_position / self.display.DEFAULT_CELL_WIDTH) * self.display.DEFAULT_CELL_WIDTH

        self.auto_adjust_scrollbars_by_scroll()
        self.auto_adjust_locators_size_by_scroll()
        self.auto_adjust_selections_by_scroll()

        self.view.main_canvas.queue_draw()

    def on_update_selection_by_keypress(self, source: GObject.Object, keyval: int, state: Gdk.ModifierType) -> None:
        active_cell_position = (self.selection.current_active_cell.column, self.selection.current_active_cell.row)
        cursor_cell_position = (self.selection.current_cursor_cell.column, self.selection.current_cursor_cell.row)
        target_cell_position = active_cell_position

        df_metadata = self.selection.current_active_cell.metadata
        df_bbox = self.data.read_cell_bbox_from_metadata(df_metadata.dfi)
        df_selected = df_bbox is not None

        match keyval:
            case Gdk.KEY_Tab | Gdk.KEY_ISO_Left_Tab:
                # Select a cell at the left to the selection
                if state == Gdk.ModifierType.SHIFT_MASK:
                    target_cell_position = (max(1, active_cell_position[0] - 1), active_cell_position[1])

                # Select a cell at the right to the selection
                else:
                    target_cell_position = (active_cell_position[0] + 1, active_cell_position[1])

            case Gdk.KEY_Return:
                # Select a cell at the bottom to the selection
                if state == Gdk.ModifierType.SHIFT_MASK:
                    target_cell_position = (active_cell_position[0], max(1, active_cell_position[1] - 1))

                # Select a cell at the top to the selection
                else:
                    target_cell_position = (active_cell_position[0], active_cell_position[1] + 1)

            case Gdk.KEY_Left:
                # Select the leftmost cell in the same row
                if state == Gdk.ModifierType.CONTROL_MASK:
                    if df_selected:
                        target_cell_position = (max(1, df_bbox.column), active_cell_position[1])
                    else:
                        target_cell_position = (1, active_cell_position[1])

                # Include a cell at the left to the selection
                elif state == Gdk.ModifierType.SHIFT_MASK:
                    target_cell_position = (active_cell_position, (max(1, cursor_cell_position[0] - 1), cursor_cell_position[1]))

                # Include all cells to the left to the selection
                elif state == (Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK):
                    if df_selected:
                        target_cell_position = (active_cell_position, (max(1, df_bbox.column), cursor_cell_position[1]))
                    else:
                        target_cell_position = (active_cell_position, (1, cursor_cell_position[1]))

                # Select a cell at the left to the selection
                else:
                    target_cell_position = (max(1, active_cell_position[0] - 1), active_cell_position[1])

            case Gdk.KEY_Right:
                # Select the rightmost cell in the same row
                if state == Gdk.ModifierType.CONTROL_MASK:
                    if df_selected:
                        target_cell_position = (max(1, df_bbox.column + df_bbox.column_span - 1), active_cell_position[1])
                    else:
                        target_cell_position = (active_cell_position[0] + 1, active_cell_position[1])

                # Include a cell at the right to the selection
                elif state == Gdk.ModifierType.SHIFT_MASK:
                    target_cell_position = (active_cell_position, (cursor_cell_position[0] + 1, cursor_cell_position[1]))

                # Include all cells to the right to the selection
                elif state == (Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK):
                    if df_selected:
                        target_cell_position = (active_cell_position, (max(1, df_bbox.column + df_bbox.column_span - 1), cursor_cell_position[1]))
                    else:
                        target_cell_position = (active_cell_position, (cursor_cell_position[0] + 1, cursor_cell_position[1]))

                # Select a cell at the right to the selection
                else:
                    target_cell_position = (active_cell_position[0] + 1, active_cell_position[1])

            case Gdk.KEY_Up:
                # Select the topmost cell in the same column
                if state == Gdk.ModifierType.CONTROL_MASK:
                    if df_selected:
                        target_cell_position = (active_cell_position[0], max(1, df_bbox.row))
                    else:
                        target_cell_position = (active_cell_position[0], 1)

                # Include a cell at the top to the selection
                elif state == Gdk.ModifierType.SHIFT_MASK:
                    target_cell_position = (active_cell_position, (cursor_cell_position[0], max(1, cursor_cell_position[1] - 1)))

                # Include all cells above to the selection
                elif state == (Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK):
                    if df_selected:
                        target_cell_position = (active_cell_position, (cursor_cell_position[0], max(1, df_bbox.row)))
                    else:
                        target_cell_position = (active_cell_position, (cursor_cell_position[0], 1))

                # Select a cell at the top to the selection
                else:
                    target_cell_position = (active_cell_position[0], max(1, active_cell_position[1] - 1))

            case Gdk.KEY_Down:
                # Select the bottommost cell in the same column
                if state == Gdk.ModifierType.CONTROL_MASK:
                    if df_selected:
                        target_cell_position = (active_cell_position[0], max(1, df_bbox.row + df_bbox.row_span - 1))
                    else:
                        target_cell_position = (active_cell_position[0], active_cell_position[1] + 1)

                # Include a cell at the bottom to the selection
                elif state == Gdk.ModifierType.SHIFT_MASK:
                    target_cell_position = (active_cell_position, (cursor_cell_position[0], cursor_cell_position[1] + 1))

                # Include all cells below to the selection
                elif state == (Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK):
                    if df_selected:
                        target_cell_position = (active_cell_position, (cursor_cell_position[0], max(1, df_bbox.row + df_bbox.row_span - 1)))
                    else:
                        target_cell_position = (active_cell_position, (cursor_cell_position[0], cursor_cell_position[1] + 1))

                # Select a cell at the bottom to the selection
                else:
                    target_cell_position = (active_cell_position[0], active_cell_position[1] + 1)

        if all(isinstance(i, int) for i in target_cell_position):
            col_1, row_1 = target_cell_position
            col_2, row_2 = col_1, row_1
        else:
            (col_1, row_1), (col_2, row_2) = target_cell_position

        self.update_selection_from_position(col_1, row_1, col_2, row_2, True, True, True)

        # Reset the current search range
        if self.selection.current_search_range is not None:
            self.selection.current_search_range = self.selection.current_active_range

    def on_update_selection_by_motion(self, source: GObject.Object, x: int, y: int) -> None:
        from .sheet_selection import SheetLocatorCell, SheetTopLocatorCell, SheetLeftLocatorCell

        active_range = self.selection.current_active_range
        range_column = active_range.column
        range_row = active_range.row

        if range_column == 0 and range_row == 0:
            return # no valid reason when the entire sheet is selected

        active_cell = self.selection.current_active_cell
        start_column = active_cell.column
        start_row = active_cell.row

        cursor_cell = self.selection.current_cursor_cell
        cursor_column = cursor_cell.column
        cursor_row = cursor_cell.row

        end_column = self.display.get_column_from_point(x)
        end_row = self.display.get_row_from_point(y)

        # Prevent the user from selecting locator cells undesirably and also from unwanted scroll jumping.
        # We may also want to decrease the sensivity of the autoscroll for this case.
        if isinstance(active_range, SheetLocatorCell):
            if isinstance(active_range, SheetTopLocatorCell):
                start_row = 0
                end_row = 0
                if end_column <= 0:
                    end_column = max(1, cursor_column - 1)
            if isinstance(active_range, SheetLeftLocatorCell):
                start_column = 0
                end_column = 0
                if end_row <= 0:
                    end_row = max(1, cursor_row - 1)
        else:
            if end_column <= 0:
                end_column = max(1, cursor_column - 1)
            if end_row <= 0:
                end_row = max(1, cursor_row - 1)

        # Skip if the cursor is not considered moving
        if end_column == cursor_column and end_row == cursor_row:
            return
        if end_column == cursor_column and end_row == 0 and cursor_row == 1:
            return
        if end_column == 0 and cursor_column == 1 and end_row == cursor_row:
            return

        scroll_axis = 'both'
        if isinstance(active_range, SheetTopLocatorCell):
            scroll_axis = 'horizontal'
        if isinstance(active_range, SheetLeftLocatorCell):
            scroll_axis = 'vertical'

        self.update_selection_from_position(start_column, start_row, end_column, end_row, True, True, True, scroll_axis)

        # Reset the current search range
        if self.selection.current_search_range is not None:
            self.selection.current_search_range = self.selection.current_active_range

    def on_update_inline_cell_data(self, source: GObject.Object, value: any) -> None:
        self.update_current_cells(value)

    def select_element_from_point(self, x: float, y: float) -> None:
        column = self.display.get_column_from_point(x)
        row = self.display.get_row_from_point(y)

        self.update_selection_from_position(column, row, column, row, False, False, False)

        # Reset the current search range
        if self.selection.current_search_range is not None:
            self.selection.current_search_range = self.selection.current_active_range

    def update_selection_from_name(self, name: str) -> None:
        vcol_1, vrow_1, vcol_2, vrow_2 = self.display.get_cell_range_from_name(name)
        col_1 = self.display.get_column_from_vcolumn(vcol_1)
        col_2 = self.display.get_column_from_vcolumn(vcol_2)
        row_1 = self.display.get_row_from_vrow(vrow_1)
        row_2 = self.display.get_row_from_vrow(vrow_2)
        self.update_selection_from_position(col_1, row_1, col_2, row_2, False, False, True)

    def update_selection_from_position(self, col_1: int, row_1: int, col_2: int, row_2: int,
                                       keep_order: bool = False, follow_cursor: bool = True,
                                       auto_scroll: bool = True, scroll_axis: str = 'both',
                                       with_offset: bool = False) -> None:
        # Save snapshot
        if not globals.is_changing_state:
            from .history_manager import SelectionState
            state = SelectionState(col_1, row_1, col_2, row_2, keep_order, follow_cursor, auto_scroll)
            globals.history.save(state)

        # Handle a special case when the user inputs e.g. "A:1" or "1:A"
        # which we want to interpret as selecting the entire sheet
        if col_1 == row_2 == 0 or row_1 == col_2 == 0:
            col_1 = row_1 = col_2 = row_2 = 0

        start_column = min(col_1, col_2)
        start_row = min(row_1, row_2)
        end_column = max(col_1, col_2)
        end_row = max(row_1, row_2)

        x = self.display.get_cell_x_from_column(start_column)
        y = self.display.get_cell_y_from_row(start_row)

        end_x = self.display.get_cell_x_from_column(end_column)
        end_y = self.display.get_cell_y_from_row(end_row)

        end_width = self.display.get_cell_width_from_column(end_column)
        end_height = self.display.get_cell_height_from_row(end_row)

        width = end_x + end_width - x
        height = end_y + end_height - y

        column_span = end_column - start_column + 1
        row_span = end_row - start_row + 1

        rtl = col_2 < col_1
        btt = row_2 < row_1

        canvas_width = self.view.main_canvas.get_width()
        canvas_height = self.view.main_canvas.get_height()

        # I know this is ridiculous, if only we don't have to support the non-destructive
        # row filtering, or hiding some rows to be precise, we only need the very last part
        # of the code below.
        vcol_1 = col_1
        vrow_1 = row_1
        if len(self.display.column_visible_series):
            if col_1 <= len(self.display.column_visible_series):
                vcol_1 = self.display.get_vcolumn_from_column(col_1)
            else:
                vcol_1 = -1 # force to be out of bounds
        if len(self.display.row_visible_series):
            if row_1 <= len(self.display.row_visible_series):
                vrow_1 = self.display.get_vrow_from_row(row_1)
            else:
                vrow_1 = -1 # force to be out of bounds
        if vcol_1 < 0 or vrow_1 < 0:
            from .sheet_data import SheetCellMetadata
            cell_metadata = SheetCellMetadata(-1, -1, -1)
        else:
            cell_metadata = self.data.get_cell_metadata_from_position(vcol_1, vrow_1)

        # Cache the previous active range, usually to prevent from unnecessary re-renders
        self.selection.previous_active_range = self.selection.current_active_range

        from .sheet_selection import SheetLocatorCell, SheetCornerLocatorCell, SheetTopLocatorCell, SheetLeftLocatorCell, SheetContentCell

        # Handle clicking on the top left locator area
        if start_column == 0 and start_row == 0:
            self.selection.current_active_range = SheetCornerLocatorCell(x, y, 0, 0, canvas_width, canvas_height, -1, -1, cell_metadata, rtl, btt)

        # Handle selecting the top locator area
        elif start_column > 0 and start_row == 0:
            self.selection.current_active_range = SheetTopLocatorCell(x, y, start_column, 0, width, canvas_height, column_span, -1, cell_metadata, rtl, btt)

        # Handle selecting the left locator area
        elif start_column == 0 and start_row > 0:
            self.selection.current_active_range = SheetLeftLocatorCell(x, y, 0, start_row, canvas_width, height, -1, row_span, cell_metadata, rtl, btt)

        # Handle selecting a cell content area
        else:
            self.selection.current_active_range = SheetContentCell(x, y, start_column, start_row, width, height, column_span, row_span, cell_metadata, rtl, btt)

        if isinstance(self.selection.current_active_range, SheetLocatorCell):
            col_1 = max(1, col_1)
            row_1 = max(1, row_1)
            col_2 = max(1, col_2)
            row_2 = max(1, row_2)
            start_column = max(1, start_column)
            start_row = max(1, start_row)
            end_column = max(1, end_column)
            end_row = max(1, end_row)

        if not keep_order:
            col_1 = start_column
            row_1 = start_row
            col_2 = end_column
            row_2 = end_row

        x = self.display.get_cell_x_from_column(col_1)
        y = self.display.get_cell_y_from_row(row_1)
        width = self.display.get_cell_width_from_column(col_1)
        height = self.display.get_cell_height_from_row(row_1)
        self.selection.current_active_cell = SheetContentCell(x, y, col_1, row_1, width, height, 1, 1, cell_metadata)

        x = self.display.get_cell_x_from_column(col_2)
        y = self.display.get_cell_y_from_row(row_2)
        width = self.display.get_cell_width_from_column(col_2)
        height = self.display.get_cell_height_from_row(row_2)
        self.selection.current_cursor_cell = SheetContentCell(x, y, col_2, row_2, width, height, 1, 1, cell_metadata)

        if auto_scroll:
            self.auto_adjust_scrollbars_by_selection(follow_cursor, scroll_axis, with_offset)

        if keep_order:
            self.notify_selection_changed(col_1, row_1, cell_metadata)
        else:
            self.notify_selection_changed(start_column, start_row, cell_metadata)

        self.view.main_canvas.queue_draw()

    def insert_from_current_rows(self, dataframe: polars.DataFrame, vflags: polars.Series = None, rheights: polars.Series = None) -> bool:
        range = self.selection.current_active_range
        active = self.selection.current_active_cell

        mrow = range.metadata.row
        row_span = range.row_span

        # Take hidden row(s) into account
        if len(self.display.row_visibility_flags):
            start_vrow = self.display.get_vrow_from_row(range.row)
            end_vrow = self.display.get_vrow_from_row(range.row + row_span - 1)
            row_span = end_vrow - start_vrow + 1

        if range.btt:
            mrow = mrow - row_span + 1

        if self.data.insert_rows_from_dataframe(dataframe, mrow, range.metadata.dfi):
            # Update row visibility flags
            if len(self.display.row_visibility_flags):
                # TODO: should be refactored to a separate function, because of too many repetitions
                if vflags is not None:
                    self.display.row_visibility_flags = polars.concat([self.display.row_visibility_flags[:mrow],
                                                                       vflags,
                                                                       self.display.row_visibility_flags[mrow:]])
                else:
                    self.display.row_visibility_flags = polars.concat([self.display.row_visibility_flags[:mrow],
                                                                       polars.Series([True] * dataframe.height),
                                                                       self.display.row_visibility_flags[mrow:]])
                self.display.row_visible_series = self.display.row_visibility_flags.arg_true()
                self.data.bbs[active.metadata.dfi].row_span = len(self.display.row_visible_series)

            # Update row heights
            if len(self.display.row_heights):
                if rheights is not None:
                    self.display.row_heights = polars.concat([self.display.row_heights[:mrow],
                                                              rheights,
                                                              self.display.row_heights[mrow:]])
                else:
                    self.display.row_heights = polars.concat([self.display.row_heights[:mrow],
                                                              polars.Series([self.display.DEFAULT_CELL_WIDTH] * dataframe.width),
                                                              self.display.row_heights[mrow:]])
                self.display.cumulative_row_heights = polars.Series('crheights', self.display.row_heights).cum_sum()

            self.renderer.render_caches = {}
            self.auto_adjust_selections_by_crud(0, 0, False)

            return True

        return False

    def insert_blank_from_current_rows(self, above: bool = False) -> bool:
        range = self.selection.current_active_range
        active = self.selection.current_active_cell

        mrow = range.metadata.row
        row_span = range.row_span

        # Take hidden row(s) into account
        if len(self.display.row_visibility_flags):
            start_vrow = self.display.get_vrow_from_row(range.row)
            end_vrow = self.display.get_vrow_from_row(range.row + row_span - 1)
            row_span = end_vrow - start_vrow + 1

        if not above:
            mrow = mrow + row_span
        if range.btt:
            mrow = mrow - row_span
        else:
            mrow = mrow - 1

        # Prepare for snapshot
        if not globals.is_changing_state:
            from .history_manager import InsertBlankRowState
            state = InsertBlankRowState(row_span, above)

        if self.data.insert_rows_from_metadata(mrow, row_span, range.metadata.dfi):
            # Save snapshot
            if not globals.is_changing_state:
                globals.history.save(state)

            # Update row visibility flags
            if len(self.display.row_visibility_flags):
                if above:
                    mrow = mrow + 1
                self.display.row_visibility_flags = polars.concat([self.display.row_visibility_flags[:mrow],
                                                                   polars.Series([True] * row_span),
                                                                   self.display.row_visibility_flags[mrow:]])
                self.display.row_visible_series = self.display.row_visibility_flags.arg_true()
                self.data.bbs[active.metadata.dfi].row_span = len(self.display.row_visible_series)

            # Update row heights
            if len(self.display.row_heights):
                self.display.row_heights = polars.concat([self.display.row_heights[:mrow],
                                                          polars.Series([self.display.DEFAULT_CELL_WIDTH] * row_span),
                                                          self.display.row_heights[mrow:]])
                self.display.cumulative_row_heights = polars.Series('crheights', self.display.row_heights).cum_sum()

            self.renderer.render_caches = {}
            self.auto_adjust_selections_by_crud(0, 0 if not above else row_span, False)

            return True

        return False

    def insert_from_current_columns(self, dataframe: polars.DataFrame, vflags: polars.Series = None, cwidths: polars.Series = None) -> bool:
        range = self.selection.current_active_range
        active = self.selection.current_active_cell

        mcolumn = range.metadata.column
        column_span = range.column_span

        # Take hidden column(s) into account
        if len(self.display.column_visibility_flags):
            start_vcolumn = self.display.get_vcolumn_from_column(range.column)
            end_vcolumn = self.display.get_vcolumn_from_column(range.column + column_span - 1)
            column_span = end_vcolumn - start_vcolumn + 1

        if range.rtl:
            mcolumn = mcolumn - column_span + 1

        if self.data.insert_columns_from_dataframe(dataframe, mcolumn, range.metadata.dfi):
            # Update column visibility flags
            if len(self.display.column_visibility_flags):
                if vflags is not None:
                    self.display.column_visibility_flags = polars.concat([self.display.column_visibility_flags[:mcolumn],
                                                                          vflags,
                                                                          self.display.column_visibility_flags[mcolumn:]])
                else:
                    self.display.column_visibility_flags = polars.concat([self.display.column_visibility_flags[:mcolumn],
                                                                          polars.Series([True] * dataframe.height),
                                                                          self.display.column_visibility_flags[mcolumn:]])
                self.display.column_visible_series = self.display.column_visibility_flags.arg_true()
                self.data.bbs[active.metadata.dfi].column_span = len(self.display.column_visible_series)

            # Update column widths
            if len(self.display.column_widths):
                if cwidths is not None:
                    self.display.column_widths = polars.concat([self.display.column_widths[:mcolumn],
                                                                cwidths,
                                                                self.display.column_widths[mcolumn:]])
                else:
                    self.display.column_widths = polars.concat([self.display.column_widths[:mcolumn],
                                                                polars.Series([self.display.DEFAULT_CELL_WIDTH] * dataframe.width),
                                                                self.display.column_widths[mcolumn:]])
                self.display.cumulative_column_widths = polars.Series('ccwidths', self.display.column_widths).cum_sum()

            self.renderer.render_caches = {}
            self.auto_adjust_selections_by_crud(0, 0, False)

            return True

        return False

    def insert_blank_from_current_columns(self, left: bool = False) -> bool:
        range = self.selection.current_active_range
        active = self.selection.current_active_cell

        mcolumn = range.metadata.column
        column_span = range.column_span

        # Take hidden row(s) into account
        if len(self.display.column_visibility_flags):
            start_vcolumn = self.display.get_vcolumn_from_column(range.column)
            end_vcolumn = self.display.get_vcolumn_from_column(range.column + column_span - 1)
            column_span = end_vcolumn - start_vcolumn + 1

        if not left:
            mcolumn = mcolumn + column_span
        else:
            mcolumn = mcolumn - column_span + 1
        if range.rtl:
            mcolumn = mcolumn - column_span + 1

        # Prepare for snapshot
        if not globals.is_changing_state:
            from .history_manager import InsertBlankColumnState
            state = InsertBlankColumnState(column_span, left)

        if self.data.insert_columns_from_metadata(mcolumn, column_span, range.metadata.dfi, left):
            # Save snapshot
            if not globals.is_changing_state:
                globals.history.save(state)

            # Update column visibility flags
            if len(self.display.column_visibility_flags):
                self.display.column_visibility_flags = polars.concat([self.display.column_visibility_flags[:mcolumn],
                                                                      polars.Series([True] * column_span),
                                                                      self.display.column_visibility_flags[mcolumn:]])
                self.display.column_visible_series = self.display.column_visibility_flags.arg_true()
                self.data.bbs[active.metadata.dfi].column_span = len(self.display.column_visible_series)

            # Update column widths
            if len(self.display.column_widths):
                self.display.column_widths = polars.concat([self.display.column_widths[:mcolumn],
                                                            polars.Series([self.display.DEFAULT_CELL_WIDTH] * column_span),
                                                            self.display.column_widths[mcolumn:]])
                self.display.cumulative_column_widths = polars.Series('ccwidths', self.display.column_widths).cum_sum()

            self.renderer.render_caches = {}
            self.auto_adjust_selections_by_crud(0 if not left else column_span, 0, False)

            return True

        return False

    # TODO: currently update, duplicate, delete, hide, and unhide functions don't support multiple dataframes.
    #       Should we add the support? I still don't wrap my head around it.

    def update_current_cells(self, value: any) -> bool:
        range = self.selection.current_active_range

        mcolumn = range.metadata.column
        mrow = range.metadata.row
        column_span = range.column_span
        row_span = range.row_span

        # Take hidden column(s) into account
        if len(self.display.column_visibility_flags):
            start_vcolumn = self.display.get_vcolumn_from_column(range.column)
            end_vcolumn = self.display.get_vcolumn_from_column(range.column + column_span - 1)
            column_span = end_vcolumn - start_vcolumn + 1

        # Take hidden row(s) into account
        if len(self.display.row_visibility_flags):
            start_vrow = self.display.get_vrow_from_row(range.row)
            end_vrow = self.display.get_vrow_from_row(range.row + row_span - 1)
            row_span = end_vrow - start_vrow + 1

        if range.rtl:
            mcolumn = mcolumn - range.column_span + 1

        if range.btt:
            mrow = mrow - row_span + 1

        if column_span < 0:
            column_span = self.data.bbs[range.metadata.dfi].column_span

        if row_span < 0:
            row_span = self.data.bbs[range.metadata.dfi].row_span - 1

        # Prepare for snapshot
        if not globals.is_changing_state:
            from .history_manager import UpdateDataState

            if range.metadata.row == 0: # includes header row
                state = UpdateDataState(self.data.read_cell_data_from_metadata(mcolumn, mrow, column_span, 1, range.metadata.dfi),
                                        self.data.read_cell_data_from_metadata(mcolumn, mrow + 1, column_span, row_span - 1, range.metadata.dfi),
                                        value)
            else: # excludes header row
                state = UpdateDataState(None,
                                        self.data.read_cell_data_from_metadata(mcolumn, mrow, column_span, row_span, range.metadata.dfi),
                                        value)

        # Update data
        if self.data.update_cell_data_from_metadata(mcolumn, mrow, column_span, row_span, range.metadata.dfi, value):
            # Save snapshot
            if not globals.is_changing_state:
                globals.history.save(state)

            self.renderer.render_caches = {}
            self.view.main_canvas.queue_draw()

            active_cell = self.selection.current_active_cell
            self.notify_selection_changed(active_cell.column, active_cell.row, active_cell.metadata)

            return True

        return False

    def duplicate_from_current_rows(self, above: bool = False) -> bool:
        range = self.selection.current_active_range
        active = self.selection.current_active_cell

        mrow = range.metadata.row
        row_span = range.row_span

        # Take hidden row(s) into account
        if len(self.display.row_visibility_flags):
            start_vrow = self.display.get_vrow_from_row(range.row)
            end_vrow = self.display.get_vrow_from_row(range.row + row_span - 1)
            row_span = end_vrow - start_vrow + 1

        if range.btt:
            mrow = mrow - row_span + 1

        # Prepare for snapshot
        if not globals.is_changing_state:
            from .history_manager import DuplicateRowState
            state = DuplicateRowState(row_span, above)

        if self.data.duplicate_rows_from_metadata(mrow, row_span, range.metadata.dfi):
            # Save snapshot
            if not globals.is_changing_state:
                globals.history.save(state)

            # Update row visibility flags
            if len(self.display.row_visibility_flags):
                if not above:
                    mrow = mrow + row_span
                self.display.row_visibility_flags = polars.concat([self.display.row_visibility_flags[:mrow],
                                                                   polars.Series([True] * row_span),
                                                                   self.display.row_visibility_flags[mrow:]])
                self.display.row_visible_series = self.display.row_visibility_flags.arg_true()
                self.data.bbs[active.metadata.dfi].row_span = len(self.display.row_visible_series)

            # Update row heights
            if len(self.display.row_heights):
                self.display.row_heights = polars.concat([self.display.row_heights[:mrow],
                                                          self.display.row_heights[mrow:mrow + row_span],
                                                          self.display.row_heights[mrow:]])
                self.display.cumulative_row_heights = polars.Series('crheights', self.display.row_heights).cum_sum()

            self.renderer.render_caches = {}
            self.auto_adjust_selections_by_crud(0, 0 if not above else row_span, False)

            return True

        return False

    def duplicate_from_current_columns(self, left: bool = False) -> bool:
        range = self.selection.current_active_range
        active = self.selection.current_active_cell

        mcolumn = range.metadata.column
        column_span = range.column_span

        # Take hidden column(s) into account
        if len(self.display.column_visibility_flags):
            start_vcolumn = self.display.get_vcolumn_from_column(range.column)
            end_vcolumn = self.display.get_vcolumn_from_column(range.column + column_span - 1)
            column_span = end_vcolumn - start_vcolumn + 1

        if range.rtl:
            mcolumn = mcolumn - column_span + 1

        # Prepare for snapshot
        if not globals.is_changing_state:
            from .history_manager import DuplicateColumnState
            state = DuplicateColumnState(column_span, left)

        if self.data.duplicate_columns_from_metadata(mcolumn, column_span, range.metadata.dfi, left):
            # Save snapshot
            if not globals.is_changing_state:
                globals.history.save(state)

            # Update column visibility flags
            if len(self.display.column_visibility_flags):
                if not left:
                    mcolumn = mcolumn + column_span
                self.display.column_visibility_flags = polars.concat([self.display.column_visibility_flags[:mcolumn],
                                                                      polars.Series([True] * column_span),
                                                                      self.display.column_visibility_flags[mcolumn:]])
                self.display.column_visible_series = self.display.column_visibility_flags.arg_true()
                self.data.bbs[active.metadata.dfi].column_span = len(self.display.column_visible_series)

            # Update column widths
            if len(self.display.column_widths):
                self.display.column_widths = polars.concat([self.display.column_widths[:mcolumn],
                                                            self.display.column_widths[mcolumn:mcolumn + column_span],
                                                            self.display.column_widths[mcolumn:]])
                self.display.cumulative_column_widths = polars.Series('ccwidths', self.display.column_widths).cum_sum()

            self.renderer.render_caches = {}
            self.auto_adjust_selections_by_crud(0 if not left else column_span, 0, False)

            return True

        return False

    def delete_current_rows(self) -> bool:
        range = self.selection.current_active_range
        active = self.selection.current_active_cell

        mrow = range.metadata.row
        row_span = range.row_span

        # Take hidden row(s) into account
        if len(self.display.row_visibility_flags):
            start_vrow = self.display.get_vrow_from_row(range.row)
            end_vrow = self.display.get_vrow_from_row(range.row + row_span - 1)
            row_span = end_vrow - start_vrow + 1

        if range.btt:
            mrow = mrow - row_span + 1

        # Prepare for snapshot
        if not globals.is_changing_state:
            from .history_manager import DeleteRowState
            column_count = self.data.bbs[range.metadata.dfi].column_span
            state = DeleteRowState(self.data.read_cell_data_from_metadata(0, mrow, column_count, row_span, range.metadata.dfi),
                                   self.display.row_visibility_flags[mrow:mrow + row_span] if len(self.display.row_visibility_flags) else None,
                                   self.display.row_heights[mrow:mrow + row_span] if len(self.display.row_heights) else None)

        if self.data.delete_rows_from_metadata(mrow, row_span, range.metadata.dfi):
            # Save snapshot
            if not globals.is_changing_state:
                globals.history.save(state)

            # Update row visibility flags
            if len(self.display.row_visibility_flags):
                self.display.row_visibility_flags = polars.concat([self.display.row_visibility_flags[:mrow],
                                                                   self.display.row_visibility_flags[mrow + row_span:]])
                self.display.row_visible_series = self.display.row_visibility_flags.arg_true()
                self.data.bbs[active.metadata.dfi].row_span = len(self.display.row_visible_series)

            # Update row heights
            if len(self.display.row_heights):
                self.display.row_heights = polars.concat([self.display.row_heights[:mrow],
                                                          self.display.row_heights[mrow + row_span:]])
                self.display.cumulative_row_heights = polars.Series('crheights', self.display.row_heights).cum_sum()

            self.renderer.render_caches = {}
            self.auto_adjust_selections_by_crud(0, 0, True)

            return True

        return False

    def delete_current_columns(self) -> bool:
        range = self.selection.current_active_range
        active = self.selection.current_active_cell

        mcolumn = range.metadata.column
        column_span = range.column_span

        # Take hidden column(s) into account
        if len(self.display.column_visibility_flags):
            start_vcolumn = self.display.get_vcolumn_from_column(range.column)
            end_vcolumn = self.display.get_vcolumn_from_column(range.column + column_span - 1)
            column_span = end_vcolumn - start_vcolumn + 1

        if range.rtl:
            mcolumn = mcolumn - column_span + 1

        # Prepare for snapshot
        if not globals.is_changing_state:
            from .history_manager import DeleteColumnState
            row_count = self.data.bbs[range.metadata.dfi].row_span - 1
            state = DeleteColumnState(self.data.read_cell_data_from_metadata(mcolumn, 1, column_span, row_count, range.metadata.dfi),
                                      self.display.column_visibility_flags[mcolumn:mcolumn + column_span] if len(self.display.column_visibility_flags) else None,
                                      self.display.column_widths[mcolumn:mcolumn + column_span] if len(self.display.column_widths) else None)

        if self.data.delete_columns_from_metadata(mcolumn, column_span, range.metadata.dfi):
            # Save snapshot
            if not globals.is_changing_state:
                globals.history.save(state)

            # Update column visibility flags
            if len(self.display.column_visibility_flags):
                self.display.column_visibility_flags = polars.concat([self.display.column_visibility_flags[:mcolumn],
                                                                      self.display.column_visibility_flags[mcolumn + column_span:]])
                self.display.column_visible_series = self.display.column_visibility_flags.arg_true()
                self.data.bbs[active.metadata.dfi].column_span = len(self.display.column_visible_series)

            # Update column widths
            if len(self.display.column_widths):
                self.display.column_widths = polars.concat([self.display.column_widths[:mcolumn],
                                                            self.display.column_widths[mcolumn + column_span:]])
                self.display.cumulative_column_widths = polars.Series('ccwidths', self.display.column_widths).cum_sum()

            self.renderer.render_caches = {}
            self.auto_adjust_selections_by_crud(0, 0, True)

            return True

        return False

    def hide_current_rows(self) -> None:
        range = self.selection.current_active_range

        mrow = range.metadata.row
        row_span = range.row_span

        # Take hidden row(s) into account
        if len(self.display.row_visibility_flags):
            start_vrow = self.display.get_vrow_from_row(range.row)
            end_vrow = self.display.get_vrow_from_row(range.row + row_span - 1)
            row_span = end_vrow - start_vrow + 1

        if range.btt:
            mrow = mrow - row_span + 1

        # Prepare for snapshot
        if not globals.is_changing_state:
            from .history_manager import HideRowState
            state = HideRowState(self.display.row_heights[range.row - 1:range.row - 1 + range.row_span] if len(self.display.row_heights) else None)

        # Update row visibility flags
        if len(self.display.row_visibility_flags):
            self.display.row_visibility_flags = polars.concat([self.display.row_visibility_flags[:mrow],
                                                               polars.Series([False] * row_span),
                                                               self.display.row_visibility_flags[mrow + row_span:]])
        else:
            # It's better if we don't have to include the third part, but it didn't work.
            # Maybe we need to change the code somewhere?
            self.display.row_visibility_flags = polars.concat([polars.Series([True] * mrow),
                                                               polars.Series([False] * row_span),
                                                               polars.Series([True] * (self.data.bbs[range.metadata.dfi].row_span - mrow - row_span))])
        self.display.row_visible_series = self.display.row_visibility_flags.arg_true()
        self.data.bbs[range.metadata.dfi].row_span = len(self.display.row_visible_series)

        # Update row heights
        if len(self.display.row_heights):
            self.display.row_heights = polars.concat([self.display.row_heights[:range.row - 1],
                                                      self.display.row_heights[range.row - 1 + row_span:]])
            self.display.cumulative_row_heights = polars.Series('crheights', self.display.row_heights).cum_sum()

        # Save snapshot
        if not globals.is_changing_state:
            globals.history.save(state)

        self.renderer.render_caches = {}
        self.auto_adjust_selections_by_crud(0, 0, True)

    def hide_current_columns(self) -> None:
        range = self.selection.current_active_range

        mcolumn = range.metadata.column
        column_span = range.column_span

        # Take hidden column(s) into account
        if len(self.display.column_visibility_flags):
            start_vcolumn = self.display.get_vcolumn_from_column(range.column)
            end_vcolumn = self.display.get_vcolumn_from_column(range.column + column_span - 1)
            column_span = end_vcolumn - start_vcolumn + 1

        if range.rtl:
            mcolumn = mcolumn - column_span + 1

        # Prepare for snapshot
        if not globals.is_changing_state:
            from .history_manager import HideColumnState
            state = HideColumnState(self.display.column_widths[range.column - 1:range.column - 1 + range.column_span] if len(self.display.column_widths) else None)

        # Update column visibility flags
        if len(self.display.column_visibility_flags):
            self.display.column_visibility_flags = polars.concat([self.display.column_visibility_flags[:mcolumn],
                                                                  polars.Series([False] * column_span),
                                                                  self.display.column_visibility_flags[mcolumn + column_span:]])
        else:
            self.display.column_visibility_flags = polars.concat([polars.Series([True] * mcolumn),
                                                                  polars.Series([False] * column_span),
                                                                  polars.Series([True] * (self.data.bbs[range.metadata.dfi].column_span - mcolumn - column_span))])
        self.display.column_visible_series = self.display.column_visibility_flags.arg_true()
        self.data.bbs[range.metadata.dfi].column_span = len(self.display.column_visible_series)

        # Update column widths
        if len(self.display.column_widths):
            self.display.column_widths = polars.concat([self.display.column_widths[:range.column - 1],
                                                        self.display.column_widths[range.column - 1 + range.column_span:]])
            self.display.cumulative_column_widths = polars.Series('ccwidths', self.display.column_widths).cum_sum()

        # Save snapshot
        if not globals.is_changing_state:
            globals.history.save(state)

        self.renderer.render_caches = {}
        self.auto_adjust_selections_by_crud(0, 0, True)

    def unhide_current_rows(self, rheights: polars.Series = None) -> None:
        range = self.selection.current_active_range

        mrow = range.metadata.row
        row_span = range.row_span

        # Take hidden row(s) into account
        if len(self.display.row_visibility_flags):
            start_vrow = self.display.get_vrow_from_row(range.row)
            end_vrow = self.display.get_vrow_from_row(range.row + row_span - 1)
            row_span = end_vrow - start_vrow + 1

        if range.btt:
            mrow = mrow - row_span + 1

        # Save snapshot
        if not globals.is_changing_state:
            from .history_manager import UnhideRowState
            state = UnhideRowState(row_span,
                                   self.display.row_visibility_flags[mrow:mrow + row_span],
                                   self.display.row_heights[mrow:mrow + row_span] if len(self.display.row_heights) else None)
            globals.history.save(state)

        # Update row visibility flags
        self.display.row_visibility_flags = polars.concat([self.display.row_visibility_flags[:mrow],
                                                           polars.Series([True] * row_span),
                                                           self.display.row_visibility_flags[mrow + row_span:]])
        self.display.row_visible_series = self.display.row_visibility_flags.arg_true()
        self.data.bbs[range.metadata.dfi].row_span = len(self.display.row_visible_series)

        # Update row heights
        if len(self.display.row_heights):
            if rheights is not None:
                self.display.row_heights = polars.concat([self.display.row_heights[:mrow],
                                                          rheights,
                                                          self.display.row_heights[mrow:]])
            else:
                # FIXME: how to recover the row heights?
                self.display.row_heights = polars.concat([self.display.row_heights[:range.row - 1],
                                                          polars.Series([self.display.DEFAULT_CELL_WIDTH] * row_span),
                                                          self.display.row_heights[range.row - 1 + row_span:]])
            self.display.cumulative_row_heights = polars.Series('crheights', self.display.row_heights).cum_sum()

        self.renderer.render_caches = {}
        self.auto_adjust_selections_by_crud(0, 0, False)

    def unhide_all_rows(self) -> None:
        # Save snapshot
        if not globals.is_changing_state:
            from .history_manager import UnhideAllRowState
            state = UnhideAllRowState(self.display.row_visibility_flags)
            globals.history.save(state)

        # TODO: support multiple dataframes?
        self.display.row_visibility_flags = polars.Series(dtype=polars.Boolean)
        self.display.row_visible_series = polars.Series(dtype=polars.UInt32)
        self.data.bbs[0].row_span = self.data.dfs[0].height + 1

        # Update row heights
        if len(self.display.row_heights):
            # FIXME: how to recover the row heights?
            pass

        self.renderer.render_caches = {}
        self.auto_adjust_selections_by_crud(0, 0, False)

    def unhide_current_columns(self, cwidths: polars.Series = None) -> None:
        range = self.selection.current_active_range

        mcolumn = range.metadata.column
        column_span = range.column_span

        # Take hidden column(s) into account
        if len(self.display.column_visibility_flags):
            start_vcolumn = self.display.get_vcolumn_from_column(range.column)
            end_vcolumn = self.display.get_vcolumn_from_column(range.column + column_span - 1)
            column_span = end_vcolumn - start_vcolumn + 1

        if range.rtl:
            mcolumn = mcolumn - column_span + 1

        # Save snapshot
        if not globals.is_changing_state:
            from .history_manager import UnhideColumnState
            state = UnhideColumnState(column_span,
                                      self.display.column_visibility_flags[mcolumn:mcolumn + column_span],
                                      self.display.column_widths[mcolumn:mcolumn + column_span] if len(self.display.column_widths) else None)
            globals.history.save(state)

        # Update column visibility flags
        self.display.column_visibility_flags = polars.concat([self.display.column_visibility_flags[:mcolumn],
                                                              polars.Series([True] * column_span),
                                                              self.display.column_visibility_flags[mcolumn + column_span:]])
        self.display.column_visible_series = self.display.column_visibility_flags.arg_true()
        self.data.bbs[range.metadata.dfi].column_span = len(self.display.column_visible_series)

        # Update column widths
        if len(self.display.column_widths):
            if cwidths is not None:
                self.display.column_widths = polars.concat([self.display.column_widths[:mcolumn],
                                                            cwidths,
                                                            self.display.column_widths[mcolumn:]])
            else:
                # FIXME: how to recover the column widths?
                self.display.column_widths = polars.concat([self.display.column_widths[:range.column - 1],
                                                            polars.Series([self.display.DEFAULT_CELL_WIDTH] * column_span),
                                                            self.display.column_widths[range.column - 1:]])
            self.display.cumulative_column_widths = polars.Series('ccwidths', self.display.column_widths).cum_sum()

        self.renderer.render_caches = {}
        self.auto_adjust_selections_by_crud(0, 0, False)

    def unhide_all_columns(self) -> None:
        # Save snapshot
        if not globals.is_changing_state:
            from .history_manager import UnhideAllColumnState
            state = UnhideAllColumnState(self.display.column_visibility_flags)
            globals.history.save(state)

        # TODO: support multiple dataframes?
        self.display.column_visibility_flags = polars.Series(dtype=polars.Boolean)
        self.display.column_visible_series = polars.Series(dtype=polars.UInt32)
        self.data.bbs[0].column_span = self.data.dfs[0].width

        # Update column widths
        if len(self.display.column_widths):
            # FIXME: how to recover the column widths?
            self.auto_adjust_column_widths()

        self.renderer.render_caches = {}
        self.auto_adjust_selections_by_crud(0, 0, False)

    def filter_current_rows(self) -> None:
        active = self.selection.current_active_cell

        # Prepare for snapshot
        if not globals.is_changing_state and 0 <= active.metadata.dfi < len(self.data.dfs):
            pexpression = self.data.fes[active.metadata.dfi]

        # Update row visibility flags
        self.display.row_visibility_flags = self.data.filter_rows_from_metadata(active.metadata.column, active.metadata.row, active.metadata.dfi)
        self.display.row_visible_series = self.display.row_visibility_flags.arg_true()
        self.data.bbs[active.metadata.dfi].row_span = len(self.display.row_visible_series)

        # TODO: update row heights
        if len(self.display.row_heights):
            pass

        if len(self.display.row_visibility_flags) == 0:
            return # shouldn't happen, but for completeness

        # Save snapshot
        if not globals.is_changing_state:
            from .history_manager import FilterRowState
            globals.history.save(FilterRowState(active.metadata.dfi, pexpression))

        self.renderer.render_caches = {}
        self.auto_adjust_selections_by_crud(0, 0, True)

    def sort_current_rows(self, descending: bool = False, vflags: polars.Series = None) -> bool:
        active = self.selection.current_active_cell

        # Take hidden row(s) into account
        # This approach will also sort hidden rows which is different from other applications,
        # I haven't made up my mind yet if we should follow other applications behavior.
        if len(self.display.row_visibility_flags) and 0 <= active.metadata.dfi < len(self.data.dfs):
            self.data.dfs[active.metadata.dfi] = self.data.dfs[active.metadata.dfi].with_columns(self.display.row_visibility_flags[1:].alias('$vrow'))

        # Prepare for snapshot
        if not globals.is_changing_state and 0 <= active.metadata.dfi < len(self.data.dfs):
            self.data.dfs[active.metadata.dfi] = self.data.dfs[active.metadata.dfi].with_row_index('$ridx')
            active.metadata.column += 1

        # Sorting is expensive; we can see double in memory usage. Anything we can do?
        if self.data.sort_rows_from_metadata(active.metadata.column, active.metadata.dfi, descending):
            # Save snapshot
            if not globals.is_changing_state:
                from .history_manager import SortRowState
                globals.history.save(SortRowState(descending, active.metadata.dfi,
                                                  self.data.dfs[active.metadata.dfi]['$ridx'],
                                                  self.display.row_visibility_flags if len(self.display.row_visibility_flags) else None))
                self.data.dfs[active.metadata.dfi].drop_in_place('$ridx')
                active.metadata.column -= 1

            # Update row visibility flags
            if len(self.display.row_visibility_flags):
                if vflags is not None:
                    self.display.row_visibility_flags = polars.concat([polars.Series([True]), vflags])
                else:
                    self.display.row_visibility_flags = polars.concat([polars.Series([True]), self.data.dfs[active.metadata.dfi]['$vrow']])
                self.data.dfs[active.metadata.dfi].drop_in_place('$vrow')
                self.display.row_visible_series = self.display.row_visibility_flags.arg_true()

            # TODO: update row heights

            self.renderer.render_caches = {}
            self.view.main_canvas.queue_draw()

            return True

        return False

    def convert_current_columns_dtype(self, dtype: polars.DataType) -> bool:
        range = self.selection.current_active_range

        # Prepare for snapshot
        if not globals.is_changing_state:
            from .history_manager import ConvertDataState
            ndtype = self.data.read_column_dtype_from_metadata(range.metadata.column, range.metadata.dfi)
            state = ConvertDataState(ndtype, dtype)

        if self.data.convert_columns_dtype_from_metadata(range.metadata.column, range.column_span, range.metadata.dfi, dtype):
            self.renderer.render_caches = {}
            self.view.main_canvas.queue_draw()

            # Save snapshot
            if not globals.is_changing_state:
                globals.history.save(state)

            return True

        return False

    def find_in_current_table(self, text_value: str, match_case: bool, match_cell: bool, within_selection: bool, use_regexp: bool) -> int:
        if text_value in ['', None]:
            return polars.DataFrame(), 0

        # Prepare the search expression
        filter_expression = polars.all().str.contains_any([text_value], ascii_case_insensitive=not match_case)
        if match_cell:
            filter_expression = polars.all().str.to_lowercase() == text_value.lower()
            if match_case:
                filter_expression = polars.all().str == text_value
        if use_regexp:
            filter_expression = polars.col(polars.String).str.contains(f'(?i){text_value}')
            if match_case:
                filter_expression = polars.col(polars.String).str.contains(text_value)

        # Collect hidden column names
        hidden_column_names = []
        for col_index, is_visible in enumerate(self.display.column_visibility_flags):
            if not is_visible:
                hidden_column_names.append(self.data.dfs[0].columns[col_index])

        select_expression = polars.col(polars.String).exclude(hidden_column_names)

        # Collect column names within the selection
        if within_selection:
            range = self.selection.current_search_range
            column_span = range.column_span

            # Take hidden column(s) into account
            if len(self.display.column_visibility_flags):
                start_vcolumn = self.display.get_vcolumn_from_column(range.column)
                end_vcolumn = self.display.get_vcolumn_from_column(range.column + column_span - 1)
                column_span = end_vcolumn - start_vcolumn + 1

            selected_column_names = self.data.dfs[0].columns[range.metadata.column:range.metadata.column + column_span]

            # Remove non-string column names
            selected_column_names = [name for name in selected_column_names if self.data.dfs[0][name].dtype == polars.String]

            # Reset the select expression
            select_expression = polars.col(selected_column_names).exclude(hidden_column_names)

        has_selected_rows = False

        # Define row range within the selection
        if within_selection:
            range = self.selection.current_search_range

            start_row = range.metadata.row - 1
            row_span = range.row_span

            # Handle edge cases where the user selected the entire column(s),
            # so there's no point to filter by row.
            has_selected_rows = row_span > 0

            # Take hidden row(s) into account
            if has_selected_rows and len(self.display.row_visibility_flags):
                start_vrow = self.display.get_vrow_from_row(range.row)
                end_vrow = self.display.get_vrow_from_row(range.row + row_span - 1)
                row_span = end_vrow - start_vrow + 1

        # Get search results mask
        # TODO: support multiple dataframes?
        search_results = self.data.dfs[0].select(select_expression) \
                                         .with_columns(filter_expression) \
                                         .with_columns(polars.any_horizontal(polars.all()).alias('$rand')) \
                                         .with_row_index('$ridx') \
                                         .filter((polars.col('$ridx') >= start_row) & (polars.col('$ridx') < start_row + row_span)
                                                 if has_selected_rows else polars.lit(True)) \
                                         .filter(polars.col('$ridx').is_in(self.display.row_visible_series[1:] - 1)
                                                 if len(self.display.row_visible_series) else polars.lit(True)) \
                                         .filter(polars.col('$rand') == True) \
                                         .drop('$rand') \
                                         .fill_null(False)

        # Drop column(s) without data
        columns_to_drop = []
        for column_name in search_results.columns:
            if column_name == '$ridx':
                continue
            if search_results[column_name].sum() == 0:
                columns_to_drop.append(column_name)
        search_results = search_results.drop(columns_to_drop)

        # Skip if no search results
        if search_results.height == 0:
            return polars.DataFrame(), 0

        # Count the number of search result items
        search_results_length = search_results.select(polars.all().exclude('$ridx')) \
                                              .sum().sum_horizontal().item()

        return search_results, search_results_length

    def check_selection_changed(self) -> bool:
        current_cell_clss = self.selection.current_active_range.__class__
        current_cell_attr = self.selection.current_active_range.__dict__.copy()
        current_cell_data = current_cell_attr.pop('metadata').__dict__

        previous_cell_clss = self.selection.previous_active_range.__class__
        previous_cell_attr = self.selection.previous_active_range.__dict__.copy()
        previous_cell_data = previous_cell_attr.pop('metadata').__dict__

        return not (current_cell_clss == previous_cell_clss and
                    current_cell_attr == previous_cell_attr and
                    current_cell_data == previous_cell_data)

    def check_selection_contains_point(self, x: int, y: int) -> bool:
        range = self.selection.current_active_range
        return range.x <= x <= range.x + range.width and \
               range.y <= y <= range.y + range.height

    def notify_selection_changed(self, column: int, row: int, metadata) -> None:
        # Handle edge cases where the last column(s) are hidden
        if column - 1 == len(self.display.column_visible_series) and \
                column < len(self.display.column_visibility_flags) and \
                not self.display.column_visibility_flags[column]:
            column += (len(self.display.column_visibility_flags) - 1) - (self.display.column_visible_series[-1] - 1) - 1

        # Handle edge cases where the last row(s) are hidden
        if row - 1 == len(self.display.row_visible_series) and \
                row < len(self.display.row_visibility_flags) and \
                not self.display.row_visibility_flags[row]:
            row += (len(self.display.row_visibility_flags) - 1) - (self.display.row_visible_series[-1] - 1) - 1

        # Cache the selected cell data usually for resetting the input bar
        vcolumn = self.display.get_vcolumn_from_column(column)
        vrow = self.display.get_vrow_from_row(row)
        self.selection.cell_name = self.display.get_cell_name_from_position(vcolumn, vrow)
        self.selection.cell_data = self.data.read_cell_data_from_metadata(metadata.column, metadata.row, 1, 1, metadata.dfi)

        # Request to update the input bar with the selected cell data
        cell_data = self.selection.cell_data
        if cell_data is None:
            cell_data = ''
        cell_data = str(cell_data)
        self.emit('selection-changed', self.selection.cell_name, cell_data)

    def auto_adjust_column_widths(self) -> None:
        if len(self.data.dfs) == 0:
            return

        globals.is_changing_state = True

        # TODO: support multiple dataframes?
        monitor = Gdk.Display.get_default().get_monitors()[0]
        max_width = monitor.get_geometry().width // 12
        sample_data = self.data.dfs[0].head(50).vstack(self.data.dfs[0].tail(50))

        font_desc = Gtk.Widget.create_pango_context(self.view.main_canvas).get_font_description()
        system_font = font_desc.get_family() if font_desc else 'Sans'
        font_desc = Pango.font_description_from_string(f'{system_font} Normal Regular {self.display.FONT_SIZE}px')
        context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 0, 0))
        layout = PangoCairo.create_layout(context)
        layout.set_font_description(font_desc)

        self.display.column_widths = polars.Series([0] * self.data.dfs[0].width)
        for col_index, col_name in enumerate(self.data.dfs[0].columns):
            sample_data = sample_data.with_columns(polars.col(col_name).cast(polars.Utf8))
            max_length = sample_data.select(polars.col(col_name).str.len_chars().max()).item()
            sample_text = sample_data.with_columns(polars.when(polars.col(col_name).str.len_chars() == max_length)
                                                         .then(polars.col(col_name)).otherwise(None)
                                                         .alias('sample_text')
            ).drop_nulls('sample_text').sample(1).item(0, 'sample_text')
            layout.set_text(str(sample_text), -1)
            text_width = layout.get_size()[0] / Pango.SCALE
            preferred_width = text_width + 2 * self.display.DEFAULT_CELL_PADDING
            self.display.column_widths[col_index] = max(self.display.DEFAULT_CELL_WIDTH, min(max_width, int(preferred_width)))

        self.display.cumulative_column_widths = polars.Series('ccwidths', self.display.column_widths).cum_sum()

        globals.is_changing_state = False

    def auto_adjust_scrollbars_by_scroll(self) -> None:
        globals.is_changing_state = True

        canvas_height = self.view.main_canvas.get_height()
        canvas_width = self.view.main_canvas.get_width()

        content_height = canvas_height
        content_width = canvas_width

        if len(self.data.bbs):
            content_height = (self.data.bbs[0].row_span + 3) * self.display.DEFAULT_CELL_HEIGHT
            content_width = (self.data.bbs[0].column_span + 1) * self.display.DEFAULT_CELL_WIDTH

            if len(self.display.cumulative_row_heights):
                content_height = self.display.cumulative_row_heights[-1] + self.display.DEFAULT_CELL_HEIGHT * 3
            if len(self.display.cumulative_column_widths):
                content_width = self.display.cumulative_column_widths[-1] + self.display.DEFAULT_CELL_WIDTH * 1

        scroll_y_upper = max(content_height + self.display.column_header_height, self.display.scroll_y_position + canvas_height)
        self.view.vertical_scrollbar.get_adjustment().set_upper(scroll_y_upper)
        self.view.vertical_scrollbar.get_adjustment().set_page_size(canvas_height)

        scroll_x_upper = max(content_width + self.display.row_header_width, self.display.scroll_x_position + canvas_width)
        self.view.horizontal_scrollbar.get_adjustment().set_upper(scroll_x_upper)
        self.view.horizontal_scrollbar.get_adjustment().set_page_size(canvas_width)

        globals.is_changing_state = False

    def auto_adjust_selections_by_scroll(self) -> None:
        globals.is_changing_state = True

        self.selection.current_active_range.x = self.display.get_cell_x_from_column(self.selection.current_active_range.column)
        self.selection.current_active_range.y = self.display.get_cell_y_from_row(self.selection.current_active_range.row)

        self.selection.current_active_cell.x = self.display.get_cell_x_from_column(self.selection.current_active_cell.column)
        self.selection.current_active_cell.y = self.display.get_cell_y_from_row(self.selection.current_active_cell.row)

        if self.selection.current_search_range is not None:
            self.selection.current_search_range.x = self.display.get_cell_x_from_column(self.selection.current_search_range.column)
            self.selection.current_search_range.y = self.display.get_cell_y_from_row(self.selection.current_search_range.row)

        globals.is_changing_state = False

    def auto_adjust_locators_size_by_scroll(self) -> None:
        globals.is_changing_state = True

        canvas_height = self.view.main_canvas.get_height()
        y_start = self.display.column_header_height
        cell_height = self.display.DEFAULT_CELL_HEIGHT

        # FIXME: sometimes not correct after filtering data; needs further investigation
        max_row_number = int(self.display.get_starting_row()) + 1 + int((canvas_height - y_start) // cell_height)
        max_row_number = self.display.get_vrow_from_row(max_row_number)

        context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))
        font_desc = Pango.font_description_from_string(f'Monospace Normal Bold {self.display.FONT_SIZE}px')

        layout = PangoCairo.create_layout(context)
        layout.set_text(str(max_row_number), -1)
        layout.set_font_description(font_desc)

        text_width = layout.get_size()[0] / Pango.SCALE
        new_row_header_width = max(40, int(text_width + self.display.DEFAULT_CELL_PADDING * 2 + 0.5))

        if new_row_header_width != self.display.row_header_width:
            self.display.row_header_width = new_row_header_width
            self.renderer.render_caches = {}

        globals.is_changing_state = False

    def auto_adjust_scrollbars_by_selection(self, follow_cursor: bool = True, scroll_axis: str = 'both', with_offset: bool = False) -> None:
        globals.is_changing_state = True

        column = self.selection.current_cursor_cell.column
        row = self.selection.current_cursor_cell.row
        viewport_height = self.view.main_canvas.get_height() - self.display.column_header_height
        viewport_width = self.view.main_canvas.get_width() - self.display.row_header_width
        self.display.scroll_to_position(column, row, viewport_height, viewport_width, scroll_axis, with_offset)

        if not follow_cursor:
            column = self.selection.current_active_cell.column
            row = self.selection.current_active_cell.row
            self.display.scroll_to_position(column, row, viewport_height, viewport_width, scroll_axis, with_offset)

        self.auto_adjust_scrollbars_by_scroll()
        self.auto_adjust_locators_size_by_scroll()
        self.auto_adjust_selections_by_scroll()

        vertical_adjustment = self.view.vertical_scrollbar.get_adjustment()
        horizontal_adjustment = self.view.horizontal_scrollbar.get_adjustment()

        vertical_adjustment.handler_block_by_func(self.on_sheet_view_scrolled)
        horizontal_adjustment.handler_block_by_func(self.on_sheet_view_scrolled)

        vertical_adjustment.set_value(self.display.scroll_y_position)
        horizontal_adjustment.set_value(self.display.scroll_x_position)

        vertical_adjustment.handler_unblock_by_func(self.on_sheet_view_scrolled)
        horizontal_adjustment.handler_unblock_by_func(self.on_sheet_view_scrolled)

        globals.is_changing_state = False

    def auto_adjust_selections_by_crud(self, column_offset: int, row_offset: int, shrink: bool) -> None:
        globals.is_changing_state = True

        active = self.selection.current_active_cell
        cursor = self.selection.current_cursor_cell

        col_1 = active.column + column_offset
        row_1 = active.row + row_offset

        if shrink:
            col_2 = col_1
            row_2 = row_1
        else:
            col_2 = cursor.column + column_offset
            row_2 = cursor.row + row_offset

        self.update_selection_from_position(col_1, row_1, col_2, row_2, True, True, False)

        globals.is_changing_state = False