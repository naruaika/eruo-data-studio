# utils.py
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


from typing import Literal

# A comprehensive list of common date formats. Order can be important for
# performance and ambiguity resolution; more specific formats should be
# listed before more general ones.
COMMON_DATE_FORMATS = [
    '%s',                 # 1577836800
    '%Y-%m-%d %H:%M:%S',  # 2025-01-15 10:30:00
    '%+',                 # 2025-01-15T10:30:00+0000
    '%Y-%m-%dT%H:%M:%SZ', # 2025-01-15T10:30:00Z
    '%Y-%m-%dT%H:%M:%S',  # 2025-01-15T10:30:00
    '%Y/%m/%d %H:%M:%S',  # 2025/01/15 10:30:00
    '%m/%d/%Y %H:%M:%S',  # 01/15/2025 10:30:00
    '%d/%m/%Y %H:%M:%S',  # 15/01/2025 10:30:00
    '%b %d, %Y %I:%M %p', # Jan 15, 2025 10:30 AM
    '%B %d, %Y %I:%M %p', # January 15, 2025 10:30 AM
    '%c',                 # Sun Jul  8 00:34:60 2001
    '%Y-%m-%d',           # 2025-01-15
    '%m/%d/%Y',           # 01/15/2025
    '%d/%m/%Y',           # 15/01/2025
    '%B %d, %Y',          # January 15, 2021
    '%b %d, %Y',          # Jan 15, 2021
    '%d-%b-%Y',           # 15-Jan-2025
    '%d %B %Y',           # 15 January 2025
    '%Y%m%d',             # 20250115
    '%H:%M:%S',           # 10:30:00
    '%I:%M %p',           # 10:30 AM
]


def get_date_format_string(date_string: str) -> str:
    from dateutil import parser as date_parser
    from datetime import datetime

    if date_string in ['', None]:
        return None

    try:
        # We'll use the result of the dateutil parsing as
        # a reference due to its robustness.
        parsed_date_1 = date_parser.parse(date_string)
    except Exception:
        return None

    for date_format in COMMON_DATE_FORMATS:
        try:
            parsed_date_2 = datetime.strptime(date_string, date_format)
            if parsed_date_1 == parsed_date_2:
                return date_format
        except Exception:
            continue

    return None



from polars import DataType, Categorical, \
                   Int8, Int16, Int32, Int64, \
                   UInt8, UInt16, UInt32, UInt64, \
                   Float32, Float64, Decimal, \
                   Date, Time, Datetime, Duration, \
                   Boolean, Utf8, Null

def get_dtype_symbol(dtype: DataType, short: bool = True) -> str:
    symbol_map = {
        Categorical: {'short': 'cat',   'long': 'categorical'},
        Int8:        {'short': 'i8',    'long': 'integer 8'},
        Int16:       {'short': 'i16',   'long': 'integer 16'},
        Int32:       {'short': 'i32',   'long': 'integer 32'},
        Int64:       {'short': 'i64',   'long': 'integer 64'},
        UInt8:       {'short': 'u8',    'long': 'unsigned integer 8'},
        UInt16:      {'short': 'u16',   'long': 'unsigned integer 16'},
        UInt32:      {'short': 'u32',   'long': 'unsigned integer 32'},
        UInt64:      {'short': 'u64',   'long': 'unsigned integer 64'},
        Float32:     {'short': 'f32',   'long': 'float 32'},
        Float64:     {'short': 'f64',   'long': 'float 64'},
        Decimal:     {'short': 'dec.',  'long': 'decimal'},
        Date:        {'short': 'date',  'long': 'date'},
        Time:        {'short': 'time',  'long': 'time'},
        Datetime:    {'short': 'date.', 'long': 'datetime'},
        Duration:    {'short': 'dur.',  'long': 'duration'},
        Boolean:     {'short': 'bool',  'long': 'boolean'},
        Utf8:        {'short': 'text',  'long': 'text'},
        Null:        {'short': 'null',  'long': 'null'},
    }
    for dt, symbol in symbol_map.items():
        if dtype == dt or isinstance(dtype, dt):
            return symbol['short'] if short else symbol['long']
    return '?'



def get_dtype_class(dtype: DataType) -> type:
    class_map = {
        Categorical: 'other',
        Int8:        'numeric',
        Int16:       'numeric',
        Int32:       'numeric',
        Int64:       'numeric',
        UInt8:       'numeric',
        UInt16:      'numeric',
        UInt32:      'numeric',
        UInt64:      'numeric',
        Float32:     'numeric',
        Float64:     'numeric',
        Decimal:     'numeric',
        Date:        'temporal',
        Time:        'other',
        Datetime:    'temporal',
        Duration:    'other',
        Boolean:     'other',
        Utf8:        'text',
        Null:        'other',
    }
    for dt, cls in class_map.items():
        if dtype == dt or isinstance(dtype, dt):
            return cls
    return None



import locale

def get_list_separator() -> Literal[',', ';']:
    try:
        locale.setlocale(locale.LC_ALL, '')
        conv = locale.localeconv()
        decimal_point = conv['decimal_point']
        if decimal_point == ',':
            return ';'
        return ','
    except Exception:
        return ','



def cast_to_boolean(string: str) -> bool:
    if string.lower() in ['true', '1']:
        return True
    return False