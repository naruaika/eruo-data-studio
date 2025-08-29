# sheet_data.py
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
from datetime import datetime
from typing import Any
import duckdb
import polars
import re

from . import globals
from . import utils
from .sheet_document import SheetDocument
from .sheet_functions import build_operation, register_sql_functions

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

    bbs: list[SheetCellBoundingBox] # visual bounding boxes
    dfs: list[polars.DataFrame]     # dataframes

    has_main_dataframe: bool

    def __init__(self,
                 document:  SheetDocument,
                 dataframe: polars.DataFrame,
                 column:    int = 1,
                 row:       int = 1) -> None:
        super().__init__()

        self.document = document

        self.bbs = []
        self.dfs = []

        self.has_main_dataframe = False

        self.unique_caches = {}

        self.setup_main_dataframe(dataframe, column, row)

    def setup_main_dataframe(self,
                             dataframe: polars.DataFrame,
                             column:    int = 1,
                             row:       int = 1) -> None:
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
            self.dfs.insert(0, dataframe)

        # Set the first dataframe as the main dataframe
        else:
            self.bbs = [SheetCellBoundingBox(column, row, width, height)]
            self.dfs = [dataframe]

        self.has_main_dataframe = True

    def insert_blank_dataframe(self,
                               column: int = 1,
                               row:    int = 1) -> polars.DataFrame:
        self.bbs.append(SheetCellBoundingBox(column, row, 0, 0))
        self.dfs.append(polars.DataFrame())

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

    def read_cell_data_block_with_operator_from_metadata(self,
                                                         column:         int,
                                                         row:            int,
                                                         column_span:    int,
                                                         row_span:       int,
                                                         dfi:            int,
                                                         operator_name:  str,
                                                         operation_args: list,
                                                         column_vseries: polars.Series,
                                                         row_vseries:    polars.Series) -> polars.DataFrame:
        new_dataframe = polars.DataFrame()

        if dfi < 0 or len(self.dfs) <= dfi:
            return new_dataframe

        def append_series(series:    polars.Series,
                          dataframe: polars.DataFrame) -> None:
            if dataframe.width == 0:
                return polars.DataFrame(series)

            series_length = len(series)
            dataframe_height = dataframe.height

            if series_length == dataframe_height:
                return dataframe.with_columns(series)

            if series_length < dataframe_height:
                n_rows_to_add = dataframe_height - series_length
                empty_rows = polars.Series([None] * n_rows_to_add, dtype=series.dtype)

                fitted_series = polars.concat([series, empty_rows])
                return dataframe.with_columns(fitted_series)

            if dataframe_height < series_length:
                n_rows_to_add = series_length - dataframe_height
                empty_rows = polars.DataFrame({column_name: polars.Series(values=[None] * n_rows_to_add, dtype=column_dtype)
                                                            for column_name, column_dtype in dataframe.schema.items()})

                padded_dataframe = dataframe.vstack(empty_rows)
                return padded_dataframe.with_columns(series)

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

            if isinstance(column_dtype, (polars.List, polars.Struct, polars.Object)):
                continue # we don't support updating a list, struct, or object

            expression = build_operation(polars.col(column_name), operator_name, operation_args)

            # Evaluate the expression
            try:
                if isinstance(expression, polars.Expr):
                    # Get the entire column
                    if row_span < 0:
                        new_series = self.dfs[dfi].with_columns(expression.alias(column_name)) \
                                                  .get_column(column_name)
                        new_dataframe = append_series(new_series.alias(column_name), new_dataframe)

                    # Get the dataframe in range, excluding the header row
                    elif stop - start > 0:
                        when_expression = polars.col('$ridx').is_between(start, stop - 1)
                        if len(row_vseries):
                            when_expression &= polars.col('$ridx').is_in(row_vseries[1:] - 1)
                        new_series = self.dfs[dfi].with_row_index('$ridx') \
                                                  .filter(when_expression) \
                                                  .select(expression.alias(column_name)) \
                                                  .to_series()
                        new_dataframe = append_series(new_series.alias(column_name), new_dataframe)

                if isinstance(expression, str):
                    when_conditions = []

                    # Get the entire column case
                    if row_span < 0:
                        when_conditions.append('TRUE')

                    # Get in range case
                    elif stop - start > 0:
                        when_conditions.append(f'"$ridx" BETWEEN {start} AND {stop - 1}')

                        if len(row_vseries):
                            if indices := [str(ridx - 1) for ridx in row_vseries[1:]]:
                                when_conditions.append(f'"$ridx" IN ({', '.join(indices)})')

                        when_clause = ' AND '.join(when_conditions)
                        expression = expression.replace('$0', f'"{column_name}"', 1)
                        case_statement = \
f"""
CASE
    WHEN {when_clause}
    THEN {expression}
    ELSE "{column_name}"
END
"""

                        query = f'SET python_enable_replacements = false;'
                        query = \
f"""
{query}
WITH indexed_self AS (
    SELECT
        "{column_name}",
        ROW_NUMBER() OVER () AS "$ridx"
    FROM self
)
SELECT {case_statement}
FROM indexed_self
"""

                        with duckdb.connect() as connection:
                            connection.register('self', self.dfs[dfi])
                            register_sql_functions(connection)

                            new_series = connection.sql(query, params=operation_args).pl().to_series()
                            new_dataframe = append_series(new_series.alias(column_name), new_dataframe)

            except Exception as e:
                print(e)
                globals.send_notification(str(e))
                break

        return new_dataframe

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

            message = str(e)
            globals.send_notification(message)

        return False

    def update_columns_with_sql_from_metadata(self,
                                              dfi:        int,
                                              query:      str,
                                              connection: duckdb.DuckDBPyConnection) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        try:
            query = f'SET python_enable_replacements = false; {query}'
            new_dataframe = connection.sql(query).pl()

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

            return True

        except Exception as e:
            print(e)

            action = ()
            message = str(e)

            if message.startswith('unable to add a column of length '):
                message = 'Column length mismatch. Create a new table?'

                action_data_id = utils.generate_ulid()
                action_name = f"app.apply-pending-table('{action_data_id}')"
                action = ('Create', action_name, action_data_id)

                # We keep the dataframe in a temporary place so that we don't need to re-execute the query
                # when the user proceeds to create a new table.
                globals.pending_action_data[action_data_id] = new_dataframe

            globals.send_notification(message, action)

        return False

    def update_cell_data_block_with_operator_from_metadata(self,
                                                           column:         int,
                                                           row:            int,
                                                           column_span:    int,
                                                           row_span:       int,
                                                           dfi:            int,
                                                           include_header: bool,
                                                           operator_name:  str,
                                                           operation_args: list,
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

            if isinstance(column_dtype, (polars.List, polars.Struct, polars.Object)):
                continue # we don't support updating a list, struct, or object

            expression = build_operation(polars.col(column_name), operator_name, operation_args)

            # Evaluate the expression
            try:
                if isinstance(expression, polars.Expr):
                    # Update the entire column
                    if row_span < 0:
                        self.dfs[dfi] = self.dfs[dfi].with_columns(expression.alias(column_name))

                    # Update the dataframe in range, excluding the header row
                    elif stop - start > 0:
                        when_expression = polars.col('$ridx').is_between(start, stop - 1)
                        if len(row_vseries):
                            when_expression &= polars.col('$ridx').is_in(row_vseries[1:] - 1)
                        self.dfs[dfi] = self.dfs[dfi].with_row_index('$ridx') \
                                                     .with_columns(polars.when(when_expression)
                                                                         .then(expression)
                                                                         .otherwise(polars.col(column_name))
                                                                         .alias(column_name)) \
                                                     .drop('$ridx')

                if isinstance(expression, str):
                    when_conditions = []

                    # Update the entire column case
                    if row_span < 0:
                        when_conditions.append('TRUE')

                    # Update in range case
                    elif stop - start > 0:
                        when_conditions.append(f'"$ridx" BETWEEN {start} AND {stop - 1}')

                        if len(row_vseries):
                            if indices := [str(ridx - 1) for ridx in row_vseries[1:]]:
                                when_conditions.append(f'"$ridx" IN ({', '.join(indices)})')

                        when_clause = ' AND '.join(when_conditions)
                        expression = expression.replace('$0', f'"{column_name}"', 1)
                        case_statement = \
f"""
CASE
    WHEN {when_clause}
    THEN {expression}
    ELSE "{column_name}"
END
"""

                        query = f'SET python_enable_replacements = false;'
                        query = \
f"""
{query}
WITH indexed_self AS (
    SELECT
        "{column_name}",
        ROW_NUMBER() OVER () AS "$ridx"
    FROM self
)
SELECT {case_statement}
FROM indexed_self
"""

                        with duckdb.connect() as connection:
                            connection.register('self', self.dfs[dfi])
                            register_sql_functions(connection)

                            new_series = connection.sql(query, params=operation_args).pl().to_series()
                            self.dfs[dfi] = self.dfs[dfi].with_columns(new_series.alias(column_name))

            except Exception as e:
                print(e)
                globals.send_notification(str(e))
                break

            if not include_header:
                continue # skip header cell

            expression = build_operation(polars.lit(column_name), operator_name, operation_args)

            # Evaluate the expression
            try:
                if isinstance(expression, polars.Expr):
                    replace_with = polars.select(expression).item()

                if isinstance(expression, str):
                    expression = expression.replace('$0', f"e'{column_name}'", 1)

                    query = f'SET python_enable_replacements = false;'
                    query = f'{query} SELECT {expression}'

                    with duckdb.connect() as connection:
                        register_sql_functions(connection)
                        replace_with = connection.sql(query, params=operation_args).pl().item()

            except Exception as e:
                globals.send_notification(str(e))
                break

            # Update the column name
            replace_with = self._generate_new_column_name(dfi, column_name, replace_with)
            self.dfs[dfi] = self.dfs[dfi].rename({column_name: replace_with})

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

            if isinstance(column_dtype, (polars.List, polars.Struct, polars.Object)):
                continue # we don't support updating a list, struct, or object

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

            # Update the column name
            replace_with = self._generate_new_column_name(dfi, column_name, new_value)
            self.dfs[dfi] = self.dfs[dfi].rename({column_name: replace_with})

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
            content_dtype = content.dtypes[content_index]

            column_name = self.dfs[dfi].columns[column]
            column_dtype = self.dfs[dfi].dtypes[column]

            new_dtype = column_dtype if column_dtype != polars.Null \
                                     else content_dtype

            # Update the dataframe in range
            self.dfs[dfi] = self.dfs[dfi].with_columns(
                self.dfs[dfi][:start, column].cast(new_dtype)
                                             .extend(content[:, content_index].cast(new_dtype))
                                             .extend(self.dfs[dfi][stop:, column])
                                             .alias(column_name)
            )

            if not include_header:
                continue # skip header cell

            replace_with = content.columns[content_index]
            replace_with = self._generate_new_column_name(dfi, column_name, replace_with)

            # Update the column name
            self.dfs[dfi] = self.dfs[dfi].rename({column_name: replace_with})

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

            # Remove the number suffix if present
            new_name = re.sub(r'_(\d+)$', '', target_name)

            # Determine a new column name
            column_number = 1
            for column_name in self.dfs[dfi].columns:
                if match := re.match(new_name + r'_(\d+)', column_name):
                    column_number = max(column_number, int(match.group(1)) + 1)
            new_name = f'{new_name}_{column_number}'

            if not left:
                column = column + column_span
            else:
                column = column - column_span + 1

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

    def materialize_view(self,
                         filters:      list,
                         column_names: list[str]) -> bool:
        if len(self.dfs) == 0:
            return False

        if not self.has_main_dataframe:
            return False

        expression = polars.lit(True)

        for index, afilter in enumerate(filters):
            if index == 0:
                expression = afilter['expression']
                continue

            if afilter['operator'] == 'and':
                expression &= afilter['expression']
            else:
                expression |= afilter['expression']

        self.dfs = [self.dfs[0].filter(expression).select(column_names)]
        self.bbs = [self.bbs[0]]

        return True

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

    def reorder_columns_from_metadata(self,
                                      columns: list,
                                      dfi:     int) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        self.dfs[dfi] = self.dfs[dfi].select(columns)

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
                    if dtype in [polars.Datetime, polars.Date]:
                        dformat = utils.get_date_format_string(first_non_null)
                    if dtype in [polars.Time]:
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

    def _generate_new_column_name(self,
                                  dfi:          int,
                                  current_name: str,
                                  replace_with: str) -> str:
        # Remove leading '$' to prevent collision from internal column names
        replace_with = replace_with.lstrip('$')

        def generate_column_name(column_name: str) -> str:
            cnumber = 1
            for cname in self.dfs[dfi].columns:
                if match := re.match(column_name + r'_(\d+)', cname):
                    cnumber = max(cnumber, int(match.group(1)) + 1)
            return f'{column_name}_{cnumber}'

        # Generate a new column name if needed
        if replace_with in ['', None]:
            replace_with = generate_column_name('column')
        else:
            replace_with = str(replace_with)
            if replace_with != current_name \
                    and replace_with in self.dfs[dfi].columns:
                replace_with = generate_column_name(replace_with)

        return replace_with