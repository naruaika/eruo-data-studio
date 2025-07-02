# dbms.py
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

from datetime import datetime
from tempfile import NamedTemporaryFile
import gc
import polars
import threading

from gi.repository import Gio, GObject

from .utils import print_log, Log

WITH_ROW_INDEX: bool = True

class DBMS(GObject.Object):
    __gtype_name__ = 'DBMS'

    file: Gio.File | None = None
    data_frame: polars.DataFrame = polars.DataFrame()
    fill_counts: list[int] = []

    temp_data_frame: polars.DataFrame = polars.DataFrame()
    temp_data_file_paths: list[str] = []

    pending_values_to_show: list[any] = []
    pending_values_to_hide: list[any] = []
    current_column_index: int = -1
    current_unique_values: polars.Series = polars.Series()
    current_unique_values_hash: str = ''

    previous_column_index: int = -1
    previous_unique_values: list[any] = []

    def __init__(self) -> None:
        super().__init__()

    def get_data(self, row: int, col: int) -> any:
        """
        Get the data from a cell.

        Args:
            row (int): The row index of the cell.
            col (int): The column index of the cell.

        Returns:
            any: The data from the cell.
        """
        return self.data_frame[row, col + WITH_ROW_INDEX]

    def set_data(self, row: int, col: int, value: any) -> bool:
        """
        Set the data in a cell.

        Args:
            row (int): The row index of the cell.
            col (int): The column index of the cell.
            value (any): The value to be set in the cell.
        """
        # Convert the input value to the correct type
        column_dtype = self.get_dtypes()[col]
        if column_dtype == polars.Date:
            try:
                value = datetime.strptime(value, '%Y-%m-%d').date()
            except Exception as e:
                print_log(f'Failed to convert value to {column_dtype} at index ({format(row, ",d")}, {format(col, ",d")}): {e}', Log.WARNING)
                return False
        elif column_dtype == polars.Datetime:
            try:
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except Exception as e:
                print_log(f'Failed to convert value to {column_dtype} at index ({format(row, ",d")}, {format(col, ",d")}): {e}', Log.WARNING)
                return False
        elif column_dtype == polars.Time:
            try:
                value = datetime.strptime(value, '%H:%M:%S').time()
            except Exception as e:
                print_log(f'Failed to convert value to {column_dtype} at index ({format(row, ",d")}, {format(col, ",d")}): {e}', Log.WARNING)
                return False

        try:
            self.data_frame[row, col + WITH_ROW_INDEX] = value
        except Exception as e:
            print_log(f'Failed to update data frame at index ({format(row, ",d")}, {format(col, ",d")}): {e}', Log.WARNING)
            return False

        return True

    def get_shape(self) -> tuple[int, int]:
        """
        Get the shape of the data frame.

        Returns:
            tuple[int, int]: A tuple containing the number of rows and columns in the data frame.
        """
        shape = self.data_frame.shape
        return (shape[0], shape[1] - WITH_ROW_INDEX)

    def get_dtypes(self) -> list[str]:
        """
        Get the data types of the columns in the data frame.

        Returns:
            list[str]: A list of data types in the data frame.
        """
        return self.data_frame.dtypes[WITH_ROW_INDEX:]

    def get_columns(self) -> list[str]:
        """
        Get the columns of the data frame.

        Returns:
            list[str]: A list of column names in the data frame.
        """
        return self.data_frame.columns[WITH_ROW_INDEX:]

    def scan_column_unique_values(self, col_index: int) -> list[str]:
        """
        Get the unique values in a column.

        Args:
            col_index (int): The index of the column to get unique values for.

        Returns:
            list[str]: A list of unique values in the specified column.
        """
        col_index = col_index + WITH_ROW_INDEX
        col_name = self.data_frame.columns[col_index]
        col_data = self.data_frame.get_column(col_name)

        # if col_index == self.previous_column_index:
        #     print_log(f'Column {col_name} has {format(len(self.previous_unique_values), ",d")} unique values: {self.previous_unique_values}', Log.DEBUG)
        #     self.current_unique_values =
        #     return self.previous_unique_values

        if col_data.dtype in [polars.Categorical, polars.Date, polars.Datetime, polars.Time, polars.Duration, polars.Null]:
            n_unique = self.data_frame.select(polars.col(col_name).n_unique()).item()
        else:
            n_unique = self.data_frame.select(polars.col(col_name).approx_n_unique()).item()
        n_unique = min(n_unique, self.data_frame.shape[0])
        if n_unique <= 1_000:
            print_log(f'Column {col_name} has {format(col_data.n_unique(), ",d")} unique values: {col_data.unique()}', Log.DEBUG)
        else:
            print_log(f'Column {col_name} has approximately {format(n_unique, ",d")} unique values; too many to display.', Log.DEBUG)
            sample_size = min(500_000, n_unique)
            sample_data = col_data.sample(sample_size, seed=0).unique().sort()
            self.current_unique_values_hash = sample_data.hash()
            self.current_unique_values = sample_data.head(1_000).to_list()
            self.current_column_index = col_index
            return self.current_unique_values + [f'eruo-data-studio:truncated']

        unique_data = col_data.unique().sort()
        self.current_unique_values_hash = unique_data.hash()
        self.current_unique_values = unique_data.to_list()
        self.current_column_index = col_index
        return self.current_unique_values

    # def cache_column_unique_values(self, col_index: int) -> None:
    #     """
    #     Cache the unique values in a column.

    #     Args:
    #         col_index (int): The index of the column to cache unique values for.
    #     """
    #     col_index += WITH_ROW_INDEX
    #     col_name = self.data_frame.columns[col_index]
    #     col_data = self.data_frame.get_column(col_name)
    #     self.current_column_index = col_index
    #     self.current_unique_values = col_data.unique()
    #     self.current_unique_values_hash = self.current_unique_values.hash()

    # def get_column_unique_values_from_cache(self, filter: str) -> list[str]:
    #     """
    #     Get the unique values in a column from the cache.

    #     Args:
    #         filter (str): The filter to apply to the unique values.

    #     Returns:
    #         list[str]: A list of unique values in the specified column.
    #     """
    #     # TODO: support another data types
    #     # TODO: support advanced filtering
    #     return self.current_unique_values.filter(self.current_unique_values.str.contains(filter)).to_list()

    def write_erquet_file(self) -> None:
        """Writes the data frame to an erquet file."""
        with NamedTemporaryFile(suffix='.erquet', delete=False) as temp_file:
            print_log(f'Writing temporary file: {temp_file.name}', Log.DEBUG)
            self.temp_data_frame.write_parquet(temp_file.name)
            self.temp_data_frame = polars.DataFrame()
            self.temp_data_file_paths.append(temp_file.name)
        gc.collect()

    def summary_fill_counts(self, col_index: int | None = None) -> None:
        """Calculates the fill counts for each column."""
        if col_index is not None:
            col_name = self.data_frame.columns[col_index + WITH_ROW_INDEX]
            fill_count = self.data_frame.shape[0] - self.data_frame.get_column(col_name).is_null().sum()
            if self.data_frame.get_column(col_name).dtype in [polars.String]:
                fill_count -= self.data_frame.filter(polars.col(col_name).str.len_bytes() == 0).shape[0]
            self.fill_counts[col_index] = fill_count
            print_log(f'Calculating fill counts for column: {col_name}...', Log.DEBUG)
            return

        self.fill_counts = []
        for col_index, col_name in enumerate(self.get_columns()):
            fill_count = self.data_frame.shape[0] - self.data_frame.get_column(col_name).is_null().sum()
            if self.data_frame.get_column(col_name).dtype in [polars.String]:
                fill_count -= self.data_frame.filter(polars.col(col_name).str.len_bytes() == 0).shape[0]
            self.fill_counts.append(fill_count)
        print_log('Calculating fill counts for all columns...', Log.DEBUG)

    def sort_column_values(self, col_index: int, descending: bool = False) -> None:
        """
        Sort the values in a column.

        Args:
            col_index (int): The index of the column to sort.
            descending (bool, optional): Whether to sort in descending order. Defaults to False.
        """
        col_name = self.data_frame.columns[col_index + WITH_ROW_INDEX]
        self.data_frame = self.data_frame.sort(col_name, descending=descending, nulls_last=True)
        direction = 'descending' if descending else 'ascending'
        print_log(f'Sorting column \'{col_name}\' in {direction} order...', Log.DEBUG)

    def apply_filter(self) -> bool:
        """Apply a filter to the data frame."""
        if 'meta:all' in self.pending_values_to_show and len(self.pending_values_to_hide) == 0:
            print_log('Applying no filter to data frame...', Log.DEBUG)
            return False

        # Cache previous unique values, so that user can undo filter
        self.previous_column_index = self.current_column_index
        self.previous_unique_values = self.current_unique_values.copy()

        # # Write current data frame to a new temporary file
        # self.temp_data_frame = self.data_frame
        # threading.Thread(target=self.write_erquet_file, daemon=True).start()

        col_name = self.data_frame.columns[self.current_column_index]

        # Apply filter to current data frame
        # TODO: support other data types
        # TODO: support advanced filtering
        if 'meta:all' in self.pending_values_to_show:
            predicates = polars.col(col_name).is_in(self.pending_values_to_hide).not_()
            if 'meta:blank' in self.pending_values_to_hide:
                predicates &= polars.col(col_name).is_not_null()
            self.data_frame = self.data_frame.filter(predicates)
            print_log(f'Applying filter to column \'{col_name}\'...', Log.DEBUG)
            return True

        if 'meta:all' in self.pending_values_to_hide and len(self.pending_values_to_show) > 0:
            predicates = polars.col(col_name).is_in(self.pending_values_to_show)
            if 'meta:blank' in self.pending_values_to_show:
                predicates |= polars.col(col_name).is_null()
            self.data_frame = self.data_frame.filter(predicates)
            print_log(f'Applying filter to column \'{col_name}\'...', Log.DEBUG)
            return True

        return False

    def reset_filter(self) -> None:
        """Reset the filter applied to the data frame."""
        raise NotImplementedError

    def convert_column_to(self, col_index: int, col_type: polars.DataType) -> bool:
        """
        Convert a column to a different data type.

        Args:
            col_index (int): The index of the column to convert.
            col_type (polars.DataType): The data type to convert the column to.

        Returns:
            bool: True if the column was successfully converted, False otherwise.
        """
        col_name = self.data_frame.columns[col_index + WITH_ROW_INDEX]
        try:
            if col_type == polars.Categorical:
                self.data_frame = self.data_frame.with_columns(polars.col(col_name).cast(polars.Categorical('lexical')))
            else:
                self.data_frame = self.data_frame.with_columns(polars.col(col_name).cast(col_type))
            print_log(f'Converting column \'{col_name}\' to {col_type.__name__.lower()}...', Log.DEBUG)
            return True
        except Exception as e:
            print_log(f'Failed to convert column \'{col_name}\' to {col_type.__name__.lower()}: {e}', Log.WARNING)
            return False
