# test_dax_function.py
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


from datetime import date, datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
from typing import Any
import math
import polars
import pytest

from src.sheet_functions import parse_dax

class TestDaxFunction:

    df = polars.DataFrame(
        {
            'Region'     : [ 'X', 'A', 'A', 'B', 'B', 'C' , 'C', 'C' , 'D', 'E'  ],
            'District'   : [ '1', '2', '3', '4', '5', '6' , '7', '8' , '9', '10' ],
            'City'       : [ 'A', 'B', 'C', 'D', 'E', 'F' , 'G', 'H' , 'I', None ],
            'Sales'      : [ 1  , 2  , 3  , 4  , 5  , 6   , 7  , 8   , 9  , 10   ],
            'Promotions' : [ 5  , 10 , 6  , 9  , 7  , ''  , 8  , None, 8.5, True ],
        },
        schema={
            'Region'     : str,
            'District'   : str,
            'City'       : str,
            'Sales'      : int,
            'Promotions' : str,
        },
        strict=False,
    )

    df2 = polars.DataFrame(
        {
            'OrderID'       : [ 101         , 102         , 103         , 104         , 105          ],
            'OrderDate'     : [ '2023-01-10', '2023-02-15', '2023-03-20', '2023-04-25', '2023-05-30' ],
            'DeliveryTime'  : [ '12:30:13'  , '14:45:14'  , '09:15:15'  , '16:00:16'  , '11:20:17'   ],
            'CustomerID'    : [ 1           , 2           , 3           , 4           , 5            ],
            'Amount'        : [ 250.00      , 150.50      , 320.75      , 450.00      , 275.25       ],
            'Profit'        : [ -20.00      , -10.00      , 50.00       , 150.00      , 250.00       ],
            'Discount'      : [ 0.15        , 0.10        , 0.05        , 0.00        , 0.20         ],
            'PurchaseTimes' : [ 2           , 0           , 2           , 1           , 10           ],
        },
        schema={
            'OrderID'       : int,
            'OrderDate'     : polars.Date,
            'DeliveryTime'  : str,
            'CustomerID'    : int,
            'Amount'        : float,
            'Profit'        : float,
            'Discount'      : float,
            'PurchaseTimes' : int,
        },
        strict=False,
    ).with_columns(polars.col('DeliveryTime').str.strptime(polars.Time, '%H:%M:%S'))

    def _run_expression(self,
                        df:         polars.DataFrame,
                        measure:    str,
                        expression: str) -> Any:
        polars_expr = parse_dax(expression)
        if 'error' in polars_expr:
            return polars_expr['error']
        return df.with_columns(polars_expr['expression'].alias(measure))

    def _argument_count_error_triggered(self,
                                        df:         polars.DataFrame,
                                        expression: str) -> bool:
        error_message = self._run_expression(df, 'Error', expression)
        return error_message.startswith('Invalid argument count for')

    #
    # Aggregation
    #

    def test_approximate_distinct_count(self):
        expression = 'No_Distinct_Region = APPROXIMATEDISTINCTCOUNT([Region])'
        df = self._run_expression(self.df, 'No_Distinct_Region', expression)
        assert df[0, 'No_Distinct_Region'] == 6

        expression = 'Error = APPROXIMATEDISTINCTCOUNT()'
        assert self._argument_count_error_triggered(self.df, expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = 'Error = APPROXIMATEDISTINCTCOUNT([Undefined])'
            self._run_expression(self.df, 'Error', expression)

            expression = 'Error = APPROXIMATEDISTINCTCOUNT(99)'
            self._run_expression(self.df, 'Error', expression)

    def test_average(self):
        expression = 'AVG_Sales = AVERAGE([Sales])'
        df = self._run_expression(self.df, 'AVG_Sales', expression)
        assert df[0, 'AVG_Sales'] == 5.5

        expression = 'Error = AVERAGE()'
        assert self._argument_count_error_triggered(self.df, expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = 'Error = AVERAGE([Undefined])'
            self._run_expression(self.df, 'Error', expression)

            expression = 'Error = AVERAGE(99)'
            self._run_expression(self.df, 'Error', expression)

    def test_average_a(self):
        expression = 'AVG_Promotions = AVERAGEA([Promotions])'
        df = self._run_expression(self.df, 'AVG_Promotions', expression)
        assert df[0, 'AVG_Promotions'] == 6.8125

        expression = 'Error = AVERAGEA()'
        assert self._argument_count_error_triggered(self.df, expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = 'Error = AVERAGEA([Undefined])'
            self._run_expression(self.df, 'Error', expression)

            expression = 'Error = AVERAGEA(99)'
            self._run_expression(self.df, 'Error', expression)

    def test_count(self):
        expression = 'No_City = COUNT([City])'
        df = self._run_expression(self.df, 'No_City', expression)
        assert df[0, 'No_City'] == 9

        expression = 'Error = COUNT()'
        assert self._argument_count_error_triggered(self.df, expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = 'Error = COUNT([Undefined])'
            self._run_expression(self.df, 'Error', expression)

            expression = 'Error = COUNT(99)'
            self._run_expression(self.df, 'Error', expression)

    def test_count_a(self):
        expression = 'No_Promoted_City = COUNTA([Promotions])'
        df = self._run_expression(self.df, 'No_Promoted_City', expression)
        assert df[0, 'No_Promoted_City'] == 8

        expression = 'Error = COUNTA()'
        assert self._argument_count_error_triggered(self.df, expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = 'Error = COUNTA([Undefined])'
            self._run_expression(self.df, 'Error', expression)

            expression = 'Error = COUNTA(99)'
            self._run_expression(self.df, 'Error', expression)

    def test_count_blank(self):
        expression = 'No_City_Without_Promotion = COUNTBLANK([Promotions])'
        df = self._run_expression(self.df, 'No_City_Without_Promotion', expression)
        assert df[0, 'No_City_Without_Promotion'] == 1

        expression = 'Error = COUNTBLANK()'
        assert self._argument_count_error_triggered(self.df, expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = 'Error = COUNTBLANK([Undefined])'
            self._run_expression(self.df, 'Error', expression)

            expression = 'Error = COUNTBLANK(99)'
            self._run_expression(self.df, 'Error', expression)

    def test_count_rows(self):
        expression = 'No_Rows = COUNTROWS()'
        df = self._run_expression(self.df, 'No_Rows', expression)
        assert df[0, 'No_Rows'] == 10

    def test_distinct_count(self):
        expression = 'No_Distinct_Region = DISTINCTCOUNT([Region])'
        df = self._run_expression(self.df, 'No_Distinct_Region', expression)
        assert df[0, 'No_Distinct_Region'] == 6

        expression = 'Error = DISTINCTCOUNT()'
        assert self._argument_count_error_triggered(self.df, expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = 'Error = DISTINCTCOUNT([Undefined])'
            self._run_expression(self.df, 'Error', expression)

            expression = 'Error = DISTINCTCOUNT(99)'
            self._run_expression(self.df, 'Error', expression)

    def test_distinct_no_blank_count(self):
        expression = 'No_Distinct_Region = DISTINCTCOUNTNOBLANK([City])'
        df = self._run_expression(self.df, 'No_Distinct_Region', expression)
        assert df[0, 'No_Distinct_Region'] == 9

        expression = 'Error = DISTINCTCOUNTNOBLANK()'
        assert self._argument_count_error_triggered(self.df, expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = 'Error = DISTINCTCOUNTNOBLANK([Undefined])'
            self._run_expression(self.df, 'Error', expression)

            expression = 'Error = DISTINCTCOUNTNOBLANK(99)'
            self._run_expression(self.df, 'Error', expression)

    def test_max(self):
        expression = 'Max_Sales = MAX([Sales])'
        df = self._run_expression(self.df, 'Max_Sales', expression)
        assert df[0, 'Max_Sales'] == 10

        expression = 'Error = MAX()'
        assert self._argument_count_error_triggered(self.df, expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = 'Error = MAX([Undefined])'
            self._run_expression(self.df, 'Error', expression)

            expression = 'Error = MAX(99)'
            self._run_expression(self.df, 'Error', expression)

    def test_max_a(self):
        expression = 'Max_Promotions = MAXA([Promotions])'
        df = self._run_expression(self.df, 'Max_Promotions', expression)
        assert df[0, 'Max_Promotions'] == 10

        expression = 'Error = MAXA()'
        assert self._argument_count_error_triggered(self.df, expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = 'Error = MAXA([Undefined])'
            self._run_expression(self.df, 'Error', expression)

            expression = 'Error = MAXA(99)'
            self._run_expression(self.df, 'Error', expression)

    def test_min(self):
        expression = 'Min_Sales = MIN([Sales])'
        df = self._run_expression(self.df, 'Min_Sales', expression)
        assert df[0, 'Min_Sales'] == 1

        expression = 'Error = MIN()'
        assert self._argument_count_error_triggered(self.df, expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = 'Error = MIN([Undefined])'
            self._run_expression(self.df, 'Error', expression)

            expression = 'Error = MIN(99)'
            self._run_expression(self.df, 'Error', expression)

    def test_min_a(self):
        expression = 'Min_Promotions = MINA([Promotions])'
        df = self._run_expression(self.df, 'Min_Promotions', expression)
        assert df[0, 'Min_Promotions'] == 1

        expression = 'Error = MINA()'
        assert self._argument_count_error_triggered(self.df, expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = 'Error = MINA([Undefined])'
            self._run_expression(self.df, 'Error', expression)

            expression = 'Error = MINA(99)'
            self._run_expression(self.df, 'Error', expression)

    def test_product(self):
        expression = 'Product_Sales = PRODUCT([Sales])'
        df = self._run_expression(self.df, 'Product_Sales', expression)
        assert df[0, 'Product_Sales'] == 3628800

        expression = 'Error = PRODUCT()'
        assert self._argument_count_error_triggered(self.df, expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = 'Error = PRODUCT([Undefined])'
            self._run_expression(self.df, 'Error', expression)

            expression = 'Error = PRODUCT(99)'
            self._run_expression(self.df, 'Error', expression)

    def test_sum(self):
        expression = 'Sum_Sales = SUM([Sales])'
        df = self._run_expression(self.df, 'Sum_Sales', expression)
        assert df[0, 'Sum_Sales'] == 55

        expression = 'Error = SUM()'
        assert self._argument_count_error_triggered(self.df, expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = 'Error = SUM([Undefined])'
            self._run_expression(self.df, 'Error', expression)

            expression = 'Error = SUM(99)'
            self._run_expression(self.df, 'Error', expression)

    #
    # Date and time
    #

    def test_date(self):
        expression = '1st_Day_of_Sales = DATE(2025, 10, 13)'
        df = self._run_expression(self.df2, '1st_Day_of_Sales', expression)
        assert df[0, '1st_Day_of_Sales'].year == 2025
        assert df[0, '1st_Day_of_Sales'].month == 10
        assert df[0, '1st_Day_of_Sales'].day == 13

        with pytest.raises(polars.exceptions.ComputeError):
            expression = 'Error = DATE(2025, 99, 15)'
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = DATE()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_date_diff(self):
        test_cases = [
            {'expression': "DATEDIFF('2025-10-13', '2025-10-14', DAY)",     'column': 'Business_Age',  'expected': 1},
            {'expression': "DATEDIFF('2025-10-14', '2025-10-13', DAY)",     'column': 'Before_Launch', 'expected': -1},
            {'expression': "DATEDIFF('2025-10-13', '2025-10-14', HOUR)",    'column': 'Business_Age',  'expected': 24},
            {'expression': "DATEDIFF('2025-10-13', '2025-10-14', MINUTE)",  'column': 'Business_Age',  'expected': 1440},
            {'expression': "DATEDIFF('2025-10-13', '2025-10-14', SECOND)",  'column': 'Business_Age',  'expected': 86400},
            {'expression': "DATEDIFF('2025-10-13', '2026-10-14', YEAR)",    'column': 'Until_IPO',     'expected': 1},
            {'expression': "DATEDIFF('2025-10-13', '2026-10-14', QUARTER)", 'column': 'Until_IPO',     'expected': 4},
            {'expression': "DATEDIFF('2025-10-13', '2026-10-14', MONTH)",   'column': 'Until_IPO',     'expected': 12},
            {'expression': "DATEDIFF('2025-10-13', '2026-10-14', WEEK)",    'column': 'Until_IPO',     'expected': 52},
            {'expression': "DATEDIFF([OrderDate],  '2026-10-14', DAY)",     'column': 'Until_IPO',     'expected': 1373},
        ]

        for case in test_cases:
            full_expression = f"{case['column']} = {case['expression']}"
            df = self._run_expression(self.df2, case['column'], full_expression)
            assert df[0, case['column']] == case['expected']

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = DATEDIFF('2025-10-13', '2025-10-99', DAY)"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = DATEDIFF('2025-10-13', [Undefined], DAY)"
            self._run_expression(self.df2, 'Error', expression)

        expression = "Error = DATEDIFF('2025-10-13', '2025-10-14', MILLISECOND)"
        error_message = self._run_expression(self.df2, 'Error', expression)
        error_message.startswith('Invalid type of argument 3 for')

        expression = 'Error = DATEDIFF()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_date_value(self):
        test_cases = [
            '2025-10-15 10:30:00',
            '2025-10-15T10:30:00',
            '2025/10/15 10:30:00',
            '10/15/2025 10:30:00',
            '15/10/2025 10:30:00',
            'Oct 15, 2025 10:30 AM',
            'October 15, 2025 10:30 AM',
            '2025-10-15',
            '10/15/2025',
            '15/10/2025',
            'October 15, 2025',
            'Oct 15, 2025',
            '15-Oct-2025',
            '15 October 2025',
            '20251015',
        ]

        for date_str in test_cases:
            expression = f"2nd_Day_of_Sales = DATEVALUE('{date_str}')"
            df = self._run_expression(self.df2, '2nd_Day_of_Sales', expression)
            assert df[0, '2nd_Day_of_Sales'].year == 2025
            assert df[0, '2nd_Day_of_Sales'].month == 10
            assert df[0, '2nd_Day_of_Sales'].day == 15

        with pytest.raises(polars.exceptions.ComputeError):
            expression = "Error = DATEVALUE('2025-99-15')"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = DATEVALUE()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_day(self):
        expression = "3rd_Day_of_Sales = DAY('2025-10-17')"
        df = self._run_expression(self.df2, '3rd_Day_of_Sales', expression)
        assert df[0, '3rd_Day_of_Sales'] == 17

        expression = f"3rd_Day_of_Sales = DAY([OrderDate])"
        df = self._run_expression(self.df2, '3rd_Day_of_Sales', expression)
        assert df[0, '3rd_Day_of_Sales'] == 10

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = DAY('2025-10-99')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = DAY([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = DAY()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_e_date(self):
        expression = "Expiration_Date = EDATE('2025-10-31', 4)"
        df = self._run_expression(self.df2, 'Expiration_Date', expression)
        assert df[0, 'Expiration_Date'].year == 2026
        assert df[0, 'Expiration_Date'].month == 2
        assert df[0, 'Expiration_Date'].day == 28

        expression = "Expiration_Date = EDATE('2025-10-31', '4')"
        df = self._run_expression(self.df2, 'Expiration_Date', expression)
        assert df[0, 'Expiration_Date'].year == 2026
        assert df[0, 'Expiration_Date'].month == 2
        assert df[0, 'Expiration_Date'].day == 28

        expression = f"Expiration_Date = EDATE([OrderDate], 4)"
        df = self._run_expression(self.df2, 'Expiration_Date', expression)
        assert df[0, 'Expiration_Date'].year == 2023
        assert df[0, 'Expiration_Date'].month == 5
        assert df[0, 'Expiration_Date'].day == 10

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = EDATE('2025-10-99', 4)"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = EDATE([Undefined], 4)"
            self._run_expression(self.df2, 'Error', expression)

        expression = "Expiration_Date = EDATE('2025-10-31', '4 MONTH')"
        error_message = self._run_expression(self.df2, 'Expiration_Date', expression)
        assert error_message.startswith('invalid literal for int() with base 10')

        expression = 'Error = EDATE()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_e_o_month(self):
        expression = "Expiration_Date = EOMONTH('2025-10-19', 4)"
        df = self._run_expression(self.df2, 'Expiration_Date', expression)
        assert df[0, 'Expiration_Date'].year == 2026
        assert df[0, 'Expiration_Date'].month == 2
        assert df[0, 'Expiration_Date'].day == 28

        expression = "Expiration_Date = EOMONTH('2025-10-19', '4')"
        df = self._run_expression(self.df2, 'Expiration_Date', expression)
        assert df[0, 'Expiration_Date'].year == 2026
        assert df[0, 'Expiration_Date'].month == 2
        assert df[0, 'Expiration_Date'].day == 28

        expression = f"Expiration_Date = EOMONTH([OrderDate], 4)"
        df = self._run_expression(self.df2, 'Expiration_Date', expression)
        assert df[0, 'Expiration_Date'].year == 2023
        assert df[0, 'Expiration_Date'].month == 5
        assert df[0, 'Expiration_Date'].day == 31

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = EOMONTH('2025-10-99', 4)"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = EOMONTH([Undefined], 4)"
            self._run_expression(self.df2, 'Error', expression)

        expression = "Expiration_Date = EOMONTH('2025-10-19', '4 MONTH')"
        error_message = self._run_expression(self.df2, 'Expiration_Date', expression)
        assert error_message.startswith('invalid literal for int() with base 10')

        expression = 'Error = EOMONTH()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_hour(self):
        expression = f"Check_In_Hour = HOUR('08:30:00')"
        df = self._run_expression(self.df2, 'Check_In_Hour', expression)
        assert df[0, 'Check_In_Hour'] == 8

        expression = f"DeliveryTime_Hour = HOUR([DeliveryTime])"
        df = self._run_expression(self.df2, 'DeliveryTime_Hour', expression)
        assert df[0, 'DeliveryTime_Hour'] == 12

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = HOUR('99:30:00')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = HOUR([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = HOUR()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_minute(self):
        expression = f"Minute_Threshold = MINUTE('08:30:00')"
        df = self._run_expression(self.df2, 'Minute_Threshold', expression)
        assert df[0, 'Minute_Threshold'] == 30

        expression = f"Minute_Threshold = MINUTE([DeliveryTime])"
        df = self._run_expression(self.df2, 'Minute_Threshold', expression)
        assert df[0, 'Minute_Threshold'] == 30

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = MINUTE('08:99:00')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = MINUTE([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = MINUTE()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_month(self):
        expression = "Month_October = MONTH('2025-10-21')"
        df = self._run_expression(self.df2, 'Month_October', expression)
        assert df[0, 'Month_October'] == 10

        expression = f"OrderDate_Month = MONTH([OrderDate])"
        df = self._run_expression(self.df2, 'OrderDate_Month', expression)
        assert df[0, 'OrderDate_Month'] == 1

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = MONTH('2025-99-21')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = MONTH([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = MONTH()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_now(self):
        expression = 'Now = NOW()'
        df = self._run_expression(self.df2, 'Now', expression)
        assert isinstance(df[0, 'Now'], datetime)
        assert df[0, 'Now'].date() == datetime.now().date()
        assert df[0, 'Now'].hour == datetime.now().hour
        assert df[0, 'Now'].minute == datetime.now().minute
        assert df[0, 'Now'].second == datetime.now().second

    def test_quarter(self):
        expression = "3rd_Quarter = QUARTER('2025-10-23')"
        df = self._run_expression(self.df2, '3rd_Quarter', expression)
        assert df[0, '3rd_Quarter'] == 4

        expression = f"OrderDate_Quarter = QUARTER([OrderDate])"
        df = self._run_expression(self.df2, 'OrderDate_Quarter', expression)
        assert df[0, 'OrderDate_Quarter'] == 1

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = QUARTER('2025-10-99')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = QUARTER([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = QUARTER()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_second(self):
        expression = f"Second_Threshold = SECOND('08:30:17')"
        df = self._run_expression(self.df2, 'Second_Threshold', expression)
        assert df[0, 'Second_Threshold'] == 17

        expression = f"DeliveryTime_Second = SECOND([DeliveryTime])"
        df = self._run_expression(self.df2, 'DeliveryTime_Second', expression)
        assert df[0, 'DeliveryTime_Second'] == 13

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = SECOND('08:30:99')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = SECOND([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = SECOND()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_time(self):
        expression = 'Work_Time = TIME(8, 30, 0)'
        df = self._run_expression(self.df2, 'Work_Time', expression)
        assert df[0, 'Work_Time'].hour == 8
        assert df[0, 'Work_Time'].minute == 30
        assert df[0, 'Work_Time'].second == 0

        with pytest.raises(polars.exceptions.ComputeError):
            expression = 'Error = TIME(99, 30, 0)'
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = TIME()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_time_value(self):
        test_cases = [
            '08:30:00',
            '08:30 AM',
            '08:30',
        ]

        for date_str in test_cases:
            expression = f"Check_In = TIMEVALUE('{date_str}')"
            df = self._run_expression(self.df2, 'Check_In', expression)
            assert df[0, 'Check_In'].hour == 8
            assert df[0, 'Check_In'].minute == 30
            assert df[0, 'Check_In'].second == 0

        expression = f"Check_Out = TIMEVALUE([DeliveryTime])"
        df = self._run_expression(self.df2, 'Check_Out', expression)
        assert df[0, 'Check_Out'].hour == 12
        assert df[0, 'Check_Out'].minute == 30
        assert df[0, 'Check_Out'].second == 13

        with pytest.raises(polars.exceptions.ComputeError):
            expression = "Error = TIMEVALUE('08:99:00')"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = TIMEVALUE()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_today(self):
        expression = 'Today = TODAY()'
        df = self._run_expression(self.df2, 'Today', expression)
        assert df[0, 'Today'] == date.today()

    def test_utc_now(self):
        expression = 'Now = UTCNOW()'
        df = self._run_expression(self.df2, 'Now', expression)
        now = datetime.now(timezone.utc)
        assert df[0, 'Now'].date() == now.date()
        assert df[0, 'Now'].hour == now.hour
        assert df[0, 'Now'].minute == now.minute
        assert df[0, 'Now'].second == now.second

    def test_utc_today(self):
        expression = 'Today = UTCTODAY()'
        df = self._run_expression(self.df2, 'Today', expression)
        assert df[0, 'Today'] == datetime.now(timezone.utc).date()

    def test_week_day(self):
        expression = "Weekend = WEEKDAY('2025-10-25')"
        df = self._run_expression(self.df2, 'Weekend', expression)
        assert df[0, 'Weekend'] == 5 # from Sunday (1) to Saturday (7)

        expression = "Weekend = WEEKDAY('2025-10-25', 1)"
        df = self._run_expression(self.df2, 'Weekend', expression)
        assert df[0, 'Weekend'] == 5 # Ibid.

        expression = "Weekend = WEEKDAY('2025-10-25', 2)"
        df = self._run_expression(self.df2, 'Weekend', expression)
        assert df[0, 'Weekend'] == 6 # from Monday (1) to Sunday (7)

        expression = "Weekend = WEEKDAY('2025-10-25', 3)"
        df = self._run_expression(self.df2, 'Weekend', expression)
        assert df[0, 'Weekend'] == 5 # from Monday (0) to Sunday (6)

        expression = f"Weekend = WEEKDAY([OrderDate])"
        df = self._run_expression(self.df2, 'Weekend', expression)
        assert df[0, 'Weekend'] == 1

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = WEEKDAY('2025-99-25')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = WEEKDAY([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = WEEKDAY()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_year(self):
        expression = "Year_2025 = YEAR('2025-10-27')"
        df = self._run_expression(self.df2, 'Year_2025', expression)
        assert df[0, 'Year_2025'] == 2025

        expression = f"OrderDate_Year = YEAR([OrderDate])"
        df = self._run_expression(self.df2, 'OrderDate_Year', expression)
        assert df[0, 'OrderDate_Year'] == 2023

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = YEAR('2025-99-27')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = YEAR([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = YEAR()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_date_add(self):
        expression = "Tomorrow = DATEADD('2025-11-01', 1, DAY)"
        df = self._run_expression(self.df2, 'Tomorrow', expression)
        tomorrow = date(2025, 11, 1) + timedelta(days=1)
        assert df[0, 'Tomorrow'] == tomorrow

        expression = 'Tomorrow = DATEADD([OrderDate], 1, DAY)'
        df = self._run_expression(self.df2, 'Tomorrow', expression)
        tomorrow = df[0, 'OrderDate'] + timedelta(days=1)
        assert df[0, 'Tomorrow'] == tomorrow

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = DATEADD('2025-99-01', 1, DAY)"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = DATEADD([Undefined], 1, DAY)"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = DATEADD()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_end_of_month(self):
        expressions = [
            "End_of_Month = ENDOFMONTH('2025-11-02')",
            "End_of_Month = ENDOFMONTH([OrderDate])"
        ]

        for expression in expressions:
            df = self._run_expression(self.df2, 'End_of_Month', expression)
            target_date = df[0, 'End_of_Month']
            first_of_next_month = date(target_date.year, target_date.month + 1, 1)
            expected_end_of_month = first_of_next_month - timedelta(days=1)
            assert target_date == expected_end_of_month

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = ENDOFMONTH('2025-99-02')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = ENDOFMONTH([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = ENDOFMONTH()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_end_of_quarter(self):

        def get_quarter_end(target: date) -> date:
            if 1 <= target.month <= 3:
                month_day = (3, 31)
            if 4 <= target.month <= 6:
                month_day = (6, 30)
            if 7 <= target.month <= 9:
                month_day = (9, 30)
            if 10 <= target.month <= 12:
                month_day = (12, 31)
            return date(target.year, *month_day)

        expression = "End_of_Quarter = ENDOFQUARTER('2025-11-03')"
        df = self._run_expression(self.df2, 'End_of_Quarter', expression)
        assert df[0, 'End_of_Quarter'] == get_quarter_end(date(2025, 11, 3))

        expression = 'End_of_Quarter = ENDOFQUARTER([OrderDate])'
        df = self._run_expression(self.df2, 'End_of_Quarter', expression)
        assert df[0, 'End_of_Quarter'] == get_quarter_end(df[0, 'OrderDate'])

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = ENDOFQUARTER('2025-99-03')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = ENDOFQUARTER([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = ENDOFQUARTER()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_end_of_year(self):
        expression = "End_of_Year = ENDOFYEAR('2025-11-04')"
        df = self._run_expression(self.df2, 'End_of_Year', expression)
        assert df[0, 'End_of_Year'] == date(2025, 12, 31)

        expression = "End_of_Year = ENDOFYEAR('2025-11-04', '2025-06-30')"
        df = self._run_expression(self.df2, 'End_of_Year', expression)
        assert df[0, 'End_of_Year'] == date(2026, 6, 30)

        expression = "End_of_Year = ENDOFYEAR('2025-01-04', '2025-06-30')"
        df = self._run_expression(self.df2, 'End_of_Year', expression)
        assert df[0, 'End_of_Year'] == date(2025, 6, 30)

        expression = "End_of_Year = ENDOFYEAR([OrderDate])"
        df = self._run_expression(self.df2, 'End_of_Year', expression)
        target_date = df[0, 'End_of_Year']
        assert target_date == date(target_date.year, 12, 31)

        # TODO: support parsing dates without year?
        #       See https://github.com/python/cpython/issues/70647.
        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "End_of_Year = ENDOFYEAR('2025-01-04', 'June 30')"
            df = self._run_expression(self.df2, 'End_of_Year', expression)
            assert df[0, 'End_of_Year'] == date(2025, 6, 30)

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = ENDOFYEAR('2025-99-04')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = ENDOFYEAR([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = ENDOFYEAR()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_first_date(self):
        expression = f"OrderDate_First = FIRSTDATE([OrderDate])"
        df = self._run_expression(self.df2, 'OrderDate_First', expression)
        assert df[0, 'OrderDate_First'] == date(2023, 1, 10)

        expression = f"OrderDate_First = FIRSTDATE('2025-01-05')"
        df = self._run_expression(self.df2, 'OrderDate_First', expression)
        assert df[0, 'OrderDate_First'] == date(2025, 1, 5)

        with pytest.raises(polars.exceptions.ComputeError):
            expression = "Error = FIRSTDATE('2025-99-05')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = FIRSTDATE([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = FIRSTDATE()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_last_date(self):
        expression = f"OrderDate_Last = LASTDATE([OrderDate])"
        df = self._run_expression(self.df2, 'OrderDate_Last', expression)
        assert df[0, 'OrderDate_Last'] == date(2023, 5, 30)

        expression = f"OrderDate_Last = LASTDATE('2025-01-06')"
        df = self._run_expression(self.df2, 'OrderDate_Last', expression)
        assert df[0, 'OrderDate_Last'] == date(2025, 1, 6)

        with pytest.raises(polars.exceptions.ComputeError):
            expression = "Error = LASTDATE('2025-99-06')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = LASTDATE([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = LASTDATE()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_next_day(self):
        expression = f"OrderDate_Next = NEXTDAY('2025-01-07')"
        df = self._run_expression(self.df2, 'OrderDate_Next', expression)
        assert df[0, 'OrderDate_Next'] == date(2025, 1, 8)

        expression = f"OrderDate_Next = NEXTDAY([OrderDate])"
        df = self._run_expression(self.df2, 'OrderDate_Next', expression)
        assert df[0, 'OrderDate_Next'] == df[0, 'OrderDate'] + relativedelta(days=1)

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = NEXTDAY('2025-99-07')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = NEXTDAY([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = NEXTDAY()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_next_month(self):
        expression = f"OrderDate_Next = NEXTMONTH('2025-01-08')"
        df = self._run_expression(self.df2, 'OrderDate_Next', expression)
        assert df[0, 'OrderDate_Next'] == date(2025, 2, 8)

        expression = f"OrderDate_Next = NEXTMONTH([OrderDate])"
        df = self._run_expression(self.df2, 'OrderDate_Next', expression)
        assert df[0, 'OrderDate_Next'] == df[0, 'OrderDate'] + relativedelta(months=1)

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = NEXTMONTH('2025-99-08')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = NEXTMONTH([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = NEXTMONTH()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_next_quarter(self):
        assert False

    def test_next_year(self):
        expression = f"OrderDate_Next = NEXTYEAR('2025-01-10')"
        df = self._run_expression(self.df2, 'OrderDate_Next', expression)
        assert df[0, 'OrderDate_Next'] == date(2026, 1, 10)

        expression = f"OrderDate_Next = NEXTYEAR([OrderDate])"
        df = self._run_expression(self.df2, 'OrderDate_Next', expression)
        assert df[0, 'OrderDate_Next'] == df[0, 'OrderDate'] + relativedelta(years=1)

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = NEXTYEAR('2025-99-10')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = NEXTYEAR([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = NEXTYEAR()'
        assert self._argument_count_error_triggered(self.df2, expression)

    #
    # Filter
    #

    #
    # Financial
    #

    #
    # Information
    #

    #
    # Logical
    #

    def test_and(self):
        expression = "We_Are_Right = AND(TRUE(), TRUE())"
        df = self._run_expression(self.df2, 'We_Are_Right', expression)
        assert df[0, 'We_Are_Right'] == True

        expression = "We_Are_Right = AND(1 < 2, 2 < 3)"
        df = self._run_expression(self.df2, 'We_Are_Right', expression)
        assert df[0, 'We_Are_Right'] == True

        expression = "We_Are_Right = AND(200 < [Amount], '2023-01-05' < [OrderDate])"
        df = self._run_expression(self.df2, 'We_Are_Right', expression)
        assert df[0, 'We_Are_Right'] == True

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = AND('Invalid', TRUE())"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = AND([Undefined], TRUE())"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = AND()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_bit_and(self):
        expression = "Bit_And = BITAND(1, 3)"
        df = self._run_expression(self.df2, 'Bit_And', expression)
        assert df[0, 'Bit_And'] == 1 # 0001 & 0011 = 0001

        expression = "Bit_And = BITAND(1, 2)"
        df = self._run_expression(self.df2, 'Bit_And', expression)
        assert df[0, 'Bit_And'] == 0 # 0001 & 0010 = 0000

        expression = "Bit_And = BITAND([OrderID], [CustomerID])"
        df = self._run_expression(self.df2, 'Bit_And', expression)
        assert df[0, 'Bit_And'] == 1 # 101 & 1 = 0001

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = BITAND('Invalid', TRUE())"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = BITAND([Undefined], TRUE())"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = BITAND()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_bit_or(self):
        expression = "Bit_Or = BITOR(1, 3)"
        df = self._run_expression(self.df2, 'Bit_Or', expression)
        assert df[0, 'Bit_Or'] == 3 # 0001 | 0011 = 0011

        expression = "Bit_Or = BITOR(1, 2)"
        df = self._run_expression(self.df2, 'Bit_Or', expression)
        assert df[0, 'Bit_Or'] == 3 # 0001 | 0010 = 0011

        expression = "Bit_Or = BITOR([OrderID], [CustomerID])"
        df = self._run_expression(self.df2, 'Bit_Or', expression)
        assert df[0, 'Bit_Or'] == 101 # 101 | 1 = 0101

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = BITOR('Invalid', TRUE())"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = BITOR([Undefined], TRUE())"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = BITOR()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_bit_xor(self):
        expression = "Bit_Xor = BITXOR(1, 3)"
        df = self._run_expression(self.df2, 'Bit_Xor', expression)
        assert df[0, 'Bit_Xor'] == 2 # 0001 ^ 0011 = 0010

        expression = "Bit_Xor = BITXOR(1, 2)"
        df = self._run_expression(self.df2, 'Bit_Xor', expression)
        assert df[0, 'Bit_Xor'] == 3 # 0001 ^ 0010 = 0011

        expression = "Bit_Xor = BITXOR([OrderID], [CustomerID])"
        df = self._run_expression(self.df2, 'Bit_Xor', expression)
        assert df[0, 'Bit_Xor'] == 100 # 101 ^ 1 = 0100

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = BITXOR('Invalid', TRUE())"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = BITXOR([Undefined], TRUE())"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = BITXOR()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_false(self):
        expression = "We_Always_Right = FALSE()"
        df = self._run_expression(self.df2, 'We_Always_Right', expression)
        assert df[0, 'We_Always_Right'] == False

    def test_not(self):
        expression = "Not = NOT(5)"
        df = self._run_expression(self.df2, 'Not', expression)
        assert df[0, 'Not'] == -6 # ~5 = -5 - 1 = -6

        expression = "Not = NOT([OrderID])"
        df = self._run_expression(self.df2, 'Not', expression)
        assert df[0, 'Not'] == -102 # ~101 = -101 - 1 = -102

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = NOT('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "x = NOT([Undefined])"
            self._run_expression(self.df2, 'x', expression)

        expression = 'Error = NOT()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_or(self):
        expression = "We_Are_Right = OR(TRUE(), FALSE())"
        df = self._run_expression(self.df2, 'We_Are_Right', expression)
        assert df[0, 'We_Are_Right'] == True

        expression = "We_Are_Right = OR(10 < 2, 2 < 30)"
        df = self._run_expression(self.df2, 'We_Are_Right', expression)
        assert df[0, 'We_Are_Right'] == True

        expression = "We_Are_Right = OR(1000 < [Amount], '2023-01-05' < [OrderDate])"
        df = self._run_expression(self.df2, 'We_Are_Right', expression)
        assert df[0, 'We_Are_Right'] == True

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = OR('Invalid', TRUE())"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = OR([Undefined], TRUE())"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = OR()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_true(self):
        expression = "We_Always_Wrong = TRUE()"
        df = self._run_expression(self.df2, 'We_Always_Wrong', expression)
        assert df[0, 'We_Always_Wrong'] == True

    #
    # Math and trigonometry
    #

    def test_abs(self):
        expression = 'Always_Positive = ABS(-17)'
        df = self._run_expression(self.df2, 'Always_Positive', expression)
        assert df[0, 'Always_Positive'] == abs(-17)

        expression = 'Keep_Positive = ABS(99)'
        df = self._run_expression(self.df2, 'Keep_Positive', expression)
        assert df[0, 'Keep_Positive'] == abs(99)

        expression = 'Manipulated_Profit = ABS([Profit])'
        df = self._run_expression(self.df2, 'Manipulated_Profit', expression)
        assert df[0, 'Manipulated_Profit'] == abs(df[0, 'Profit'])

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = ABS('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = ABS([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = ABS()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_acos(self):
        expression = 'x = ACOS(0.99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.acos(0.99)

        expression = 'x = ACOS([Discount])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.acos(df[0, 'Discount'])

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = ACOS('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = ACOS([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = ACOS()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_acosh(self):
        expression = 'x = ACOSH(99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.acosh(99)

        expression = 'x = ACOSH([PurchaseTimes])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.acosh(df[0, 'PurchaseTimes'])

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = ACOSH('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = ACOSH([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = ACOSH()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_acot(self):
        expression = 'x = ACOT(99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.atan(1 / 99)

        expression = 'x = ACOT([PurchaseTimes])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.atan(1 / df[0, 'PurchaseTimes'])

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = ACOT('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = ACOT([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = ACOT()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_acoth(self):
        expression = 'x = ACOTH(99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.atanh(1 / 99)

        expression = 'x = ACOTH([PurchaseTimes])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.atanh(1 / df[0, 'PurchaseTimes'])

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = ACOTH('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = ACOTH([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = ACOTH()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_asin(self):
        expression = 'x = ASIN(0.99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.asin(0.99)

        expression = 'x = ASIN([Discount])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.asin(df[0, 'Discount'])

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = ASIN('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = ASIN([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = ASIN()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_asinh(self):
        expression = 'x = ASINH(99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.asinh(99)

        expression = 'x = ASINH([PurchaseTimes])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.asinh(df[0, 'PurchaseTimes'])

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = ASINH('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = ASINH([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = ASINH()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_atan(self):
        expression = 'x = ATAN(99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.atan(99)

        expression = 'x = ATAN([PurchaseTimes])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.atan(df[0, 'PurchaseTimes'])

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = ATAN('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = ATAN([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = ATAN()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_atanh(self):
        expression = 'x = ATANH(0.99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.atanh(0.99)

        expression = 'x = ATANH([Discount])'
        df = self._run_expression(self.df2, 'x', expression)
        assert math.isclose(df[0, 'x'], math.atanh(df[0, 'Discount']))

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = ATANH('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = ATANH([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = ATANH()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_cos(self):
        expression = 'x = COS(99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.cos(99)

        expression = 'x = COS([PurchaseTimes])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.cos(df[0, 'PurchaseTimes'])

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = COS('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = COS([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = COS()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_cosh(self):
        expression = 'x = COSH(99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.cosh(99)

        expression = 'x = COSH([PurchaseTimes])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.cosh(df[0, 'PurchaseTimes'])

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = COSH('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = COSH([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = COSH()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_cot(self):
        expression = 'x = COT(99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == 1 / math.tan(99)

        expression = 'x = COT([PurchaseTimes])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == 1 / math.tan(df[0, 'PurchaseTimes'])

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = COT('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = COT([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = COT()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_degrees(self):
        expression = 'x = DEGREES(99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.degrees(99)

        expression = 'x = DEGREES([PurchaseTimes])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.degrees(df[0, 'PurchaseTimes'])

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = DEGREES('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = DEGREES([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = DEGREES()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_divide(self):
        expression = 'x = DIVIDE(17, 99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == 17 / 99

        expression = 'x = DIVIDE(0, 99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == 0

        expression = 'x = DIVIDE(17, 0)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.inf

        expression = 'x = DIVIDE(0, 0)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == None

        expression = 'x = DIVIDE(0, 0, -1)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == -1

        expression = 'x = DIVIDE([PurchaseTimes], 99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == df[0, 'PurchaseTimes'] / 99

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = DIVIDE('Invalid', 99)"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = DIVIDE([Undefined], 99)"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = DIVIDE()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_even(self):
        expression = 'x = EVEN(18)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == 18

        expression = 'x = EVEN(99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == 100

        expression = 'x = EVEN([PurchaseTimes])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == 2

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = EVEN('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = EVEN([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = EVEN()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_odd(self):
        expression = 'x = ODD(17)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == 17

        expression = 'x = ODD(98)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == 99

        expression = 'x = ODD([PurchaseTimes])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == 3

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = ODD('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = ODD([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = ODD()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_pi(self):
        expression = "Pi = PI()"
        df = self._run_expression(self.df2, 'Pi', expression)
        assert df[0, 'Pi'] == math.pi

    def test_exp(self):
        expression = 'x = EXP(99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.exp(99)

        expression = 'x = EXP([PurchaseTimes])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.exp(df[0, 'PurchaseTimes'])

        expression = "x = EXP('Invalid')"
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == None

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = EXP([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = EXP()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_ln(self):
        expression = 'x = LN(99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.log(99)

        expression = 'x = LN([PurchaseTimes])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.log(df[0, 'PurchaseTimes'])

        expression = "x = LN('Invalid')"
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == None

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = LN([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = LN()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_log(self):
        expression = 'x = LOG(99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.log(99)

        expression = 'x = LOG(99, 2)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.log(99, 2)

        expression = 'x = LOG([PurchaseTimes])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.log(df[0, 'PurchaseTimes'])

        expression = "x = LOG('Invalid')"
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == None

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "x = LOG([Undefined])"
            self._run_expression(self.df2, 'x', expression)

        expression = 'Error = LOG()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_log_10(self):
        expression = 'x = LOG10(99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.log(99, 10)

        expression = 'x = LOG10([PurchaseTimes])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.log(df[0, 'PurchaseTimes'], 10)

        expression = "x = LOG10('Invalid')"
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == None

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "x = LOG10([Undefined])"
            self._run_expression(self.df2, 'x', expression)

        expression = 'Error = LOG10()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_power(self):
        expression = 'x = POWER(17, 2)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == 17 ** 2

        expression = 'x = POWER(0, 99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == 0

        expression = 'x = POWER(17, 0)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == 1

        expression = 'x = POWER(0, 0)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == 1

        expression = 'x = POWER([PurchaseTimes], 2)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == df[0, 'PurchaseTimes'] ** 2

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = POWER('Invalid', 2)"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = POWER([Undefined], 2)"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = POWER()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_radians(self):
        expression = 'x = RADIANS(99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.radians(99)

        expression = 'x = RADIANS([PurchaseTimes])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.radians(df[0, 'PurchaseTimes'])

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = RADIANS('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "x = RADIANS([Undefined])"
            self._run_expression(self.df2, 'x', expression)

        expression = 'Error = RADIANS()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_sign(self):
        expression = 'x = SIGN(17)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == 1

        expression = 'x = SIGN(-99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == -1

        expression = 'x = SIGN([Profit])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == -1

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = SIGN('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "x = SIGN([Undefined])"
            self._run_expression(self.df2, 'x', expression)

        expression = 'Error = SIGN()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_sin(self):
        expression = 'x = SIN(0.99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.sin(0.99)

        expression = 'x = SIN([Discount])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.sin(df[0, 'Discount'])

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = SIN('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = SIN([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = SIN()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_sinh(self):
        expression = 'x = SINH(0.99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.sinh(0.99)

        expression = 'x = SINH([Discount])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.sinh(df[0, 'Discount'])

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = SINH('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = SINH([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = SINH()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_sqrt(self):
        expression = 'x = SQRT(99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.sqrt(99)

        expression = 'x = SQRT([Amount])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.sqrt(df[0, 'Amount'])

        expression = "x = SQRT('Invalid')"
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == None

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = SQRT([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = SQRT()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_sqrt_pi(self):
        expression = 'x = SQRTPI(99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.sqrt(99 * math.pi)

        expression = 'x = SQRTPI([Amount])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.sqrt(df[0, 'Amount'] * math.pi)

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = SQRTPI('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = SQRTPI([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = SQRTPI()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_tan(self):
        expression = 'x = TAN(0.99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.tan(0.99)

        expression = 'x = TAN([Discount])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.tan(df[0, 'Discount'])

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = TAN('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = TAN([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = TAN()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_tanh(self):
        expression = 'x = TANH(0.99)'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.tanh(0.99)

        expression = 'x = TANH([Discount])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == math.tanh(df[0, 'Discount'])

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = TANH('Invalid')"
            self._run_expression(self.df2, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = TANH([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = TANH()'
        assert self._argument_count_error_triggered(self.df2, expression)

    #
    # Statistical
    #

    #
    # Text
    #

    def test_len(self):
        expression = "x = LEN('Some text')"
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == len('Some text')

        expression = 'x = LEN([City])'
        df = self._run_expression(self.df, 'x', expression)
        assert df[0, 'x'] == len(df[0, 'City'])

        expression = 'x = LEN([OrderID])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == len(str(df[0, 'OrderID']))

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = LEN([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = LEN()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_lower(self):
        expression = "x = LOWER('Some text')"
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == 'Some text'.lower()

        expression = 'x = LOWER([City])'
        df = self._run_expression(self.df, 'x', expression)
        assert df[0, 'x'] == df[0, 'City'].lower()

        expression = 'x = LOWER([OrderID])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == str(df[0, 'OrderID']).lower()

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = LOWER([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = LOWER()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_upper(self):
        expression = "x = UPPER('Some text')"
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == 'Some text'.upper()

        expression = 'x = UPPER([City])'
        df = self._run_expression(self.df, 'x', expression)
        assert df[0, 'x'] == df[0, 'City'].upper()

        expression = 'x = UPPER([OrderID])'
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == str(df[0, 'OrderID']).upper()

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = UPPER([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = UPPER()'
        assert self._argument_count_error_triggered(self.df2, expression)

    def test_value(self):
        expression = "x = VALUE('1799')"
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == 1799

        expression = "x = VALUE('17.99')"
        df = self._run_expression(self.df2, 'x', expression)
        assert df[0, 'x'] == 17.99

        expression = 'x = VALUE([District])'
        df = self._run_expression(self.df, 'x', expression)
        assert df[0, 'x'] == int(df[0, 'District'])

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = "Error = VALUE('Invalid')"
            self._run_expression(self.df, 'Error', expression)

        with pytest.raises(polars.exceptions.InvalidOperationError):
            expression = 'Error = VALUE([City])'
            self._run_expression(self.df, 'Error', expression)

        with pytest.raises(polars.exceptions.ColumnNotFoundError):
            expression = "Error = VALUE([Undefined])"
            self._run_expression(self.df2, 'Error', expression)

        expression = 'Error = VALUE()'
        assert self._argument_count_error_triggered(self.df2, expression)

    #
    # Other
    #

    def test_blank(self):
        expression = 'Blank = BLANK()'
        df = self._run_expression(self.df2, 'Blank', expression)
        assert df[0, 'Blank'] == None