# sheet_document.py
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


from gi.repository import Gdk, GLib, GObject, Gtk, Pango, PangoCairo
from typing import Any
import cairo
import copy
import duckdb
import polars
import re

from . import globals
from . import utils
from .clipboard_manager import ClipboardManager
from .sheet_functions import parse_dax, register_sql_functions

class SheetDocument(GObject.Object):
    __gtype_name__ = 'SheetDocument'

    __gsignals__ = {
        'cancel-operation'  : (GObject.SIGNAL_RUN_FIRST, None, ()),
        'selection-changed' : (GObject.SIGNAL_RUN_FIRST, None, ()),
        'columns-changed'   : (GObject.SIGNAL_RUN_FIRST, None, (int,)),
        'sorts-changed'     : (GObject.SIGNAL_RUN_FIRST, None, (int,)),
        'filters-changed'   : (GObject.SIGNAL_RUN_FIRST, None, (int,)),
        'open-context-menu' : (GObject.SIGNAL_RUN_FIRST, None, (int, int, str)),
    }

    document_id = GObject.Property(type=str, default='sheet_1')
    title = GObject.Property(type=str, default='Sheet 1')

    configs = {
        'show-auto-filters'         : True,
        'ctrl-wheel-to-scroll'      : False,

        # Exclusive for setup_document()
        'auto-adjust-column-widths' : True,
        'auto-adjust-scrollbars'    : True,
        'auto-adjust-selection'     : True,
    }

    def __init__(self,
                 sheet_manager     = None,
                 document_id:  str = '',
                 title:        str = '',
                 dataframe:    polars.DataFrame = None,
                 configs:      dict = {}) -> None:
        super().__init__()

        self.sheet_manager = sheet_manager

        self.document_id = document_id
        self.title = title

        self.configs = copy.deepcopy(self.configs)
        self.configs.update(configs)

        from .sheet_widget import SheetWidget
        self.widgets: list[SheetWidget] = []

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
        self.view = SheetView(self, self.configs)

        self.hovered_widget: SheetWidget = None
        self.focused_widget: SheetWidget = None

        self.is_refreshing_uis: bool = False
        self.is_expanding_cells: bool = False
        self.is_selecting_cells: bool = False
        self.is_cutting_cells: bool = False
        self.is_copying_cells: bool = False

        self.is_searching_cells: bool = False
        # Basically we want to know which widget is currently performing
        # a search range operation, specifically to decide when or not to
        # draw the search range selection box. For example, when we performs
        # a search range operation from the widget on the sidebar but at the
        # same time we have the quick search bar open and want to close it,
        # the search range selection box should keep be shown.
        self.search_range_performer: str = ''

        self.current_dfi: int = 0 if dataframe is not None \
                                  else -1

        self.pending_sorts: dict = {}
        self.current_sorts: dict = {}

        self.pending_filters: list = []
        self.current_filters: list = []

        self.clipboard: ClipboardManager = None

        self.canvas_tick_callback: int = 0

        self.setup_main_canvas()
        self.setup_scrollbars()
        self.setup_document()
        self.setup_history()

    #
    # Setup
    #

    def setup_document(self) -> None:
        if self.configs['auto-adjust-column-widths']:
            self.auto_adjust_column_widths()
        if self.configs['auto-adjust-scrollbars']:
            self.auto_adjust_scrollbars_by_scroll()
        if self.configs['auto-adjust-selection']:
            self.auto_adjust_selections_by_crud(0, 0, False)
        self.repopulate_column_resizer_widgets()
        self.repopulate_auto_filter_widgets()

    def setup_main_canvas(self) -> None:
        self.view.main_canvas.set_draw_func(self.renderer.render)
        self.view.connect('cancel-operation', self.on_operation_cancelled)
        self.view.connect('select-by-keypress', self.on_update_selection_by_keypress)
        self.view.connect('select-by-motion', self.on_update_selection_by_motion)
        self.view.connect('pointer-moved', self.on_update_pointer_moved)
        self.view.connect('pointer-released', self.on_update_pointer_released)

    def setup_scrollbars(self) -> None:
        scroll_increment = self.display.scroll_increment
        page_increment = self.display.page_increment

        vertical_adjustment = Gtk.Adjustment.new(0, 0, 0, scroll_increment, page_increment, 0)
        vertical_adjustment.connect('value-changed', self.on_sheet_view_scrolled)
        self.view.vertical_scrollbar.set_adjustment(vertical_adjustment)

        horizontal_adjustment = Gtk.Adjustment.new(0, 0, 0, scroll_increment, page_increment, 0)
        horizontal_adjustment.connect('value-changed', self.on_sheet_view_scrolled)
        self.view.horizontal_scrollbar.set_adjustment(horizontal_adjustment)

    def setup_history(self) -> None:
        globals.history = self.history

        # Initialize the selection
        globals.is_changing_state = True
        self.update_selection_from_name('A1')
        globals.is_changing_state = False

        # Initialize the undo stack
        self.history.setup_history()

    #
    # Event handlers
    #

    def on_sheet_view_scrolled(self, source: GObject.Object) -> None:
        if self.is_refreshing_uis:
            return

        vscrollbar = self.view.vertical_scrollbar
        hscrollbar = self.view.horizontal_scrollbar

        vadjustment = vscrollbar.get_adjustment()
        hadjustment = hscrollbar.get_adjustment()

        self.display.scroll_y_position = int(vadjustment.get_value())
        self.display.scroll_x_position = int(hadjustment.get_value())

        self.auto_adjust_scrollbars_by_scroll()
        self.auto_adjust_locators_size_by_scroll()
        self.auto_adjust_selections_by_scroll()
        self.repopulate_auto_filter_widgets()

        self.view.main_canvas.queue_draw()

    def on_operation_cancelled(self, source: GObject.Object) -> None:
        self.cancel_cutcopy_operation()
        self.view.main_canvas.queue_draw()
        self.emit('cancel-operation')

    def on_update_selection_by_keypress(self,
                                        source: GObject.Object,
                                        keyval: int,
                                        state:  Gdk.ModifierType) -> None:
        active_cell = self.selection.current_active_cell
        cursor_cell = self.selection.current_cursor_cell

        active_cell_position = (active_cell.column, active_cell.row)
        cursor_cell_position = (cursor_cell.column, cursor_cell.row)
        target_cell_position = active_cell_position

        df_metadata = active_cell.metadata
        df_bbox = self.data.read_cell_bbox_from_metadata(df_metadata.dfi)
        df_selected = df_bbox is not None

        match keyval:
            case Gdk.KEY_Tab | Gdk.KEY_ISO_Left_Tab:
                # Select a cell at the left to the selection
                if state == Gdk.ModifierType.SHIFT_MASK:
                    target_cell_position = (active_cell_position[0] - 1,
                                            active_cell_position[1])

                    # If the cursor is currently within a table and it's reaching the first column,
                    # re-target to the last column of the previous row instead.
                    if df_selected and target_cell_position[0] == 0:
                        target_cell_position = (df_bbox.column + df_bbox.column_span - 1,
                                                target_cell_position[1] - 1)

                # Select a cell at the right to the selection
                else:
                    target_cell_position = (active_cell_position[0] + 1,
                                            active_cell_position[1])

                    # If the cursor is currently within a table and it's reaching the last column,
                    # re-target to the first column of the next row instead.
                    if df_selected and df_bbox.column + df_bbox.column_span - 1 < target_cell_position[0]:
                        target_cell_position = (1, # first column
                                                target_cell_position[1] + 1)

            case Gdk.KEY_Return:
                # Select a cell at the bottom to the selection
                if state == Gdk.ModifierType.SHIFT_MASK:
                    target_cell_position = (active_cell_position[0],
                                            max(1, active_cell_position[1] - 1))

                # Select a cell at the top to the selection
                else:
                    target_cell_position = (active_cell_position[0],
                                            active_cell_position[1] + 1)

            case Gdk.KEY_Left:
                # Select the leftmost cell in the same row
                if state == Gdk.ModifierType.CONTROL_MASK:
                    if df_selected:
                        target_cell_position = (max(1, df_bbox.column),
                                                active_cell_position[1])
                    else:
                        target_cell_position = (1, # first column
                                                active_cell_position[1])

                # Include a cell at the left to the selection
                elif state == Gdk.ModifierType.SHIFT_MASK:
                    new_cursor_cell_position = (max(1, cursor_cell_position[0] - 1),
                                                cursor_cell_position[1])
                    target_cell_position = (active_cell_position,
                                            new_cursor_cell_position)

                # Include all cells to the left to the selection
                elif state == (Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK):
                    if df_selected:
                        new_cursor_cell_position = (max(1, df_bbox.column),
                                                    cursor_cell_position[1])
                        target_cell_position = (active_cell_position,
                                                new_cursor_cell_position)
                    else:
                        target_cell_position = (active_cell_position,
                                                (1, cursor_cell_position[1]))

                # Select a cell at the left to the selection
                else:
                    target_cell_position = (max(1, active_cell_position[0] - 1),
                                            active_cell_position[1])

            case Gdk.KEY_Right:
                # Select the rightmost cell in the same row
                if state == Gdk.ModifierType.CONTROL_MASK:
                    if df_selected:
                        target_cell_position = (max(1, df_bbox.column + df_bbox.column_span - 1),
                                                active_cell_position[1])
                    else:
                        target_cell_position = (active_cell_position[0] + 1,
                                                active_cell_position[1])

                # Include a cell at the right to the selection
                elif state == Gdk.ModifierType.SHIFT_MASK:
                    new_cursor_cell_position = (cursor_cell_position[0] + 1,
                                                cursor_cell_position[1])
                    target_cell_position = (active_cell_position,
                                            new_cursor_cell_position)

                # Include all cells to the right to the selection
                elif state == (Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK):
                    if df_selected:
                        new_cursor_cell_position = (max(1, df_bbox.column + df_bbox.column_span - 1),
                                                    cursor_cell_position[1])
                        target_cell_position = (active_cell_position,
                                                new_cursor_cell_position)
                    else:
                        new_cursor_cell_position = (cursor_cell_position[0] + 1,
                                                    cursor_cell_position[1])
                        target_cell_position = (active_cell_position,
                                                new_cursor_cell_position)

                # Select a cell at the right to the selection
                else:
                    target_cell_position = (active_cell_position[0] + 1,
                                            active_cell_position[1])

            case Gdk.KEY_Up:
                # Select the topmost cell in the same column
                if state == Gdk.ModifierType.CONTROL_MASK:
                    if df_selected:
                        target_cell_position = (active_cell_position[0],
                                                max(1, df_bbox.row))
                    else:
                        target_cell_position = (active_cell_position[0],
                                                1) # first row

                # Include a cell at the top to the selection
                elif state == Gdk.ModifierType.SHIFT_MASK:
                    new_cursor_cell_position = (cursor_cell_position[0],
                                                max(1, cursor_cell_position[1] - 1))
                    target_cell_position = (active_cell_position,
                                            new_cursor_cell_position)

                # Include all cells above to the selection
                elif state == (Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK):
                    if df_selected:
                        new_cursor_cell_position = (cursor_cell_position[0],
                                                    max(1, df_bbox.row))
                        target_cell_position = (active_cell_position,
                                                new_cursor_cell_position)
                    else:
                        new_cursor_cell_position = (cursor_cell_position[0],
                                                    1) # first row
                        target_cell_position = (active_cell_position,
                                                new_cursor_cell_position)

                # Select a cell at the top to the selection
                else:
                    target_cell_position = (active_cell_position[0],
                                            max(1, active_cell_position[1] - 1))

            case Gdk.KEY_Down:
                # Select the bottommost cell in the same column
                if state == Gdk.ModifierType.CONTROL_MASK:
                    if df_selected:
                        target_cell_position = (active_cell_position[0],
                                                max(1, df_bbox.row + df_bbox.row_span - 1))
                    else:
                        target_cell_position = (active_cell_position[0],
                                                active_cell_position[1] + 1)

                # Include a cell at the bottom to the selection
                elif state == Gdk.ModifierType.SHIFT_MASK:
                    new_cursor_cell_position = (cursor_cell_position[0],
                                                cursor_cell_position[1] + 1)
                    target_cell_position = (active_cell_position,
                                            new_cursor_cell_position)

                # Include all cells below to the selection
                elif state == (Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK):
                    if df_selected:
                        new_cursor_cell_position = (cursor_cell_position[0],
                                                    max(1, df_bbox.row + df_bbox.row_span - 1))
                        target_cell_position = (active_cell_position,
                                                new_cursor_cell_position)
                    else:
                        new_cursor_cell_position = (cursor_cell_position[0],
                                                    cursor_cell_position[1] + 1)
                        target_cell_position = (active_cell_position,
                                                new_cursor_cell_position)

                # Select a cell at the bottom to the selection
                else:
                    target_cell_position = (active_cell_position[0],
                                            active_cell_position[1] + 1)

        if all(isinstance(i, int) for i in target_cell_position):
            col_1, row_1 = target_cell_position
            col_2, row_2 = col_1, row_1
        else:
            (col_1, row_1), (col_2, row_2) = target_cell_position

        self.update_selection_from_position(col_1, row_1,
                                            col_2, row_2,
                                            keep_order=True,
                                            follow_cursor=True,
                                            auto_scroll=True)

        self.view.main_canvas.queue_draw()

        self.notify_selected_table_changed()

    def on_update_selection_by_motion(self,
                                      source: GObject.Object,
                                      x:      int,
                                      y:      int) -> None:
        if self.focused_widget is not None:
            return

        self.is_selecting_cells = True

        from .sheet_selection import SheetLocatorCell, \
                                     SheetTopLocatorCell, \
                                     SheetLeftLocatorCell

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
        if end_column == cursor_column \
                and end_row == cursor_row:
            return
        if end_column == cursor_column \
                and end_row == 0 \
                and cursor_row == 1:
            return
        if end_column == 0 \
                and cursor_column == 1 \
                and end_row == cursor_row:
            return

        scroll_axis = 'both'
        if isinstance(active_range, SheetTopLocatorCell):
            scroll_axis = 'horizontal'
        if isinstance(active_range, SheetLeftLocatorCell):
            scroll_axis = 'vertical'

        self.update_selection_from_position(start_column,
                                            start_row,
                                            end_column,
                                            end_row,
                                            keep_order=True,
                                            follow_cursor=True,
                                            auto_scroll=True,
                                            scroll_axis=scroll_axis,
                                            with_offset=False,
                                            smooth_scroll=True)

        self.view.main_canvas.queue_draw()

        self.notify_selected_table_changed()

    def on_update_pointer_moved(self,
                                source: GObject.Object,
                                x:      int,
                                y:      int) -> None:
        if self.is_selecting_cells:
            return

        if self.focused_widget is not None:
            if self.focused_widget.do_on_dragged(x, y):
                return

        hovered_widget = None

        # Find and track the hovered widget
        for widget in self.widgets:
            if widget.contains(x, y):
                hovered_widget = widget
                widget.do_on_enter(x, y)
                continue

            if self.hovered_widget == widget:
                widget.do_on_leave(x, y)
                continue

        self.view.main_canvas.set_cursor(self.view.default_cursor)

        if hovered_widget is not None:
            self.view.main_canvas.set_cursor(hovered_widget.cursor)

        self.hovered_widget = hovered_widget

    def on_update_pointer_released(self,
                                   source: GObject.Object,
                                   x:      int,
                                   y:      int) -> None:
        self.is_selecting_cells = False

        if self.focused_widget is not None:
            self.focused_widget.do_on_released(x, y)
            self.focused_widget = None

    #
    # Selection
    #

    def select_element_from_point(self,
                                  x:     float,
                                  y:     float,
                                  state: Gdk.ModifierType = None) -> None:
        # Trigger the on_pressed event of the hovered widget if the pointer is under one,
        # otherwise select the hovered cell.
        self.focused_widget = self.hovered_widget
        if self.focused_widget is not None:
            if self.focused_widget.do_on_pressed(x, y):
                return

        column = self.display.get_column_from_point(x)
        row = self.display.get_row_from_point(y)

        start_column = column
        start_row = row
        end_column = column
        end_row = row

        if state == Gdk.ModifierType.SHIFT_MASK:
            active = self.selection.current_active_cell
            start_column = active.column
            start_row = active.row

        self.update_selection_from_position(start_column,
                                            start_row,
                                            end_column,
                                            end_row,
                                            keep_order=True,
                                            follow_cursor=False,
                                            auto_scroll=False)

        self.view.main_canvas.queue_draw()

        self.notify_selected_table_changed()

    def try_to_select_entire_content_rows(self, include_header: bool = False) -> None:
        arange = self.selection.current_active_range

        if arange.row_span > 0:
            return

        mdfi = arange.metadata.dfi
        mrow = arange.metadata.row

        if mdfi < 0 or len(self.data.dfs) <= mdfi:
            return

        column = 1
        row_1 = mrow if include_header else (mrow + 1)
        row_2 = (row_1 - 1) + self.data.bbs[mdfi].row_span - (0 if include_header else 1)

        self.update_selection_from_position(column, row_1, column, row_2, auto_scroll=False)

    def try_to_select_entire_content_columns(self) -> None:
        arange = self.selection.current_active_range

        if arange.column_span > 0:
            return

        mdfi = arange.metadata.dfi
        mcolumn = arange.metadata.column

        if mdfi < 0 or len(self.data.dfs) <= mdfi:
            return

        column_1 = mcolumn
        column_2 = (column_1 - 1) + self.data.bbs[mdfi].column_span
        row = 1

        self.update_selection_from_position(column_1, row, column_2, row, auto_scroll=False)

    def update_selection_from_name(self, name: str) -> None:
        vcol_1, vrow_1, vcol_2, vrow_2 = self.display.get_cell_range_from_name(name)

        col_1 = self.display.get_column_from_vcolumn(vcol_1)
        col_2 = self.display.get_column_from_vcolumn(vcol_2)
        row_1 = self.display.get_row_from_vrow(vrow_1)
        row_2 = self.display.get_row_from_vrow(vrow_2)

        self.update_selection_from_position(col_1, row_1,
                                            col_2, row_2,
                                            keep_order=False,
                                            follow_cursor=False,
                                            auto_scroll=True)

        self.view.main_canvas.queue_draw()

        self.notify_selected_table_changed()

    def update_selection_from_position(self,
                                       col_1:         int,
                                       row_1:         int,
                                       col_2:         int,
                                       row_2:         int,
                                       keep_order:    bool = False,
                                       follow_cursor: bool = True,
                                       auto_scroll:   bool = True,
                                       scroll_axis:   str = 'both',
                                       with_offset:   bool = False,
                                       smooth_scroll: bool = False) -> None:
        # Save snapshot
        if not globals.is_changing_state and not globals.is_editing_cells:
            from .history_manager import SelectionState
            state = SelectionState(col_1, row_1,
                                   col_2, row_2,
                                   keep_order,
                                   follow_cursor,
                                   auto_scroll)
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

        from .sheet_selection import SheetLocatorCell, \
                                     SheetCornerLocatorCell, \
                                     SheetTopLocatorCell, \
                                     SheetLeftLocatorCell, \
                                     SheetContentCell

        # Handle clicking on the top left locator area
        if start_column == 0 and start_row == 0:
            self.selection.current_active_range = SheetCornerLocatorCell(x, y,
                                                                         0, 0,
                                                                         canvas_width,
                                                                         canvas_height,
                                                                         -1, -1,
                                                                         cell_metadata,
                                                                         rtl, btt)

        # Handle selecting the top locator area
        elif start_column > 0 and start_row == 0:
            self.selection.current_active_range = SheetTopLocatorCell(x, y,
                                                                      start_column, 0,
                                                                      width, canvas_height,
                                                                      column_span, -1,
                                                                      cell_metadata,
                                                                      rtl, btt)

        # Handle selecting the left locator area
        elif start_column == 0 and start_row > 0:
            self.selection.current_active_range = SheetLeftLocatorCell(x, y,
                                                                       0, start_row,
                                                                       canvas_width, height,
                                                                       -1, row_span,
                                                                       cell_metadata,
                                                                       rtl, btt)

        # Handle selecting a cell content area
        else:
            self.selection.current_active_range = SheetContentCell(x, y,
                                                                   start_column, start_row,
                                                                   width, height,
                                                                   column_span, row_span,
                                                                   cell_metadata,
                                                                   rtl, btt)

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
        self.selection.current_active_cell = SheetContentCell(x, y,
                                                              col_1, row_1,
                                                              width, height,
                                                              1, 1,
                                                              cell_metadata)

        x = self.display.get_cell_x_from_column(col_2)
        y = self.display.get_cell_y_from_row(row_2)
        width = self.display.get_cell_width_from_column(col_2)
        height = self.display.get_cell_height_from_row(row_2)
        self.selection.current_cursor_cell = SheetContentCell(x, y,
                                                              col_2, row_2,
                                                              width, height,
                                                              1, 1,
                                                              cell_metadata)

        if auto_scroll:
            self.auto_adjust_scrollbars_by_selection(follow_cursor,
                                                     scroll_axis,
                                                     with_offset,
                                                     smooth_scroll)
            self.auto_adjust_locators_size_by_scroll()
            self.auto_adjust_selections_by_scroll()
            self.repopulate_auto_filter_widgets()

        if keep_order:
            self.notify_selection_changed(col_1, row_1, cell_metadata)
        else:
            self.notify_selection_changed(start_column, start_row, cell_metadata)

        # Reset the current search range
        if not globals.is_changing_state \
                and self.selection.current_search_range is not None:
            arange = self.selection.current_active_range
            self.selection.current_search_range = arange

    #
    # DDL and CRUD
    #

    def create_table_from_operator(self,
                                   operator_name:  str,
                                   operation_args: list = [],
                                   on_column:      bool = False) -> polars.DataFrame:
        arange = self.selection.current_active_range
        mdfi = arange.metadata.dfi

        if mdfi < 0:
            return False

        mcolumn = arange.metadata.column
        mrow = arange.metadata.row
        column_span = arange.column_span
        row_span = arange.row_span

        bbox = self.data.bbs[mdfi]

        if on_column:
            mrow = 1

        if arange.column_span < 0:
            column_span = bbox.column_span + 1

        if arange.row_span < 0 or on_column:
            row_span = bbox.row_span + 2

        column_span = self.get_logical_column_span(column_span)
        row_span = self.get_logical_row_span(row_span)

        if arange.column_span < 0:
            column_span -= 1

        if arange.row_span < 0 or on_column:
            row_span -= 3

        if arange.rtl:
            mcolumn = mcolumn - column_span + 1

        if arange.btt:
            mrow = mrow - row_span + 1

        return self.data.read_cell_data_block_with_operator_from_metadata(mcolumn,
                                                                          mrow,
                                                                          column_span,
                                                                          row_span,
                                                                          mdfi,
                                                                          operator_name,
                                                                          operation_args,
                                                                          self.display.column_visible_series,
                                                                          self.display.row_visible_series)

    def insert_from_current_rows(self,
                                 dataframe: polars.DataFrame,
                                 vflags:    polars.Series = None,
                                 rheights:  polars.Series = None) -> bool:
        self.try_to_select_entire_content_rows()
        arange = self.selection.current_active_range

        mdfi = arange.metadata.dfi
        mrow = arange.metadata.row

        row_span = self.get_logical_row_span()

        if arange.btt:
            mrow = mrow - row_span + 1

        if self.data.insert_rows_from_dataframe(dataframe, mrow, mdfi):
            # Update row visibility flags
            if len(self.display.row_visibility_flags):
                if vflags is not None:
                    self.display.row_visibility_flags = polars.concat([self.display.row_visibility_flags[:mrow],
                                                                       vflags,
                                                                       self.display.row_visibility_flags[mrow:]])
                else:
                    self.display.row_visibility_flags = polars.concat([self.display.row_visibility_flags[:mrow],
                                                                       polars.Series([True] * dataframe.height),
                                                                       self.display.row_visibility_flags[mrow:]])
                self.display.row_visible_series = self.display.row_visibility_flags.arg_true()
                self.data.bbs[mdfi].row_span = len(self.display.row_visible_series)
            else:
                self.data.bbs[mdfi].row_span = self.data.dfs[mdfi].height + 1

            # Update row heights
            if len(self.display.row_heights):
                if rheights is not None:
                    self.display.row_heights = polars.concat([self.display.row_heights[:mrow],
                                                              rheights,
                                                              self.display.row_heights[mrow:]])
                else:
                    self.display.row_heights = polars.concat([self.display.row_heights[:mrow],
                                                              polars.Series([self.display.DEFAULT_CELL_HEIGHT] * dataframe.height,
                                                                            dtype=polars.Int32),
                                                              self.display.row_heights[mrow:]])
                row_heights_visible_only = self.display.row_heights
                if len(self.display.row_visibility_flags):
                    row_heights_visible_only = row_heights_visible_only.filter(self.display.row_visibility_flags)
                self.display.cumulative_row_heights = polars.Series('crheights', row_heights_visible_only).cum_sum()

            self.cancel_cutcopy_operation()
            self.auto_adjust_selections_by_crud(0, 0, False)

            # TODO: clear only for the related columns
            self.data.clear_cell_data_unique_cache(0)

            self.renderer.render_caches = {}
            self.view.main_canvas.queue_draw()

            return True

        return False

    def insert_blank_from_current_rows(self,
                                       above:     bool = False,
                                       row_span:  int = -1,
                                       on_border: bool = False,
                                       dfi:       int = -1) -> bool:
        self.try_to_select_entire_content_rows()
        arange = self.selection.current_active_range

        mrow = arange.metadata.row
        mdfi = arange.metadata.dfi

        auto_range = row_span == -1

        if dfi > -1:
            mdfi = dfi

        # Simulate the cursor's movement to the edge of the dataframe
        if on_border:
            mrow = self.data.bbs[mdfi].row
            if above:
                mrow -= row_span + 1
            else:
                mrow += self.data.dfs[mdfi].height - 1
            mrow += 1

        if auto_range:
            row_span = self.get_logical_row_span()

            if not above:
                mrow = mrow + row_span

            if arange.btt:
                mrow = mrow - row_span
            else:
                mrow = mrow - 1

        # Prepare for snapshot
        if not globals.is_changing_state:
            from .history_manager import InsertBlankRowState
            state = InsertBlankRowState(above, row_span, on_border, mdfi, auto_range)

        if self.data.insert_rows_from_metadata(mrow, row_span, mdfi):
            # Save snapshot
            if not globals.is_changing_state:
                globals.history.save(state)

            mrow = arange.metadata.row

            if not above:
                mrow += row_span

            if on_border:
                mrow = self.data.bbs[mdfi].row

                if not above:
                    mrow += self.data.dfs[mdfi].height - row_span + 1

            # Update row visibility flags
            if len(self.display.row_visibility_flags):
                self.display.row_visibility_flags = polars.concat([self.display.row_visibility_flags[:mrow],
                                                                   polars.Series([True] * row_span),
                                                                   self.display.row_visibility_flags[mrow:]])
                self.display.row_visible_series = self.display.row_visibility_flags.arg_true()
                self.data.bbs[mdfi].row_span = len(self.display.row_visible_series)
            else:
                self.data.bbs[mdfi].row_span = self.data.dfs[mdfi].height + 1

            # Update row heights
            if len(self.display.row_heights):
                self.display.row_heights = polars.concat([self.display.row_heights[:mrow],
                                                          polars.Series([self.display.DEFAULT_CELL_HEIGHT] * row_span, dtype=polars.Int32),
                                                          self.display.row_heights[mrow:]])
                row_heights_visible_only = self.display.row_heights
                if len(self.display.row_visibility_flags):
                    row_heights_visible_only = row_heights_visible_only.filter(self.display.row_visibility_flags)
                self.display.cumulative_row_heights = polars.Series('crheights', row_heights_visible_only).cum_sum()

            if not self.is_expanding_cells:
                self.cancel_cutcopy_operation()

            self.auto_adjust_selections_by_crud(0, 0 if not above else row_span, False)

            # TODO: clear only for the related columns
            self.data.clear_cell_data_unique_cache(0)

            self.renderer.render_caches = {}
            self.view.main_canvas.queue_draw()

            return True

        return False

    def insert_from_current_columns(self,
                                    dataframe: polars.DataFrame,
                                    vflags:    polars.Series = None,
                                    cwidths:   polars.Series = None) -> bool:
        self.try_to_select_entire_content_rows()
        arange = self.selection.current_active_range

        mdfi = arange.metadata.dfi
        mcolumn = arange.metadata.column

        column_span = self.get_logical_column_span(column_span)

        if arange.rtl:
            mcolumn = mcolumn - column_span + 1

        if self.data.insert_columns_from_dataframe(dataframe, mcolumn, mdfi):
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
                self.data.bbs[mdfi].column_span = len(self.display.column_visible_series)
            else:
                self.data.bbs[mdfi].column_span = self.data.dfs[mdfi].width

            # Update column widths
            if len(self.display.column_widths):
                if cwidths is not None:
                    self.display.column_widths = polars.concat([self.display.column_widths[:mcolumn],
                                                                cwidths,
                                                                self.display.column_widths[mcolumn:]])
                else:
                    self.display.column_widths = polars.concat([self.display.column_widths[:mcolumn],
                                                                polars.Series([self.display.DEFAULT_CELL_WIDTH] * dataframe.width,
                                                                              dtype=polars.Int32),
                                                                self.display.column_widths[mcolumn:]])
                column_widths_visible_only = self.display.column_widths
                if len(self.display.column_visibility_flags):
                    column_widths_visible_only = column_widths_visible_only.filter(self.display.column_visibility_flags)
                self.display.cumulative_column_widths = polars.Series('ccwidths', column_widths_visible_only).cum_sum()

            self.cancel_cutcopy_operation()
            self.auto_adjust_selections_by_crud(0, 0, False)
            self.repopulate_auto_filter_widgets()

            # TODO: clear only for the related columns
            self.data.clear_cell_data_unique_cache(0)

            self.renderer.render_caches = {}
            self.view.main_canvas.queue_draw()

            self.emit('columns-changed', mdfi)

            return True

        return False

    def insert_blank_from_current_columns(self,
                                          left:        bool = False,
                                          column_span: int = -1,
                                          on_border:   bool = False,
                                          dfi:         int = -1) -> bool:
        self.try_to_select_entire_content_columns()
        arange = self.selection.current_active_range

        mcolumn = arange.metadata.column
        mdfi = arange.metadata.dfi

        auto_range = column_span == -1

        if dfi > -1:
            mdfi = dfi

        # Simulate the cursor's movement to the edge of the dataframe
        if on_border:
            mcolumn = self.data.bbs[mdfi].column

            if left:
                mcolumn -= column_span
            else:
                mcolumn += self.data.dfs[mdfi].width - 1

        if auto_range:
            column_span = self.get_logical_column_span()

            if not left:
                mcolumn = mcolumn + column_span
            else:
                mcolumn = mcolumn - column_span + 1

            if arange.rtl:
                mcolumn = mcolumn - column_span + 1

        # Prepare for snapshot
        if not globals.is_changing_state:
            from .history_manager import InsertBlankColumnState
            state = InsertBlankColumnState(left, column_span, on_border, mdfi, auto_range)

        if self.data.insert_columns_from_metadata(mcolumn, column_span, mdfi, left):
            # Save snapshot
            if not globals.is_changing_state:
                globals.history.save(state)

            mcolumn = arange.metadata.column

            if not left:
                mcolumn += column_span

            if on_border:
                mcolumn = self.data.bbs[mdfi].column - 1
                if not left:
                    mcolumn += self.data.dfs[mdfi].width - column_span

            # Update column visibility flags
            if len(self.display.column_visibility_flags):
                self.display.column_visibility_flags = polars.concat([self.display.column_visibility_flags[:mcolumn],
                                                                      polars.Series([True] * column_span),
                                                                      self.display.column_visibility_flags[mcolumn:]])
                self.display.column_visible_series = self.display.column_visibility_flags.arg_true()
                self.data.bbs[mdfi].column_span = len(self.display.column_visible_series)
            else:
                self.data.bbs[mdfi].column_span = self.data.dfs[mdfi].width

            # Update column widths
            if len(self.display.column_widths):
                self.display.column_widths = polars.concat([self.display.column_widths[:mcolumn],
                                                            polars.Series([self.display.DEFAULT_CELL_WIDTH] * column_span,
                                                                          dtype=polars.UInt32),
                                                            self.display.column_widths[mcolumn:]])
                column_widths_visible_only = self.display.column_widths
                if len(self.display.column_visibility_flags):
                    column_widths_visible_only = column_widths_visible_only.filter(self.display.column_visibility_flags)
                self.display.cumulative_column_widths = polars.Series('ccwidths', column_widths_visible_only).cum_sum()

            if not self.is_expanding_cells:
                self.cancel_cutcopy_operation()

            self.auto_adjust_selections_by_crud(0 if not left else column_span, 0, False)
            self.repopulate_auto_filter_widgets()

            # TODO: clear only for the related columns
            self.data.clear_cell_data_unique_cache(0)

            self.renderer.render_caches = {}
            self.view.main_canvas.queue_draw()

            self.emit('columns-changed', mdfi)

            return True

        return False

    def update_current_columns_from_dax(self, query: str) -> bool:
        arange = self.selection.current_active_range
        mdfi = arange.metadata.dfi

        # Check bounding box collision
        from .sheet_data import SheetCellBoundingBox
        arange_bbox = SheetCellBoundingBox(arange.column,
                                           arange.row,
                                           arange.column_span,
                                           arange.row_span)
        for bbox in self.data.bbs:
            collision_info = bbox.check_collision(arange_bbox)

            has_collision = collision_info['has_collision']
            in_bounds = collision_info['nonov_column_span'] + collision_info['nonov_row_span'] == 0
            is_sticky = collision_info['horizontal_gap'] + collision_info['vertical_gap'] == 0

            if (has_collision and not in_bounds) or is_sticky:
                mdfi = self.data.bbs.index(bbox)
                break

        if mdfi < 0:
            return False # TODO: create a new table?

        expression = parse_dax(query)

        if 'error' in expression:
            globals.send_notification(expression['error'])
            return False

        is_new_column = expression['measure'] not in self.data.dfs[mdfi].columns

        if is_new_column:
            target_column_names = []
            added_column_names = [expression['measure']]
        else:
            target_column_names = [expression['measure']]
            added_column_names = []

        # Save snapshot
        if not globals.is_changing_state:
            from .history_manager import UpdateColumnDataFromDaxState
            state = UpdateColumnDataFromDaxState(self.data.read_cell_data_chunks_from_metadata(target_column_names, 0, -1, mdfi),
                                                 target_column_names,
                                                 added_column_names,
                                                 mdfi,
                                                 query)

        # Apply the query
        if self.data.update_columns_with_expression_from_metadata(mdfi,
                                                                  expression['measure'],
                                                                  expression['expression']):
            # Update column visibility flags
            if len(self.display.column_visibility_flags):
                self.display.column_visibility_flags = polars.concat([self.display.column_visibility_flags,
                                                                      polars.Series([True])])
                self.display.column_visible_series = self.display.column_visibility_flags.arg_true()

            # Update column widths
            if len(self.display.column_widths):
                self.display.column_widths = polars.concat([self.display.column_widths,
                                                            polars.Series([self.display.DEFAULT_CELL_WIDTH], dtype=polars.UInt32)])
                column_widths_visible_only = self.display.column_widths
                if len(self.display.column_visibility_flags):
                    column_widths_visible_only = column_widths_visible_only.filter(self.display.column_visibility_flags)
                self.display.cumulative_column_widths = polars.Series('ccwidths', column_widths_visible_only).cum_sum()

            # TODO: what should we do instead when no new columns were added?
            if is_new_column:
                bbox = self.data.bbs[mdfi]
                self.update_selection_from_position(bbox.column + bbox.column_span - 1, 1,
                                                    bbox.column + bbox.column_span - 1, 1,
                                                    follow_cursor=False)

            # Save snapshot
            if not globals.is_changing_state:
                globals.history.save(state)

            # TODO: clear only for the related columns
            self.data.clear_cell_data_unique_cache(0)

            self.renderer.render_caches = {}
            self.view.main_canvas.queue_draw()

            arange = self.selection.current_active_range
            self.notify_selection_changed(arange.column, arange.row, arange.metadata)

            self.emit('columns-changed', mdfi)

            return True

        return False

    def update_current_columns_from_sql(self, query: str) -> bool:
        arange = self.selection.current_active_range
        mdfi = arange.metadata.dfi

        # Check bounding box collision
        from .sheet_data import SheetCellBoundingBox
        arange_bbox = SheetCellBoundingBox(arange.column,
                                           arange.row,
                                           arange.column_span,
                                           arange.row_span)
        for bbox in self.data.bbs:
            collision_info = bbox.check_collision(arange_bbox)

            has_collision = collision_info['has_collision']
            in_bounds = collision_info['nonov_column_span'] + collision_info['nonov_row_span'] == 0
            is_sticky = collision_info['horizontal_gap'] + collision_info['vertical_gap'] == 0

            if (has_collision and not in_bounds) or is_sticky:
                mdfi = self.data.bbs.index(bbox)
                break

        if mdfi < 0:
            return False # TODO: create a new table?

        # Clean up the query
        nquery = query.split('=', 1)[1].strip()

        # Add "FROM self" if needed
        if 'from' not in nquery.lower():
            if 'where' in nquery.lower():
                nquery = nquery.replace('where', 'FROM self WHERE', 1)
            else:
                nquery += ' FROM self'

        target_column_names = []
        added_column_names = []

        connection = duckdb.connect()

        # Register all the data sources
        if self.data.has_main_dataframe:
            connection.register('self', self.data.dfs[0])
        connection_strings = globals.register_connection(connection)

        register_sql_functions(connection)

        try:
            rquery = connection_strings + nquery
            relation = connection.sql(rquery)
            target_column_names = list(set(self.data.dfs[mdfi].columns) & set(relation.columns))
            added_column_names = list(set(relation.columns) - set(target_column_names))
            n_added_columns = len(added_column_names)
        except:
            pass # ignore it as it'll also fail in the next processing step

        # Save snapshot
        if not globals.is_changing_state:
            from .history_manager import UpdateColumnDataFromSqlState
            state = UpdateColumnDataFromSqlState(self.data.read_cell_data_chunks_from_metadata(target_column_names, 0, -1, mdfi),
                                                 target_column_names,
                                                 added_column_names,
                                                 mdfi,
                                                 query)

        # Apply the query
        if self.data.update_columns_with_sql_from_metadata(mdfi, nquery, connection):
            # Update column visibility flags
            if len(self.display.column_visibility_flags):
                self.display.column_visibility_flags = polars.concat([self.display.column_visibility_flags,
                                                                      polars.Series([True] * n_added_columns)])
                self.display.column_visible_series = self.display.column_visibility_flags.arg_true()

            # Update column widths
            if len(self.display.column_widths):
                self.display.column_widths = polars.concat([self.display.column_widths,
                                                            polars.Series([self.display.DEFAULT_CELL_WIDTH] * n_added_columns, dtype=polars.UInt32)])
                column_widths_visible_only = self.display.column_widths
                if len(self.display.column_visibility_flags):
                    column_widths_visible_only = column_widths_visible_only.filter(self.display.column_visibility_flags)
                self.display.cumulative_column_widths = polars.Series('ccwidths', column_widths_visible_only).cum_sum()

            # TODO: what should we do instead when no new columns were added?
            if n_added_columns > 0:
                bbox = self.data.bbs[mdfi]
                self.update_selection_from_position(bbox.column + bbox.column_span - n_added_columns, 1,
                                                    bbox.column + bbox.column_span - 1, 1,
                                                    follow_cursor=False)

            # Save snapshot
            if not globals.is_changing_state:
                globals.history.save(state)

            # TODO: clear only for the related columns
            self.data.clear_cell_data_unique_cache(0)

            self.renderer.render_caches = {}
            self.view.main_canvas.queue_draw()

            arange = self.selection.current_active_range
            self.notify_selection_changed(arange.column, arange.row, arange.metadata)

            self.emit('columns-changed', mdfi)

            connection.close()

            return True

        connection.close()

        return False

    def update_current_cells_from_formula(self, formula: str) -> bool:
        arange = self.selection.current_active_range
        mdfi = arange.metadata.dfi

        if mdfi < 0:
            return False # TODO: create a new table?

        from pprint import pprint
        pprint(parse_dax(formula), sort_dicts=False)

        return True

    def update_current_cells_from_operator(self,
                                           operator_name:  str,
                                           operation_args: list = [],
                                           on_column:      bool = False) -> bool:
        arange = self.selection.current_active_range
        mdfi = arange.metadata.dfi

        if mdfi < 0:
            return False

        mcolumn = arange.metadata.column
        mrow = arange.metadata.row
        column_span = arange.column_span
        row_span = arange.row_span

        bbox = self.data.bbs[mdfi]

        if on_column:
            mrow = 1

        if arange.column_span < 0:
            column_span = bbox.column_span + 1

        if arange.row_span < 0 or on_column:
            row_span = bbox.row_span + 2

        column_span = self.get_logical_column_span(column_span)
        row_span = self.get_logical_row_span(row_span)

        if arange.column_span < 0:
            column_span -= 1

        if arange.row_span < 0 or on_column:
            row_span -= 3

        if arange.rtl:
            mcolumn = mcolumn - column_span + 1

        if arange.btt:
            mrow = mrow - row_span + 1

        # By now header is always in the first row
        include_header = mrow == 0

        # Prepare for snapshot
        if not globals.is_changing_state:
            from .history_manager import UpdateDataFromOperatorState
            content = self.data.read_cell_data_block_from_metadata(mcolumn,
                                                                   mrow,
                                                                   column_span,
                                                                   row_span,
                                                                   mdfi,
                                                                   include_header)
            state = UpdateDataFromOperatorState(mcolumn,
                                                mrow,
                                                column_span,
                                                row_span,
                                                mdfi,
                                                content,
                                                include_header,
                                                operator_name,
                                                operation_args,
                                                on_column)

        # Update data
        if self.data.update_cell_data_block_with_operator_from_metadata(mcolumn,
                                                                        mrow,
                                                                        column_span,
                                                                        row_span,
                                                                        mdfi,
                                                                        include_header,
                                                                        operator_name,
                                                                        operation_args,
                                                                        self.display.column_visible_series,
                                                                        self.display.row_visible_series):
            # Save snapshot
            if not globals.is_changing_state:
                globals.history.save(state)

            # TODO: clear only for the related columns
            self.data.clear_cell_data_unique_cache(0)

            self.renderer.render_caches = {}
            self.view.main_canvas.queue_draw()

            active_cell = self.selection.current_active_cell
            self.notify_selection_changed(active_cell.column, active_cell.row, active_cell.metadata)

            return True

        return False

    def update_current_cells_from_literal(self, new_value: Any) -> bool:
        arange = self.selection.current_active_range
        active = self.selection.current_active_cell
        cursor = self.selection.current_cursor_cell

        mdfi = arange.metadata.dfi

        should_expand = False
        collision_info = {}

        # Check bounding box collision
        from .sheet_data import SheetCellBoundingBox
        arange_bbox = SheetCellBoundingBox(arange.column,
                                           arange.row,
                                           arange.column_span,
                                           arange.row_span)
        for bbox in self.data.bbs:
            collision_info = bbox.check_collision(arange_bbox)

            has_collision = collision_info['has_collision']
            in_bounds = collision_info['nonov_column_span'] + collision_info['nonov_row_span'] == 0
            is_sticky = collision_info['horizontal_gap'] + collision_info['vertical_gap'] == 0

            if (has_collision and not in_bounds) or is_sticky:
                mdfi = self.data.bbs.index(bbox)
                should_expand = True
                break

        if mdfi < 0:
            return False # TODO: do something

        bbox = self.data.bbs[mdfi]

        # Exclude the case where the cell is being inserted below right,
        # it should not expand the target dataframe
        if should_expand and collision_info['direction'] == 'right-below':
            return False

        # Automatically expand the dataframe if needed
        if should_expand and 'below' in collision_info['direction']:
            self.insert_blank_from_current_rows(above=False,
                                                row_span=collision_info['nonov_row_span'],
                                                on_border=True,
                                                dfi=mdfi)

        if should_expand and 'right' in collision_info['direction']:
            self.insert_blank_from_current_columns(left=False,
                                                   column_span=collision_info['nonov_column_span'],
                                                   on_border=True,
                                                   dfi=mdfi)

        if should_expand and 'left' in collision_info['direction']:
            self.insert_blank_from_current_columns(left=True,
                                                   column_span=collision_info['nonov_column_span'],
                                                   on_border=True,
                                                   dfi=mdfi)

        # Restore the selection range
        if should_expand:
            self.update_selection_from_position(active.column,
                                                active.row,
                                                cursor.column,
                                                cursor.row,
                                                keep_order=True,
                                                follow_cursor=True,
                                                auto_scroll=True)
            arange = self.selection.current_active_range

        mcolumn = arange.metadata.column
        mrow = arange.metadata.row
        column_span = arange.column_span
        row_span = arange.row_span

        if arange.column_span < 0:
            column_span = bbox.column_span + 1

        if arange.row_span < 0:
            row_span = bbox.row_span + 2

        column_span = self.get_logical_column_span(column_span)
        row_span = self.get_logical_row_span(row_span)

        if arange.column_span < 0:
            column_span -= 1

        if arange.row_span < 0:
            row_span -= 3

        if arange.rtl:
            mcolumn = mcolumn - column_span + 1

        if arange.btt:
            mrow = mrow - row_span + 1

        # By now header is always in the first row
        include_header = mrow == 0

        # Prepare for snapshot
        if not globals.is_changing_state:
            from .history_manager import UpdateDataState
            content = self.data.read_cell_data_block_from_metadata(mcolumn,
                                                                   mrow,
                                                                   column_span,
                                                                   row_span,
                                                                   mdfi,
                                                                   include_header)
            state = UpdateDataState(mcolumn,
                                    mrow,
                                    column_span,
                                    row_span,
                                    mdfi,
                                    content,
                                    new_value,
                                    include_header)

        # Update data
        # TODO: we still miss to tell the user when the update isn't successful.
        # Looking at other applications, it should always commit the update,
        # but make the cells appear in some way e.g. "######" whenever there's
        # an error or something that the user should do in response.
        if self.data.update_cell_data_block_with_single_from_metadata(mcolumn,
                                                                      mrow,
                                                                      column_span,
                                                                      row_span,
                                                                      mdfi,
                                                                      include_header,
                                                                      new_value,
                                                                      self.display.column_visible_series,
                                                                      self.display.row_visible_series):
            # Save snapshot
            if not globals.is_changing_state:
                globals.history.save(state)

            if self.is_cutting_cells:
                self.cancel_cutcopy_operation()

            # TODO: clear only for the related columns
            self.data.clear_cell_data_unique_cache(0)

            self.renderer.render_caches = {}
            self.view.main_canvas.queue_draw()

            active_cell = self.selection.current_active_cell
            self.notify_selection_changed(active_cell.column, active_cell.row, active_cell.metadata)

            return True

        return False

    def update_current_cells_from_datatable(self, datatable: polars.DataFrame = None) -> bool:
        if datatable is None:
            if self.clipboard is None:
                return False
            datatable = self.clipboard.datatable
            crange = self.clipboard.crange

        # Create a dummy crange
        else:
            from .sheet_data import SheetCellMetadata
            from .sheet_selection import SheetCell
            column_span = datatable.width
            row_span = datatable.height
            metadata = SheetCellMetadata(-1, -1, -1)
            crange = SheetCell(-1, -1, -1, -1, -1, -1,
                               column_span, row_span,
                               metadata)

        arange = self.selection.current_active_range
        active = self.selection.current_active_cell
        cursor = self.selection.current_cursor_cell

        mdfi = arange.metadata.dfi

        should_expand = False
        collision_info = {}

        # Check bounding box collision
        from .sheet_data import SheetCellBoundingBox
        arange_bbox = SheetCellBoundingBox(arange.column,
                                           arange.row,
                                           crange.column_span,
                                           crange.row_span)
        for bbox in self.data.bbs:
            collision_info = bbox.check_collision(arange_bbox)

            has_collision = collision_info['has_collision']
            in_bounds = collision_info['nonov_column_span'] + collision_info['nonov_row_span'] == 0
            is_sticky = collision_info['horizontal_gap'] + collision_info['vertical_gap'] == 0

            if (has_collision and not in_bounds) or is_sticky:
                mdfi = self.data.bbs.index(bbox)
                should_expand = True
                break

        if mdfi < 0:
            return False # TODO: do something

        if 'nonov_column_span' in collision_info and collision_info['nonov_column_span'] == -1:
            collision_info['nonov_column_span'] = arange.column - 1
            collision_info['direction'] = collision_info['direction'].replace('above', '') \
                                                                     .replace('below', '') \
                                                                     .replace('left', 'right')

        if 'nonov_row_span' in collision_info and collision_info['nonov_row_span'] == -1:
            collision_info['nonov_row_span'] = arange.row - 1
            collision_info['direction'] = collision_info['direction'].replace('left', '') \
                                                                     .replace('right', '') \
                                                                     .replace('above', 'below')

        bbox = self.data.bbs[mdfi]

        # Exclude the case where the cell is being inserted below right,
        # it should not expand the target dataframe
        if should_expand and collision_info['direction'] == 'right-below':
            return False

        self.is_expanding_cells = True

        # Automatically expand the dataframe if needed
        if should_expand and 'below' in collision_info['direction']:
            self.insert_blank_from_current_rows(above=False,
                                                row_span=collision_info['nonov_row_span'],
                                                on_border=True,
                                                dfi=mdfi)

        if should_expand and 'right' in collision_info['direction']:
            self.insert_blank_from_current_columns(left=False,
                                                   column_span=collision_info['nonov_column_span'],
                                                   on_border=True,
                                                   dfi=mdfi)

        if should_expand and 'left' in collision_info['direction']:
            self.insert_blank_from_current_columns(left=True,
                                                   column_span=collision_info['nonov_column_span'],
                                                   on_border=True,
                                                   dfi=mdfi)

        self.is_expanding_cells = False

        # Restore the selection range
        if should_expand:
            self.update_selection_from_position(active.column,
                                                active.row,
                                                cursor.column,
                                                cursor.row,
                                                keep_order=True,
                                                follow_cursor=True,
                                                auto_scroll=True)
            arange = self.selection.current_active_range

        mcolumn = arange.metadata.column
        mrow = arange.metadata.row
        column_span = crange.column_span
        row_span = crange.row_span

        if arange.column_span < 0:
            column_span = bbox.column_span + 1

        if arange.row_span < 0:
            row_span = bbox.row_span + 2

        column_span = self.get_logical_column_span(column_span)
        row_span = self.get_logical_row_span(row_span)

        if arange.column_span < 0:
            column_span -= 1

        if arange.row_span < 0:
            row_span -= 3

        if arange.rtl:
            mcolumn = mcolumn - column_span + 1

        if arange.btt:
            mrow = mrow - row_span + 1

        # By now header is always in the first row
        include_header = mrow == 0

        # Prepare for snapshot
        if not globals.is_changing_state:
            from .history_manager import UpdateDataFromDataTableState
            content = self.data.read_cell_data_block_from_metadata(mcolumn,
                                                                   mrow,
                                                                   column_span,
                                                                   row_span,
                                                                   mdfi,
                                                                   include_header)
            state = UpdateDataFromDataTableState(mcolumn,
                                                 mrow,
                                                 column_span,
                                                 row_span,
                                                 mdfi,
                                                 include_header,
                                                 content,   # before
                                                 datatable) # after

        # Move the first row to the header row
        if include_header:
            first_row = datatable[0].cast(polars.String).row(0)
            for column_index, column_name in enumerate(datatable.columns):
                datatable = datatable.rename({column_name: first_row[column_index]})
            datatable = datatable[1:]

        # Update data
        if self.data.update_cell_data_block_from_metadata(mcolumn,
                                                          mrow,
                                                          crange.column_span,
                                                          crange.row_span,
                                                          mdfi,
                                                          include_header,
                                                          datatable,
                                                          self.display.column_visible_series,
                                                          self.display.row_visible_series):
            from .sheet_selection import SheetLocatorCell

            # Update selection to fit the size of the dataframe being updated
            if not isinstance(crange, SheetLocatorCell):
                self.update_selection_from_position(arange.column,
                                                    arange.row,
                                                    arange.column + crange.column_span - 1,
                                                    arange.row + crange.row_span - 1,
                                                    keep_order=True,
                                                    follow_cursor=False,
                                                    auto_scroll=False)

            # Save snapshot
            if not globals.is_changing_state:
                state.save_selection(True)
                globals.history.save(state)

            if self.is_cutting_cells:
                self.cancel_cutcopy_operation()

            # TODO: clear only for the related columns
            self.data.clear_cell_data_unique_cache(0)

            self.renderer.render_caches = {}
            self.view.main_canvas.queue_draw()

            active = self.selection.current_active_cell
            self.notify_selection_changed(active.column, active.row, active.metadata)

            return True

        return False

    def duplicate_from_current_rows(self, above: bool = False) -> bool:
        self.try_to_select_entire_content_rows()
        arange = self.selection.current_active_range

        mdfi = arange.metadata.dfi
        mrow = arange.metadata.row

        row_span = self.get_logical_row_span()

        if arange.btt:
            mrow = mrow - row_span + 1

        # Prepare for snapshot
        if not globals.is_changing_state:
            from .history_manager import DuplicateRowState
            state = DuplicateRowState(row_span, above)

        if self.data.duplicate_rows_from_metadata(mrow, row_span, arange.metadata.dfi):
            # Save snapshot
            if not globals.is_changing_state:
                globals.history.save(state)

            if not above:
                mrow += row_span

            # Update row visibility flags
            if len(self.display.row_visibility_flags):
                self.display.row_visibility_flags = polars.concat([self.display.row_visibility_flags[:mrow],
                                                                   polars.Series([True] * row_span),
                                                                   self.display.row_visibility_flags[mrow:]])
                self.display.row_visible_series = self.display.row_visibility_flags.arg_true()
                self.data.bbs[mdfi].row_span = len(self.display.row_visible_series)
            else:
                self.data.bbs[mdfi].row_span = self.data.dfs[mdfi].height + 1

            srow = mrow

            if not above:
                srow -= row_span

            # Update row heights
            if len(self.display.row_heights):
                self.display.row_heights = polars.concat([self.display.row_heights[:mrow],
                                                          self.display.row_heights[srow:srow + row_span],
                                                          self.display.row_heights[mrow:]])
                row_heights_visible_only = self.display.row_heights
                if len(self.display.row_visibility_flags):
                    row_heights_visible_only = row_heights_visible_only.filter(self.display.row_visibility_flags)
                self.display.cumulative_row_heights = polars.Series('crheights', row_heights_visible_only).cum_sum()

            self.cancel_cutcopy_operation()
            self.auto_adjust_selections_by_crud(0, 0 if not above else row_span, False)

            # TODO: clear only for the related columns
            self.data.clear_cell_data_unique_cache(0)

            self.renderer.render_caches = {}
            self.view.main_canvas.queue_draw()

            return True

        return False

    def duplicate_from_current_columns(self, left: bool = False) -> bool:
        self.try_to_select_entire_content_columns()
        arange = self.selection.current_active_range

        mdfi = arange.metadata.dfi
        mcolumn = arange.metadata.column

        column_span = self.get_logical_column_span()

        if arange.rtl:
            mcolumn = mcolumn - column_span + 1

        # Prepare for snapshot
        if not globals.is_changing_state:
            from .history_manager import DuplicateColumnState
            state = DuplicateColumnState(column_span, left)

        if self.data.duplicate_columns_from_metadata(mcolumn, column_span, mdfi, left):
            # Save snapshot
            if not globals.is_changing_state:
                globals.history.save(state)

            if not left:
                mcolumn += column_span

            # Update column visibility flags
            if len(self.display.column_visibility_flags):
                self.display.column_visibility_flags = polars.concat([self.display.column_visibility_flags[:mcolumn],
                                                                      polars.Series([True] * column_span),
                                                                      self.display.column_visibility_flags[mcolumn:]])
                self.display.column_visible_series = self.display.column_visibility_flags.arg_true()
                self.data.bbs[mdfi].column_span = len(self.display.column_visible_series)

            scolumn = mcolumn

            if not left:
                scolumn -= column_span

            # Update column widths
            if len(self.display.column_widths):
                self.display.column_widths = polars.concat([self.display.column_widths[:mcolumn],
                                                            self.display.column_widths[scolumn:scolumn + column_span],
                                                            self.display.column_widths[mcolumn:]])
                column_widths_visible_only = self.display.column_widths
                if len(self.display.column_visibility_flags):
                    column_widths_visible_only = column_widths_visible_only.filter(self.display.column_visibility_flags)
                self.display.cumulative_column_widths = polars.Series('ccwidths', column_widths_visible_only).cum_sum()

            self.cancel_cutcopy_operation()
            self.auto_adjust_selections_by_crud(0 if not left else column_span, 0, False)
            self.repopulate_auto_filter_widgets()

            # TODO: clear only for the related columns
            self.data.clear_cell_data_unique_cache(0)

            self.renderer.render_caches = {}
            self.view.main_canvas.queue_draw()

            self.emit('columns-changed', mdfi)

            return True

        return False

    def delete_current_rows(self,
                            above:     bool = False,
                            row_span:  int = -1,
                            on_border: bool = False,
                            dfi:       int = -1) -> bool:
        self.try_to_select_entire_content_rows()
        arange = self.selection.current_active_range

        mdfi = arange.metadata.dfi
        mrow = arange.metadata.row

        row_span = self.get_logical_row_span()

        if arange.btt:
            mrow = mrow - row_span + 1

        # Prepare for snapshot
        if not globals.is_changing_state:
            from .history_manager import DeleteRowState
            column_count = self.data.dfs[mdfi].width
            state = DeleteRowState(self.data.read_cell_data_block_from_metadata(0, mrow, column_count, row_span, mdfi),
                                   self.display.row_visibility_flags[mrow:mrow + row_span] if len(self.display.row_visibility_flags)
                                                                                           else None,
                                   self.display.row_heights[mrow:mrow + row_span] if len(self.display.row_heights)
                                                                                  else None)

        if self.data.delete_rows_from_metadata(mrow, row_span, mdfi):
            # Save snapshot
            if not globals.is_changing_state:
                globals.history.save(state)

            # Update row visibility flags
            if len(self.display.row_visibility_flags):
                self.display.row_visibility_flags = polars.concat([self.display.row_visibility_flags[:mrow],
                                                                   self.display.row_visibility_flags[mrow + row_span:]])
                self.display.row_visible_series = self.display.row_visibility_flags.arg_true()
                self.data.bbs[mdfi].row_span = len(self.display.row_visible_series)
            else:
                self.data.bbs[mdfi].row_span = self.data.dfs[mdfi].height + 1

            # Update row heights
            if len(self.display.row_heights):
                self.display.row_heights = polars.concat([self.display.row_heights[:mrow],
                                                          self.display.row_heights[mrow + row_span:]])
                row_heights_visible_only = self.display.row_heights
                if len(self.display.row_visibility_flags):
                    row_heights_visible_only = row_heights_visible_only.filter(self.display.row_visibility_flags)
                self.display.cumulative_row_heights = polars.Series('crheights', row_heights_visible_only).cum_sum()

            self.cancel_cutcopy_operation()
            self.auto_adjust_selections_by_crud(0, 0, True)

            # TODO: clear only for the related columns
            self.data.clear_cell_data_unique_cache(0)

            self.renderer.render_caches = {}
            self.view.main_canvas.queue_draw()

            return True

        return False

    def delete_current_columns(self,
                               left:        bool = False,
                               column_span: int = -1,
                               on_border:   bool = False,
                               dfi:         int = -1) -> bool:
        self.try_to_select_entire_content_columns()
        arange = self.selection.current_active_range

        mdfi = arange.metadata.dfi
        mcolumn = arange.metadata.column

        if dfi > -1:
            mdfi = dfi

        # Simulate the cursor's movement to the edge of the dataframe
        if on_border:
            mcolumn = self.data.bbs[mdfi].column - 1

            if not left:
                mcolumn += self.data.dfs[mdfi].width - column_span

        else:
            column_span = self.get_logical_column_span()

            if arange.rtl:
                mcolumn = mcolumn - column_span + 1

        # Prepare for snapshot
        if not globals.is_changing_state:
            from .history_manager import DeleteColumnState
            row_count = self.data.dfs[mdfi].height - 1
            state = DeleteColumnState(self.data.read_cell_data_block_from_metadata(mcolumn, 1, column_span, row_count, mdfi),
                                      self.display.column_visibility_flags[mcolumn:mcolumn + column_span] if len(self.display.column_visibility_flags)
                                                                                                          else None,
                                      self.display.column_widths[mcolumn:mcolumn + column_span] if len(self.display.column_widths)
                                                                                                else None)

        if self.data.delete_columns_from_metadata(mcolumn, column_span, mdfi):
            # Save snapshot
            if not globals.is_changing_state:
                globals.history.save(state)

            # Update column visibility flags
            if len(self.display.column_visibility_flags):
                self.display.column_visibility_flags = polars.concat([self.display.column_visibility_flags[:mcolumn],
                                                                      self.display.column_visibility_flags[mcolumn + column_span:]])
                self.display.column_visible_series = self.display.column_visibility_flags.arg_true()
                self.data.bbs[mdfi].column_span = len(self.display.column_visible_series)
            else:
                self.data.bbs[mdfi].column_span = self.data.dfs[mdfi].width

            # Update column widths
            if len(self.display.column_widths):
                self.display.column_widths = polars.concat([self.display.column_widths[:mcolumn],
                                                            self.display.column_widths[mcolumn + column_span:]])
                column_widths_visible_only = self.display.column_widths
                if len(self.display.column_visibility_flags):
                    column_widths_visible_only = column_widths_visible_only.filter(self.display.column_visibility_flags)
                self.display.cumulative_column_widths = polars.Series('ccwidths', column_widths_visible_only).cum_sum()

            self.cancel_cutcopy_operation()
            self.auto_adjust_selections_by_crud(0, 0, True)
            self.repopulate_auto_filter_widgets()

            # TODO: clear only for the related columns
            self.data.clear_cell_data_unique_cache(0)

            self.renderer.render_caches = {}
            self.view.main_canvas.queue_draw()

            if not self.is_refreshing_uis:
                # FIXME: remove incompatible filters?
                self.emit('columns-changed', mdfi)

            return True

        return False

    def hide_current_columns(self) -> None:
        arange = self.selection.current_active_range

        mcolumn = arange.metadata.column
        column_span = arange.column_span

        mdfi = arange.metadata.dfi
        bbox = self.data.bbs[mdfi]

        if arange.column_span < 0:
            column_span = bbox.column_span + 1

        column_span = self.get_logical_column_span(column_span)

        if arange.column_span < 0:
            column_span -= 1

        if arange.rtl:
            mcolumn = mcolumn - column_span + 1

        # Save snapshot
        if not globals.is_changing_state:
            from .history_manager import HideColumnState
            state = HideColumnState()
            globals.history.save(state)

        # Update column visibility flags
        if len(self.display.column_visibility_flags):
            self.display.column_visibility_flags = polars.concat([self.display.column_visibility_flags[:mcolumn],
                                                                  polars.Series([False] * column_span),
                                                                  self.display.column_visibility_flags[mcolumn + column_span:]])
        else:
            rcolumn = self.data.bbs[arange.metadata.dfi].column_span - mcolumn - column_span
            self.display.column_visibility_flags = polars.concat([polars.Series([True] * mcolumn, dtype=polars.Boolean),
                                                                  polars.Series([False] * column_span),
                                                                  polars.Series([True] * rcolumn, dtype=polars.Boolean)])
        self.display.column_visible_series = self.display.column_visibility_flags.arg_true()
        self.data.bbs[arange.metadata.dfi].column_span = len(self.display.column_visible_series)

        # Update column widths
        if len(self.display.column_widths):
            column_widths_visible_only = self.display.column_widths
            if len(self.display.column_visibility_flags):
                column_widths_visible_only = column_widths_visible_only.filter(self.display.column_visibility_flags)
            self.display.cumulative_column_widths = polars.Series('ccwidths', column_widths_visible_only).cum_sum()

        self.auto_adjust_selections_by_crud(0, 0, True)
        self.repopulate_auto_filter_widgets()
        self.renderer.render_caches = {}
        self.view.main_canvas.queue_draw()

        self.emit('columns-changed', arange.metadata.dfi)

    def unhide_current_columns(self) -> None:
        arange = self.selection.current_active_range

        mcolumn = arange.metadata.column
        column_span = arange.column_span

        mdfi = arange.metadata.dfi
        bbox = self.data.bbs[mdfi]

        if arange.column_span < 0:
            column_span = bbox.column_span + 1

        column_span = self.get_logical_column_span(column_span)

        if arange.column_span < 0:
            column_span -= 1

        if arange.rtl:
            mcolumn = mcolumn - column_span + 1

        # Save snapshot
        if not globals.is_changing_state:
            from .history_manager import UnhideColumnState
            state = UnhideColumnState(column_span,
                                      self.display.column_visibility_flags[mcolumn:mcolumn + column_span])
            globals.history.save(state)

        # Update column visibility flags
        self.display.column_visibility_flags = polars.concat([self.display.column_visibility_flags[:mcolumn],
                                                              polars.Series([True] * column_span),
                                                              self.display.column_visibility_flags[mcolumn + column_span:]])
        self.display.column_visible_series = self.display.column_visibility_flags.arg_true()
        self.data.bbs[arange.metadata.dfi].column_span = len(self.display.column_visible_series)

        # Update column widths
        if len(self.display.column_widths):
            column_widths_visible_only = self.display.column_widths
            if len(self.display.column_visibility_flags):
                column_widths_visible_only = column_widths_visible_only.filter(self.display.column_visibility_flags)
            self.display.cumulative_column_widths = polars.Series('ccwidths', column_widths_visible_only).cum_sum()

        self.auto_adjust_selections_by_crud(0, 0, False)
        self.repopulate_auto_filter_widgets()
        self.renderer.render_caches = {}
        self.view.main_canvas.queue_draw()

        self.emit('columns-changed', arange.metadata.dfi)

    def unhide_all_columns(self) -> None:
        arange = self.selection.current_active_range

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
            column_widths_visible_only = self.display.column_widths
            if len(self.display.column_visibility_flags):
                column_widths_visible_only = column_widths_visible_only.filter(self.display.column_visibility_flags)
            self.display.cumulative_column_widths = polars.Series('ccwidths', column_widths_visible_only).cum_sum()

        self.auto_adjust_selections_by_crud(0, 0, False)
        self.repopulate_auto_filter_widgets()
        self.renderer.render_caches = {}
        self.view.main_canvas.queue_draw()

        self.emit('columns-changed', arange.metadata.dfi)

    def filter_current_rows(self,
                            multiple: bool = False,
                            inverse:  bool = False) -> None:
        active = self.selection.current_active_cell

        metadata = active.metadata
        mcolumn = active.metadata.column
        mdfi = active.metadata.dfi

        if mdfi < 0 or len(self.data.dfs) <= mdfi:
            return False

        # Build pending filters from a single value
        if not multiple:
            column_name = self.data.dfs[mdfi].columns[mcolumn]
            column_index = self.data.dfs[mdfi].columns.index(column_name)
            column_dtype = self.data.dfs[mdfi].schema[column_name]

            cell_value = self.data.read_single_cell_data_from_metadata(mcolumn, metadata.row, mdfi)

            operator = '=' if not inverse else '!='
            expression = polars.col(column_name).eq(cell_value)
            expression = expression.not_() if inverse else expression

            # TODO: create a new class?
            self.pending_filters = [{
                'qhash': hash((column_name, 'single')),
                'qtype': 'primitive',
                'operator': 'and',
                'query-builder': {
                    'operator': 'and',
                    'conditions': [{
                        'findex': column_index,
                        'fdtype': column_dtype,
                        'field': column_name,
                        'operator': operator,
                        'value': cell_value,
                    }],
                },
                'expression': expression,
            }]

        # Save snapshot
        if not globals.is_changing_state:
            from .history_manager import FilterRowState
            globals.history.save(FilterRowState(self.display.row_visibility_flags if len(self.display.row_visibility_flags)
                                                                                  else None,
                                                self.display.row_heights if len(self.display.row_heights)
                                                                         else None,
                                                multiple, inverse,
                                                copy.deepcopy(self.current_filters),
                                                copy.deepcopy(self.pending_filters)))

        # Prepare for updating the current filters
        pindex = 0
        while pindex < len(self.pending_filters):
            pfilter = self.pending_filters[pindex]

            if pfilter['qhash'] is None:
                pindex += 1
                continue # skip duplicable filters

            # Check for duplicates
            for cfilter in self.current_filters:
                if cfilter['qhash'] == pfilter['qhash']:
                    self.current_filters.remove(cfilter)
                    break

            # Remove empty not-in filters, usually comes from selecting
            # all unique values for the target column
            if pfilter['qtype'] == 'primitive':
                condition = pfilter['query-builder']['conditions'][0]
                if condition['operator'] == 'not in' and len(condition['value']) == 0:
                    self.pending_filters.remove(pfilter)
                    pindex += 1
                    continue

            pindex += 1

        # Update current filters
        self.current_filters += self.pending_filters
        self.pending_filters = []

        # Update row visibility flags
        self.display.row_visibility_flags = self.data.filter_rows_from_metadata(self.current_filters, mdfi)
        self.display.row_visible_series = self.display.row_visibility_flags.arg_true()
        self.data.bbs[mdfi].row_span = len(self.display.row_visible_series)

        # Update row heights
        if len(self.display.row_heights):
            row_heights_visible_only = self.display.row_heights.filter(self.display.row_visibility_flags)
            self.display.cumulative_row_heights = polars.Series('crheights', row_heights_visible_only).cum_sum()

        self.cancel_cutcopy_operation()
        self.auto_adjust_locators_size_by_scroll()
        self.auto_adjust_selections_by_crud(0, 0, True)
        self.repopulate_auto_filter_widgets()

        active = self.selection.current_active_cell
        mdfi = active.metadata.dfi

        # Automatically adjust when the cursor is outside the current dataframe bounding box
        if mdfi < 0:
            row = self.display.row_visible_series[-1] + 1
            cell_name = self.display.get_cell_name_from_position(active.column, row)
            self.update_selection_from_name(cell_name)

        self.renderer.render_caches = {}
        self.view.main_canvas.queue_draw()

        if not self.is_refreshing_uis:
            self.emit('filters-changed', mdfi)

    def reset_all_filters(self) -> None:
        # Save snapshot
        if not globals.is_changing_state:
            from .history_manager import ResetFilterRowState
            globals.history.save(ResetFilterRowState(self.display.row_visibility_flags if len(self.display.row_visibility_flags)
                                                                                       else None,
                                                     self.display.row_heights if len(self.display.row_heights)
                                                                              else None,
                                                     copy.deepcopy(self.current_filters)))

        # Update current filters
        self.current_filters = []
        self.pending_filters = []

        # Update row visibility flags
        # TODO: support multiple dataframes?
        self.display.row_visibility_flags = polars.Series(dtype=polars.Boolean)
        self.display.row_visible_series = polars.Series(dtype=polars.UInt32)
        self.data.bbs[0].row_span = self.data.dfs[0].height + 1

        # Update row heights
        if len(self.display.row_heights):
            self.display.cumulative_row_heights = polars.Series('crheights', self.display.row_heights).cum_sum()

        self.cancel_cutcopy_operation()
        self.auto_adjust_selections_by_crud(0, 0, True)
        self.renderer.render_caches = {}
        self.view.main_canvas.queue_draw()

        if not self.is_refreshing_uis:
            self.emit('filters-changed', 0)

    def sort_current_rows(self,
                          descending: bool = False,
                          multiple:   bool = False) -> None:
        active = self.selection.current_active_cell
        mdfi = active.metadata.dfi
        mcolumn = active.metadata.column

        if mdfi < 0 or len(self.data.dfs) <= mdfi:
            return

        # FIXME: this approach will also sort hidden rows which is different from other applications,
        # I haven't made up my mind yet if we should follow other applications behavior, because I think
        # it'll be too expensive.
        self.data.dfs[mdfi] = self.data.dfs[mdfi].with_row_index('$ridx')
        if len(self.display.row_visibility_flags):
            self.data.dfs[mdfi] = self.data.dfs[mdfi].with_columns(self.display.row_visibility_flags[1:].alias('$vrow'))
        mcolumn += 1

        # Prepare for snapshot
        if not globals.is_changing_state:
            csorts = copy.deepcopy(self.current_sorts)
            psorts = copy.deepcopy(self.pending_sorts)

        # Update current filters
        if multiple:
            self.current_sorts = self.pending_sorts
        else:
            column_name = self.data.dfs[mdfi].columns[mcolumn]
            self.current_sorts = {column_name: {'descending': descending}}
        self.pending_sorts = {}

        # Sorting is expensive; we can see double in memory usage. Anything we can do? I think, no :(
        self.data.sort_rows_from_metadata(self.current_sorts, mdfi)

        # Save snapshot
        if not globals.is_changing_state:
            from .history_manager import SortRowState
            globals.history.save(SortRowState(self.data.dfs[mdfi]['$ridx'],
                                              self.display.row_visibility_flags if len(self.display.row_visibility_flags) else None,
                                              mdfi, descending, multiple,
                                              csorts, psorts))

        # Update row visibility flags
        if len(self.display.row_visibility_flags):
            self.display.row_visibility_flags = polars.concat([polars.Series([True]), self.data.dfs[mdfi]['$vrow']])
            self.display.row_visible_series = self.display.row_visibility_flags.arg_true()

        # Update row heights
        if len(self.display.row_heights):
            row_header_height = self.display.row_heights[0]
            sorted_row_heights = polars.DataFrame({'rheights': self.display.row_heights[1:],
                                                   '$ridx': self.data.dfs[mdfi]['$ridx']}).sort('$ridx').to_series()
            self.display.row_heights = polars.concat([polars.Series([row_header_height]), sorted_row_heights])
            row_heights_visible_only = self.display.row_heights
            if len(self.display.row_visibility_flags):
                row_heights_visible_only = row_heights_visible_only.filter(self.display.row_visibility_flags)
            self.display.cumulative_row_heights = polars.Series('crheights', row_heights_visible_only).cum_sum()

        # Clean up the temporary helper columns
        self.data.dfs[mdfi].drop_in_place('$ridx')
        if len(self.display.row_visibility_flags):
            self.data.dfs[mdfi].drop_in_place('$vrow')

        self.cancel_cutcopy_operation()
        self.auto_adjust_selections_by_crud(0, 0, True)
        self.renderer.render_caches = {}
        self.view.main_canvas.queue_draw()

        if not self.is_refreshing_uis:
            self.emit('sorts-changed', mdfi)

    def reorder_current_columns(self, columns: list[str]) -> None:
        arange = self.selection.current_active_range
        mdfi = arange.metadata.dfi

        old_columns = self.data.dfs[mdfi].columns

        self.data.reorder_columns_from_metadata(columns, mdfi)

        new_columns = self.data.dfs[mdfi].columns

        # Save snapshot
        if not globals.is_changing_state:
            from .history_manager import ReorderColumnState
            globals.history.save(ReorderColumnState(old_columns, new_columns))

        new_column_indices = [old_columns.index(column) for column in new_columns]
        new_column_indices = polars.Series(new_column_indices)

        # Update column visibility flags
        if len(self.display.column_visibility_flags):
            # With the assumption that there's only one dataframe. Now let's flag it
            # as a TODO in case we want to support multiple dataframes in the future.
            self.display.column_visibility_flags = self.display.column_visibility_flags.gather(new_column_indices)
            self.display.column_visible_series = self.display.column_visibility_flags.arg_true()

        # Update column widths
        if len(self.display.column_widths):
            self.display.column_widths = self.display.column_widths.gather(new_column_indices)
            column_widths_visible_only = self.display.column_widths
            if len(self.display.column_visibility_flags):
                column_widths_visible_only = column_widths_visible_only.filter(self.display.column_visibility_flags)
            self.display.cumulative_column_widths = polars.Series('ccwidths', column_widths_visible_only).cum_sum()

        self.auto_adjust_selections_by_crud(0, 0, False)
        self.repopulate_auto_filter_widgets()

        # TODO: clear only for the related columns
        self.data.clear_cell_data_unique_cache(0)

        self.renderer.render_caches = {}
        self.view.main_canvas.queue_draw()

        if globals.is_changing_state:
            self.emit('columns-changed', mdfi)

    def convert_current_columns_dtype(self, dtype: polars.DataType) -> bool:
        arange = self.selection.current_active_range
        column_span = arange.column_span
        metadata = arange.metadata

        mdfi = arange.metadata.dfi
        bbox = self.data.bbs[mdfi]

        if arange.column_span < 0:
            column_span = bbox.column_span + 1

        column_span = self.get_logical_column_span(column_span)

        if arange.column_span < 0:
            column_span -= 1

        # Prepare for snapshot
        if not globals.is_changing_state:
            from .history_manager import ConvertColumnDataTypeState
            # FIXME: this doesn't handle different data types well when multiple columns are selected,
            #        even though usually they are the same. Should we disable multiple selection?
            ndtype = self.data.read_column_dtype_from_metadata(metadata.column, metadata.dfi)
            state = ConvertColumnDataTypeState(ndtype, dtype)

        # FIXME: datetime to string conversion doesn't recover the original content.
        # Maybe for numerical and temporal data, we should store the entire content? Or just the string format?
        if self.data.convert_columns_dtype_from_metadata(metadata.column, column_span, metadata.dfi, dtype):
            # Save snapshot
            if not globals.is_changing_state:
                globals.history.save(state)

            self.auto_adjust_selections_by_crud(0, 0, True)

            # TODO: clear only for the related columns
            self.data.clear_cell_data_unique_cache(0)

            self.renderer.render_caches = {}
            self.view.main_canvas.queue_draw()

            if not self.is_refreshing_uis:
                # FIXME: should we remove incompatible filters?
                self.emit('columns-changed', metadata.dfi)
                self.emit('filters-changed', metadata.dfi)

            return True

        return False

    def materialize_view(self) -> None:
        if len(self.data.dfs) == 0:
            return

        if not self.data.has_main_dataframe:
            return

        # Collect hidden column names
        visible_column_names = []
        for col_index, is_visible in enumerate(self.display.column_visibility_flags):
            if is_visible:
                visible_column_names.append(self.data.dfs[0].columns[col_index])
        if len(self.display.column_visibility_flags) == 0:
            visible_column_names = self.data.dfs[0].columns

        # Discard all dataframes
        if len(visible_column_names) == 0:
            self.data.bbs = []
            self.data.dfs = []
            return

        # Discards all dataframes but the main one
        self.data.materialize_view(self.current_filters, visible_column_names)

        # Update column widths and visibility flags
        if len(self.display.column_visibility_flags):
            if len(self.display.column_widths):
                self.display.column_widths = self.display.column_widths.filter(self.display.column_visibility_flags)
            self.display.column_visibility_flags = polars.Series(dtype=polars.Boolean)
            self.display.column_visible_series = polars.Series(dtype=polars.UInt32)

        # Update row heights and visibility flags
        if len(self.display.row_visibility_flags):
            if len(self.display.row_heights):
                self.display.row_heights = self.display.row_heights.filter(self.display.row_visibility_flags)
            self.display.row_visibility_flags = polars.Series(dtype=polars.Boolean)
            self.display.row_visible_series = polars.Series(dtype=polars.UInt32)

        self.auto_adjust_selections_by_crud(0, 0, False)
        self.repopulate_auto_filter_widgets()

        self.renderer.render_caches = {}
        self.view.main_canvas.queue_draw()

        # Reset these as they're no longer relevant
        self.current_sorts = []
        self.current_filters = []

    def rechunk_table(self) -> None:
        # TODO: support multiple dataframes?
        if not self.data.has_main_dataframe:
            return
        self.data.dfs[0] = self.data.dfs[0].rechunk()

    def find_in_current_cells(self,
                              text_value:       str,
                              match_case:       bool,
                              match_cell:       bool,
                              within_selection: bool,
                              use_regexp:       bool) -> int:
        # Prepare the search expression
        filter_expression = polars.col(polars.String).str.contains_any([text_value], ascii_case_insensitive=not match_case)
        if match_cell:
            filter_expression = polars.col(polars.String).str.to_lowercase() == text_value.lower()
            if match_case:
                filter_expression = polars.col(polars.String).str == text_value
        if use_regexp:
            filter_expression = polars.col(polars.String).str.contains(f'(?i){text_value}')
            if match_case:
                filter_expression = polars.col(polars.String).str.contains(text_value)

        if text_value in ['', None]:
            filter_expression = polars.col(polars.String).is_null()
        else:
            filter_expression &= polars.col(polars.String).is_not_null()

        # Collect hidden column names
        hidden_column_names = []
        for col_index, is_visible in enumerate(self.display.column_visibility_flags):
            if not is_visible:
                hidden_column_names.append(self.data.dfs[0].columns[col_index])

        # TODO: support non-string columns?
        select_expression = polars.col(polars.String).exclude(hidden_column_names)

        # Collect column names within the selection
        if within_selection:
            arange = self.selection.current_search_range
            column_span = arange.column_span

            mdfi = arange.metadata.dfi
            bbox = self.data.bbs[mdfi]

            if arange.column_span < 0:
                column_span = bbox.column_span + 1

            column_span = self.get_logical_column_span(column_span)

            if arange.column_span < 0:
                column_span -= 1

            selected_column_names = self.data.dfs[0].columns[arange.metadata.column:arange.metadata.column + column_span]

            # Remove non-string column names
            selected_column_names = [name for name in selected_column_names if self.data.dfs[0][name].dtype == polars.String]

            # Reset the select expression
            select_expression = polars.col(selected_column_names).exclude(hidden_column_names)

        has_selected_rows = False

        # Define row range within the selection
        if within_selection:
            arange = self.selection.current_search_range

            start_row = arange.metadata.row - 1
            row_span = arange.row_span

            # Handle edge cases where the user selected the entire column(s),
            # so there's no point to filter by row.
            has_selected_rows = row_span > 0

            # Take hidden row(s) into account
            if has_selected_rows and len(self.display.row_visibility_flags):
                row_span = self.get_logical_row_span()

        selected_rows_expression = (polars.col('$ridx') >= start_row) & (polars.col('$ridx') < start_row + row_span) \
                                   if has_selected_rows else polars.lit(True)

        # -1 because we exclude the header row
        visible_rows_expression = polars.col('$ridx').is_in(self.display.row_visible_series[1:] - 1) \
                                  if len(self.display.row_visible_series) else polars.lit(True)

        # Get search results mask
        # TODO: support multiple dataframes?
        search_results = self.data.dfs[0].select(select_expression) \
                                         .with_columns(filter_expression) \
                                         .with_columns(polars.any_horizontal(polars.all()).alias('$rand')) \
                                         .with_row_index('$ridx') \
                                         .filter(selected_rows_expression & visible_rows_expression) \
                                         .filter(polars.col('$rand') == True) \
                                         .drop('$rand')

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

    def find_replace_in_current_cells(self,
                                      replace_with:   str,
                                      search_pattern: str,
                                      match_case:     bool) -> bool:
        arange = self.selection.current_active_range
        mcolumn = arange.metadata.column
        mrow = arange.metadata.row
        mdfi = arange.metadata.dfi

        # Prepare for snapshot
        if not globals.is_changing_state:
            from .history_manager import FindReplaceDataState
            content = self.data.read_single_cell_data_from_metadata(mcolumn, mrow, mdfi)
            state = FindReplaceDataState(content, replace_with, search_pattern, match_case)

        # Update data
        if self.data.replace_cell_data_by_pattern_from_metadata(mcolumn,
                                                                mrow,
                                                                mdfi,
                                                                replace_with,
                                                                search_pattern,
                                                                match_case):
            # Save snapshot
            if not globals.is_changing_state:
                globals.history.save(state)

            # TODO: clear only for the related columns
            self.data.clear_cell_data_unique_cache(0)

            self.renderer.render_caches = {}
            self.view.main_canvas.queue_draw()

            active_cell = self.selection.current_active_cell
            self.notify_selection_changed(active_cell.column, active_cell.row, active_cell.metadata)

            return True

        return False

    def find_replace_all_in_current_cells(self,
                                          search_pattern:   str,
                                          replace_with:     str,
                                          match_case:       bool,
                                          match_cell:       bool,
                                          within_selection: bool,
                                          use_regexp:       bool) -> None:
        # Collect hidden column names
        hidden_column_names = []
        for col_index, is_visible in enumerate(self.display.column_visibility_flags):
            if not is_visible:
                hidden_column_names.append(self.data.dfs[0].columns[col_index])

        select_expression = polars.col(polars.String).exclude(hidden_column_names)

        # Collect column names within the selection
        if within_selection:
            arange = self.selection.current_search_range
            column_span = arange.column_span

            mdfi = arange.metadata.dfi
            bbox = self.data.bbs[mdfi]

            if arange.column_span < 0:
                column_span = bbox.column_span + 1

            column_span = self.get_logical_column_span(column_span)

            if arange.column_span < 0:
                column_span -= 1

            selected_column_names = self.data.dfs[0].columns[arange.metadata.column:arange.metadata.column + column_span]

            # Remove non-string column names
            selected_column_names = [name for name in selected_column_names if self.data.dfs[0][name].dtype == polars.String]

            # Reset the select expression
            select_expression = polars.col(selected_column_names).exclude(hidden_column_names)

        has_selected_rows = False
        start_row = -1
        row_span = -1

        # Define row range within the selection
        if within_selection:
            arange = self.selection.current_search_range

            start_row = arange.metadata.row - 1
            row_span = arange.row_span

            # Handle edge cases where the user selected the entire column(s),
            # so there's no point to filter by row.
            has_selected_rows = row_span > 0

            # Take hidden row(s) into account
            if has_selected_rows and len(self.display.row_visibility_flags):
                row_span = self.get_logical_row_span()

        target_column_names = self.data.dfs[0].select(select_expression).columns

        selected_rows_expression = (polars.col('$ridx') >= start_row) & (polars.col('$ridx') < start_row + row_span) \
                                   if has_selected_rows else polars.lit(True)

        # -1 because we exclude the header row
        visible_rows_expression = polars.col('$ridx').is_in(self.display.row_visible_series[1:] - 1) \
                                  if len(self.display.row_visible_series) else polars.lit(True)

        with_columns = {}

        # Prepare for the replacement expressions
        nsearch_pattern = search_pattern
        if not use_regexp:
            nsearch_pattern = re.escape(search_pattern)
        if not match_case:
            nsearch_pattern = f'(?i){search_pattern}'

        for column_name in target_column_names:
            if search_pattern in ['', None]:
                filter_expression = polars.col(column_name).is_null()
                with_columns[column_name] = polars.when(filter_expression & selected_rows_expression & visible_rows_expression) \
                                                  .then(polars.col(column_name).fill_null(replace_with)) \
                                                  .otherwise(polars.col(column_name))
                continue

            # Prepare the search expression
            filter_expression = polars.col(column_name).str.contains_any([search_pattern], ascii_case_insensitive=not match_case)
            if match_cell:
                filter_expression = polars.col(column_name).str.to_lowercase() == search_pattern.lower()
                if match_case:
                    filter_expression = polars.col(column_name).str == search_pattern
            if use_regexp:
                filter_expression = polars.col(column_name).str.contains(f'(?i){search_pattern}')
                if match_case:
                    filter_expression = polars.col(column_name).str.contains(search_pattern)

            with_columns[column_name] = polars.when(filter_expression & selected_rows_expression & visible_rows_expression) \
                                              .then(polars.col(column_name).str.replace_all(nsearch_pattern, replace_with)) \
                                              .otherwise(polars.col(column_name))

        # Save snapshot
        # TODO: support multiple dataframes?
        if not globals.is_changing_state:
            from .history_manager import FindReplaceAllDataState
            globals.history.save(FindReplaceAllDataState(self.data.read_cell_data_chunks_from_metadata(target_column_names, start_row, row_span, 0),
                                                         target_column_names,
                                                         start_row,
                                                         row_span,
                                                         0,
                                                         search_pattern,
                                                         replace_with,
                                                         match_case,
                                                         match_cell,
                                                         within_selection,
                                                         use_regexp))

        # Bulk replace cells
        self.data.dfs[0] = self.data.dfs[0].with_row_index('$ridx') \
                                           .with_columns(**with_columns) \
                                           .drop('$ridx')

        # TODO: clear only for the related columns
        self.data.clear_cell_data_unique_cache(0)

        self.renderer.render_caches = {}
        self.view.main_canvas.queue_draw()

        active_cell = self.selection.current_active_cell
        self.notify_selection_changed(active_cell.column, active_cell.row, active_cell.metadata)

    def toggle_column_visibility(self,
                                 column: int,
                                 show:   bool) -> None:
        arange = self.selection.current_active_range
        mdfi = arange.metadata.dfi

        # Save snapshot
        if not globals.is_changing_state:
            from .history_manager import ToggleColumnVisibilityState
            globals.history.save(ToggleColumnVisibilityState(column, show))

        df_width = self.data.dfs[mdfi].width

        # Update column visibility flags
        if len(self.display.column_visibility_flags):
            self.display.column_visibility_flags = polars.concat([self.display.column_visibility_flags[:column - 1],
                                                                  polars.Series([show]),
                                                                  self.display.column_visibility_flags[column:]])
        else:
            if show:
                self.display.column_visibility_flags = polars.Series(dtype=polars.Boolean)
            else:
                self.display.column_visibility_flags = polars.concat([polars.Series([True] * (column - 1), dtype=polars.Boolean),
                                                                      polars.Series([False]),
                                                                      polars.Series([True] * (df_width - column), dtype=polars.Boolean)])
        self.display.column_visible_series = self.display.column_visibility_flags.arg_true()
        if len(self.display.column_visible_series):
            self.data.bbs[mdfi].column_span = len(self.display.column_visible_series)
        else:
            self.data.bbs[mdfi].column_span = df_width

        # Update column widths
        if len(self.display.column_widths):
            column_widths_visible_only = self.display.column_widths
            if len(self.display.column_visibility_flags):
                column_widths_visible_only = column_widths_visible_only.filter(self.display.column_visibility_flags)
            self.display.cumulative_column_widths = polars.Series('ccwidths', column_widths_visible_only).cum_sum()

        self.cancel_cutcopy_operation()
        self.auto_adjust_selections_by_crud(0, 0, False)
        self.repopulate_auto_filter_widgets()

        self.renderer.render_caches = {}
        self.view.main_canvas.queue_draw()

        if not self.is_refreshing_uis:
            self.emit('columns-changed', mdfi)

    def update_column_width(self,
                            column: int,
                            width:  int) -> None:
        # Initialize column widths if needed
        if len(self.display.column_widths) == 0:
            self.display.column_widths = polars.Series([self.display.DEFAULT_CELL_WIDTH] * (column - 1), dtype=polars.Int32)

        # Expand column widths if needed
        if len(self.display.column_widths) < column:
            offset = column - len(self.display.column_widths)
            self.display.column_widths = polars.concat([self.display.column_widths,
                                                        polars.Series([self.display.DEFAULT_CELL_WIDTH] * offset, dtype=polars.Int32)])

        # Save snapshot
        if not globals.is_changing_state:
            from .history_manager import UpdateColumnWidthState
            old_width = self.display.column_widths[column - 1]
            globals.history.save(UpdateColumnWidthState(column, old_width, width))

        # Update column widths
        self.display.column_widths[column - 1] = width
        column_widths_visible_only = self.display.column_widths
        if len(self.display.column_visibility_flags):
            column_widths_visible_only = column_widths_visible_only.filter(self.display.column_visibility_flags)
        self.display.cumulative_column_widths = polars.Series('ccwidths', column_widths_visible_only).cum_sum()

        # Update the current cut/copy range
        if self.selection.current_cutcopy_range is not None:
            ccrange = self.selection.current_cutcopy_range

            x = self.display.get_cell_x_from_column(ccrange.column)
            y = self.display.get_cell_y_from_row(ccrange.row)
            end_x = self.display.get_cell_x_from_column(ccrange.column + ccrange.column_span)
            end_y = self.display.get_cell_y_from_row(ccrange.row + ccrange.row_span)

            if ccrange.column_span > 0:
                ccrange.x = x
                ccrange.width = end_x - x

            if ccrange.row_span > 0:
                ccrange.y = y
                ccrange.height = end_y - y

        # Update the current search range
        if self.selection.current_search_range is not None:
            srange = self.selection.current_search_range

            x = self.display.get_cell_x_from_column(srange.column)
            y = self.display.get_cell_y_from_row(srange.row)
            end_x = self.display.get_cell_x_from_column(srange.column + srange.column_span)
            end_y = self.display.get_cell_y_from_row(srange.row + srange.row_span)

            if srange.column_span > 0:
                srange.x = x
                srange.width = end_x - x

            if srange.row_span > 0:
                srange.y = y
                srange.height = end_y - y

        self.auto_adjust_selections_by_crud(0, 0, False)
        self.repopulate_column_resizer_widgets()
        self.repopulate_auto_filter_widgets()

    def use_first_row_as_headers(self) -> None:
        if len(self.data.dfs) == 0:
            return

        if not self.data.has_main_dataframe:
            return

        if self.data.bbs[0].row_span <= 1:
            return # skip if no visible rows

        mcolumn = self.data.bbs[0].column
        mrow = self.data.bbs[0].row
        column_span = self.data.bbs[0].column_span

        table_width = self.data.dfs[0].width
        row_index = self.display.get_vrow_from_row(mrow + 1)
        first_row = self.data.read_cell_data_block_from_metadata(0, row_index - 1, table_width, 1, 0)

        self.update_selection_from_position(mcolumn, mrow, column_span, mrow)
        self.update_current_cells_from_datatable(first_row)

        self.update_selection_from_position(mcolumn, mrow + 1, column_span, mrow + 1)
        self.delete_current_rows()

        self.update_selection_from_position(mcolumn, mrow, column_span, mrow, auto_scroll=False)

        self.auto_adjust_selections_by_crud(0, 0, False)

        # TODO: clear only for the related columns
        self.data.clear_cell_data_unique_cache(0)

        self.renderer.render_caches = {}
        self.view.main_canvas.queue_draw()

    def use_headers_as_first_row(self) -> None:
        if len(self.data.dfs) == 0:
            return

        if not self.data.has_main_dataframe:
            return

        mcolumn = self.data.bbs[0].column
        mrow = self.data.bbs[0].row
        column_span = self.data.bbs[0].column_span

        self.update_selection_from_position(mcolumn, mrow, column_span, mrow)
        self.insert_blank_from_current_rows()

        self.update_selection_from_position(mcolumn, mrow + 1, column_span, mrow + 1)

        header_row = polars.DataFrame({cname: [cname] for cname in self.data.dfs[0].columns})
        self.update_current_cells_from_datatable(header_row)

        self.update_selection_from_position(mcolumn, mrow, column_span, mrow)
        self.update_current_cells_from_literal('')

        self.auto_adjust_selections_by_crud(0, 0, False)

        # TODO: clear only for the related columns
        self.data.clear_cell_data_unique_cache(0)

        self.renderer.render_caches = {}
        self.view.main_canvas.queue_draw()

    #
    # Clipboard
    #

    def cut_from_current_selection(self, clipboard: ClipboardManager) -> None:
        self.copy_from_current_selection(clipboard)
        self.is_copying_cells = False
        self.is_cutting_cells = True

    def copy_from_current_selection(self, clipboard: ClipboardManager) -> None:
        if self.focused_widget is not None:
            return # TODO: do something

        self.is_cutting_cells = False
        self.is_copying_cells = True

        arange = self.selection.current_active_range
        mdfi = arange.metadata.dfi

        # TODO: support multiple dataframes?
        if mdfi < 0:
            return # TODO: do something

        self.selection.current_cutcopy_range = arange

        mrow = arange.metadata.row
        mcolumn = arange.metadata.column

        row_span = arange.row_span
        column_span = arange.column_span
        bbox = self.data.bbs[mdfi]

        if arange.column_span < 0:
            column_span = bbox.column_span + 1

        if arange.row_span < 0:
            row_span = bbox.row_span + 2

        column_span = self.get_logical_column_span(column_span)
        row_span = self.get_logical_row_span(row_span)

        if arange.column_span < 0:
            column_span -= 1

        if arange.row_span < 0:
            row_span -= 2

        if arange.rtl:
            mcolumn = mcolumn - column_span + 1

        if arange.btt:
            mrow = mrow - row_span + 1

        # Collect hidden column names
        hidden_column_names = []
        for col_index, is_visible in enumerate(self.display.column_visibility_flags):
            if not is_visible:
                hidden_column_names.append(self.data.dfs[mdfi].columns[col_index])

        select_expression = polars.all().exclude(hidden_column_names)

        # Collect column names within the selection
        selected_column_names = self.data.dfs[mdfi].columns[mcolumn:mcolumn + column_span]

        # Reset the select expression
        select_expression = polars.col(selected_column_names).exclude(hidden_column_names)

        # Handle edge cases where the user selected the entire column(s),
        # so there's no point to filter by row.
        has_selected_rows = row_span > 0

        selected_rows_expression = (polars.col('$ridx') >= (mrow - 1)) & (polars.col('$ridx') < (mrow - 1) + row_span) \
                                   if has_selected_rows else polars.lit(True)

        # -1 because we exclude the header row
        visible_rows_expression = polars.col('$ridx').is_in(self.display.row_visible_series[1:] - 1) \
                                  if len(self.display.row_visible_series) else polars.lit(True)

        # Get selected cell contents
        datatable = self.data.dfs[mdfi].select(select_expression) \
                                       .with_row_index('$ridx') \
                                       .filter(selected_rows_expression & visible_rows_expression) \
                                       .drop('$ridx')

        last_selected_row_number = mrow + row_span
        last_selected_column_number = mcolumn + column_span

        table_height = self.data.dfs[mdfi].height + 1
        table_width = self.data.dfs[mdfi].width

        # Expand the datatable with nulls if the user selects out of bounds.
        # Because as of now we don't support multiple dataframes and the main dataframe
        # always start at the (1, 1) position, so we only need to handle the expansion
        # to the right and bottom.
        if surplus_rows := last_selected_row_number - table_height:
            datatable = datatable.vstack(polars.DataFrame({column_name: [None] * surplus_rows
                                                                        for column_name in datatable.columns}))

        if surplus_columns := last_selected_column_number - table_width:
            datatable = datatable.hstack(polars.DataFrame([[None] * datatable.height] * surplus_columns))

        # By now header is always in the first row
        include_header = mrow == 0

        # Transform contents to tab-separated values
        text_contents = datatable.write_csv(include_header=include_header, separator='\t').strip('\n')
        clipboard.set_text(text_contents)

        # Move the header row to the first row
        if include_header:
            header_row = polars.DataFrame({cname: [cname] for cname in datatable.columns})
            datatable = polars.concat([header_row, datatable.cast(polars.String)])

        clipboard.crange = arange
        clipboard.datatable = datatable

        self.clipboard = clipboard

        # Run the cut/copy animation
        self.canvas_tick_callback = self.view.main_canvas.add_tick_callback(self.run_cutcopy_animation)

    def paste_into_current_selection(self,
                                     clipboard: ClipboardManager,
                                     content:   Any) -> None:
        if self.focused_widget is not None:
            return # TODO: do something

        crange = clipboard.crange

        # Clear the source area if it's a cut operation
        def post_cutting_cells_action() -> None:
            arange = self.selection.current_active_range

            self.update_selection_from_position(crange.column,
                                                crange.row,
                                                crange.column + crange.column_span - 1,
                                                crange.row + crange.row_span - 1,
                                                keep_order=True,
                                                follow_cursor=False,
                                                auto_scroll=False)
            self.update_current_cells_from_literal('')

            self.update_selection_from_position(arange.column,
                                                arange.row,
                                                arange.column + arange.column_span - 1,
                                                arange.row + arange.row_span - 1,
                                                keep_order=True,
                                                follow_cursor=False,
                                                auto_scroll=False)

            self.notify_selection_changed(arange.column, arange.row, arange.metadata)

        is_cutting_cells = self.is_cutting_cells
        is_content_tabular = clipboard.datatable is not None

        # Try to read the content with CSV reader
        if not is_content_tabular:
            try:
                datatable = polars.read_csv(content, has_header=False)
                is_content_tabular = True
            except Exception as e:
                print(e)

        # Retry by ignoring any errors
        if not is_content_tabular:
            try:
                datatable = polars.read_csv(content,
                                            has_header=False,
                                            ignore_errors=True,
                                            infer_schema=False)
                is_content_tabular = True
            except Exception as e:
                print(e)

        # Set the clipboard datatable if it's not already set
        if is_content_tabular and clipboard.datatable is None:
            clipboard.datatable = datatable

        if is_content_tabular:
            self.update_current_cells_from_datatable()

            if is_cutting_cells:
                post_cutting_cells_action()

            return

        self.update_current_cells_from_literal(content)

        if is_cutting_cells:
            post_cutting_cells_action()

    #
    # Helpers
    #

    def run_cutcopy_animation(self,
                              widget:      Gtk.Widget,
                              frame_clock: Gdk.FrameClock) -> bool:
        self.view.main_canvas.queue_draw()
        return True

    def cancel_cutcopy_operation(self) -> None:
        if self.clipboard is not None:
            self.clipboard.clear()
            self.clipboard = None

        self.is_cutting_cells = False
        self.is_copying_cells = False

        self.selection.current_cutcopy_range = None

        self.view.main_canvas.remove_tick_callback(self.canvas_tick_callback)

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

    def check_selection_contains_point(self,
                                       x: int,
                                       y: int) -> bool:
        arange = self.selection.current_active_range
        return arange.x <= x <= arange.x + arange.width and \
               arange.y <= y <= arange.y + arange.height

    def get_logical_row_span(self, row_span: int = -2) -> int:
        arange = self.selection.current_active_range
        if row_span == -2:
            row_span = arange.row_span
        start_vrow = self.display.get_vrow_from_row(arange.row)
        end_vrow = self.display.get_vrow_from_row(arange.row + row_span - 1)
        return end_vrow - start_vrow + 1

    def get_logical_column_span(self, column_span: int = -2) -> int:
        arange = self.selection.current_active_range
        if column_span == -2:
            column_span = arange.column_span
        start_vcolumn = self.display.get_vcolumn_from_column(arange.column)
        end_vcolumn = self.display.get_vcolumn_from_column(arange.column + column_span - 1)
        return end_vcolumn - start_vcolumn + 1

    #
    # Signals
    #

    def notify_selection_changed(self,
                                 column: int,
                                 row:    int,
                                 metadata) -> None:
        vcolumn = self.display.get_vcolumn_from_column(column)
        vrow = self.display.get_vrow_from_row(row)

        mcolumn = metadata.column
        mrow = metadata.row
        mdfi = metadata.dfi

        # Cache the selected cell data usually for resetting the input bar
        self.selection.cell_name = self.display.get_cell_name_from_position(vcolumn, vrow)
        self.selection.cell_data = self.data.read_single_cell_data_from_metadata(mcolumn, mrow, mdfi)

        # We don't natively support object types, but in any case the user has perfomed
        # an operation that returned an object, we want to show it properly in minimal.
        # FIXME: we should prevent this from happening in the first place, maybe spread
        #        it to multiple columns. A use case would be the user executing SQL query
        #        that involves a function that do similar to split_part().
        # See https://duckdb.org/docs/stable/sql/functions/text#splitstring-separator
        if isinstance(self.selection.cell_data, polars.Series):
            self.selection.cell_data = self.selection.cell_data.to_list()

        cell_dtype = self.data.read_column_dtype_from_metadata(mcolumn, mdfi)
        self.selection.cell_dtype = utils.get_dtype_symbol(cell_dtype) if cell_dtype is not None else None

        # Request to update the input bar with the selected cell data
        self.emit('selection-changed')

    def notify_selected_table_changed(self, force: bool = False) -> None:
        arange = self.selection.current_active_range
        mdfi = arange.metadata.dfi

        if force or self.current_dfi != mdfi:
            self.current_dfi = mdfi
            self.emit('columns-changed', mdfi)

    #
    # Adjustments
    #

    def repopulate_column_resizer_widgets(self) -> None:
        from .sheet_widget import SheetColumnResizer

        # Remove existing column resizer widget
        self.widgets = [widget for widget in self.widgets if not isinstance(widget, SheetColumnResizer)]

        def on_hovered() -> None:
            self.view.main_canvas.queue_draw()

        def on_released(target_column: int, column_width: int) -> None:
            vcolumn = self.display.get_vcolumn_from_column(target_column)

            if column_width == 0:
                self.toggle_column_visibility(vcolumn, False)
            else:
                self.update_column_width(vcolumn, column_width)
                self.renderer.render_caches = {}
                self.view.main_canvas.queue_draw()

        x = 0
        y = 3
        width = 8 # in pixels
        height = self.display.top_locator_height - 6

        # We need only one column resizer that'll adapt to the position of the pointer on the canvas
        # around any nearby column horizontal edges
        column_resizer = SheetColumnResizer(x, y, width, height, self.display, self.data, on_hovered, on_released)
        self.widgets.append(column_resizer)

    def repopulate_auto_filter_widgets(self) -> None:
        if not self.configs['show-auto-filters']:
            return

        if len(self.data.dfs) == 0:
            return

        from .sheet_widget import SheetAutoFilter

        # Remove existing auto filter widgets
        # FIXME: do not repopulate if not hide/unhide/delete/insert/resizing rows/columns
        self.widgets = [widget for widget in self.widgets if not isinstance(widget, SheetAutoFilter)]

        icon_size = self.display.ICON_SIZE

        cell_y = self.display.get_cell_y_from_row(1)
        cell_height = self.display.get_cell_height_from_row(1)
        y = cell_y + (cell_height - icon_size) / 2 + self.display.scroll_y_position

        def on_clicked(x: int, y: int) -> None:
            GLib.idle_add(self.emit, 'open-context-menu', x, y, 'header')

        # TODO: support multiple dataframes?
        n_columns = self.data.dfs[0].width
        if len(self.display.column_visible_series):
            n_columns = len(self.display.column_visible_series)
        for column in range(n_columns):
            cell_x = self.display.get_cell_x_from_column(column + 1)
            cell_width = self.display.get_cell_width_from_column(column + 1)
            x = cell_x + self.display.scroll_x_position + cell_width - icon_size - 3
            auto_filter = SheetAutoFilter(x, y,  icon_size, icon_size, self.display, on_clicked)
            self.widgets.insert(0, auto_filter)

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
        font_desc = Pango.font_description_from_string(f'{system_font} Normal Regular {self.display.FONT_SIZE}px #tnum=1')
        context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 0, 0))
        layout = PangoCairo.create_layout(context)
        layout.set_font_description(font_desc)

        self.display.column_widths = polars.Series([self.display.DEFAULT_CELL_WIDTH] * self.data.dfs[0].width, dtype=polars.UInt32)

        for col_index, col_name in enumerate(self.data.dfs[0].columns):
            if self.data.dfs[0].height == 0:
                continue
            sample_data = sample_data.with_columns(polars.col(col_name).fill_null('[Blank]').cast(polars.Utf8))
            max_length = sample_data.select(polars.col(col_name).str.len_chars().max()).item()
            try:
                expr = polars.when(polars.col(col_name).str.len_chars() == max_length) \
                             .then(polars.col(col_name)) \
                             .otherwise(None) \
                             .alias('sample_text')
                sample_text = sample_data.with_columns(expr) \
                                         .drop_nulls('sample_text') \
                                         .sample(1).item(0, 'sample_text')
            except Exception:
                continue
            layout.set_text(str(sample_text), -1)
            text_width = layout.get_size()[0] / Pango.SCALE
            preferred_width = text_width + 2 * self.display.DEFAULT_CELL_PADDING
            self.display.column_widths[col_index] = max(self.display.DEFAULT_CELL_WIDTH, min(max_width, int(preferred_width)))

        self.display.cumulative_column_widths = polars.Series('ccwidths', self.display.column_widths).cum_sum()

        globals.is_changing_state = False

    def auto_adjust_scrollbars_by_scroll(self) -> None:
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

        scroll_y_upper = max(content_height + self.display.top_locator_height,
                             self.display.scroll_y_position + canvas_height)
        self.view.vertical_scrollbar.get_adjustment().set_upper(scroll_y_upper)
        self.view.vertical_scrollbar.get_adjustment().set_page_size(canvas_height)

        scroll_x_upper = max(content_width + self.display.left_locator_width,
                             self.display.scroll_x_position + canvas_width)
        self.view.horizontal_scrollbar.get_adjustment().set_upper(scroll_x_upper)
        self.view.horizontal_scrollbar.get_adjustment().set_page_size(canvas_width)

    def auto_adjust_selections_by_scroll(self) -> None:
        self.selection.current_active_range.x = self.display.get_cell_x_from_column(self.selection.current_active_range.column)
        self.selection.current_active_range.y = self.display.get_cell_y_from_row(self.selection.current_active_range.row)

        self.selection.current_active_cell.x = self.display.get_cell_x_from_column(self.selection.current_active_cell.column)
        self.selection.current_active_cell.y = self.display.get_cell_y_from_row(self.selection.current_active_cell.row)

        if self.selection.current_search_range is not None:
            self.selection.current_search_range.x = self.display.get_cell_x_from_column(self.selection.current_search_range.column)
            self.selection.current_search_range.y = self.display.get_cell_y_from_row(self.selection.current_search_range.row)

        if self.selection.current_cutcopy_range is not None:
            self.selection.current_cutcopy_range.x = self.display.get_cell_x_from_column(self.selection.current_cutcopy_range.column)
            self.selection.current_cutcopy_range.y = self.display.get_cell_y_from_row(self.selection.current_cutcopy_range.row)

    def auto_adjust_locators_size_by_scroll(self) -> None:
        # Determine the starting row number
        row_index = self.display.get_starting_row() + 1
        max_row_number = row_index

        # Find the last visible row number
        y = self.display.top_locator_height
        while y < self.view.main_canvas_height:
            max_row_number = self.display.get_vrow_from_row(row_index)
            y += self.display.DEFAULT_CELL_HEIGHT
            row_index += 1

        context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))
        font_desc = Pango.font_description_from_string(f'Monospace Normal Bold {self.display.FONT_SIZE}px')

        layout = PangoCairo.create_layout(context)
        layout.set_text(str(max_row_number), -1)
        layout.set_font_description(font_desc)

        text_width = layout.get_size()[0] / Pango.SCALE
        new_left_locator_width = max(40, int(text_width + self.display.DEFAULT_CELL_PADDING * 2 + 0.5))

        if new_left_locator_width != self.display.left_locator_width:
            self.display.left_locator_width = new_left_locator_width
            self.renderer.render_caches = {}

    def auto_adjust_scrollbars_by_selection(self,
                                            follow_cursor: bool = True,
                                            scroll_axis:   str = 'both',
                                            with_offset:   bool = False,
                                            smooth_scroll: bool = False) -> None:
        column = self.selection.current_cursor_cell.column
        row = self.selection.current_cursor_cell.row

        viewport_height = self.view.main_canvas.get_height() - self.display.top_locator_height
        viewport_width = self.view.main_canvas.get_width() - self.display.left_locator_width

        # TODO: implement smooth scrolling so that the cursor doesn't jump infinitely
        # when the cursor near the edge of the viewport

        self.display.scroll_to_position(column, row, viewport_height, viewport_width, scroll_axis, with_offset)

        if not follow_cursor:
            column = self.selection.current_active_cell.column
            row = self.selection.current_active_cell.row
            self.display.scroll_to_position(column, row, viewport_height, viewport_width, scroll_axis, with_offset)

        self.auto_adjust_scrollbars_by_scroll()

        self.is_refreshing_uis = True

        self.view.vertical_scrollbar.get_adjustment().set_value(self.display.scroll_y_position)
        self.view.horizontal_scrollbar.get_adjustment().set_value(self.display.scroll_x_position)

        self.is_refreshing_uis = False

    def auto_adjust_selections_by_crud(self,
                                       column_offset: int,
                                       row_offset:    int,
                                       shrink:        bool) -> None:
        cstate = globals.is_changing_state
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

        self.update_selection_from_position(col_1, row_1,
                                            col_2, row_2,
                                            keep_order=True,
                                            follow_cursor=True,
                                            auto_scroll=False)

        globals.is_changing_state = cstate