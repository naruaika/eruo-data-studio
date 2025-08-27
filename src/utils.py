# utils.py
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


from typing import Literal

# A comprehensive list of common date formats. Order can be important for
# performance and ambiguity resolution; more specific formats should be
# listed before more general ones.
COMMON_DATE_FORMATS = [
    '%Y-%m-%d %H:%M:%S',  # 2025-01-15 10:30:00
    '%Y-%m-%dT%H:%M:%S',  # 2025-01-15T10:30:00
    '%Y/%m/%d %H:%M:%S',  # 2025/01/15 10:30:00
    '%m/%d/%Y %H:%M:%S',  # 01/15/2025 10:30:00
    '%d/%m/%Y %H:%M:%S',  # 15/01/2025 10:30:00
    '%b %d, %Y %I:%M %p', # Jan 15, 2025 10:30 AM
    '%B %d, %Y %I:%M %p', # January 15, 2025 10:30 AM
    '%Y-%m-%d',           # 2025-01-15
    '%m/%d/%Y',           # 01/15/2025
    '%d/%m/%Y',           # 15/01/2025
    '%B %d, %Y',          # January 15, 2021
    '%b %d, %Y',          # Jan 15, 2021
    '%d-%b-%Y',           # 15-Jan-2025
    '%d %B %Y',           # 15 January 2025
    '%Y%m%d',             # 20250115
    '%Y',                 # 2025
    '%Y-%m',              # 2025-01
    '%m-%Y',              # 01-2025
    '%m/%Y',              # 01/2025
    '%b %Y',              # Jan 2025
    '%b-%Y',              # Jan-2025
    '%B %Y',              # January 2025
#   '%m-%d',              # 01-15
#   '%m/%d',              # 01/15
#   '%d/%m',              # 15/01
#   '%B %d,',             # January 15
#   '%b %d,',             # Jan 15
#   '%d-%b',              # 15-Jan
#   '%d %B',              # 15 January
]


COMMON_TIME_FORMATS = [
    '%H:%M:%S',           # 10:30:00
    '%I:%M %p',           # 10:30 AM
    '%H:%M',              # 10:30
]


def get_date_format_string(date_string: str) -> str:
    from dateutil import parser as date_parser
    from datetime import datetime

    if isinstance(date_string, int):
        return None

    if date_string in ['', None]:
        return None

    if not isinstance(date_string, str):
        date_string = str(date_string)

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


def get_time_format_string(date_string: str) -> str:
    from dateutil import parser as date_parser
    from datetime import datetime

    if isinstance(date_string, int):
        return None

    if date_string in ['', None]:
        return None

    if not isinstance(date_string, str):
        date_string = str(date_string)

    try:
        # We'll use the result of the dateutil parsing as
        # a reference due to its robustness.
        parsed_date_1 = date_parser.parse(date_string)
    except Exception:
        return None

    for date_format in COMMON_TIME_FORMATS:
        try:
            parsed_date_2 = datetime.strptime(date_string, date_format)
            if parsed_date_1.hour == parsed_date_2.hour \
                    and parsed_date_1.minute == parsed_date_2.minute:
                return date_format
        except Exception:
            continue

    return None



from polars import DataType, Categorical, \
                   Int8, Int16, Int32, Int64, \
                   UInt8, UInt16, UInt32, UInt64, \
                   Float32, Float64, Decimal, \
                   Date, Time, Datetime, Duration, \
                   Boolean, Utf8, Null, List, Struct, \
                   Binary

def get_dtype_symbol(dtype: DataType, short: bool = True) -> str:
    symbol_map = {
        Categorical: {'short': 'cat',    'long': 'categorical'},
        Int8:        {'short': 'i8',     'long': 'integer 8'},
        Int16:       {'short': 'i16',    'long': 'integer 16'},
        Int32:       {'short': 'i32',    'long': 'integer 32'},
        Int64:       {'short': 'i64',    'long': 'integer 64'},
        UInt8:       {'short': 'u8',     'long': 'unsigned integer 8'},
        UInt16:      {'short': 'u16',    'long': 'unsigned integer 16'},
        UInt32:      {'short': 'u32',    'long': 'unsigned integer 32'},
        UInt64:      {'short': 'u64',    'long': 'unsigned integer 64'},
        Float32:     {'short': 'f32',    'long': 'float 32'},
        Float64:     {'short': 'f64',    'long': 'float 64'},
        Decimal:     {'short': 'dec.',   'long': 'decimal'},
        Date:        {'short': 'date',   'long': 'date'},
        Time:        {'short': 'time',   'long': 'time'},
        Datetime:    {'short': 'date.',  'long': 'datetime'},
        Duration:    {'short': 'dur.',   'long': 'duration'},
        Boolean:     {'short': 'bool',   'long': 'boolean'},
        Utf8:        {'short': 'text',   'long': 'text'},
        Null:        {'short': 'null',   'long': 'null'},
        List:        {'short': 'list',   'long': 'list'},
        Struct:      {'short': 'struct', 'long': 'struct'},
        Binary:      {'short': 'bin.',   'long': 'binary'},
    }
    for dt, symbol in symbol_map.items():
        if dtype == dt or isinstance(dtype, dt):
            return symbol['short'] if short else symbol['long']
    return '?'



def get_dtype_class(dtype: DataType) -> type:
    class_map = {
        Categorical: 'category',
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
        Time:        'time',
        Datetime:    'temporal',
        Duration:    'duration',
        Boolean:     'boolean',
        Utf8:        'text',
        Null:        'null',
        List:        'list',
        Struct:      'struct',
        Binary:      'binary',
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



import time

def generate_ulid():
    return int(time.time() * 1000)



from typing import Any

def is_iterable(obj: Any) -> bool:
    try:
        iter(obj)
        return True
    except TypeError:
        return False


from gi.repository import Gtk

COMMAND_EVAL_GLOBALS = {
    '__builtins__': {
        'str': str,
        'bool': bool,
    }
}


def check_command_eligible(window: Gtk.Window, when_expression: str) -> bool:
    _globals = COMMAND_EVAL_GLOBALS.copy()

    from .sheet_document import SheetDocument
    from .sheet_notebook import SheetNotebook

    document = window.get_current_active_document()
    if isinstance(document, SheetDocument):
        _globals['document'] = 'worksheet'
    if isinstance(document, SheetNotebook):
        _globals['document'] = 'notebook'

    return eval(when_expression, _globals, {})