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
import datetime
import gc
import numpy
import polars
import re

from . import globals
from .sheet_document import SheetDocument

class SheetCellBoundingBox(GObject.Object):
    __gtype_name__ = 'SheetCellBoundingBox'

    column: int
    row: int

    column_span: int
    row_span: int

    def __init__(self, column: int, row: int, column_span: int, row_span: int) -> None:
        super().__init__()

        self.column = column
        self.row = row

        self.column_span = column_span
        self.row_span = row_span



class SheetCellMetadata(GObject.Object):
    __gtype_name__ = 'SheetCellMetadata'

    column: int
    row: int

    dfi: int

    def __init__(self, column: int, row: int, dfi: int) -> None:
        super().__init__()

        self.column = column
        self.row = row

        self.dfi = dfi



class SheetData(GObject.Object):
    __gtype_name__ = 'SheetData'

    bbs: list[SheetCellBoundingBox] = [] # visual bounding boxes
    dfs: list[polars.DataFrame | numpy.ndarray] = []
    fes: list[polars.Expr | None] = []

    def __init__(self, document: SheetDocument, dataframe: polars.DataFrame) -> None:
        super().__init__()

        self.document = document

        if dataframe is None:
            return
        self.dfs = [dataframe]
        # TODO: should we support dataframe starting from row > 1 and/or column > 1?
        self.bbs = [SheetCellBoundingBox(1, 1, dataframe.width, dataframe.height + 1)]
        self.fes = [None]

    def get_cell_metadata_from_position(self, column: int, row: int) -> SheetCellMetadata:
        # Handle the locator cells
        column = max(1, column)
        row = max(1, row)

        for bbi, bbs in enumerate(self.bbs):
            if bbs.column <= column < (bbs.column + self.dfs[bbi].width) and bbs.row <= row < (bbs.row + self.dfs[bbi].height + 1):
                column = column - bbs.column
                row = row - bbs.row
                return SheetCellMetadata(column, row, bbi)

        return SheetCellMetadata(-1, -1, -1)

    def read_column_dtype_from_metadata(self, column: int, dfi: int) -> any:
        if dfi < 0 or len(self.dfs) <= dfi:
            return None
        return self.dfs[dfi].dtypes[column]

    def read_cell_data_from_metadata(self, column: int, row: int, column_span: int, row_span: int, dfi: int) -> any:
        if dfi < 0 or len(self.dfs) <= dfi:
            return None

        row -= 1

        # Get the header(s)
        if row < 0:
            df = self.dfs[dfi].columns[column: column + column_span]
            if column_span > 1:
                return df
            else:
                return df[0]

        # Get the content(s)
        if row_span == 1 and column_span == 1:
            return self.dfs[dfi][row, column]
        else:
            return self.dfs[dfi][row:row + row_span, column:column + column_span]

    def read_cell_data_chunks_from_metadata(self, column_names: list[str], row: int, row_span: int, dfi: int) -> any:
        if dfi < 0 or len(self.dfs) <= dfi:
            return None

        if row_span < 0:
            return self.dfs[dfi].select(column_names)
        return self.dfs[dfi].select(column_names)[row:row + row_span]

    def read_cell_bbox_from_metadata(self, dfi: int) -> any:
        if dfi < 0 or len(self.dfs) <= dfi:
            return None
        return self.bbs[dfi]

    def insert_rows_from_metadata(self, row: int, row_span: int, dfi: int) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        empty_rows = polars.DataFrame({
            column_name: polars.Series(
                values=[None] * row_span,
                dtype=column_dtype,
            )
            for column_name, column_dtype in self.dfs[dfi].schema.items()
        })

        self.dfs[dfi] = polars.concat([
            self.dfs[dfi].slice(0, row),
            empty_rows,
            self.dfs[dfi].slice(row),
        ])

        return True

    def insert_columns_from_dataframe(self, dataframe: polars.DataFrame, column: int, dfi: int) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        for counter, column in enumerate(range(column, column + dataframe.width)):
            self.dfs[dfi] = self.dfs[dfi].insert_column(column, dataframe[:, counter])
            self.bbs[dfi].column_span += 1

        del dataframe
        gc.collect()

        return True

    def insert_columns_from_metadata(self, column: int, column_span: int, dfi: int, left: bool = False) -> bool:
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

    def insert_rows_from_dataframe(self, dataframe: polars.DataFrame, row: int, dfi: int) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        self.dfs[dfi] = polars.concat([
            self.dfs[dfi].slice(0, row - 1),
            dataframe,
            self.dfs[dfi].slice(row - 1),
        ])
        self.bbs[dfi].row_span += dataframe.height

        return True

    def update_cell_data_from_metadata(self, column: int, row: int, column_span: int, row_span: int, dfi: int,
                                       replace_with: any, search_pattern: str, match_case: bool) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        if isinstance(replace_with, list):
            return self.update_cell_data_with_array_from_metadata(column, row, column_span, row_span, dfi, replace_with)

        return self.update_cell_data_with_single_from_metadata(column, row, column_span, row_span, dfi,
                                                               replace_with, search_pattern, match_case)

    def update_cell_data_with_single_from_metadata(self, column: int, row: int, column_span: int, row_span: int, dfi: int,
                                                   replace_with: any, search_pattern: str, match_case: bool) -> bool:
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
            if self.dfs[dfi].width <= column:
                break

            column_name = self.dfs[dfi].columns[column]
            column_dtype = self.dfs[dfi].dtypes[column]

            # Cast empty string
            if replace_with == '' and search_pattern is None:
                replace_with = None

            # Convert the input value to the correct type
            if column_dtype in (polars.Date, polars.Datetime, polars.Time):
                if column_dtype == polars.Date:
                    new_value = datetime.strptime(new_value, '%Y-%m-%d').date()
                elif column_dtype == polars.Datetime:
                    new_value = datetime.strptime(new_value, '%Y-%m-%d %H:%M:%S')
                else: # polars.Time
                    new_value = datetime.strptime(new_value, '%H:%M:%S').time()
            else:
                try:
                    new_value = polars.Series([replace_with]).cast(column_dtype)[0]
                except Exception:
                    new_value = str(replace_with)

            # FIXME: exclude the hidden row(s) from being updated
            # Update the entire column
            if row_span < 0:
                self.dfs[dfi] = self.dfs[dfi].with_columns(polars.repeat(new_value, row_count, eager=True, dtype=column_dtype)
                                                                 .alias(column_name))
            # Update the dataframe in range, excluding the header row
            elif stop - start > 0:
                if search_pattern is None:
                    self.dfs[dfi] = self.dfs[dfi].with_columns(
                        self.dfs[dfi][0:start, column].extend(polars.repeat(replace_with, stop - start, eager=True, dtype=column_dtype))
                                                      .extend(self.dfs[dfi][stop:row_count, column])
                                                      .alias(column_name),
                    )
                else:
                    # Pattern is used only for search and replace. The target should always be a single cell
                    # and its value should always a string. Cast empty string if necessary. For the replace
                    # all operation, we call a different function.
                    if self.dfs[dfi][start, column] == search_pattern and replace_with == '':
                        self.dfs[dfi][start, column] = None
                    else:
                        if match_case:
                            self.dfs[dfi][start, column] = self.dfs[dfi][start, column].replace(search_pattern, replace_with)
                        else:
                            self.dfs[dfi][start, column] = re.sub(re.escape(search_pattern), replace_with, self.dfs[dfi][start, column], flags=re.IGNORECASE)

            if row >= 0:
                continue # skip header cell

            # Generate a new column name if needed
            if new_value is None:
                if re.match(r'column_(\d+)', column_name):
                    continue # skip renaming already named column
                cnumber = 1
                for cname in self.dfs[dfi].columns:
                    if match := re.match(r'column_(\d+)', cname):
                        cnumber = max(cnumber, int(match.group(1)) + 1)
                new_value = f'column_{cnumber}'
            else:
                new_value = str(replace_with)

            # Update the column name
            self.dfs[dfi] = self.dfs[dfi].rename({column_name: new_value})

        return True

    def update_cell_data_with_array_from_metadata(self, column: int, row: int, column_span: int, row_span: int, dfi: int, content: list) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        row -= 1

        header = content[0]
        content = content[1]

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

            # Update the dataframe in range, excluding the header row
            if isinstance(content, polars.DataFrame):
                self.dfs[dfi] = self.dfs[dfi].with_columns(
                    self.dfs[dfi][0:start, column].extend(content[:, content_index].cast(column_dtype))
                                                  .extend(self.dfs[dfi][stop:row_count, column])
                                                  .alias(column_name)
                )
            elif content is not None:
                self.dfs[dfi] = self.dfs[dfi].with_columns(
                    self.dfs[dfi][0:start, column].extend(polars.Series([content]).cast(column_dtype))
                                                  .extend(self.dfs[dfi][stop:row_count, column])
                                                  .alias(column_name)
                )

            if header is None:
                continue # skip header cell

            # Update the column name
            if isinstance(header, list):
                self.dfs[dfi] = self.dfs[dfi].rename({column_name: header[content_index]})
            else:
                self.dfs[dfi] = self.dfs[dfi].rename({column_name: header})

        del content
        gc.collect()

        return True

    def update_cell_data_with_chunk_from_metadata(self, column_names: list[str], row: int, row_span: int, dfi: int, content: polars.DataFrame) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        for column_name in column_names:
            column = self.dfs[dfi].columns.index(column_name)
            if row_span < 0: # update the entire column
                self.dfs[dfi] = self.dfs[dfi].with_columns(content[column_name].alias(column_name))
            else: # update within the range
                self.dfs[dfi] = self.dfs[dfi].with_columns(
                    self.dfs[dfi][0:row, column].extend(content[column_name])
                                                .extend(self.dfs[dfi][row + row_span:, column])
                                                .alias(column_name)
                )

        del content
        gc.collect()

        return True

    def duplicate_rows_from_metadata(self, row: int, row_span: int, dfi: int) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        self.dfs[dfi] = polars.concat([
            self.dfs[dfi].slice(0, row + row_span - 1),
            self.dfs[dfi].slice(row - 1, row_span),
            self.dfs[dfi].slice(row + row_span - 1),
        ])
        self.bbs[dfi].row_span += row_span

        return True

    def duplicate_columns_from_metadata(self, column: int, column_span: int, dfi: int, left: bool = False) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

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

    def delete_rows_from_metadata(self, row: int, row_span: int, dfi: int) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        # TODO: should we shift all dataframes below the current selection up?

        row -= 1

        # Prevent from deleting the header row
        if row < 0:
            row = 0
            row_span -= 1

        self.dfs[dfi] = self.dfs[dfi].with_row_index() \
                                     .remove(polars.col('index').is_in(range(row, row + row_span))) \
                                     .drop('index')
        self.bbs[dfi].row_span -= row_span

        return True

    def delete_columns_from_metadata(self, column: int, column_span: int, dfi: int) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        # TODO: should we shift all dataframes on the right side of the current selection to the left?

        column_names = self.dfs[dfi].columns[column:column + column_span]
        self.dfs[dfi] = self.dfs[dfi].drop(column_names)
        self.bbs[dfi].column_span -= column_span

        return True

    def filter_rows_from_metadata(self, column: int, row: int, dfi: int) -> polars.Series:
        if dfi < 0 or len(self.dfs) <= dfi:
            return polars.Series(dtype=polars.Boolean)

        column_name = self.dfs[dfi].columns[column]
        cell_value = self.read_cell_data_from_metadata(column, row, 1, 1, dfi)

        # Update the filter expression
        if self.fes[dfi] is None:
            self.fes[dfi] = polars.col(column_name).is_in([cell_value], nulls_equal=True)
        else:
            self.fes[dfi] = self.fes[dfi] & polars.col(column_name).is_in([cell_value], nulls_equal=True)

        # We don't do the actual filtering on the original dataframe here, instead we
        # just want to get the boolean series to flag which rows should be visible.
        return polars.concat([polars.Series([True]), # for header row
                              self.dfs[dfi].with_columns(self.fes[dfi].alias('$vrow'))['$vrow']])

    def sort_rows_from_metadata(self, column: int, dfi: int, descending: bool = False) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return False

        column_name = self.dfs[dfi].columns[column]
        self.dfs[dfi] = self.dfs[dfi].sort(column_name, descending=descending, nulls_last=True)

        return True

    def convert_columns_dtype_from_metadata(self, column: int, column_span: int, dfi: int, dtype: polars.DataType) -> bool:
        if dfi < 0 or len(self.dfs) <= dfi:
            return

        if isinstance(dtype, polars.Categorical):
            dtype = polars.Categorical('lexical')

        try:
            self.dfs[dfi] = self.dfs[dfi].with_columns(
                **{
                    column_name: polars.col(column_name).cast(dtype)
                        for column, column_name in enumerate(self.dfs[dfi].columns[column:column + column_span], column)
                }
            )
        except Exception:
            globals.send_notification(f'Cannot convert to: {dtype}')
            return False

        return True