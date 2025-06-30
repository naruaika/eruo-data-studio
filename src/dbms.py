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

from enum import Enum
import polars

from gi.repository import Gio, GObject

from .utils import print_log, Log

WITH_ROW_INDEX: bool = True

class DBMS(GObject.Object):
    __gtype_name__ = 'DBMS'

    file: Gio.File | None = None
    data_frame: polars.DataFrame = polars.DataFrame()

    fill_counts: list[int] = []

    def __init__(self) -> None:
        super().__init__()

    def get_data(self, row: int, col: int) -> str:
        """
        Get the data from a cell.

        Args:
            row (int): The row index of the cell.
            col (int): The column index of the cell.

        Returns:
            str: The data from the cell.
        """
        return self.data_frame[row, col + WITH_ROW_INDEX]

    def set_data(self, row: int, col: int, value: any) -> None:
        """
        Set the data in a cell.

        Args:
            row (int): The row index of the cell.
            col (int): The column index of the cell.
            value (any): The value to be set in the cell.
        """
        self.data_frame[row, col + WITH_ROW_INDEX] = value

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

    def get_column_unique_values(self, col_index: int) -> list[str]:
        """
        Get the unique values in a column.

        Args:
            col_index (int): The index of the column to get unique values for.

        Returns:
            list[str]: A list of unique values in the specified column.
        """
        col_name = self.data_frame.columns[col_index + WITH_ROW_INDEX]
        col_data = self.data_frame.get_column(col_name)
        if col_data.dtype in [polars.Categorical, polars.Enum, polars.Date, polars.Duration, polars.Time, polars.Boolean, polars.Null]:
            print_log(f'Column {col_name} has {format(col_data.n_unique(), ",d")} unique values: {col_data.unique()}', Log.DEBUG)
        else:
            approx_n_unique = self.data_frame.select(polars.col(col_name).approx_n_unique()).item()
            if approx_n_unique <= 1024:
                print_log(f'Column {col_name} has {format(col_data.n_unique(), ",d")} unique values: {col_data.unique()}', Log.DEBUG)
            else:
                print_log(f'Column {col_name} has approximately {format(approx_n_unique, ",d")} unique values; too many to display.', Log.DEBUG)
                return []
        return col_data.unique().to_list()

    def summary_fill_counts(self) -> None:
        """Calculates the fill counts for each column."""
        print_log('Calculating fill counts...', Log.DEBUG)
        for col_name in self.get_columns():
            fill_count = self.data_frame.shape[0] - self.data_frame[col_name].is_null().sum()
            self.fill_counts.append(fill_count)

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
        print_log(f'Sorting column {col_name} in {direction} order...', Log.DEBUG)

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
            self.data_frame = self.data_frame.with_columns(polars.col(col_name).cast(col_type))
            print_log(f'Converting column {col_name} to {col_type.__name__.lower()}...', Log.DEBUG)
            return True
        except Exception as e:
            print_log(f'Failed to convert column {col_name} to {col_type.__name__.lower()}: {e}', Log.WARNING)
            return False
