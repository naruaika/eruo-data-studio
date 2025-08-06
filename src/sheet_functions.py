# sheet_functions.py
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


import re

from .utils import get_list_separator

FORMULAS = {
    'ABS'                      : None,
    'ACCRINT'                  : None,
    'ACCRINTM'                 : None,
    'ACOS'                     : None,
    'ACOSH'                    : None,
    'ACOT'                     : None,
    'ACOTH'                    : None,
    'AGGREGATE'                : None,
    'ADDRESS'                  : None,
    'AMORDEGRC'                : None,
    'AMORLINC'                 : None,
    'AND'                      : None,
    'ARABIC'                   : None,
    'AREAS'                    : None,
    'ARRAYTOTEXT'              : None,
    'ASC'                      : None,
    'ASIN'                     : None,
    'ASINH'                    : None,
    'ATAN'                     : None,
    'ATAN2'                    : None,
    'ATANH'                    : None,
    'AVEDEV'                   : None,
    'AVERAGE'                  : None,
    'AVERAGEA'                 : None,
    'AVERAGEIF'                : None,
    'AVERAGEIFS'               : None,
    'BAHTTEXT'                 : None,
    'BASE'                     : None,
    'BESSELI'                  : None,
    'BESSELJ'                  : None,
    'BESSELK'                  : None,
    'BESSELY'                  : None,
    'BETADIST'                 : None,
    'BETA.DIST'                : None,
    'BETAINV'                  : None,
    'BETA.INVn'                : None,
    'BIN2DEC'                  : None,
    'BIN2HEX'                  : None,
    'BIN2OCT'                  : None,
    'BINOMDIST'                : None,
    'BINOM.DIST'               : None,
    'BINOM.DIST.RANGE'         : None,
    'BINOM.INV'                : None,
    'BITAND'                   : None,
    'BITLSHIFT'                : None,
    'BITOR'                    : None,
    'BITRSHIFT'                : None,
    'BITXOR'                   : None,
    'BYCOL'                    : None,
    'BYROW'                    : None,
    'CALL'                     : None,
    'CEILING'                  : None,
    'CEILING.MATH'             : None,
    'CEILING.PRECISE'          : None,
    'CELL'                     : None,
    'CHAR'                     : None,
    'CHIDIST'                  : None,
    'CHIINV'                   : None,
    'CHITEST'                  : None,
    'CHISQ.DIST'               : None,
    'CHISQ.DIST.RT'            : None,
    'CHISQ.INV'                : None,
    'CHISQ.INV.RT'             : None,
    'CHISQ.TEST'               : None,
    'CHOOSE'                   : None,
    'CHOOSECOLS'               : None,
    'CHOOSEROWS'               : None,
    'CLEAN'                    : None,
    'CODE'                     : None,
    'COLUMN'                   : None,
    'COLUMNS'                  : None,
    'COMBIN'                   : None,
    'COMBINA'                  : None,
    'COMPLEX'                  : None,
    'CONCAT'                   : None,
    'CONCATENATE'              : None,
    'CONFIDENCE'               : None,
    'CONFIDENCE.NORM'          : None,
    'CONFIDENCE.T'             : None,
    'CONVERT'                  : None,
    'CORREL'                   : None,
    'COS'                      : None,
    'COSH'                     : None,
    'COT'                      : None,
    'COTH'                     : None,
    'COUNT'                    : None,
    'COUNTA'                   : None,
    'COUNTBLANK'               : None,
    'COUNTIF'                  : None,
    'COUNTIFS'                 : None,
    'COUPDAYBS'                : None,
    'COUPDAYS'                 : None,
    'COUPDAYSNC'               : None,
    'COUPNCD'                  : None,
    'COUPNUM'                  : None,
    'COUPPCD'                  : None,
    'COVAR'                    : None,
    'COVARIANCE.P'             : None,
    'COVARIANCE.S'             : None,
    'CRITBINOM'                : None,
    'CSC'                      : None,
    'CSCH'                     : None,
    'CUBEKPIMEMBER'            : None,
    'CUBEMEMBER'               : None,
    'CUBEMEMBERPROPERTY'       : None,
    'CUBERANKEDMEMBER'         : None,
    'CUBESET'                  : None,
    'CUBESETCOUNT'             : None,
    'CUBEVALUE'                : None,
    'CUMIPMT'                  : None,
    'CUMPRINC'                 : None,
    'DATE'                     : None,
    'DATEDIF'                  : None,
    'DATEVALUE'                : None,
    'DAVERAGE'                 : None,
    'DAY'                      : None,
    'DAYS'                     : None,
    'DAYS360'                  : None,
    'DB'                       : None,
    'DBCS'                     : None,
    'DCOUNT'                   : None,
    'DCOUNTA'                  : None,
    'DDB'                      : None,
    'DEC2BIN'                  : None,
    'DEC2HEX'                  : None,
    'DEC2OCT'                  : None,
    'DECIMAL'                  : None,
    'DEGREES'                  : None,
    'DELTA'                    : None,
    'DETECTLANGUAGE'           : None,
    'DEVSQ'                    : None,
    'DGET'                     : None,
    'DISC'                     : None,
    'DMAX'                     : None,
    'DMIN'                     : None,
    'DOLLAR'                   : None,
    'DOLLARDE'                 : None,
    'DOLLARFR'                 : None,
    'DPRODUCT'                 : None,
    'DROP'                     : None,
    'DSTDEV'                   : None,
    'DSTDEVP'                  : None,
    'DSUM'                     : None,
    'DURATION'                 : None,
    'DVAR'                     : None,
    'DVARP'                    : None,
    'EDATE'                    : None,
    'EFFECT'                   : None,
    'ENCODEURL'                : None,
    'EOMONTH'                  : None,
    'ERF'                      : None,
    'ERF.PRECISE'              : None,
    'ERFC'                     : None,
    'ERFC.PRECISE'             : None,
    'ERROR.TYPE'               : None,
    'EUROCONVERT'              : None,
    'EVEN'                     : None,
    'EXACT'                    : None,
    'EXP'                      : None,
    'EXPAND'                   : None,
    'EXPON.DIST'               : None,
    'EXPONDIST'                : None,
    'FACT'                     : None,
    'FACTDOUBLE'               : None,
    'FALSE'                    : None,
    'IST'                      : None,
    'FDIST'                    : None,
    'IST.RT'                   : None,
    'FILTER'                   : None,
    'FILTERXML'                : None,
    'FIND'                     : None,
    'FINDB'                    : None,
    'NV'                       : None,
    'NV.RT'                    : None,
    'FINV'                     : None,
    'FISHER'                   : None,
    'FISHERINV'                : None,
    'FIXED'                    : None,
    'FLOOR'                    : None,
    'FLOOR.MATH'               : None,
    'FLOOR.PRECISE'            : None,
    'FORECAST.LINEAR'          : None,
    'FORECAST.ETS'             : None,
    'FORECAST.ETS.CONFINT'     : None,
    'FORECAST.ETS.SEASONALITY' : None,
    'FORECAST.ETS.STAT'        : None,
    'FORECAST.LINEAR'          : None,
    'FORMULATEXT'              : None,
    'FREQUENCY'                : None,
    'EST'                      : None,
    'FTEST'                    : None,
    'FV'                       : None,
    'FVSCHEDULE'               : None,
    'GAMMA'                    : None,
    'GAMMA.DIST'               : None,
    'GAMMADIST'                : None,
    'GAMMA.INV'                : None,
    'GAMMAINV'                 : None,
    'GAMMALN'                  : None,
    'GAMMALN.PRECISE'          : None,
    'GAUSS'                    : None,
    'GCD'                      : None,
    'GEOMEAN'                  : None,
    'GESTEP'                   : None,
    'GETPIVOTDATA'             : None,
    'GROUPBY'                  : None,
    'GROWTH'                   : None,
    'HARMEAN'                  : None,
    'HEX2BIN'                  : None,
    'HEX2DEC'                  : None,
    'HEX2OCT'                  : None,
    'HLOOKUP'                  : None,
    'HOUR'                     : None,
    'HSTACK'                   : None,
    'HYPERLINK'                : None,
    'HYPGEOM.DIST'             : None,
    'HYPGEOMDIST'              : None,
    'IF'                       : None,
    'IFERROR'                  : None,
    'IFNA'                     : None,
    'IFS'                      : None,
    'IMABS'                    : None,
    'IMAGE'                    : None,
    'IMAGINARY'                : None,
    'IMARGUMENT'               : None,
    'IMCONJUGATE'              : None,
    'IMCOS'                    : None,
    'IMCOSH'                   : None,
    'IMCOT'                    : None,
    'IMCSC'                    : None,
    'IMCSCH'                   : None,
    'IMDIV'                    : None,
    'IMEXP'                    : None,
    'IMLN'                     : None,
    'IMLOG10'                  : None,
    'IMLOG2'                   : None,
    'IMPOWER'                  : None,
    'IMPRODUCT'                : None,
    'IMREAL'                   : None,
    'IMSEC'                    : None,
    'IMSECH'                   : None,
    'IMSIN'                    : None,
    'IMSINH'                   : None,
    'IMSQRT'                   : None,
    'IMSUB'                    : None,
    'IMSUM'                    : None,
    'IMTAN'                    : None,
    'INDEX'                    : None,
    'INDIRECT'                 : None,
    'INFO'                     : None,
    'INT'                      : None,
    'INTERCEPT'                : None,
    'INTRATE'                  : None,
    'IPMT'                     : None,
    'IRR'                      : None,
    'ISBLANK'                  : None,
    'ISERR'                    : None,
    'ISERROR'                  : None,
    'ISEVEN'                   : None,
    'ISFORMULA'                : None,
    'ISLOGICAL'                : None,
    'ISNA'                     : None,
    'ISNONTEXT'                : None,
    'ISNUMBER'                 : None,
    'ISODD'                    : None,
    'ISOMITTED'                : None,
    'ISREF'                    : None,
    'ISTEXT'                   : None,
    'ISO.CEILING'              : None,
    'ISOWEEKNUM'               : None,
    'ISPMT'                    : None,
    'JIS'                      : None,
    'KURT'                     : None,
    'LAMBDA'                   : None,
    'LARGE'                    : None,
    'LCM'                      : None,
    'LEFT'                     : None,
    'LEFTB'                    : None,
    'LEN'                      : None,
    'LENB'                     : None,
    'LET'                      : None,
    'LINEST'                   : None,
    'LN'                       : None,
    'LOG'                      : None,
    'LOG10'                    : None,
    'LOGEST'                   : None,
    'LOGINV'                   : None,
    'LOGNORM.DIST'             : None,
    'LOGNORMDIST'              : None,
    'LOGNORM.INV'              : None,
    'LOOKUP'                   : None,
    'LOWER'                    : None,
    'MAKEARRAY'                : None,
    'MAP'                      : None,
    'MATCH'                    : None,
    'MAX'                      : None,
    'MAXA'                     : None,
    'MAXIFS'                   : None,
    'MDETERM'                  : None,
    'MDURATION'                : None,
    'MEDIAN'                   : None,
    'MID, MIDB'                : None,
    'MIN'                      : None,
    'MINIFS'                   : None,
    'MINA'                     : None,
    'MINUTE'                   : None,
    'MINVERSE'                 : None,
    'MIRR'                     : None,
    'MMULT'                    : None,
    'MOD'                      : None,
    'MODE'                     : None,
    'MODE.MULT'                : None,
    'MODE.SNGL'                : None,
    'MONTH'                    : None,
    'MROUND'                   : None,
    'MULTINOMIAL'              : None,
    'MUNIT'                    : None,
    'NA'                       : None,
    'NEGBINOM.DIST'            : None,
    'NEGBINOMDIST'             : None,
    'NETWORKDAYS'              : None,
    'NETWORKDAYS.INTL'         : None,
    'NOMINAL'                  : None,
    'NORM.DIST'                : None,
    'NORMDIST'                 : None,
    'NORMINV'                  : None,
    'NORM.INV'                 : None,
    'NORM.S.DIST'              : None,
    'NORMSDIST'                : None,
    'NORM.S.INV'               : None,
    'NORMSINV'                 : None,
    'NOT'                      : None,
    'NOW'                      : None,
    'NPER'                     : None,
    'NPV'                      : None,
    'NUMBERVALUE'              : None,
    'OCT2BIN'                  : None,
    'OCT2DEC'                  : None,
    'OCT2HEX'                  : None,
    'ODD'                      : None,
    'ODDFPRICE'                : None,
    'ODDFYIELD'                : None,
    'ODDLPRICE'                : None,
    'ODDLYIELD'                : None,
    'OFFSET'                   : None,
    'OR'                       : None,
    'PDURATION'                : None,
    'PEARSON'                  : None,
    'PERCENTILE.EXC'           : None,
    'PERCENTILE.INC'           : None,
    'PERCENTILE'               : None,
    'PERCENTOF'                : None,
    'PERCENTRANK.EXC'          : None,
    'PERCENTRANK.INC'          : None,
    'PERCENTRANK'              : None,
    'PERMUT'                   : None,
    'PERMUTATIONA'             : None,
    'PHI'                      : None,
    'PHONETIC'                 : None,
    'PI'                       : None,
    'PIVOTBY'                  : None,
    'PMT'                      : None,
    'POISSON.DIST'             : None,
    'POISSON'                  : None,
    'POWER'                    : None,
    'PPMT'                     : None,
    'PRICE'                    : None,
    'PRICEDISC'                : None,
    'PRICEMAT'                 : None,
    'PROB'                     : None,
    'PRODUCT'                  : None,
    'PROPER'                   : None,
    'PV'                       : None,
    'QUARTILE'                 : None,
    'QUARTILE.EXC'             : None,
    'QUARTILE.INC'             : None,
    'QUOTIENT'                 : None,
    'RADIANS'                  : None,
    'RAND'                     : None,
    'RANDARRAY'                : None,
    'RANDBETWEEN'              : None,
    'RANK.AVG'                 : None,
    'RANK.EQ'                  : None,
    'RANK'                     : None,
    'RATE'                     : None,
    'RECEIVED'                 : None,
    'REDUCE'                   : None,
    'REGEXEXTRACT'             : None,
    'REGEXREPLACE'             : None,
    'REGEXTEST'                : None,
    'REGISTER.ID'              : None,
    'REPLACE'                  : None,
    'REPLACEB'                 : None,
    'REPT'                     : None,
    'RIGHT'                    : None,
    'RIGHTB'                   : None,
    'ROMAN'                    : None,
    'ROUND'                    : None,
    'ROUNDDOWN'                : None,
    'ROUNDUP'                  : None,
    'ROW'                      : None,
    'ROWS'                     : None,
    'RRI'                      : None,
    'RSQ'                      : None,
    'RTD'                      : None,
    'SCAN'                     : None,
    'SEARCH'                   : None,
    'SEARCHB'                  : None,
    'SEC'                      : None,
    'SECH'                     : None,
    'SECOND'                   : None,
    'SEQUENCE'                 : None,
    'SERIESSUM'                : None,
    'SHEET'                    : None,
    'SHEETS'                   : None,
    'SIGN'                     : None,
    'SIN'                      : None,
    'SINH'                     : None,
    'SKEW'                     : None,
    'SKEW.P'                   : None,
    'SLN'                      : None,
    'SLOPE'                    : None,
    'SMALL'                    : None,
    'SORT'                     : None,
    'SORTBY'                   : None,
    'SQRT'                     : None,
    'SQRTPI'                   : None,
    'STANDARDIZE'              : None,
    'STOCKHISTORY'             : None,
    'STDEV'                    : None,
    'STDEV.P'                  : None,
    'STDEV.S'                  : None,
    'STDEVA'                   : None,
    'STDEVP'                   : None,
    'STDEVPA'                  : None,
    'STEYX'                    : None,
    'STOCKHISTORY'             : None,
    'SUBSTITUTE'               : None,
    'SUBTOTAL'                 : None,
    'SUM'                      : None,
    'SUMIF'                    : None,
    'SUMIFS'                   : None,
    'SUMPRODUCT'               : None,
    'SUMSQ'                    : None,
    'SUMX2MY2'                 : None,
    'SUMX2PY2'                 : None,
    'SUMXMY2'                  : None,
    'SWITCH'                   : None,
    'SYD'                      : None,
    'TAN'                      : None,
    'TANH'                     : None,
    'TAKE'                     : None,
    'TBILLEQ'                  : None,
    'TBILLPRICE'               : None,
    'TBILLYIELD'               : None,
    'IST'                      : None,
    'IST.2T'                   : None,
    'IST.RT'                   : None,
    'TDIST'                    : None,
    'TEXT'                     : None,
    'TEXTAFTER'                : None,
    'TEXTBEFORE'               : None,
    'TEXTJOIN'                 : None,
    'TEXTSPLIT'                : None,
    'TIME'                     : None,
    'TIMEVALUE'                : None,
    'NV'                       : None,
    'NV.2T'                    : None,
    'TINV'                     : None,
    'TOCOL'                    : None,
    'TOROW'                    : None,
    'TODAY'                    : None,
    'TRANSLATE'                : None,
    'TRANSPOSE'                : None,
    'TREND'                    : None,
    'TRIM'                     : None,
    'TRIMMEAN'                 : None,
    'TRIMRANGE'                : None,
    'TRUE'                     : None,
    'TRUNC'                    : None,
    'EST'                      : None,
    'TTEST'                    : None,
    'TYPE'                     : None,
    'UNICHAR'                  : None,
    'UNICODE'                  : None,
    'UNIQUE'                   : None,
    'UPPER'                    : None,
    'VALUE'                    : None,
    'VALUETOTEXT'              : None,
    'VAR'                      : None,
    'VAR.P'                    : None,
    'VAR.S'                    : None,
    'VARA'                     : None,
    'VARP'                     : None,
    'VARPA'                    : None,
    'VDB'                      : None,
    'VLOOKUP'                  : None,
    'VSTACK'                   : None,
    'WEBSERVICE'               : None,
    'WEEKDAY'                  : None,
    'WEEKNUM'                  : None,
    'WEIBULL'                  : None,
    'WEIBULL.DIST'             : None,
    'WORKDAY'                  : None,
    'WORKDAY.INTL'             : None,
    'WRAPCOLS'                 : None,
    'WRAPROWS'                 : None,
    'XIRR'                     : None,
    'XLOOKUP'                  : None,
    'XMATCH'                   : None,
    'XNPV'                     : None,
    'XOR'                      : None,
    'YEAR'                     : None,
    'YEARFRAC'                 : None,
    'YIELD'                    : None,
    'YIELDDISC'                : None,
    'YIELDMAT'                 : None,
    'EST'                      : None,
    'ZTEST'                    : None,
}


DAXS = {}


def _split_top_level_arguments(args_string: str) -> list[str]:
    """
    Splits a string of function arguments by top-level commas.

    This function correctly handles nested parentheses, ensuring that commas
    inside nested function calls or expressions are not treated as separators.

    Args:
        args_string (str): A string containing function arguments.

    Returns:
        list[str]: A list of strings, where each string is a single argument.
    """
    arguments = []
    balance = 0
    start = 0
    for i, char in enumerate(args_string):
        if char == '(':
            balance += 1
        if char == ')':
            balance -= 1
        if char == get_list_separator() and balance == 0:
            arguments.append(args_string[start:i].strip())
            start = i + 1
    arguments.append(args_string[start:].strip())
    return arguments

def _parse_term(arg_string: str) -> dict[str, any]:
    """
    Parses a single argument string and returns a structured object.

    This helper function handles different types of terms like columns,
    cell references, strings, numbers, and nested function calls.
    """
    # Check for a column reference [Column Name]
    column_match = re.match(r'^\[(.*)\]$', arg_string)
    if column_match:
        return {'type': 'column', 'name': column_match.group(1)}

    # Check for a cell range, e.g., A1:B2
    cell_range_match = re.match(r'^[A-Z]+\d+:[A-Z]+\d+$', arg_string, re.IGNORECASE)
    if cell_range_match:
        return {'type': 'cell_range', 'value': arg_string}

    # Check for a single cell reference, e.g., A1
    cell_ref_match = re.match(r'^[A-Z]+\d+$', arg_string, re.IGNORECASE)
    if cell_ref_match:
        return {'type': 'cell_reference', 'value': arg_string}

    # Check for a literal string "text" or a number
    string_match = re.match(r'^"([^"]*)"$', arg_string)
    if string_match:
        return {'type': 'string', 'value': string_match.group(1)}

    number_match = re.match(r'^-?\d+(\.\d+)?$', arg_string)
    if number_match:
        return {'type': 'number', 'value': float(number_match.group(0))}

    # Check for a nested function call
    nested_function_match = re.match(r'^([a-zA-Z_]+)\s*\((.*)\)\s*$', arg_string)
    if nested_function_match:
        nested_function_name = nested_function_match.group(1)
        nested_args_content = nested_function_match.group(2)
        parsed_nested_args = [
            # Recursively handle operators within arguments
            _parse_expression(arg)
            for arg in _split_top_level_arguments(nested_args_content)
        ]
        return {
            'type': 'function',
            'name': nested_function_name,
            'arguments': parsed_nested_args
        }

    # If it's a simple expression, store it as-is
    return {'type': 'expression', 'value': arg_string}

def _parse_value(formula_string: str) -> dict[str, any]:
    """Parses a simple value, a grouped expression, or a term."""
    trimmed_string = formula_string.strip()
    if trimmed_string.startswith('(') and trimmed_string.endswith(')'):
        inner_content = trimmed_string[1:-1].strip()
        return _parse_expression(inner_content)

    return _parse_term(trimmed_string)

def _parse_exponentiation(formula_string: str) -> dict[str, any]:
    """Parses exponentiation, which has the highest precedence."""
    balance = 0
    operator_index = -1
    for i in range(len(formula_string) - 1, -1, -1):
        char = formula_string[i]
        if char == '(':
            balance += 1
        elif char == ')':
            balance -= 1
        elif balance == 0 and char == '^':
            operator_index = i
            break

    if operator_index != -1:
        left_str = formula_string[:operator_index].strip()
        right_str = formula_string[operator_index+1:].strip()
        operator = formula_string[operator_index]
        return {
            'type': 'operation',
            'operator': operator,
            'left': _parse_exponentiation(left_str),
            'right': _parse_value(right_str)
        }

    return _parse_value(formula_string)

def _parse_multiplication_division(formula_string: str) -> dict[str, any]:
    """Parses multiplication, division, modulo, and floor division."""
    balance = 0
    operator_index = -1
    operator = ''

    # Iterate from right to left to find the operator with lowest precedence
    # in this group. Prioritize multi-character operators.
    for i in range(len(formula_string) - 1, -1, -1):
        char = formula_string[i]
        if char == '(':
            balance += 1
        elif char == ')':
            balance -= 1
        elif balance == 0:
            if i > 0 and formula_string[i-1:i+1] == '//':
                operator_index = i - 1
                operator = '//'
                break
            elif char in ['*', '/', '%']:
                operator_index = i
                operator = char
                break

    if operator_index != -1:
        if operator == '//':
            left_str = formula_string[:operator_index].strip()
            right_str = formula_string[operator_index+2:].strip()
        else:
            left_str = formula_string[:operator_index].strip()
            right_str = formula_string[operator_index+1:].strip()

        return {
            'type': 'operation',
            'operator': operator,
            'left': _parse_multiplication_division(left_str),
            'right': _parse_exponentiation(right_str)
        }

    return _parse_exponentiation(formula_string)

def _parse_expression(formula_string: str) -> dict[str, any]:
    """
    Parses a full formula string, handling addition and subtraction.
    This function has the lowest precedence.
    """
    balance = 0
    operator_index = -1
    for i in range(len(formula_string) - 1, -1, -1):
        char = formula_string[i]
        if char == '(':
            balance += 1
        elif char == ')':
            balance -= 1
        elif balance == 0 and char in ['+', '-']:
            operator_index = i
            break

    if operator_index != -1:
        left_str = formula_string[:operator_index].strip()
        right_str = formula_string[operator_index+1:].strip()
        operator = formula_string[operator_index]
        return {
            'type': 'operation',
            'operator': operator,
            'left': _parse_expression(left_str),
            'right': _parse_multiplication_division(right_str)
        }

    return _parse_multiplication_division(formula_string)

def parse_dax(expression: str) -> dict[str, any]:
    """
    Parses e.g. `Measure = Function(...)` or `= Function(...)`.

    Args:
        expression (str): The DAX or Excel-like expression string.

    Returns:
        dict: A dictionary with a structured representation of the parsed
              expression, or an error message.
    """
    expression_to_parse = expression.strip()

    # Case 1: Excel-like "= Formula"
    if expression_to_parse.startswith("="):
        formula_string = expression_to_parse[1:].strip()
        parsed_formula = _parse_expression(formula_string)
        return {
            'formula': parsed_formula
        }

    # Case 2: DAX-like "Measure = Formula"
    parts = re.split(r'\s*=\s*', expression_to_parse, maxsplit=1)
    if len(parts) == 2:
        measure_name = parts[0].strip()
        formula_string = parts[1].strip()
        parsed_formula = _parse_expression(formula_string)
        return {
            'measure-name': measure_name,
            'formula': parsed_formula
        }

    # Invalid syntax
    return {'error': 'Invalid syntax'}