# sheet_data.py
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
from datetime import datetime
from time import time
import gc
import polars
import re

from . import globals
from . import utils
from .sheet_document import SheetDocument

class SheetCellBoundingBox(GObject.Object):
    __gtype_name__ = 'SheetCellBoundingBox'

    column: int
    row: int

    column_span: int
    row_span: int

    def __init__(self,
                 column:      int,
                 row:         int,
                 column_span: int,
                 row_span:    int) -> None:
        super().__init__()

        self.column = column
        self.row = row

        self.column_span = column_span
        self.row_span = row_span

    def check_collision(self, target: 'SheetCellBoundingBox') -> tuple[bool, int, int, str]:
        """
        Checks if the current bounding box collides with a target bounding box, calculates the intersecting
        column and row differences, and determines the relative direction of the target box.
        """
        # Calculate the exclusive end coordinates for both boxes.
        target_end_column = target.column + target.column_span
        target_end_row = target.row + target.row_span

        self_end_column = self.column + self.column_span
        self_end_row = self.row + self.row_span

        # Calculate the start and end of the intersection region
        intersect_start_column = max(target.column, self.column)
        intersect_end_column = min(target_end_column, self_end_column)

        intersect_start_row = max(target.row, self.row)
        intersect_end_row = min(target_end_row, self_end_row)

        # Calculate the width and height of the actual intersection
        overlapping_column_diff = max(0, intersect_end_column - intersect_start_column)
        overlapping_row_diff = max(0, intersect_end_row - intersect_start_row)

        # Determine if a collision occurred
        has_collision = (overlapping_column_diff > 0) and (overlapping_row_diff > 0)

        # Calculate non-overlapping parts of the target box
        if has_collision:
            # If there's a collision, the non-overlapping part is the target's total span
            # minus the span of the overlap.
            non_overlapping_target_column_span = target.column_span - overlapping_column_diff
            non_overlapping_target_row_span = target.row_span - overlapping_row_diff
        else:
            # If there's no collision, the entire target box is non-overlapping.
            non_overlapping_target_column_span = target.column_span
            non_overlapping_target_row_span = target.row_span

        # Initialize distances and direction
        horizontal_gap = 0
        vertical_gap = 0
        direction_parts = []

        if has_collision:
            direction_parts.append("overlap")
            # Check if target extends beyond self's boundaries
            if target.column < self.column:
                direction_parts.append("left")
            if target_end_column > self_end_column:
                direction_parts.append("right")
            if target.row < self.row:
                direction_parts.append("above")
            if target_end_row > self_end_row:
                direction_parts.append("below")
            direction = "-".join(direction_parts)
            # Gaps remain 0 if there's an overlap

        else:
            # Calculate horizontal separation (gap)
            if self_end_column <= target.column: # Current box is to the left of target
                horizontal_gap = target.column - self_end_column
            elif target_end_column <= self.column: # Target box is to the left of current
                horizontal_gap = self.column - target_end_column
            # If neither, they must overlap horizontally, so horizontal_gap remains 0

            # Calculate vertical separation (gap)
            if self_end_row <= target.row: # Current box is above target
                vertical_gap = target.row - self_end_row
            elif target_end_row <= self.row: # Target box is above current
                vertical_gap = self.row - target_end_row
            # If neither, they must overlap vertically, so vertical_gap remains 0

            # Determine direction based on relative positions and gaps
            is_right = (self_end_column <= target.column)
            is_left = (target_end_column <= self.column)
            is_below = (self_end_row <= target.row)
            is_above = (target_end_row <= self.row)

            if is_left:
                direction_parts.append("left")
            if is_right:
                direction_parts.append("right")
            if is_above:
                direction_parts.append("above")
            if is_below:
                direction_parts.append("below")

            if direction_parts:
                direction = "-".join(direction_parts)
            else:
                direction = "no-relation-complex-separation"
            # If none of the above, it means no collision, and no clear single-axis or diagonal separation
            # (e.g., they might be touching exactly at an edge or corner, or complex alignment)
            # The default "no-relation-complex-separation" handles this.

        return {
            'has_collision':     has_collision,
            'nonov_column_span': non_overlapping_target_column_span,
            'nonov_row_span':    non_overlapping_target_row_span,
            'direction':         direction,
            'horizontal_gap':    horizontal_gap,
            'vertical_gap':      vertical_gap
        }



class SheetCellMetadata(GObject.Object):
    __gtype_name__ = 'SheetCellMetadata'

    column: int
    row: int

    dfi: int

    def __init__(self,
                 column: int,
                 row:    int,
                 dfi:    int) -> None:
        super().__init__()

        self.column = column
        self.row = row

        self.dfi = dfi



class SheetData(GObject.Object):
    __gtype_name__ = 'SheetData'

    bbs: list[SheetCellBoundingBox] = [] # visual bounding boxes
    dfs: list[polars.DataFrame] = [] # dataframes

    has_main_dataframe: bool = False

    def __init__(self,
                 document:  SheetDocument,
                 dataframe: polars.DataFrame,
                 column:    int = 1,
                 row:       int = 1) -> None:
        super().__init__()

        self.document = document

        self.unique_caches = {}

        self.setup_main_df(dataframe, column, row)

    def setup_main_df(self,
                      dataframe: polars.DataFrame,
                      column:    int,
                      row:       int) -> None:
        if dataframe is None:
            return

        width = dataframe.width
        height = dataframe.height + 1 # +1 for the header

        # TODO: auto-rechunk every dataframe on application idle?
        dataframe = dataframe.rechunk()

        # Remove leading '$' from column names to prevent collision
        # from internal column names
        for col_name in dataframe.columns:
            if not col_name.startswith('$'):
                continue
            dataframe = dataframe.rename({col_name: col_name.lstrip('$')})

        # Replace the main dataframe
        if self.has_main_dataframe:
            self.bbs[0] = SheetCellBoundingBox(column, row, width, height)
            del self.dfs[0]
            self.dfs.insert(0, dataframe)

        # Set the first dataframe as the main dataframe
        else:
            self.bbs = [SheetCellBoundingBox(column, row, width, height)]
            self.dfs = [dataframe]

        self.has_main_dataframe = True

        gc.collect()

    def get_cell_metadata_from_position(self,
                                        column: int,
                                        row:    int) -> SheetCellMetadata:
        # Handle the locator cells
        column = max(1, column)
        row = max(1, row)

        for bbi, bbs in enumerate(self.bbs):
            column_in_range = bbs.column <= column < (bbs.column + self.dfs[bbi].width)
            row_in_range = bbs.row <= row < (bbs.row + self.dfs[bbi].height + 1)

            if column_in_range and row_in_range:
                column = column - bbs.column
                row = row - bbs.row
                return SheetCellMetadata(column, row, bbi)

        return SheetCellMetadata(-1, -1, -1)

    def read_column_dtype_from_metadata(self,
                                        column: int,
                                        dfi:    int) -> polars.DataType:
        if dfi < 0 or len(self.dfs) <= dfi:
            return None

        if len(self.dfs[dfi].columns) <= column:
            return None

        return self.dfs[dfi].dtypes[column]

    def read_single_cell_data_from_metadata(self,
                                            column: int,
                                            row:    int,
                                            dfi:    int) -> any:
        if dfi < 0 or len(self.dfs) <= dfi:
            return None

        if len(self.dfs[dfi].columns) <= column:
            return None

        row -= 1 # coordinate to index

        # Get the header
        if row < 0:
            return self.dfs[dfi].columns[column]

        # Get the content
        return self.dfs[dfi][row, column]

    def read_cell_data_block_from_metadata(self,
                                           column:         int,
                                           row:            int,
                                           column_span:    int,
                                           row_span:       int,
                                           dfi:            int,
                                           include_header: bool = False,
                                           with_hidden:    bool = True) -> polars.DataFrame:
        if dfi < 0 or len(self.dfs) <= dfi:
            return None

        row -= 1

        if include_header:
            row += 1
            row_span -= 1

        return self.dfs[dfi][row:row + row_span, column:column + column_span]

    def read_cell_data_chunks_from_metadata(self,
                                            column_names: list[str],
                                            row:          int,
                                            row_span:     int,
                                            dfi:          int) -> any:
        if dfi < 0 or len(self.dfs) <= dfi:
            return None

        if len(column_names) == 0:
            None

        # Get the entire content
        if row_span < 0:
            return self.dfs[dfi].select(column_names)

        # Get the content in range
        return self.dfs[dfi].select(column_names)[row:row + row_span]

    def read_cell_data_approx_n_unique_from_metadata(self,
                                                     column: int,
                                                     dfi:    int) -> any:
        if dfi < 0 or len(self.dfs) <= dfi:
            return None

        column_name = self.dfs[dfi].columns[column]

        try:
            return self.dfs[dfi].select(polars.col(column_name).approx_n_unique()).item()
        except Exception:
            return self.dfs[dfi].select(polars.col(column_name).n_unique()).item()

    def read_cell_data_n_unique_from_metadata(self,
                                              column:       int,
                                              dfi:          int,
                                              search_query: str = None,
                                              use_regexp:   bool = False) -> any:
        if dfi < 0 or len(self.dfs) <= dfi:
            return None

        column_name = self.dfs[dfi].columns[column]

        filter_expression = polars.lit(True)
        if search_query is not None:
            filter_expression = polars.col(column_name).str.contains_any([search_query], ascii_case_insensitive=True)
            if use_regexp:
                filter_expression = polars.col(column_name).str.contains(f'(?i){search_query}')

        return self.dfs[dfi].filter(filter_expression) \
                            .select(polars.col(column_name).n_unique()) \
                            .item()

    def read_cell_data_unique_from_metadata(self,
                                            column:       int,
                                            dfi:          int,
                                            sample_only:  bool = False,
                                            search_query: str = None,
                                            use_regexp:   bool = False) -> any:
        if dfi < 0 or len(self.dfs) <= dfi:
            return None

        if self.check_cell_data_unique_cache(column, dfi) \
                and search_query is None:
            return self.unique_caches[dfi][column]

        column_name = self.dfs[dfi].columns[column]

        filter_expression = polars.lit(True)
        if search_query is not None:
            filter_expression = polars.col(column_name).str.contains_any([search_query], ascii_case_insensitive=True)
            if use_regexp:
                filter_expression = polars.col(column_name).str.contains(f'(?i){search_query}')

        if sample_only:
            unique_values = self.dfs[dfi].filter(filter_expression).get_column(column_name) \
                                         .sample(1_000_000, seed=99, with_replacement=True) \
                                         .unique().sort()

        unique_values = self.dfs[dfi].filter(filter_expression).get_column(column_name).unique().sort()

        if search_query is None:
            self.unique_caches[dfi][column] = unique_values

        return unique_values

    def check_cell_data_unique_cache(self,
                                     column: int,
                                     dfi:    int) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        if dfi not in self.unique_caches:
            self.unique_caches[dfi] = {}

        return column in self.unique_caches[dfi]

    def clear_cell_data_unique_cache(self,
                                     dfi: int,
                                     column: int = None) -> None:
        if column is None and dfi in self.unique_caches:
            del self.unique_caches[dfi]
            return
        if dfi in self.unique_caches and column in self.unique_caches[dfi]:
            del self.unique_caches[dfi][column]

    def read_cell_bbox_from_metadata(self, dfi: int) -> SheetCellBoundingBox:
        if dfi < 0 or len(self.dfs) <= dfi:
            return None
        return self.bbs[dfi]

    def insert_rows_from_metadata(self,
                                  row:      int,
                                  row_span: int,
                                  dfi:      int) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        empty_rows = polars.DataFrame({column_name: polars.Series(values=[None] * row_span, dtype=column_dtype)
                                                    for column_name, column_dtype in self.dfs[dfi].schema.items()})

        self.dfs[dfi] = polars.concat([self.dfs[dfi].slice(0, row),
                                       empty_rows,
                                       self.dfs[dfi].slice(row)])

        return True

    def insert_columns_from_metadata(self,
                                     column:      int,
                                     column_span: int,
                                     dfi:         int,
                                     left:        bool = False) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        column_number = 1
        for column_name in self.dfs[dfi].columns:
            if match := re.match(r'column_(\d+)', column_name):
                column_number = max(column_number, int(match.group(1)) + 1)

        if left:
            column += column_span - 1
            column_number += column_span - 1

        for _ in range(column_span):
            column_name = f'column_{column_number}'
            self.dfs[dfi] = self.dfs[dfi].insert_column(column, polars.lit(None).alias(column_name))
            self.bbs[dfi].column_span += 1

            if not left:
                column += 1
                column_number += 1
            else:
                column_number -= 1

        return True

    def insert_rows_from_dataframe(self,
                                   dataframe: polars.DataFrame,
                                   row:       int,
                                   dfi:       int) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        # FIXME: exclude hidden column/rows

        self.dfs[dfi] = polars.concat([self.dfs[dfi].slice(0, row - 1),
                                       dataframe,
                                       self.dfs[dfi].slice(row - 1)])
        self.bbs[dfi].row_span += dataframe.height

        return True

    def insert_columns_from_dataframe(self,
                                      dataframe: polars.DataFrame,
                                      column:    int,
                                      dfi:       int) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        # FIXME: exclude hidden column/rows

        for counter, column in enumerate(range(column, column + dataframe.width)):
            self.dfs[dfi] = self.dfs[dfi].insert_column(column, dataframe[:, counter])
            self.bbs[dfi].column_span += 1

        del dataframe
        gc.collect()

        return True

    def update_columns_with_expression_from_metadata(self,
                                                     dfi:     int,
                                                     measure: str,
                                                     expr:    polars.Expr) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        if not isinstance(expr, polars.Expr):
            expr = polars.lit(expr)

        try:
            is_new_column = measure not in self.dfs[dfi].columns
            self.dfs[dfi] = self.dfs[dfi].with_columns(expr.alias(measure))
            self.bbs[dfi].column_span += is_new_column
            return True

        except Exception as e:
            print(e)

        globals.send_notification('Cannot execute the query')
        return False

    def update_columns_with_sql_from_metadata(self,
                                              dfi:    int,
                                              query:  str) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        try:
            new_dataframe = self.dfs[dfi].sql(query)

            incoming_column_names = new_dataframe.columns
            existing_column_names = self.dfs[dfi].columns

            added_column_names = list(set(incoming_column_names) - set(existing_column_names))
            n_added_columns = len(added_column_names)

            for col_name in incoming_column_names:
                if len(new_dataframe.get_column(col_name)) == 1:
                    sel_value = new_dataframe.get_column(col_name).first()
                    new_series = polars.Series([sel_value] * self.dfs[dfi].height)
                    self.dfs[dfi] = self.dfs[dfi].with_columns(new_series.alias(col_name))
                    continue

                expr = new_dataframe.get_column(col_name).alias(col_name)
                self.dfs[dfi] = self.dfs[dfi].with_columns(expr)

            self.bbs[dfi].column_span += n_added_columns

        except Exception as e:
            print(e)

            message = f'Cannot execute the query'
            action = ()
            e = str(e)

            if e.startswith('sql parser error: '):
                message = f'Invalid SQL syntax: {e.split('sql parser error: ', 1)[1]}'
            if e.startswith('unable to find column '):
                message = f'Unknown column name: {e.split('unable to find column ', 1)[1].split(';')[0]}'
            if e.startswith('unable to add a column of length '):
                message = 'Column length mismatch. Create a new table?'

                action_data_id = str(int(time()))
                action_name = f"app.apply-pending-table('{action_data_id}')"
                action = ('Create', action_name, action_data_id)

                # We keep the dataframe in a temporary place so that we don't need to re-execute the query
                # when the user proceeds to create a new table.
                globals.pending_action_data[action_data_id] = new_dataframe

            globals.send_notification(message, action)

            return False

        return True

    def update_cell_data_block_with_single_from_metadata(self,
                                                         column:         int,
                                                         row:            int,
                                                         column_span:    int,
                                                         row_span:       int,
                                                         dfi:            int,
                                                         include_header: bool,
                                                         new_value:      any,
                                                         column_vseries: polars.Series,
                                                         row_vseries:    polars.Series) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        row -= 1

        row_count = self.dfs[dfi].height

        end_column = column + column_span
        if column_span < 0:
            end_column = self.dfs[dfi].width

        start = max(0, row)
        stop = min(row + row_span, row_count)

        for column in range(column, end_column):
            # Skip if the column is hidden
            if len(column_vseries) and column not in column_vseries:
                continue

            # Skip out of range columns
            if self.dfs[dfi].width <= column:
                break

            column_name = self.dfs[dfi].columns[column]
            column_dtype = self.dfs[dfi].dtypes[column]

            # Convert the input value to the correct type
            try:
                match column_dtype:
                    case polars.Datetime:
                        replace_with = datetime.strptime(new_value, '%Y-%m-%d %H:%M:%S')
                    case polars.Date:
                        replace_with = datetime.strptime(new_value, '%Y-%m-%d').date()
                    case polars.Time:
                        replace_with = datetime.strptime(new_value, '%H:%M:%S').time()
                    case _:
                        replace_with = polars.Series([new_value]).cast(column_dtype)[0]
            except Exception:
                replace_with = str(new_value)

            # Cast empty string
            if replace_with == '':
                replace_with = None

            # Update the entire column
            if row_span < 0:
                self.dfs[dfi] = self.dfs[dfi].with_columns(polars.repeat(replace_with, row_count,
                                                                         eager=True, dtype=column_dtype)
                                                                 .alias(column_name))
            # Update the dataframe in range, excluding the header row
            elif stop - start > 0:
                when_expression = polars.col('$ridx').is_between(start, stop - 1)
                if len(row_vseries):
                    when_expression &= polars.col('$ridx').is_in(row_vseries[1:] - 1)
                # FIXME: this strategy automatically converts column to string when needed,
                #        but it won't restore the dtype when undoing
                self.dfs[dfi] = self.dfs[dfi].with_row_index('$ridx') \
                                             .with_columns(polars.when(when_expression)
                                                                 .then(polars.lit(replace_with))
                                                                 .otherwise(polars.col(column_name))
                                                                 .alias(column_name)) \
                                             .drop('$ridx')

            if not include_header:
                continue # skip header cell

            # Remove leading '$' to prevent collision from internal column names
            replace_with = new_value.lstrip('$')

            def generate_next_column_name(column_name: str) -> str:
                cnumber = 1
                for cname in self.dfs[dfi].columns:
                    if match := re.match(column_name + r'_(\d+)', cname):
                        cnumber = max(cnumber, int(match.group(1)) + 1)
                return f'{column_name}_{cnumber}'

            # Generate a new column name if needed
            if replace_with in ['', None]:
                replace_with = generate_next_column_name('column')
            else:
                replace_with = str(replace_with)
                if replace_with in self.dfs[dfi].columns:
                    replace_with = generate_next_column_name(replace_with)

            # Update the column name
            self.dfs[dfi] = self.dfs[dfi].rename({column_name: replace_with})

        return True

    def update_cell_data_block_with_range_from_metadata(self,
                                                        t_column:         int,
                                                        t_row:            int,
                                                        column_span:      int,
                                                        row_span:         int,
                                                        t_dfi:            int,
                                                        t_include_header: bool,
                                                        crange:           any,
                                                        column_vseries:   polars.Series,
                                                        row_vseries:      polars.Series) -> bool:
        if t_dfi < 0 or len(self.dfs) <= t_dfi:
            return False

        s_dfi = crange.metadata.dfi
        s_include_header = crange.metadata.row == 0 # by now header is always in the first row

        # TODO: support multiple dataframes?
        if column_span == -1:
            column_span = self.bbs[s_dfi].column_span

        if row_span == -1:
            row_span = self.bbs[s_dfi].row_span

        s_row_start = max(0, crange.metadata.row - 1)
        s_row_stop = min(crange.metadata.row - 1 + row_span, self.dfs[s_dfi].height)

        t_row_start = max(0, t_row - 1)
        t_row_stop = min(t_row - 1 + row_span, self.dfs[t_dfi].height)

        t_n_rows = t_row_stop - t_row_start
        s_n_rows = s_row_stop - s_row_start

        # Prepare for source row index
        if len(row_vseries):
            s_ridx_length = self.dfs[s_dfi].height
            s_ridx = (
                polars.DataFrame({'$ridx': polars.int_range(0, s_ridx_length, eager=True)})
                      .filter(polars.col('$ridx').is_in(row_vseries[1:] - 1) |
                              polars.col('$ridx').ge(self.dfs[s_dfi].height))
                      .slice(s_row_start + s_include_header - 1, s_n_rows + s_include_header)['$ridx']
            )
            if s_include_header:
                s_ridx = polars.concat([polars.Series([-1]), s_ridx[1:].cast(polars.Int64) - 1])
        else:
            s_ridx = polars.int_range(s_row_start, s_row_stop, eager=True)

        # Prepare for target row index
        if len(row_vseries):
            t_ridx_offset = row_vseries.index_of(t_row)
            t_ridx = row_vseries.slice(t_ridx_offset + t_include_header, t_n_rows) - 1
            if t_include_header:
                t_ridx = polars.concat([polars.Series([-1]), t_ridx.cast(polars.Int64)])
        else:
            t_ridx_offset = t_row_start + s_include_header - t_include_header
            t_ridx = polars.int_range(t_ridx_offset, t_ridx_offset + row_span - s_include_header, eager=True)

        # Handle a case when the user selects a range that contains cells
        # that are vertically out of range of the source dataframe.
        if s_n_rows < t_n_rows:
            s_ridx.extend(polars.Series([-1] * (t_n_rows - s_n_rows)))

        t_end_column = t_column + column_span
        if column_span < 0:
            t_end_column = self.dfs[t_dfi].width

        s_column_index = crange.metadata.column

        for t_column in range(t_column, t_end_column):
            # Skip if the column is hidden
            if len(column_vseries) and t_column not in column_vseries:
                continue

            # Skip out of range columns
            if self.dfs[t_dfi].width <= t_column:
                break

            t_column_name = self.dfs[t_dfi].columns[t_column]

            # Handle a case when the user selects a range that contains cells
            # that are horizontally out of range of the source dataframe.
            if self.dfs[s_dfi].width <= s_column_index and t_n_rows > 0:
                self.dfs[t_dfi] = (
                    self.dfs[t_dfi]
                        .with_row_index('$t_ridx')
                        .join(
                            polars.DataFrame({
                                '$t_nval': polars.DataFrame({
                                    t_column_name: [None] * (t_n_rows + (t_n_rows - s_n_rows))
                                }),
                                '$t_ridx': t_ridx
                            }),
                            on='$t_ridx',
                            how='left',
                        )
                        .with_columns(polars.when(polars.col('$t_ridx').is_in(t_ridx))
                                            .then(polars.col('$t_nval'))
                                            .otherwise(polars.col(t_column_name))
                                            .alias(t_column_name)
                        )
                        .drop(['$t_ridx', '$t_nval'])
                )
                continue

            s_column_name = self.dfs[s_dfi].columns[s_column_index]
            s_column_index += 1

            # Update the dataframe in range, excluding the header row
            # FIXME: updating the same area as the source area will clear its contents
            self.dfs[t_dfi] = (
                self.dfs[t_dfi]
                    .with_row_index('$t_ridx')
                    .join(
                        polars.DataFrame({
                            '$t_nval': (
                                polars.concat([
                                    self.dfs[s_dfi][s_column_name],
                                    polars.Series([None] * (t_n_rows - s_n_rows)),
                                ]).gather(s_ridx)
                            ),
                            '$t_ridx': t_ridx
                        }),
                        on='$t_ridx',
                        how='left',
                    )
                    .with_columns(polars.when(polars.col('$t_ridx').is_in(t_ridx))
                                        .then(polars.col('$t_nval'))
                                        .otherwise(polars.col(t_column_name))
                                        .alias(t_column_name)
                    )
                    .drop(['$t_ridx', '$t_nval'])
            )

            if not s_include_header and not t_include_header:
                continue

            t_first_row = self.dfs[s_dfi][s_row_start, s_column_name]

            if t_first_row is None:
                t_first_row = ''

            t_first_row = str(t_first_row)

            if s_include_header:
                t_first_row = s_column_name

            if not t_include_header:
                self.dfs[t_dfi][t_row_start, t_column_name] = t_first_row
                continue

            # Remove leading '$' to prevent collision from internal column names
            t_new_col_name = t_first_row.lstrip('$')

            def generate_next_column_name(column_name: str) -> str:
                cnumber = 1
                for cname in self.dfs[t_dfi].columns:
                    if match := re.match(column_name + r'_(\d+)', cname):
                        cnumber = max(cnumber, int(match.group(1)) + 1)
                return f'{column_name}_{cnumber}'

            # Generate a new column name if needed
            if t_new_col_name in ['', None]:
                t_new_col_name = generate_next_column_name('column')
            else:
                t_new_col_name = str(t_new_col_name)
                if t_new_col_name in self.dfs[t_dfi].columns:
                    t_new_col_name = generate_next_column_name(t_new_col_name)

            # Update the column name
            self.dfs[t_dfi] = self.dfs[t_dfi].rename({t_column_name: t_new_col_name})

        return True

    def update_cell_data_block_from_metadata(self,
                                             column:         int,
                                             row:            int,
                                             column_span:    int,
                                             row_span:       int,
                                             dfi:            int,
                                             include_header: bool,
                                             content:        polars.DataFrame) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        row -= 1

        row_count = self.dfs[dfi].height

        end_column = column + column_span
        if column_span < 0:
            end_column = self.dfs[dfi].width

        if row_span < 0:
            row_span = row_count

        start = max(0, row)
        stop = min(row + row_span, row_count)

        content_index = -1
        for column in range(column, end_column):
            if self.dfs[dfi].width <= column:
                break

            content_index += 1

            column_name = self.dfs[dfi].columns[column]
            column_dtype = self.dfs[dfi].dtypes[column]

            # Update the dataframe in range
            self.dfs[dfi] = self.dfs[dfi].with_columns(
                self.dfs[dfi][:start, column].extend(content[:, content_index].cast(column_dtype))
                                             .extend(self.dfs[dfi][stop:, column])
                                             .alias(column_name)
            )

            if not include_header:
                continue # skip header cell

            # Update the column name
            self.dfs[dfi] = self.dfs[dfi].rename({column_name: content.columns[content_index]})

        del content
        gc.collect()

        return True

    def update_cell_data_blocks_from_metadata(self,
                                              column_names: list[str],
                                              row: int,
                                              row_span: int,
                                              dfi: int,
                                              content: polars.DataFrame) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        for column_name in column_names:
            column = self.dfs[dfi].columns.index(column_name)
            if row_span < 0: # update the entire column
                self.dfs[dfi] = self.dfs[dfi].with_columns(content[column_name].alias(column_name))
            else: # update within the range
                self.dfs[dfi] = self.dfs[dfi].with_columns(self.dfs[dfi][0:row, column].extend(content[column_name])
                                                                                       .extend(self.dfs[dfi][row + row_span:, column])
                                                                                       .alias(column_name))

        del content
        gc.collect()

        return True

    def duplicate_rows_from_metadata(self,
                                     row:      int,
                                     row_span: int,
                                     dfi:      int) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        # FIXME: exclude hidden column/rows

        self.dfs[dfi] = polars.concat([self.dfs[dfi].slice(0, row + row_span - 1),
                                       self.dfs[dfi].slice(row - 1, row_span),
                                       self.dfs[dfi].slice(row + row_span - 1)])
        self.bbs[dfi].row_span += row_span

        return True

    def duplicate_columns_from_metadata(self,
                                        column:      int,
                                        column_span: int,
                                        dfi:         int,
                                        left:        bool = False) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        # FIXME: exclude hidden column/rows

        if left:
            column += column_span - 1

        for _ in range(column_span):
            target_name = self.dfs[dfi].columns[column]
            new_name = re.sub(r'_(\d+)$', '', target_name)

            # Determine a new column name
            column_number = 1
            for column_name in self.dfs[dfi].columns:
                if match := re.match(new_name + r'_(\d+)', column_name):
                    column_number = max(column_number, int(match.group(1)) + 1)
                column_name = self.dfs[dfi].columns[column]

            if not left:
                column = column + column_span
            else:
                column = column - column_span + 1

            new_name = f'{new_name}_{column_number}'
            self.dfs[dfi] = self.dfs[dfi].insert_column(column, polars.col(target_name).alias(new_name))
            self.bbs[dfi].column_span += 1

            if not left:
                column = column - column_span + 1
            else:
                column = column + column_span - 1

        return True

    def delete_rows_from_metadata(self,
                                  row:      int,
                                  row_span: int,
                                  dfi:      int) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        # FIXME: exclude hidden column/rows

        row -= 1

        # Prevent from deleting the header row
        if row < 0:
            row = 0
            row_span -= 1

        self.dfs[dfi] = self.dfs[dfi].with_row_index('$ridx') \
                                     .remove(polars.col('$ridx').is_in(range(row, row + row_span))) \
                                     .drop('$ridx')
        self.bbs[dfi].row_span -= row_span

        return True

    def delete_columns_from_metadata(self,
                                     column:      int,
                                     column_span: int,
                                     dfi:         int) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        # FIXME: exclude hidden column/rows

        column_names = self.dfs[dfi].columns[column:column + column_span]
        self.dfs[dfi] = self.dfs[dfi].drop(column_names)
        self.bbs[dfi].column_span -= column_span

        return True

    def filter_rows_from_metadata(self,
                                  filters: list,
                                  dfi:     int) -> polars.Series:
        if dfi < 0 or len(self.dfs) <= dfi:
            return polars.Series(dtype=polars.Boolean)

        expression = polars.lit(True)

        for index, afilter in enumerate(filters):
            if index == 0:
                expression = afilter['expression']
                continue

            if afilter['operator'] == 'and':
                expression &= afilter['expression']
            else:
                expression |= afilter['expression']

        # We don't do the actual filtering on the original dataframe here, instead
        # we just want to get the boolean series to flag which rows should be visible.
        return polars.concat([polars.Series([True]), # for header row
                              self.dfs[dfi].with_columns(expression.alias('$vrow'))['$vrow']])

    def sort_rows_from_metadata(self,
                                sorts: dict,
                                dfi:   int) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        sort_cnames = []
        sort_descendings = []

        for column_name in sorts:
            sort_cnames.append(column_name)
            sort_descendings.append(sorts[column_name]['descending'])

        self.dfs[dfi] = self.dfs[dfi].sort(sort_cnames,
                                           descending=sort_descendings,
                                           nulls_last=True)

        return True

    def convert_columns_dtype_from_metadata(self,
                                            column:      int,
                                            column_span: int,
                                            dfi:         int,
                                            dtype:       polars.DataType) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        expressions = []

        for column, column_name in enumerate(self.dfs[dfi].columns[column:column + column_span], column):
            if isinstance(dtype, polars.Categorical):
                dtype = polars.Categorical('lexical')
                expressions.append(polars.col(column_name).cast(dtype).alias(column_name))

            elif dtype in (polars.Datetime, polars.Date, polars.Time):
                original_dtype = self.dfs[dfi].schema[column_name]
                first_non_null = self.dfs[dfi].filter(polars.col(column_name).is_not_null()) \
                                              .head(1)[column_name].item()

                if isinstance(original_dtype, polars.String) and first_non_null:
                    if dtype in (polars.Datetime, polars.Date):
                        dformat = utils.get_date_format_string(first_non_null)
                    if dtype in (polars.Time):
                        dformat = utils.get_time_format_string(first_non_null)
                    expressions.append(polars.col(column_name).str.strip_chars()
                                                              .str.strptime(dtype, dformat)
                                                              .alias(column_name))
                else:
                    expressions.append(polars.col(column_name).cast(dtype).alias(column_name))

            else:
                expressions.append(polars.col(column_name).cast(dtype).alias(column_name))

        try:
            self.dfs[dfi] = self.dfs[dfi].with_columns(expressions)
            return True
        except Exception as e:
            print(e)

        dtype = utils.get_dtype_symbol(dtype, False)
        globals.send_notification(f'Cannot be converted to: {dtype}')

        return False

    def replace_cell_data_by_pattern_from_metadata(self,
                                                   column:         int,
                                                   row:            int,
                                                   dfi:            int,
                                                   replace_with:   str,
                                                   search_pattern: str,
                                                   match_case:     bool) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        row -= 1

        if self.dfs[dfi][row, column] == search_pattern and replace_with == '':
            self.dfs[dfi][row, column] = None
            return True

        if match_case:
            self.dfs[dfi][row, column] = self.dfs[dfi][row, column].replace(search_pattern, replace_with)
        else:
            self.dfs[dfi][row, column] = re.sub(re.escape(search_pattern),
                                                replace_with,
                                                self.dfs[dfi][row, column],
                                                flags=re.IGNORECASE)

        return True