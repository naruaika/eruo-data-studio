# sheet_functions.py
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


from datetime import datetime, date, time, timezone
from typing import Any, Dict, List, Union
from pyarrow import compute
import copy
import math
import polars
import re

from . import utils

MATH_EVAL_GLOBALS = {
    '__builtins__' : {},
    'acos'         : math.acos,
    'acosh'        : math.acosh,
    'asin'         : math.asin,
    'asinh'        : math.asinh,
    'atan'         : math.atan,
    'atan2'        : math.atan2,
    'atanh'        : math.atanh,
    'cbrt'         : math.cbrt,
    'ceil'         : math.ceil,
    'ceil'         : math.ceil,
    'comb'         : math.comb,
    'copysign'     : math.copysign,
    'cos'          : math.cos,
    'cosh'         : math.cosh,
    'degrees'      : math.degrees,
    'dist'         : math.dist,
    'erf'          : math.erf,
    'erfc'         : math.erfc,
    'exp'          : math.exp,
    'exp2'         : math.exp2,
    'expm1'        : math.expm1,
    'fabs'         : math.fabs,
    'factorial'    : math.factorial,
    'floor'        : math.floor,
    'floor'        : math.floor,
    'fmod'         : math.fmod,
    'frexp'        : math.frexp,
    'fsum'         : math.fsum,
    'gamma'        : math.gamma,
    'gcd'          : math.gcd,
    'hypot'        : math.hypot,
    'isclose'      : math.isclose,
    'isinf'        : math.isinf,
    'isfinite'     : math.isfinite,
    'isnan'        : math.isnan,
    'isqrt'        : math.isqrt,
    'lcm'          : math.lcm,
    'ldexp'        : math.ldexp,
    'lgamma'       : math.lgamma,
    'log'          : math.log,
    'log10'        : math.log10,
    'log1p'        : math.log1p,
    'log2'         : math.log2,
    'modf'         : math.modf,
    'nextafter'    : math.nextafter,
    'nextafter'    : math.nextafter,
    'perm'         : math.perm,
    'pow'          : math.pow,
    'prod'         : math.prod,
    'prod'         : math.prod,
    'prod'         : math.prod,
    'radians'      : math.radians,
    'remainder'    : math.remainder,
    'sin'          : math.sin,
    'sinh'         : math.sinh,
    'sumprod'      : math.sumprod,
    'sqrt'         : math.sqrt,
    'tan'          : math.tan,
    'tanh'         : math.tanh,
    'trunc'        : math.trunc,
    'ulp'          : math.ulp,
#   'fma'          : math.fma, # not supported prior to Python version 3.13
    'pi'           : math.pi,
    'e'            : math.e,
    'inf'          : math.inf,
    'nan'          : math.nan,
    'tau'          : math.tau
}

FUNCTION_CONSTANTS = [
    # Interval
    'SECOND',
    'MINUTE',
    'HOUR',
    'DAY',
    'WEEK',
    'MONTH',
    'QUARTER',
    'YEAR',
]

#
# Operations Expression Builder
#

def _get_operation_expression(left_expr:      polars.Expr,
                              operator_name:  str,
                              right_expr:     polars.Expr = None,
                              operation_args: list = []) -> polars.Expr | str:
    match operator_name:
        # Comparisons
        case '>='                                     : return left_expr.ge(right_expr)
        case '<='                                     : return left_expr.le(right_expr)
        case '=='                                     : return left_expr.eq(right_expr)
        case '='                                      : return left_expr.eq(right_expr)
        case '!='                                     : return left_expr.eq(right_expr).not_()
        case '<>'                                     : return left_expr.eq(right_expr).not_()
        case '>'                                      : return left_expr.gt(right_expr)
        case '<'                                      : return left_expr.lt(right_expr)

        # Bitwise
        case 'AND'                                    : return left_expr.and_(right_expr)
        case 'OR'                                     : return left_expr.or_(right_expr)
        case 'XOR'                                    : return left_expr.xor(right_expr)
        case 'XAND'                                   : return (left_expr.and_(right_expr)).or_(left_expr.not_().and_(right_expr.not_()))
        case 'XNOR'                                   : return (left_expr.and_(right_expr)).or_(left_expr.not_().and_(right_expr.not_()))
        case '&'                                      : return left_expr.and_(right_expr) # TODO: add support for string concatenation
        case '|'                                      : return left_expr.or_(right_expr)
        case '^'                                      : return left_expr.xor(right_expr)  # TODO: add support as math power() function

        # Numeric
        case '+'                                      : return left_expr.add(right_expr)  # TODO: add support for string concatenation
        case '-'                                      : return left_expr.sub(right_expr)
        case '*'                                      : return left_expr.mul(right_expr)
        case '/'                                      : return left_expr.truediv(right_expr)
        case '//'                                     : return left_expr.floordiv(right_expr)
        case '%'                                      : return left_expr.mod(right_expr)
        case '**'                                     : return left_expr.pow(right_expr)

        # String
        case 'append-prefix'                          : return operation_args[0] + left_expr
        case 'append-suffix'                          : return left_expr + operation_args[0]
        case 'camel-case'                             : return _get_change_case_to_camel_case_expression(left_expr)
        case 'constant-case'                          : return _get_change_case_to_constant_case_expression(left_expr)
        case 'dot-case'                               : return _get_change_case_to_dot_case_expression(left_expr)
        case 'decode-base64'                          : return left_expr.str.decode('base64', strict=False)
        case 'decode-hexadecimal'                     : return left_expr.str.decode('hex', strict=False)
        case 'decode-url'                             : return 'url_decode($0)'
        case 'encode-base64'                          : return left_expr.str.encode('base64')
        case 'encode-hexadecimal'                     : return left_expr.str.encode('hex')
        case 'encode-url'                             : return 'url_encode($0)'
        case 'kebab-case'                             : return _get_change_case_to_kebab_case_expression(left_expr)
        case 'lowercase'                              : return left_expr.str.to_lowercase()
        case 'pascal-case'                            : return _get_change_case_to_pascal_case_expression(left_expr)
        case 'pad-end-custom'                         : return left_expr.str.pad_end(operation_args[0], operation_args[1])
        case 'pad-end-default'                        : return left_expr.str.pad_end(operation_args[0])
        case 'pad-start-custom'                       : return left_expr.str.pad_start(operation_args[0], operation_args[1])
        case 'pad-start-default'                      : return left_expr.str.pad_start(operation_args[0])
        case 'remove-prefix-case-insensitive'         : return left_expr.str.replace(f'(?i)^{re.escape(operation_args[0])}', '')
        case 'remove-prefix-case-sensitive'           : return left_expr.str.replace(f'^{re.escape(operation_args[0])}', '')
        case 'remove-suffix-case-insensitive'         : return left_expr.str.replace(f'(?i){re.escape(operation_args[0])}$', '')
        case 'remove-suffix-case-sensitive'           : return left_expr.str.replace(f'{re.escape(operation_args[0])}$', '')
        case 'remove-whitespaces'                     : return left_expr.str.replace_all(r'\s+', '')
        case 'remove-new-lines'                       : return left_expr.str.replace_all(r'\n+', '')
        case 'replace-whitespace-with-a-single-space' : return left_expr.str.replace_all(r'\s+', ' ')
        case 'replace-whitespace-and-new-lines-' \
             'with-a-single-space'                    : return left_expr.str.replace_all(r'[\s\n]+', ' ')
        case 'snake-case'                             : return _get_change_case_to_snake_case_expression(left_expr)
        case 'sentence-case'                          : return left_expr.strx.to_sentence_case()
        case 'slugify'                                : return _get_slugify_expression(left_expr)
        case 'split-by-characters'                    : return left_expr.strx.split_by_chars(operation_args[0])
        case 'sponge-case'                            : return left_expr.strx.to_sponge_case()
        case 'title-case'                             : return left_expr.str.to_titlecase()
        case 'unicode-normalization-nfc'              : return left_expr.str.normalize('NFC')
        case 'unicode-normalization-nfd'              : return left_expr.str.normalize('NFD')
        case 'unicode-normalization-nfkc'             : return left_expr.str.normalize('NFKC')
        case 'unicode-normalization-nfkd'             : return left_expr.str.normalize('NFKD')
        case 'unicode-normalization-nfc'              : return left_expr.str.normalize('NFC')
        case 'unicode-normalization-nfd'              : return left_expr.str.normalize('NFD')
        case 'unicode-normalization-nfkc'             : return left_expr.str.normalize('NFKC')
        case 'unicode-normalization-nfkd'             : return left_expr.str.normalize('NFKD')
        case 'pig-latinnify'                          : return left_expr.strx.pig_latinnify()
        case 'uppercase'                              : return left_expr.str.to_uppercase()
        case 'reverse-text'                           : return left_expr.str.reverse()
        case 'swap-text-case'                         : return _get_swap_text_case_expression(left_expr)
        case 'trim-whitespace'                        : return left_expr.str.strip_chars()
        case 'trim-whitespace-and-remove-new-lines'   : return left_expr.str.strip_chars().str.replace_all('\n', '')
        case 'trim-start-whitespace'                  : return left_expr.str.strip_chars_start()
        case 'trim-end-whitespace'                    : return left_expr.str.strip_chars_end()
        case 'wrap-with-text-different'               : return operation_args[0] + left_expr + operation_args[1]
        case 'wrap-with-text-same'                    : return operation_args[0] + left_expr + operation_args[0]

    raise ValueError(f'Unsupported operator: {operator_name}')

def _get_change_case_to_camel_case_expression(expr: polars.Expr) -> polars.Expr:
    pascal_cased = expr.pipe(_get_operation_expression, 'pascal-case')
    first_letter = pascal_cased.str.slice(0, 1).str.to_lowercase()
    return first_letter + pascal_cased.str.slice(1, None)

def _get_change_case_to_kebab_case_expression(expr: polars.Expr) -> polars.Expr:
    return expr.str.replace_all('([a-z])([A-Z])', r'${1}-${2}') \
               .str.replace_all(r'[\.\s_-]+', '-') \
               .str.to_lowercase() \
               .str.strip_chars('-')

def _get_change_case_to_constant_case_expression(expr: polars.Expr) -> polars.Expr:
    return expr.str.replace_all(r'([a-z])([A-Z])', r'${1}_${2}') \
               .str.replace_all(r'[\.\s_-]+', '_') \
               .str.to_uppercase() \
               .str.strip_chars('_')

def _get_change_case_to_dot_case_expression(expr: polars.Expr) -> polars.Expr:
    return expr.str.replace_all(r'([a-z])([A-Z])', r'${1}.${2}') \
               .str.replace_all(r'[\s_-]+', '.') \
               .str.to_lowercase() \
               .str.strip_chars('.')

def _get_change_case_to_pascal_case_expression(expr: polars.Expr) -> polars.Expr:
    normalized_string = expr.str.replace_all(r'([a-z])([A-Z])', r'${1} ${2}') \
                            .str.replace_all(r'[\.\s_-]+', ' ') \
                            .str.strip_chars(' ')
    words = normalized_string.str.split(' ')
    first_part = polars.element().str.slice(0, 1).str.to_uppercase()
    last_part = polars.element().str.slice(1, None).str.to_lowercase()
    return words.list.eval(first_part + last_part).list.join('')

def _get_change_case_to_snake_case_expression(expr: polars.Expr) -> polars.Expr:
    return expr.str.replace_all(r'([a-z])([A-Z])', r'${1}_${2}') \
               .str.replace_all(r'[\.\s_-]+', '_') \
               .str.to_lowercase() \
               .str.strip_chars('_')

def _get_swap_text_case_expression(expr: polars.Expr) -> polars.Expr:
    def swap_text_case(series: polars.Series) -> polars.Series:
        return polars.Series(compute.utf8_swapcase(series.to_arrow()))
    return expr.map_batches(swap_text_case, polars.self_dtype())

def _get_slugify_expression(expr: polars.Expr) -> polars.Expr:
    return expr.str.to_lowercase() \
               .str.replace_all(r'[^a-z0-9]+', '-') \
               .str.strip_chars('-')

def build_operation(expression:     polars.Expr,
                    operator_name:  str,
                    operation_args: list = []) -> polars.Expr | str:
    return _get_operation_expression(expression, operator_name, operation_args=operation_args)

#
# Formula Expression Builder
#

def _get_formula_expression(func_name: str, args: List) -> polars.Expr:
    func_name = func_name.upper()

    match func_name:
        case 'ABS'                      : return None
        case 'ACCRINT'                  : return None
        case 'ACCRINTM'                 : return None
        case 'ACOS'                     : return None
        case 'ACOSH'                    : return None
        case 'ACOT'                     : return None
        case 'ACOTH'                    : return None
        case 'AGGREGATE'                : return None
        case 'ADDRESS'                  : return None
        case 'AMORDEGRC'                : return None
        case 'AMORLINC'                 : return None
        case 'AND'                      : return None
        case 'ARABIC'                   : return None
        case 'AREAS'                    : return None
        case 'ARRAYTOTEXT'              : return None
        case 'ASC'                      : return None
        case 'ASIN'                     : return None
        case 'ASINH'                    : return None
        case 'ATAN'                     : return None
        case 'ATAN2'                    : return None
        case 'ATANH'                    : return None
        case 'AVEDEV'                   : return None
        case 'AVERAGE'                  : return None
        case 'AVERAGEA'                 : return None
        case 'AVERAGEIF'                : return None
        case 'AVERAGEIFS'               : return None
        case 'BAHTTEXT'                 : return None
        case 'BASE'                     : return None
        case 'BESSELI'                  : return None
        case 'BESSELJ'                  : return None
        case 'BESSELK'                  : return None
        case 'BESSELY'                  : return None
        case 'BETADIST'                 : return None
        case 'BETA.DIST'                : return None
        case 'BETAINV'                  : return None
        case 'BETA.INVn'                : return None
        case 'BIN2DEC'                  : return None
        case 'BIN2HEX'                  : return None
        case 'BIN2OCT'                  : return None
        case 'BINOMDIST'                : return None
        case 'BINOM.DIST'               : return None
        case 'BINOM.DIST.RANGE'         : return None
        case 'BINOM.INV'                : return None
        case 'BITAND'                   : return None
        case 'BITLSHIFT'                : return None
        case 'BITOR'                    : return None
        case 'BITRSHIFT'                : return None
        case 'BITXOR'                   : return None
        case 'BYCOL'                    : return None
        case 'BYROW'                    : return None
        case 'CALL'                     : return None
        case 'CEILING'                  : return None
        case 'CEILING.MATH'             : return None
        case 'CEILING.PRECISE'          : return None
        case 'CELL'                     : return None
        case 'CHAR'                     : return None
        case 'CHIDIST'                  : return None
        case 'CHIINV'                   : return None
        case 'CHITEST'                  : return None
        case 'CHISQ.DIST'               : return None
        case 'CHISQ.DIST.RT'            : return None
        case 'CHISQ.INV'                : return None
        case 'CHISQ.INV.RT'             : return None
        case 'CHISQ.TEST'               : return None
        case 'CHOOSE'                   : return None
        case 'CHOOSECOLS'               : return None
        case 'CHOOSEROWS'               : return None
        case 'CLEAN'                    : return None
        case 'CODE'                     : return None
        case 'COLUMN'                   : return None
        case 'COLUMNS'                  : return None
        case 'COMBIN'                   : return None
        case 'COMBINA'                  : return None
        case 'COMPLEX'                  : return None
        case 'CONCAT'                   : return None
        case 'CONCATENATE'              : return None
        case 'CONFIDENCE'               : return None
        case 'CONFIDENCE.NORM'          : return None
        case 'CONFIDENCE.T'             : return None
        case 'CONVERT'                  : return None
        case 'CORREL'                   : return None
        case 'COS'                      : return None
        case 'COSH'                     : return None
        case 'COT'                      : return None
        case 'COTH'                     : return None
        case 'COUNT'                    : return None
        case 'COUNTA'                   : return None
        case 'COUNTBLANK'               : return None
        case 'COUNTIF'                  : return None
        case 'COUNTIFS'                 : return None
        case 'COUPDAYBS'                : return None
        case 'COUPDAYS'                 : return None
        case 'COUPDAYSNC'               : return None
        case 'COUPNCD'                  : return None
        case 'COUPNUM'                  : return None
        case 'COUPPCD'                  : return None
        case 'COVAR'                    : return None
        case 'COVARIANCE.P'             : return None
        case 'COVARIANCE.S'             : return None
        case 'CRITBINOM'                : return None
        case 'CSC'                      : return None
        case 'CSCH'                     : return None
        case 'CUBEKPIMEMBER'            : return None
        case 'CUBEMEMBER'               : return None
        case 'CUBEMEMBERPROPERTY'       : return None
        case 'CUBERANKEDMEMBER'         : return None
        case 'CUBESET'                  : return None
        case 'CUBESETCOUNT'             : return None
        case 'CUBEVALUE'                : return None
        case 'CUMIPMT'                  : return None
        case 'CUMPRINC'                 : return None
        case 'DATE'                     : return None
        case 'DATEDIF'                  : return None
        case 'DATEVALUE'                : return None
        case 'DAVERAGE'                 : return None
        case 'DAY'                      : return None
        case 'DAYS'                     : return None
        case 'DAYS360'                  : return None
        case 'DB'                       : return None
        case 'DBCS'                     : return None
        case 'DCOUNT'                   : return None
        case 'DCOUNTA'                  : return None
        case 'DDB'                      : return None
        case 'DEC2BIN'                  : return None
        case 'DEC2HEX'                  : return None
        case 'DEC2OCT'                  : return None
        case 'DECIMAL'                  : return None
        case 'DEGREES'                  : return None
        case 'DELTA'                    : return None
        case 'DETECTLANGUAGE'           : return None
        case 'DEVSQ'                    : return None
        case 'DGET'                     : return None
        case 'DISC'                     : return None
        case 'DMAX'                     : return None
        case 'DMIN'                     : return None
        case 'DOLLAR'                   : return None
        case 'DOLLARDE'                 : return None
        case 'DOLLARFR'                 : return None
        case 'DPRODUCT'                 : return None
        case 'DROP'                     : return None
        case 'DSTDEV'                   : return None
        case 'DSTDEVP'                  : return None
        case 'DSUM'                     : return None
        case 'DURATION'                 : return None
        case 'DVAR'                     : return None
        case 'DVARP'                    : return None
        case 'EDATE'                    : return None
        case 'EFFECT'                   : return None
        case 'ENCODEURL'                : return None
        case 'EOMONTH'                  : return None
        case 'ERF'                      : return None
        case 'ERF.PRECISE'              : return None
        case 'ERFC'                     : return None
        case 'ERFC.PRECISE'             : return None
        case 'ERROR.TYPE'               : return None
        case 'EUROCONVERT'              : return None
        case 'EVEN'                     : return None
        case 'EXACT'                    : return None
        case 'EXP'                      : return None
        case 'EXPAND'                   : return None
        case 'EXPON.DIST'               : return None
        case 'EXPONDIST'                : return None
        case 'FACT'                     : return None
        case 'FACTDOUBLE'               : return None
        case 'FALSE'                    : return None
        case 'IST'                      : return None
        case 'FDIST'                    : return None
        case 'IST.RT'                   : return None
        case 'FILTER'                   : return None
        case 'FILTERXML'                : return None
        case 'FIND'                     : return None
        case 'FINDB'                    : return None
        case 'NV'                       : return None
        case 'NV.RT'                    : return None
        case 'FINV'                     : return None
        case 'FISHER'                   : return None
        case 'FISHERINV'                : return None
        case 'FIXED'                    : return None
        case 'FLOOR'                    : return None
        case 'FLOOR.MATH'               : return None
        case 'FLOOR.PRECISE'            : return None
        case 'FORECAST.LINEAR'          : return None
        case 'FORECAST.ETS'             : return None
        case 'FORECAST.ETS.CONFINT'     : return None
        case 'FORECAST.ETS.SEASONALITY' : return None
        case 'FORECAST.ETS.STAT'        : return None
        case 'FORECAST.LINEAR'          : return None
        case 'FORMULATEXT'              : return None
        case 'FREQUENCY'                : return None
        case 'EST'                      : return None
        case 'FTEST'                    : return None
        case 'FV'                       : return None
        case 'FVSCHEDULE'               : return None
        case 'GAMMA'                    : return None
        case 'GAMMA.DIST'               : return None
        case 'GAMMADIST'                : return None
        case 'GAMMA.INV'                : return None
        case 'GAMMAINV'                 : return None
        case 'GAMMALN'                  : return None
        case 'GAMMALN.PRECISE'          : return None
        case 'GAUSS'                    : return None
        case 'GCD'                      : return None
        case 'GEOMEAN'                  : return None
        case 'GESTEP'                   : return None
        case 'GETPIVOTDATA'             : return None
        case 'GROUPBY'                  : return None
        case 'GROWTH'                   : return None
        case 'HARMEAN'                  : return None
        case 'HEX2BIN'                  : return None
        case 'HEX2DEC'                  : return None
        case 'HEX2OCT'                  : return None
        case 'HLOOKUP'                  : return None
        case 'HOUR'                     : return None
        case 'HSTACK'                   : return None
        case 'HYPERLINK'                : return None
        case 'HYPGEOM.DIST'             : return None
        case 'HYPGEOMDIST'              : return None
        case 'IF'                       : return None
        case 'IFERROR'                  : return None
        case 'IFNA'                     : return None
        case 'IFS'                      : return None
        case 'IMABS'                    : return None
        case 'IMAGE'                    : return None
        case 'IMAGINARY'                : return None
        case 'IMARGUMENT'               : return None
        case 'IMCONJUGATE'              : return None
        case 'IMCOS'                    : return None
        case 'IMCOSH'                   : return None
        case 'IMCOT'                    : return None
        case 'IMCSC'                    : return None
        case 'IMCSCH'                   : return None
        case 'IMDIV'                    : return None
        case 'IMEXP'                    : return None
        case 'IMLN'                     : return None
        case 'IMLOG10'                  : return None
        case 'IMLOG2'                   : return None
        case 'IMPOWER'                  : return None
        case 'IMPRODUCT'                : return None
        case 'IMREAL'                   : return None
        case 'IMSEC'                    : return None
        case 'IMSECH'                   : return None
        case 'IMSIN'                    : return None
        case 'IMSINH'                   : return None
        case 'IMSQRT'                   : return None
        case 'IMSUB'                    : return None
        case 'IMSUM'                    : return None
        case 'IMTAN'                    : return None
        case 'INDEX'                    : return None
        case 'INDIRECT'                 : return None
        case 'INFO'                     : return None
        case 'INT'                      : return None
        case 'INTERCEPT'                : return None
        case 'INTRATE'                  : return None
        case 'IPMT'                     : return None
        case 'IRR'                      : return None
        case 'ISBLANK'                  : return None
        case 'ISERR'                    : return None
        case 'ISERROR'                  : return None
        case 'ISEVEN'                   : return None
        case 'ISFORMULA'                : return None
        case 'ISLOGICAL'                : return None
        case 'ISNA'                     : return None
        case 'ISNONTEXT'                : return None
        case 'ISNUMBER'                 : return None
        case 'ISODD'                    : return None
        case 'ISOMITTED'                : return None
        case 'ISREF'                    : return None
        case 'ISTEXT'                   : return None
        case 'ISO.CEILING'              : return None
        case 'ISOWEEKNUM'               : return None
        case 'ISPMT'                    : return None
        case 'JIS'                      : return None
        case 'KURT'                     : return None
        case 'LAMBDA'                   : return None
        case 'LARGE'                    : return None
        case 'LCM'                      : return None
        case 'LEFT'                     : return None
        case 'LEFTB'                    : return None
        case 'LEN'                      : return None
        case 'LENB'                     : return None
        case 'LET'                      : return None
        case 'LINEST'                   : return None
        case 'LN'                       : return None
        case 'LOG'                      : return None
        case 'LOG10'                    : return None
        case 'LOGEST'                   : return None
        case 'LOGINV'                   : return None
        case 'LOGNORM.DIST'             : return None
        case 'LOGNORMDIST'              : return None
        case 'LOGNORM.INV'              : return None
        case 'LOOKUP'                   : return None
        case 'LOWER'                    : return None
        case 'MAKEARRAY'                : return None
        case 'MAP'                      : return None
        case 'MATCH'                    : return None
        case 'MAX'                      : return None
        case 'MAXA'                     : return None
        case 'MAXIFS'                   : return None
        case 'MDETERM'                  : return None
        case 'MDURATION'                : return None
        case 'MEDIAN'                   : return None
        case 'MID, MIDB'                : return None
        case 'MIN'                      : return None
        case 'MINIFS'                   : return None
        case 'MINA'                     : return None
        case 'MINUTE'                   : return None
        case 'MINVERSE'                 : return None
        case 'MIRR'                     : return None
        case 'MMULT'                    : return None
        case 'MOD'                      : return None
        case 'MODE'                     : return None
        case 'MODE.MULT'                : return None
        case 'MODE.SNGL'                : return None
        case 'MONTH'                    : return None
        case 'MROUND'                   : return None
        case 'MULTINOMIAL'              : return None
        case 'MUNIT'                    : return None
        case 'NA'                       : return None
        case 'NEGBINOM.DIST'            : return None
        case 'NEGBINOMDIST'             : return None
        case 'NETWORKDAYS'              : return None
        case 'NETWORKDAYS.INTL'         : return None
        case 'NOMINAL'                  : return None
        case 'NORM.DIST'                : return None
        case 'NORMDIST'                 : return None
        case 'NORMINV'                  : return None
        case 'NORM.INV'                 : return None
        case 'NORM.S.DIST'              : return None
        case 'NORMSDIST'                : return None
        case 'NORM.S.INV'               : return None
        case 'NORMSINV'                 : return None
        case 'NOT'                      : return None
        case 'NOW'                      : return None
        case 'NPER'                     : return None
        case 'NPV'                      : return None
        case 'NUMBERVALUE'              : return None
        case 'OCT2BIN'                  : return None
        case 'OCT2DEC'                  : return None
        case 'OCT2HEX'                  : return None
        case 'ODD'                      : return None
        case 'ODDFPRICE'                : return None
        case 'ODDFYIELD'                : return None
        case 'ODDLPRICE'                : return None
        case 'ODDLYIELD'                : return None
        case 'OFFSET'                   : return None
        case 'OR'                       : return None
        case 'PDURATION'                : return None
        case 'PEARSON'                  : return None
        case 'PERCENTILE.EXC'           : return None
        case 'PERCENTILE.INC'           : return None
        case 'PERCENTILE'               : return None
        case 'PERCENTOF'                : return None
        case 'PERCENTRANK.EXC'          : return None
        case 'PERCENTRANK.INC'          : return None
        case 'PERCENTRANK'              : return None
        case 'PERMUT'                   : return None
        case 'PERMUTATIONA'             : return None
        case 'PHI'                      : return None
        case 'PHONETIC'                 : return None
        case 'PI'                       : return None
        case 'PIVOTBY'                  : return None
        case 'PMT'                      : return None
        case 'POISSON.DIST'             : return None
        case 'POISSON'                  : return None
        case 'POWER'                    : return None
        case 'PPMT'                     : return None
        case 'PRICE'                    : return None
        case 'PRICEDISC'                : return None
        case 'PRICEMAT'                 : return None
        case 'PROB'                     : return None
        case 'PRODUCT'                  : return None
        case 'PROPER'                   : return None
        case 'PV'                       : return None
        case 'QUARTILE'                 : return None
        case 'QUARTILE.EXC'             : return None
        case 'QUARTILE.INC'             : return None
        case 'QUOTIENT'                 : return None
        case 'RADIANS'                  : return None
        case 'RAND'                     : return None
        case 'RANDARRAY'                : return None
        case 'RANDBETWEEN'              : return None
        case 'RANK.AVG'                 : return None
        case 'RANK.EQ'                  : return None
        case 'RANK'                     : return None
        case 'RATE'                     : return None
        case 'RECEIVED'                 : return None
        case 'REDUCE'                   : return None
        case 'REGEXEXTRACT'             : return None
        case 'REGEXREPLACE'             : return None
        case 'REGEXTEST'                : return None
        case 'REGISTER.ID'              : return None
        case 'REPLACE'                  : return None
        case 'REPLACEB'                 : return None
        case 'REPT'                     : return None
        case 'RIGHT'                    : return None
        case 'RIGHTB'                   : return None
        case 'ROMAN'                    : return None
        case 'ROUND'                    : return None
        case 'ROUNDDOWN'                : return None
        case 'ROUNDUP'                  : return None
        case 'ROW'                      : return None
        case 'ROWS'                     : return None
        case 'RRI'                      : return None
        case 'RSQ'                      : return None
        case 'RTD'                      : return None
        case 'SCAN'                     : return None
        case 'SEARCH'                   : return None
        case 'SEARCHB'                  : return None
        case 'SEC'                      : return None
        case 'SECH'                     : return None
        case 'SECOND'                   : return None
        case 'SEQUENCE'                 : return None
        case 'SERIESSUM'                : return None
        case 'SHEET'                    : return None
        case 'SHEETS'                   : return None
        case 'SIGN'                     : return None
        case 'SIN'                      : return None
        case 'SINH'                     : return None
        case 'SKEW'                     : return None
        case 'SKEW.P'                   : return None
        case 'SLN'                      : return None
        case 'SLOPE'                    : return None
        case 'SMALL'                    : return None
        case 'SORT'                     : return None
        case 'SORTBY'                   : return None
        case 'SQRT'                     : return None
        case 'SQRTPI'                   : return None
        case 'STANDARDIZE'              : return None
        case 'STOCKHISTORY'             : return None
        case 'STDEV'                    : return None
        case 'STDEV.P'                  : return None
        case 'STDEV.S'                  : return None
        case 'STDEVA'                   : return None
        case 'STDEVP'                   : return None
        case 'STDEVPA'                  : return None
        case 'STEYX'                    : return None
        case 'STOCKHISTORY'             : return None
        case 'SUBSTITUTE'               : return None
        case 'SUBTOTAL'                 : return None
        case 'SUM'                      : return None
        case 'SUMIF'                    : return None
        case 'SUMIFS'                   : return None
        case 'SUMPRODUCT'               : return None
        case 'SUMSQ'                    : return None
        case 'SUMX2MY2'                 : return None
        case 'SUMX2PY2'                 : return None
        case 'SUMXMY2'                  : return None
        case 'SWITCH'                   : return None
        case 'SYD'                      : return None
        case 'TAN'                      : return None
        case 'TANH'                     : return None
        case 'TAKE'                     : return None
        case 'TBILLEQ'                  : return None
        case 'TBILLPRICE'               : return None
        case 'TBILLYIELD'               : return None
        case 'IST'                      : return None
        case 'IST.2T'                   : return None
        case 'IST.RT'                   : return None
        case 'TDIST'                    : return None
        case 'TEXT'                     : return None
        case 'TEXTAFTER'                : return None
        case 'TEXTBEFORE'               : return None
        case 'TEXTJOIN'                 : return None
        case 'TEXTSPLIT'                : return None
        case 'TIME'                     : return None
        case 'TIMEVALUE'                : return None
        case 'NV'                       : return None
        case 'NV.2T'                    : return None
        case 'TINV'                     : return None
        case 'TOCOL'                    : return None
        case 'TOROW'                    : return None
        case 'TODAY'                    : return None
        case 'TRANSLATE'                : return None
        case 'TRANSPOSE'                : return None
        case 'TREND'                    : return None
        case 'TRIM'                     : return None
        case 'TRIMMEAN'                 : return None
        case 'TRIMRANGE'                : return None
        case 'TRUE'                     : return None
        case 'TRUNC'                    : return None
        case 'EST'                      : return None
        case 'TTEST'                    : return None
        case 'TYPE'                     : return None
        case 'UNICHAR'                  : return None
        case 'UNICODE'                  : return None
        case 'UNIQUE'                   : return None
        case 'UPPER'                    : return None
        case 'VALUE'                    : return None
        case 'VALUETOTEXT'              : return None
        case 'VAR'                      : return None
        case 'VAR.P'                    : return None
        case 'VAR.S'                    : return None
        case 'VARA'                     : return None
        case 'VARP'                     : return None
        case 'VARPA'                    : return None
        case 'VDB'                      : return None
        case 'VLOOKUP'                  : return None
        case 'VSTACK'                   : return None
        case 'WEBSERVICE'               : return None
        case 'WEEKDAY'                  : return None
        case 'WEEKNUM'                  : return None
        case 'WEIBULL'                  : return None
        case 'WEIBULL.DIST'             : return None
        case 'WORKDAY'                  : return None
        case 'WORKDAY.INTL'             : return None
        case 'WRAPCOLS'                 : return None
        case 'WRAPROWS'                 : return None
        case 'XIRR'                     : return None
        case 'XLOOKUP'                  : return None
        case 'XMATCH'                   : return None
        case 'XNPV'                     : return None
        case 'XOR'                      : return None
        case 'YEAR'                     : return None
        case 'YEARFRAC'                 : return None
        case 'YIELD'                    : return None
        case 'YIELDDISC'                : return None
        case 'YIELDMAT'                 : return None
        case 'EST'                      : return None
        case 'ZTEST'                    : return None

    return None

#
# DAX Expression Builder
#

def _get_dax_expression(func_name: str, args: List) -> polars.Expr:
    func_name = func_name.upper()

    match func_name:
        # Aggregation
        case 'APPROXIMATEDISTINCTCOUNT'    : return _get_dax_approximate_distinct_count_expression(args)
        case 'AVERAGE'                     : return _get_dax_average_expression(args)
        case 'AVERAGEA'                    : return _get_dax_average_a_expression(args)
        case 'AVERAGEX'                    : return None # not supported
        case 'COUNT'                       : return _get_dax_count_expression(args)
        case 'COUNTA'                      : return _get_dax_count_a_expression(args)
        case 'COUNTAX'                     : return None # not supported
        case 'COUNTBLANK'                  : return _get_dax_count_blank_expression(args)
        case 'COUNTROWS'                   : return _get_dax_count_rows_expression(args)
        case 'COUNTX'                      : return None # not supported
        case 'DISTINCTCOUNT'               : return _get_dax_distinct_count_expression(args)
        case 'DISTINCTCOUNTNOBLANK'        : return _get_dax_distinct_count_no_blank_expression(args)
        case 'MAX'                         : return _get_dax_max_expression(args)
        case 'MAXA'                        : return _get_dax_max_a_expression(args)
        case 'MAXX'                        : return None # not supported
        case 'MIN'                         : return _get_dax_min_expression(args)
        case 'MINA'                        : return _get_dax_min_a_expression(args)
        case 'MINX'                        : return None # not supported
        case 'PRODUCT'                     : return _get_dax_product_expression(args)
        case 'PRODUCTX'                    : return None # not supported
        case 'SUM'                         : return _get_dax_sum_expression(args)
        case 'SUMX'                        : return None # not supported

        # Date and time
        case 'CALENDAR'                    : return None # not supported
        case 'CALENDARAUTO'                : return None # not supported
        case 'DATE'                        : return _get_dax_date_expression(args)
        case 'DATEDIFF'                    : return _get_dax_date_diff_expression(args)
        case 'DATEVALUE'                   : return _get_dax_date_value_expression(args)
        case 'DAY'                         : return _get_dax_day_expression(args)
        case 'EDATE'                       : return _get_dax_e_date_expression(args)
        case 'EOMONTH'                     : return _get_dax_e_o_month_expression(args)
        case 'HOUR'                        : return _get_dax_hour_expression(args)
        case 'MINUTE'                      : return _get_dax_minute_expression(args)
        case 'MONTH'                       : return _get_dax_month_expression(args)
        case 'NETWORKDAYS'                 : return None
        case 'NOW'                         : return polars.lit(datetime.now())
        case 'QUARTER'                     : return _get_dax_quarter_expression(args)
        case 'SECOND'                      : return _get_dax_second_expression(args)
        case 'TIME'                        : return _get_dax_time_expression(args)
        case 'TIMEVALUE'                   : return _get_dax_time_value_expression(args)
        case 'TODAY'                       : return polars.lit(datetime.today().date())
        case 'UTCNOW'                      : return polars.lit(datetime.now(timezone.utc))
        case 'UTCTODAY'                    : return polars.lit(datetime.now(timezone.utc).date())
        case 'WEEKDAY'                     : return _get_dax_week_day_expression(args)
        case 'WEEKNUM'                     : return _get_dax_week_num_expression(args)
        case 'YEAR'                        : return _get_dax_year_expression(args)
        case 'YEARFRAC'                    : return None

        # Time Intelligence
        case 'CLOSINGBALANCEMONTH'         : return None
        case 'CLOSINGBALANCEQUARTER'       : return None
        case 'CLOSINGBALANCEYEAR'          : return None
        case 'DATEADD'                     : return _get_dax_date_add_expression(args)
        case 'DATESBETWEEN'                : return None # TODO: support for multiple tables
        case 'DATESINPERIOD'               : return None # TODO: support for multiple tables
        case 'DATESMTD'                    : return None # TODO: support for multiple tables
        case 'DATESQTD'                    : return None # TODO: support for multiple tables
        case 'DATESYTD'                    : return None # TODO: support for multiple tables
        case 'ENDOFMONTH'                  : return _get_dax_end_of_month_expression(args)
        case 'ENDOFQUARTER'                : return _get_dax_end_of_quarter_expression(args)
        case 'ENDOFYEAR'                   : return _get_dax_end_of_year_expression(args)
        case 'FIRSTDATE'                   : return _get_dax_first_date_expression(args)
        case 'LASTDATE'                    : return _get_dax_last_date_expression(args)
        case 'NEXTDAY'                     : return None # not supported
        case 'NEXTMONTH'                   : return None # not supported
        case 'NEXTQUARTER'                 : return None # not supported
        case 'NEXTYEAR'                    : return None # not supported
        case 'OPENINGBALANCEMONTH'         : return None
        case 'OPENINGBALANCEQUARTER'       : return None
        case 'OPENINGBALANCEYEAR'          : return None
        case 'PARALLELPERIOD'              : return None
        case 'PREVIOUSDAY'                 : return None # not supported
        case 'PREVIOUSMONTH'               : return None # not supported
        case 'PREVIOUSQUARTER'             : return None # not supported
        case 'PREVIOUSYEAR'                : return None # not supported
        case 'SAMEPERIODLASTYEAR'          : return None
        case 'STARTOFMONTH'                : return _get_dax_start_of_month_expression(args)
        case 'STARTOFQUARTER'              : return _get_dax_start_of_quarter_expression(args)
        case 'STARTOFYEAR'                 : return _get_dax_start_of_year_expression(args)
        case 'TOTALMTD'                    : return None
        case 'TOTALQTD'                    : return None
        case 'TOTALYTD'                    : return None

        # Filter
        case 'ALL'                         : return None
        case 'ALLCROSSFILTERED'            : return None
        case 'ALLEXCEPT'                   : return None
        case 'ALLNOBLANKROW'               : return None
        case 'ALLSELECTED'                 : return None
        case 'CALCULATE'                   : return None
        case 'CALCULATETABLE'              : return None
        case 'EARLIER'                     : return None
        case 'EARLIEST'                    : return None
        case 'FILTER'                      : return None
        case 'FIRST'                       : return None
        case 'INDEX'                       : return None
        case 'KEEPFILTERS'                 : return None
        case 'LAST'                        : return None
        case 'LOOKUP'                      : return None
        case 'LOOKUPWITHTOTALS'            : return None
        case 'LOOKUPVALUE'                 : return None
        case 'MATCHBY'                     : return None
        case 'MOVINGAVERAGE'               : return None
        case 'NEXT'                        : return None
        case 'OFFSET'                      : return None
        case 'ORDERBY'                     : return None
        case 'PARTITIONBY'                 : return None
        case 'PREVIOUS'                    : return None
        case 'RANGE'                       : return None
        case 'RANK'                        : return None
        case 'REMOVEFILTERS'               : return None
        case 'ROWNUMBER'                   : return None
        case 'RUNNINGSUM'                  : return None
        case 'SELECTEDVALUE'               : return None
        case 'WINDOW'                      : return None

        # Financial
        case 'ACCRINT'                     : return None
        case 'ACCRINTM'                    : return None
        case 'AMORDEGRC'                   : return None
        case 'AMORLINC'                    : return None
        case 'COUPDAYBS'                   : return None
        case 'COUPDAYS'                    : return None
        case 'COUPDAYSNC'                  : return None
        case 'COUPNCD'                     : return None
        case 'COUPNUM'                     : return None
        case 'COUPPCD'                     : return None
        case 'CUMIPMT'                     : return None
        case 'CUMPRINC'                    : return None
        case 'DB'                          : return None
        case 'DDB'                         : return None
        case 'DISC'                        : return None
        case 'DOLLARDE'                    : return None
        case 'DOLLARFR'                    : return None
        case 'DURATION'                    : return None
        case 'EFFECT'                      : return None
        case 'FV'                          : return None
        case 'INTRATE'                     : return None
        case 'IPMT'                        : return None
        case 'ISPMT'                       : return None
        case 'MDURATION'                   : return None
        case 'NOMINAL'                     : return None
        case 'NPER'                        : return None
        case 'ODDFPRICE'                   : return None
        case 'ODDFYIELD'                   : return None
        case 'ODDLPRICE'                   : return None
        case 'ODDLYIELD'                   : return None
        case 'PDURATION'                   : return None
        case 'PMT'                         : return None
        case 'PPMT'                        : return None
        case 'PRICE'                       : return None
        case 'PRICEDISC'                   : return None
        case 'PRICEMAT'                    : return None
        case 'PV'                          : return None
        case 'RATE'                        : return None
        case 'RECEIVED'                    : return None
        case 'RRI'                         : return None
        case 'SLN'                         : return None
        case 'SYD'                         : return None
        case 'TBILLEQ'                     : return None
        case 'TBILLPRICE'                  : return None
        case 'TBILLYIELD'                  : return None
        case 'VDB'                         : return None
        case 'XIRR'                        : return None
        case 'XNPV'                        : return None
        case 'YIELD'                       : return None
        case 'YIELDDISC'                   : return None
        case 'YIELDMAT'                    : return None

        # Information
        case 'COLUMNSTATISTICS'            : return None
        case 'CONTAINS'                    : return None
        case 'CONTAINSROW'                 : return None
        case 'CONTAINSSTRING'              : return None
        case 'CONTAINSSTRINGEXACT'         : return None
        case 'CUSTOMDATA'                  : return None
        case 'HASONEFILTER'                : return None
        case 'HASONEVALUE'                 : return None
        case 'ISAFTER'                     : return None
        case 'ISBLANK'                     : return None
        case 'ISCROSSFILTERED'             : return None
        case 'ISEMPTY'                     : return None
        case 'ISERROR'                     : return None
        case 'ISEVEN'                      : return None
        case 'ISFILTERED'                  : return None
        case 'ISINSCOPE'                   : return None
        case 'ISLOGICAL'                   : return None
        case 'ISNONTEXT'                   : return None
        case 'ISNUMBER'                    : return None
        case 'ISODD'                       : return None
        case 'ISONORAFTER'                 : return None
        case 'ISSELECTEDMEASURE'           : return None
        case 'ISSUBTOTAL'                  : return None
        case 'ISTEXT'                      : return None
        case 'NONVISUAL'                   : return None
        case 'SELECTEDMEASURE'             : return None
        case 'SELECTEDMEASUREFORMATSTRING' : return None
        case 'SELECTEDMEASURENAME'         : return None
        case 'USERCULTURE'                 : return None
        case 'USERNAME'                    : return None
        case 'USEROBJECTID'                : return None
        case 'USERPRINCIPALNAME'           : return None

        # Logical
        case 'AND'                         : return _get_dax_and_expression(args)
        case 'BITAND'                      : return _get_dax_bit_and_expression(args)
        case 'BITLSHIFT'                   : return None
        case 'BITOR'                       : return _get_dax_bit_or_expression(args)
        case 'BITRSHIFT'                   : return None
        case 'BITXOR'                      : return _get_dax_bit_xor_expression(args)
        case 'COALESCE'                    : return None
        case 'FALSE'                       : return polars.lit(False)
        case 'IF'                          : return None
        case 'IF.EAGER'                    : return None
        case 'IFERROR'                     : return None
        case 'NOT'                         : return _get_dax_not_expression(args)
        case 'OR'                          : return _get_dax_or_expression(args)
        case 'SWITCH'                      : return None
        case 'TRUE'                        : return polars.lit(True)

        # Math and trigonometry
        case 'ABS'                         : return _get_dax_abs_expression(args)
        case 'ACOS'                        : return _get_dax_acos_expression(args)
        case 'ACOSH'                       : return _get_dax_acosh_expression(args)
        case 'ACOT'                        : return _get_dax_acot_expression(args)
        case 'ACOTH'                       : return _get_dax_acoth_expression(args)
        case 'ASIN'                        : return _get_dax_asin_expression(args)
        case 'ASINH'                       : return _get_dax_asinh_expression(args)
        case 'ATAN'                        : return _get_dax_atan_expression(args)
        case 'ATANH'                       : return _get_dax_atanh_expression(args)
        case 'CEILING'                     : return None
        case 'CONVERT'                     : return None
        case 'COS'                         : return _get_dax_cos_expression(args)
        case 'COSH'                        : return _get_dax_cosh_expression(args)
        case 'COT'                         : return _get_dax_cot_expression(args)
        case 'COTH'                        : return None
        case 'CURRENCY'                    : return None
        case 'DEGREES'                     : return _get_dax_degrees_expression(args)
        case 'DIVIDE'                      : return _get_dax_divide_expression(args)
        case 'EVEN'                        : return _get_dax_even_expression(args)
        case 'EXP'                         : return _get_dax_exp_expression(args)
        case 'FACT'                        : return None
        case 'FLOOR'                       : return None
        case 'GCD'                         : return None
        case 'INT'                         : return None
        case 'ISO.CEILING'                 : return None
        case 'LCM'                         : return None
        case 'LN'                          : return _get_dax_ln_expression(args)
        case 'LOG'                         : return _get_dax_log_expression(args)
        case 'LOG10'                       : return _get_dax_log_10_expression(args)
        case 'MOD'                         : return None
        case 'MROUND'                      : return None
        case 'ODD'                         : return _get_dax_odd_expression(args)
        case 'PI'                          : return polars.lit(math.pi)
        case 'POWER'                       : return _get_dax_power_expression(args)
        case 'QUOTIENT'                    : return None
        case 'RADIANS'                     : return _get_dax_radians_expression(args)
        case 'RAND'                        : return None
        case 'RANDBETWEEN'                 : return None
        case 'ROUND'                       : return None
        case 'ROUNDDOWN'                   : return None
        case 'ROUNDUP'                     : return None
        case 'SIGN'                        : return _get_dax_sign_expression(args)
        case 'SIN'                         : return _get_dax_sin_expression(args)
        case 'SINH'                        : return _get_dax_sinh_expression(args)
        case 'SQRT'                        : return _get_dax_sqrt_expression(args)
        case 'SQRTPI'                      : return _get_dax_sqrt_pi_expression(args)
        case 'TAN'                         : return _get_dax_tan_expression(args)
        case 'TANH'                        : return _get_dax_tanh_expression(args)
        case 'TRUNC'                       : return None

        # Statistical
        case 'BETA.DIST'                   : return None
        case 'BETA.INV'                    : return None
        case 'CHISQ.DIST'                  : return None
        case 'CHISQ.DIST.RT'               : return None
        case 'CHISQ.INV'                   : return None
        case 'CHISQ.INV.RT'                : return None
        case 'COMBIN'                      : return None
        case 'COMBINA'                     : return None
        case 'CONFIDENCE.NORM'             : return None
        case 'CONFIDENCE.T'                : return None
        case 'EXPON.DIST'                  : return None
        case 'GEOMEAN'                     : return None
        case 'GEOMEANX'                    : return None
        case 'LINEST'                      : return None
        case 'LINESTX'                     : return None
        case 'MEDIAN'                      : return None
        case 'MEDIANX'                     : return None
        case 'NORM.DIST'                   : return None
        case 'NORM.INV'                    : return None
        case 'NORM.S.DIST'                 : return None
        case 'NORM.S.INV'                  : return None
        case 'PERCENTILE.EXC'              : return None
        case 'PERCENTILE.INC'              : return None
        case 'PERCENTILEX.EXC'             : return None
        case 'PERCENTILEX.INC'             : return None
        case 'PERMUT'                      : return None
        case 'POISSON.DIST'                : return None
        case 'RANK.EQ'                     : return None
        case 'RANKX'                       : return None
        case 'SAMPLE'                      : return None
        case 'STDEV.P'                     : return None
        case 'STDEV.S'                     : return None
        case 'STDEVX.P'                    : return None
        case 'STDEVX.S'                    : return None
        case 'T.DIST'                      : return None
        case 'T.DIST.2T'                   : return None
        case 'T.DIST.RT'                   : return None
        case 'T.INV'                       : return None
        case 'T.INV.2t'                    : return None
        case 'VAR.P'                       : return None
        case 'VAR.S'                       : return None
        case 'VARX.P'                      : return None
        case 'VARX.S'                      : return None

        # Text
        case 'COMBINEVALUES'               : return None
        case 'CONCATENATE'                 : return None
        case 'CONCATENATEX'                : return None
        case 'EXACT'                       : return None
        case 'FIND'                        : return None
        case 'FIXED'                       : return None
        case 'FORMAT'                      : return None
        case 'LEFT'                        : return None
        case 'LEN'                         : return _get_dax_len_expression(args)
        case 'LOWER'                       : return _get_dax_lower_expression(args)
        case 'MID'                         : return None
        case 'REPLACE'                     : return None
        case 'REPT'                        : return None
        case 'RIGHT'                       : return None
        case 'SEARCH'                      : return None
        case 'SUBSTITUTE'                  : return None
        case 'TRIM'                        : return None
        case 'UNICHAR'                     : return None
        case 'UNICODE'                     : return None
        case 'UPPER'                       : return _get_dax_upper_expression(args)
        case 'VALUE'                       : return _get_dax_value_expression(args)

        # Other
        case 'BLANK'                       : return polars.lit(None)

    return None

def _get_dax_approximate_distinct_count_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for APPROXIMATEDISTINCTCOUNT(column)')
    return _convert_dax_arg_to_column_expr(args[0]).approx_n_unique()

def _get_dax_average_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for AVERAGE(column)')
    expr = _convert_dax_arg_to_column_expr(args[0])
    return expr.cast(polars.Float64, wrap_numerical=True).mean()

def _get_dax_average_a_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for AVERAGEA(column)')
    return _convert_dax_arg_to_non_numeric_column_expr(args[0], autofill=False).mean()

def _get_dax_count_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for COUNT(column)')
    return _convert_dax_arg_to_column_expr(args[0]).count()

def _get_dax_count_a_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for COUNTA(column)')
    return _convert_dax_arg_to_non_numeric_column_expr(args[0], autofill=False).count()

def _get_dax_distinct_count_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for DISTINCTCOUNT(column)')
    return _convert_dax_arg_to_column_expr(args[0]).n_unique()

def _get_dax_count_blank_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for COUNTBLANK(column)')
    return _convert_dax_arg_to_column_expr(args[0]).null_count()

def _get_dax_count_rows_expression(args: List) -> polars.Expr:
    # TODO: support for specifying a table
    return polars.len()

def _get_dax_distinct_count_no_blank_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for DISTINCTCOUNTNOBLANK(column)')
    col_expr = _convert_dax_arg_to_column_expr(args[0])
    return col_expr.n_unique() - col_expr.null_count().gt(0)

def _get_dax_max_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for MAX(column)')
    return _convert_dax_arg_to_column_expr(args[0]).max()

def _get_dax_max_a_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for MAXA(column)')
    return _convert_dax_arg_to_non_numeric_column_expr(args[0], autofill=False).max()

def _get_dax_min_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for MIN(column)')
    return _convert_dax_arg_to_column_expr(args[0]).min()

def _get_dax_min_a_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for MINA(column)')
    return _convert_dax_arg_to_non_numeric_column_expr(args[0], autofill=False).min()

def _get_dax_product_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for PRODUCT(column)')
    return _convert_dax_arg_to_column_expr(args[0]).product()

def _get_dax_sum_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for SUM(column)')
    return _convert_dax_arg_to_column_expr(args[0]).sum()

def _get_dax_date_expression(args: List) -> polars.Expr:
    if len(args) < 3:
        raise Exception('Invalid argument count for DATE(year, month, day)')
    args[0] = _convert_dax_arg_to_numeric_or_column_expr(args[0])
    args[1] = _convert_dax_arg_to_numeric_or_column_expr(args[1])
    args[2] = _convert_dax_arg_to_numeric_or_column_expr(args[2])
    return polars.date(args[0], args[1], args[2])

def _get_dax_date_diff_expression(args: List) -> polars.Expr:
    if len(args) < 3:
        raise Exception('Invalid argument count for DATEDIFF(date1, date2, interval)')
    date1_expr = _convert_dax_arg_to_date_time_or_column_expr(args[0])
    date2_expr = _convert_dax_arg_to_date_time_or_column_expr(args[1])
    interval = str(args[2]).upper()
    if interval not in ['SECOND', 'MINUTE', 'HOUR', 'DAY', 'WEEK', 'MONTH', 'QUARTER', 'YEAR']:
        raise Exception('Invalid type of argument 3 for DATEDIFF(date1, date2, interval)')
    diff_datetime = date2_expr - date1_expr
    if interval == 'DAY':
        return diff_datetime.dt.total_days()
    if interval == 'WEEK':
        return diff_datetime.dt.total_days() // 7
    if interval == 'HOUR':
        return diff_datetime.dt.total_hours().cast(polars.Int64)
    if interval == 'MINUTE':
        return diff_datetime.dt.total_minutes().cast(polars.Int64)
    if interval == 'SECOND':
        return diff_datetime.dt.total_seconds().cast(polars.Int64)
    year_months = (date2_expr.dt.year() - date1_expr.dt.year()) * 12
    diff_months = date2_expr.dt.month() - date1_expr.dt.month()
    if interval == 'MONTH':
        return year_months + diff_months
    if interval == 'QUARTER':
        return (year_months + diff_months) // 3
    if interval == 'YEAR':
        return date2_expr.dt.year() - date1_expr.dt.year()

def _get_dax_date_value_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for DATEVALUE(date_text)')
    return _convert_dax_arg_to_date_time(args[0]).dt.date()

def _get_dax_day_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for DAY(datetime)')
    return _convert_dax_arg_to_date_time_or_column_expr(args[0]).dt.day()

def _get_dax_e_date_expression(args: List) -> polars.Expr:
    if len(args) < 2:
        raise Exception('Invalid argument count for EDATE(start_date, months)')
    expr = _convert_dax_arg_to_date_time_or_column_expr(args[0])
    months = int(_convert_dax_arg_to_literal(args[1]))
    return expr.dt.offset_by(f'{months}mo').dt.date()

def _get_dax_e_o_month_expression(args: List) -> polars.Expr:
    if len(args) < 2:
        raise Exception('Invalid argument count for EOMONTH(start_date, months)')
    expr = _convert_dax_arg_to_date_time_or_column_expr(args[0])
    months = int(_convert_dax_arg_to_literal(args[1]))
    return expr.dt.offset_by(f'{months}mo').dt.month_end().dt.date()

def _get_dax_hour_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for HOUR(datetime)')
    return _convert_dax_arg_to_time_or_column_expr(args[0]).dt.hour()

def _get_dax_minute_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for MINUTE(datetime)')
    return _convert_dax_arg_to_time_or_column_expr(args[0]).dt.minute()

def _get_dax_month_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for MONTH(datetime)')
    return _convert_dax_arg_to_date_time_or_column_expr(args[0]).dt.month()

def _get_dax_quarter_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for QUARTER(datetime)')
    return _convert_dax_arg_to_date_time_or_column_expr(args[0]).dt.quarter()

def _get_dax_second_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for SECOND(datetime)')
    return _convert_dax_arg_to_time_or_column_expr(args[0]).dt.second()

def _get_dax_time_expression(args: List) -> polars.Expr:
    if len(args) < 3:
        raise Exception('Invalid argument count for TIME(hour, minute, second)')
    args[0] = _convert_dax_arg_to_numeric_or_column_expr(args[0])
    args[1] = _convert_dax_arg_to_numeric_or_column_expr(args[1])
    args[2] = _convert_dax_arg_to_numeric_or_column_expr(args[2])
    return polars.time(args[0], args[1], args[2])

def _get_dax_time_value_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for TIMEVALUE(time_text)')
    return _convert_dax_arg_to_time_or_column_expr(args[0]).dt.time()

def _get_dax_week_day_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for WEEKDAY(date, [return_type])')
    expr = _convert_dax_arg_to_date_time_or_column_expr(args[0])
    rtype = 1
    if len(args) > 1:
        rtype = int(_convert_dax_arg_to_literal(args[1]))
        rtype = max(1, min(3, rtype))
        if rtype == 3:
            return expr.dt.weekday() - 1
    return polars.when(expr.dt.weekday() == 1).then(7).otherwise(expr.dt.weekday() - 2 + rtype)

def _get_dax_week_num_expression(args: List) -> polars.Expr:
    # TODO: implement the return_type parameter
    # See https://learn.microsoft.com/en-us/dax/weeknum-function-dax
    if len(args) < 1:
        raise Exception('Invalid argument count for WEEKNUM(date)')
    return _convert_dax_arg_to_date_time_or_column_expr(args[0]).dt.week()

def _get_dax_year_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for YEAR(datetime)')
    return _convert_dax_arg_to_date_time_or_column_expr(args[0]).dt.year()

def _get_dax_date_add_expression(args: List) -> polars.Expr:
    if len(args) < 3:
        raise Exception('Invalid argument count for DATEADD(dates, number_of_intervals, interval)')
    args[0] = _convert_dax_arg_to_date_time_or_column_expr(args[0])
    args[1] = int(_convert_dax_arg_to_literal(args[1]))
    args[2] = str(_convert_dax_arg_to_literal(args[2])).upper()
    AVAILABLE_INTERVALS = {
        'YEAR'    : 'y',
        'QUARTER' : 'q',
        'MONTH'   : 'mo',
        'DAY'     : 'd',
    }
    if args[2] not in AVAILABLE_INTERVALS:
        raise Exception('Invalid type of argument 3 for DATEADD(dates, number_of_intervals, interval)')
    interval = AVAILABLE_INTERVALS[args[2]]
    return args[0].dt.offset_by(f'{args[1]}{interval}').cast(polars.Date)

def _get_dax_end_of_month_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for ENDOFMONTH(dates)')
    args[0] = _convert_dax_arg_to_date_time_or_column_expr(args[0])
    return args[0].dt.month_end().dt.date()

def _get_dax_end_of_quarter_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for ENDOFQUARTER(dates)')
    args[0] = _convert_dax_arg_to_date_time_or_column_expr(args[0])
    target_quarter = args[0].dt.quarter()
    target_year = args[0].dt.year()
    expr = polars.when(target_quarter.eq(1)).then(polars.date(target_year, 3, 31)) \
                 .when(target_quarter.eq(2)).then(polars.date(target_year, 6, 30)) \
                 .when(target_quarter.eq(3)).then(polars.date(target_year, 9, 30)) \
                 .otherwise(polars.date(target_year, 12, 31))
    return expr.cast(polars.Date)

def _get_dax_end_of_year_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for ENDOFYEAR(dates, [year_end_date])')
    args[0] = _convert_dax_arg_to_date_time_or_column_expr(args[0])
    target_year = args[0].dt.year()
    target_month = args[0].dt.month()
    target_day = args[0].dt.day()
    year_end_date = polars.date(target_year, 12, 31)
    if len(args) > 1:
        year_end_date = _convert_dax_arg_to_date_time_or_column_expr(args[1])
    end_month = year_end_date.dt.month()
    end_day = year_end_date.dt.day()
    return polars.when((target_month <= end_month) & (target_day <= end_day)) \
                 .then(polars.date(target_year, end_month, end_day)) \
                 .otherwise(polars.date(target_year + 1, end_month, end_day))

def _get_dax_first_date_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for FIRSTDATE(dates)')
    args[0] = _convert_dax_arg_to_date_time_or_column_expr(args[0])
    if args[0].meta.is_column():
        return args[0].min()
    return args[0].dt.date()

def _get_dax_last_date_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for LASTDATE(dates)')
    args[0] = _convert_dax_arg_to_date_time_or_column_expr(args[0])
    if args[0].meta.is_column():
        return args[0].max()
    return args[0].dt.date()

def _get_dax_start_of_month_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for STARTOFMONTH(dates)')
    args[0] = _convert_dax_arg_to_date_time_or_column_expr(args[0])
    return args[0].dt.month_start().dt.date()

def _get_dax_start_of_quarter_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for STARTOFQUARTER(dates)')
    args[0] = _convert_dax_arg_to_date_time_or_column_expr(args[0])
    target_quarter = args[0].dt.quarter()
    target_year = args[0].dt.year()
    expr = polars.when(target_quarter.eq(1)).then(polars.date(target_year, 1, 31)) \
                 .when(target_quarter.eq(2)).then(polars.date(target_year, 4, 30)) \
                 .when(target_quarter.eq(3)).then(polars.date(target_year, 7, 31)) \
                 .otherwise(polars.date(target_year, 10, 31))
    return expr.cast(polars.Date)

def _get_dax_start_of_year_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for STARTOFYEAR(dates, [year_end_date])')
    args[0] = _convert_dax_arg_to_date_time_or_column_expr(args[0])
    target_year = args[0].dt.year()
    target_month = args[0].dt.month()
    target_day = args[0].dt.day()
    year_end_date = polars.date(target_year, 1, 31)
    if len(args) > 1:
        year_end_date = _convert_dax_arg_to_date_time_or_column_expr(args[1])
    end_month = year_end_date.dt.month()
    end_day = year_end_date.dt.day()
    return polars.when((target_month <= end_month) & (target_day <= end_day)) \
                 .then(polars.date(target_year - 1, end_month, end_day).dt.offset_by('1d')) \
                 .otherwise(polars.date(target_year, end_month, end_day).dt.offset_by('1d'))

def _get_dax_and_expression(args: List) -> polars.Expr:
    if len(args) < 2:
        raise Exception('Invalid argument count for AND(logical1, logical2)')
    args[0] = _convert_dax_arg_to_numeric_or_boolean_or_column_expr(args[0])
    args[1] = _convert_dax_arg_to_numeric_or_boolean_or_column_expr(args[1])
    return args[0].and_(args[1])

def _get_dax_bit_and_expression(args: List) -> polars.Expr:
    if len(args) < 2:
        raise Exception('Invalid argument count for BITAND(number1, number2)')
    args[0] = _convert_dax_arg_to_numeric_or_boolean_or_column_expr(args[0])
    args[1] = _convert_dax_arg_to_numeric_or_boolean_or_column_expr(args[1])
    return args[0].and_(args[1])

def _get_dax_bit_or_expression(args: List) -> polars.Expr:
    if len(args) < 2:
        raise Exception('Invalid argument count for BITOR(number1, number2)')
    args[0] = _convert_dax_arg_to_numeric_or_boolean_or_column_expr(args[0])
    args[1] = _convert_dax_arg_to_numeric_or_boolean_or_column_expr(args[1])
    return args[0].or_(args[1])

def _get_dax_bit_xor_expression(args: List) -> polars.Expr:
    if len(args) < 2:
        raise Exception('Invalid argument count for BITXOR(number1, number2)')
    args[0] = _convert_dax_arg_to_numeric_or_boolean_or_column_expr(args[0])
    args[1] = _convert_dax_arg_to_numeric_or_boolean_or_column_expr(args[1])
    return args[0].xor(args[1])

def _get_dax_not_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for NOT(logical)')
    args[0] = _convert_dax_arg_to_numeric_or_boolean_or_column_expr(args[0])
    return args[0].not_()

def _get_dax_or_expression(args: List) -> polars.Expr:
    if len(args) < 2:
        raise Exception('Invalid argument count for OR(logical1, logical2)')
    args[0] = _convert_dax_arg_to_numeric_or_boolean_or_column_expr(args[0])
    args[1] = _convert_dax_arg_to_numeric_or_boolean_or_column_expr(args[1])
    return args[0].or_(args[1])

def _get_dax_abs_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for ABS(number)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).abs()

def _get_dax_acos_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for ACOS(number)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).arccos()

def _get_dax_acosh_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for ACOSH(number)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).arccosh()

def _get_dax_acot_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for ACOT(number)')
    expr = _convert_dax_arg_to_numeric_or_column_expr(args[0])
    return (polars.lit(1) / expr).arctan()

def _get_dax_acoth_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for ACOTH(number)')
    expr = _convert_dax_arg_to_numeric_or_column_expr(args[0])
    return (polars.lit(1) / expr).arctanh()

def _get_dax_asin_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for ASIN(number)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).arcsin()

def _get_dax_asinh_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for ASINH(number)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).arcsinh()

def _get_dax_atan_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for ATAN(number)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).arctan()

def _get_dax_atanh_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for ATANH(number)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).arctanh()

def _get_dax_cos_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for COS(number)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).cos()

def _get_dax_cosh_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for COSH(number)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).cosh()

def _get_dax_cot_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for COT(number)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).cot()

def _get_dax_degrees_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for DEGREES(angle)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).degrees()

def _get_dax_divide_expression(args: List) -> polars.Expr:
    if len(args) < 2:
        raise Exception('Invalid argument count for DIVIDE(numerator, denominator, [alternateresult])')
    args[0] = _convert_dax_arg_to_numeric_or_column_expr(args[0])
    args[1] = _convert_dax_arg_to_numeric_or_column_expr(args[1])
    alt_result = None
    if len(args) > 2:
        alt_result = _convert_dax_arg_to_numeric_or_column_expr(args[2])
    return args[0].truediv(args[1]).fill_nan(alt_result)

def _get_dax_even_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for EVEN(number)')
    def positive(e: polars.Expr) -> polars.Expr:
        rounded = e.ceil()
        return polars.when(rounded % 2 != 0).then(rounded + 1).otherwise(rounded)
    def negative(e: polars.Expr) -> polars.Expr:
        rounded = e.floor()
        return polars.when(rounded % 2 != 0).then(rounded - 1).otherwise(rounded)
    expr = _convert_dax_arg_to_numeric_or_column_expr(args[0])
    expr = polars.when(expr >= 0).then(positive(expr)).otherwise(negative(expr))
    return expr.cast(polars.Int64)

def _get_dax_odd_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for ODD(number)')
    def positive(e: polars.Expr) -> polars.Expr:
        rounded = e.ceil()
        return polars.when(rounded % 2 == 0).then(rounded + 1).otherwise(rounded)
    def negative(e: polars.Expr) -> polars.Expr:
        rounded = e.floor()
        return polars.when(rounded % 2 == 0).then(rounded - 1).otherwise(rounded)
    expr = _convert_dax_arg_to_numeric_or_column_expr(args[0])
    expr = polars.when(expr >= 0).then(positive(expr)).otherwise(negative(expr))
    return expr.cast(polars.Int64)

def _get_dax_exp_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for EXP(number)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).exp()

def _get_dax_ln_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for LN(number)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).log()

def _get_dax_log_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for LOG(number, [base])')
    base = math.e
    if len(args) > 1:
        base = float(args[1])
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).log(base)

def _get_dax_log_10_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for LOG10(number)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).log(10)

def _get_dax_power_expression(args: List) -> polars.Expr:
    if len(args) < 2:
        raise Exception('Invalid argument count for POWER(number, power)')
    args[0] = _convert_dax_arg_to_numeric_or_column_expr(args[0])
    args[1] = _convert_dax_arg_to_numeric_or_column_expr(args[1])
    return args[0].pow(args[1])

def _get_dax_radians_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for RADIANS(angle)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).radians()

def _get_dax_sign_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for SIGN(number)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).sign()

def _get_dax_sin_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for SIN(number)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).sin()

def _get_dax_sinh_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for SINH(number)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).sinh()

def _get_dax_sqrt_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for SQRT(number)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).sqrt()

def _get_dax_sqrt_pi_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for SQRTPI(number)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).mul(math.pi).sqrt()

def _get_dax_tan_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for TAN(number)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).tan()

def _get_dax_tanh_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for TANH(number)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).tanh()

def _get_dax_len_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for LEN(text)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).cast(polars.String).str.len_chars()

def _get_dax_lower_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for LOWER(text)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).cast(polars.String).str.to_lowercase()

def _get_dax_upper_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for UPPER(text)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).cast(polars.String).str.to_uppercase()

def _get_dax_value_expression(args: List) -> polars.Expr:
    if len(args) < 1:
        raise Exception('Invalid argument count for VALUE(text)')
    return _convert_dax_arg_to_numeric_or_column_expr(args[0]).cast(polars.Float64)

#
# DAX Expression Helpers
#

def _convert_dax_arg_to_literal(arg: Any) -> Any:
    if isinstance(arg, (int, float, str, bool)):
        return arg
    if isinstance(arg, (datetime, date, time)):
        return arg
    if isinstance(arg, polars.Expr):
        if arg.meta.is_column():
            return arg
        if arg.meta.is_literal():
            return polars.select(arg).item()
    return arg

def _convert_dax_arg_to_date_time(arg: Any) -> polars.Expr:
    if isinstance(arg, datetime):
        return polars.lit(arg).cast(polars.Datetime)
    if isinstance(arg, polars.Datetime):
        return arg
    if isinstance(arg, (polars.Date, polars.Time)):
        return arg.cast(polars.Datetime)
    if isinstance(arg, str):
        string_date = arg
    if isinstance(arg, polars.Expr) and arg.meta.is_literal():
        string_date = _convert_dax_arg_to_literal(arg)
    if isinstance(string_date, datetime):
        return polars.lit(string_date).cast(polars.Datetime)
    if dformat := utils.get_date_format_string(string_date):
        expr = polars.lit(string_date).cast(polars.String)
        return expr.str.strptime(polars.Datetime, dformat)
    return polars.lit(string_date)

def _convert_dax_arg_to_date_time_or_column_expr(arg: Any) -> polars.Expr:
    if isinstance(arg, datetime):
        return polars.lit(arg).cast(polars.Datetime)
    if isinstance(arg, polars.Datetime):
        return arg
    if isinstance(arg, (polars.Date, polars.Time)):
        return arg.cast(polars.Datetime)
    if isinstance(arg, polars.Expr):
        if arg.meta.is_column():
            return arg
        if not arg.meta.is_literal():
            return arg
        string_date = _convert_dax_arg_to_literal(arg)
    if isinstance(arg, str):
        string_date = arg
    if isinstance(string_date, datetime):
        return polars.lit(string_date).cast(polars.Datetime)
    if dformat := utils.get_date_format_string(string_date):
        expr = polars.lit(string_date).cast(polars.String)
        return expr.str.strptime(polars.Datetime, dformat)
    return polars.lit(string_date)

def _convert_dax_arg_to_time_or_column_expr(arg: Any) -> polars.Expr:
    if isinstance(arg, time):
        return polars.lit(arg).cast(polars.Time)
    if isinstance(arg, polars.Time):
        return arg
    if isinstance(arg, (polars.Datetime, polars.Date)):
        return arg.cast(polars.Time)
    if isinstance(arg, polars.Expr):
        if arg.meta.is_column():
            return arg
        if not arg.meta.is_literal():
            return arg
        string_date = _convert_dax_arg_to_literal(arg)
    if isinstance(arg, str):
        string_date = arg
    if isinstance(string_date, time):
        return polars.lit(string_date).cast(polars.Time)
    if dformat := utils.get_time_format_string(string_date):
        expr = polars.lit(string_date).cast(polars.String)
        return expr.str.strptime(polars.Time, dformat)
    return polars.lit(string_date)

def _convert_dax_arg_to_column_expr(arg: Any) -> polars.Expr:
    if isinstance(arg, str):
        return polars.col(arg)
    if isinstance(arg, polars.Expr):
        return arg
    return polars.col(str(arg))

def _convert_dax_arg_to_non_numeric_column_expr(arg: Any, autofill: bool = True) -> polars.Expr:
    col_expr = _convert_dax_arg_to_column_expr(arg).cast(polars.String)
    nom_expr = col_expr.str.strip_chars().str.to_lowercase().eq('true')
    expr = polars.when(nom_expr).then(1).otherwise(col_expr)
    expr = expr.cast(polars.Float64, strict=False, wrap_numerical=True)
    if autofill:
        return expr.fill_null(0)
    return expr

def _convert_dax_arg_to_numeric_or_boolean_or_column_expr(arg: Any) -> Any:
    if isinstance(arg, (int, float, bool)):
        return polars.lit(arg)
    if isinstance(arg, polars.Expr):
        if arg.meta.is_column():
            return arg
        if not arg.meta.is_literal():
            return arg
        arg = polars.select(arg).item()
        if isinstance(arg, str):
            return _convert_dax_arg_to_column_expr(arg)
    return polars.lit(arg)

def _convert_dax_arg_to_numeric_or_column_expr(arg: Any) -> polars.Expr:
    if isinstance(arg, (int, float)):
        return polars.lit(arg)
    if isinstance(arg, polars.Expr):
        if arg.meta.is_column():
            return arg
        if not arg.meta.is_literal():
            return arg
        arg = polars.select(arg).item()
        if isinstance(arg, str):
            return _convert_dax_arg_to_column_expr(arg)
    return polars.lit(arg)

#
# DAX Parse Functions
#

def _split_top_level_arguments(arguments_string: str) -> List[str]:
    """
    Splits a string of function arguments by top-level commas.

    This function correctly handles nested parentheses, ensuring that commas
    inside nested function calls or expressions are not treated as separators.
    """
    arguments = []
    arg_separator = utils.get_list_separator()
    bracket_balance = 0
    square_balance = 0
    in_single_quote = False
    in_double_quote = False
    start = 0

    for i, char in enumerate(arguments_string):
        if char == "'":
            in_single_quote = not in_single_quote
        elif char == '"':
            in_double_quote = not in_double_quote

        if not in_single_quote and not in_double_quote:
            if char == '(':
                bracket_balance += 1
            elif char == ')':
                bracket_balance -= 1
            elif char == '[':
                square_balance += 1
            elif char == ']':
                square_balance -= 1
            elif char == arg_separator and bracket_balance == 0 and square_balance == 0:
                arguments.append(arguments_string[start:i].strip())
                start = i + 1
    arguments.append(arguments_string[start:].strip())
    return arguments

def _parse_term(arg_string: str) -> Dict[str, Any]:
    """
    Parses a single argument string and returns a structured object.

    This helper function handles different types of terms like columns,
    table/column references, cell references, strings, numbers, and nested
    function calls. If it's not one of these, it returns an error.
    """
    # Check for a literal string "text" or 'text'
    if match := re.match(r'^"([^"]*)"$', arg_string):
        return {
            'type': 'string',
            'value': match.group(1)
        }
    if match := re.match(r"^'(.*)'$", arg_string):
        return {
            'type': 'string',
            'value': match.group(1)
        }

    # Check for a number
    if match := re.match(r'^-?\d+(\.\d+)?$', arg_string):
        try:
            # Try to parse as an integer first
            value = int(match.group(0))
        except:
            # If that fails, parse as a float
            value = float(match.group(0))
        return {
            'type': 'number',
            'value': value
        }

    # Check for a nested function call
    if match := re.match(r'^([a-zA-Z_0-9]+)\s*\((.*)\)\s*$', arg_string):
        nested_function_name = match.group(1)
        nested_args_content = match.group(2)

        parsed_arguments = _split_top_level_arguments(nested_args_content)

        # Handle the special case where a function has no arguments
        if parsed_arguments == ['']:
            return {
                'type': 'function',
                'name': nested_function_name,
                'arguments': []
            }

        parsed_nested_args = []

        for arg in parsed_arguments:
            parsed_arg = _parse_xand_expression(arg)
            if 'error' in parsed_arg:
                return parsed_arg
            parsed_nested_args.append(parsed_arg)

        return {
            'type': 'function',
            'name': nested_function_name,
            'arguments': parsed_nested_args
        }

    # Check for a constant from the predefined list
    if arg_string.upper() in FUNCTION_CONSTANTS:
        return {
            'type': 'constant',
            'value': arg_string.upper()
        }

    # Check for a standalone table name
    if match := re.match(r'^([a-zA-Z0-9_]+)$', arg_string):
        return {
            'type': 'table',
            'name': match.group(1)
        }

    # Check for an unquoted table and column reference Table[Column]
    if match := re.match(r"^([a-zA-Z0-9_]+)\[(.*)\]$", arg_string):
        table_name = match.group(1)
        column_name = match.group(2)
        return {
            'type': 'table_column',
            'table': table_name,
            'column': column_name
        }

    # Check for a quoted table and column reference 'Table'[Column]
    if match := re.match(r"^'([^']*)'\[(.*)\]$", arg_string):
        table_name = match.group(1)
        column_name = match.group(2)
        return {
            'type': 'table_column',
            'table': table_name,
            'column': column_name
        }

    # Check for a column reference [Column]
    if match := re.match(r'^\[(.*)\]$', arg_string):
        return {
            'type': 'column',
            'name': match.group(1)
        }

    # Check for a cell range, e.g. A1:B2
    if re.match(r'^[A-Z]+\d+:[A-Z]+\d+$', arg_string, re.IGNORECASE):
        return {
            'type': 'cell_range',
            'value': arg_string
        }

    # Check for a single cell reference, e.g. A1
    if re.match(r'^[A-Z]+\d+$', arg_string, re.IGNORECASE):
        return {
            'type': 'cell_reference',
            'value': arg_string
        }

    # If no specific type is matched, it's an unrecognized term.
    return {'error': f'Unrecognized term or invalid expression: {arg_string}'}

def _find_top_level_operator(formula_string: str, operators: List[Union[str, List[str]]]) -> tuple[int, str]:
    """
    Finds the rightmost top-level operator in a string, respecting quotes, parentheses,
    and square brackets. Returns (index, operator_string) or (-1, '').
    """
    bracket_balance = 0
    square_balance = 0
    in_single_quote = False
    in_double_quote = False

    # Define operators that should be treated as whole words
    WORD_OPERATORS = {'AND', 'OR', 'XOR', 'NOT', 'XAND', 'XNOR'}

    # Sort operators by length descending to prioritize multi-character operators (e.g., '//' before '/')
    sort_key = lambda x: len(x) if isinstance(x, str) else len(x[0])
    sorted_operators = sorted(operators, key=sort_key, reverse=True)

    for i in range(len(formula_string) - 1, -1, -1):
        char = formula_string[i]

        if char == "'":
            in_single_quote = not in_single_quote
        elif char == '"':
            in_double_quote = not in_double_quote

        if not in_single_quote and not in_double_quote:
            if char == '(':
                bracket_balance -= 1
            elif char == ')':
                bracket_balance += 1
            elif char == '[':
                square_balance -= 1
            elif char == ']':
                square_balance += 1

            if bracket_balance == 0 and square_balance == 0:
                for op in sorted_operators:
                    op_str = op[0] if isinstance(op, list) else op
                    op_len = len(op_str)

                    # Check for match
                    if i - op_len + 1 >= 0 and formula_string[i - op_len + 1 : i + 1].upper() == op_str.upper():
                        # This ensures the `**` operator is handled by its dedicated parser function.
                        if op_str == '*' and ((i > 0 and formula_string[i-1] == '*')
                                              or (i < len(formula_string) - 1 and formula_string[i+1] == '*')):
                            continue

                        # If it's a word operator, check for word boundaries
                        if op_str.upper() in WORD_OPERATORS:
                            is_word_boundary_before = (i - op_len < 0) or \
                                                      (not formula_string[i - op_len].isalnum())

                            # A word operator should not be immediately followed by a parenthesis.
                            if i + 1 < len(formula_string) and formula_string[i + 1] == '(':
                                continue

                            is_word_boundary_after = (i + 1 >= len(formula_string)) or \
                                                     (not formula_string[i + 1].isalnum())

                            if is_word_boundary_before and is_word_boundary_after:
                                return i - op_len + 1, op_str

                        # It's a symbol operator, no word boundary check needed
                        else:
                            return i - op_len + 1, op_str
    return -1, ''

def _parse_value(formula_string: str) -> Dict[str, Any]:
    """Parses a simple value, a grouped expression, or a term."""
    trimmed_string = formula_string.strip()

    if trimmed_string.startswith('(') and trimmed_string.endswith(')'):
        inner_content = trimmed_string[1:-1].strip()
        parsed_inner = _parse_xand_expression(inner_content)
        if 'error' in parsed_inner:
            return parsed_inner
        return parsed_inner

    return _parse_term(trimmed_string)

def _parse_unary_minus_expression(formula_string: str) -> Dict[str, Any]:
    """Parses unary minus, with a higher precedence than binary arithmetic operators."""
    trimmed_string = formula_string.strip()

    if trimmed_string.startswith('-'):
        # Check if it's a unary minus, not a negative number literal
        operand_str = trimmed_string[1:].strip()
        operand_parsed = _parse_unary_minus_expression(operand_str)  # Unary minus can be chained
        if 'error' in operand_parsed:
            return operand_parsed
        return {
            'type': 'operation',
            'operator': '-',
            'operand': operand_parsed
        }

    return _parse_value(formula_string)

def _parse_exponentiation(formula_string: str) -> Dict[str, Any]:
    """Parses exponentiation, which has the highest precedence among binary ops."""
    op_index, operator = _find_top_level_operator(formula_string, ['**'])

    if op_index != -1:
        left_str = formula_string[:op_index].strip()
        right_str = formula_string[op_index+len(operator):].strip()

        left_parsed = _parse_unary_minus_expression(left_str)
        if 'error' in left_parsed:
            return left_parsed

        right_parsed = _parse_exponentiation(right_str)
        if 'error' in right_parsed:
            return right_parsed

        return {
            'type': 'operation',
            'operator': operator,
            'left': left_parsed,
            'right': right_parsed
        }

    return _parse_unary_minus_expression(formula_string)

def _parse_multiplication_division(formula_string: str) -> Dict[str, Any]:
    """Parses multiplication, division, modulo, and floor division."""
    op_index, operator = _find_top_level_operator(formula_string, ['//', '*', '/', '%'])

    if op_index != -1:
        left_str = formula_string[:op_index].strip()
        right_str = formula_string[op_index+len(operator):].strip()

        # The left side can have lower precedence ops, so we recurse here.
        left_parsed = _parse_multiplication_division(left_str)
        if 'error' in left_parsed:
            return left_parsed

        # The right side must be a higher precedence expression (or a chain of them).
        right_parsed = _parse_exponentiation(right_str)
        if 'error' in right_parsed:
            return right_parsed

        return {
            'type': 'operation',
            'operator': operator,
            'left': left_parsed,
            'right': right_parsed
        }

    return _parse_exponentiation(formula_string)

def _parse_addition_subtraction(formula_string: str) -> Dict[str, Any]:
    """Parses addition and subtraction, which have lower precedence than multiplication/division."""
    op_index, operator = _find_top_level_operator(formula_string, ['+', '-'])

    if op_index != -1:
        left_str = formula_string[:op_index].strip()
        right_str = formula_string[op_index+len(operator):].strip()

        # If the left-hand side is empty, it's a unary operator.
        # We need to treat the entire expression as a value and pass it down.
        if not left_str and operator == '-':
            # Pass the expression down to handle the unary minus correctly.
            return _parse_multiplication_division(formula_string)

        left_parsed = _parse_addition_subtraction(left_str)
        if 'error' in left_parsed:
            return left_parsed

        right_parsed = _parse_multiplication_division(right_str)
        if 'error' in right_parsed:
            return right_parsed

        return {
            'type': 'operation',
            'operator': operator,
            'left': left_parsed,
            'right': right_parsed
        }

    return _parse_multiplication_division(formula_string)

def _parse_bitwise_and_expression(formula_string: str) -> Dict[str, Any]:
    """Parses the bitwise AND operator (&)."""
    op_index, operator = _find_top_level_operator(formula_string, ['&'])

    if op_index != -1:
        left_str = formula_string[:op_index].strip()
        right_str = formula_string[op_index+len(operator):].strip()

        left_parsed = _parse_bitwise_and_expression(left_str)
        if 'error' in left_parsed:
            return left_parsed

        right_parsed = _parse_addition_subtraction(right_str)
        if 'error' in right_parsed:
            return right_parsed

        return {
            'type': 'operation',
            'operator': operator,
            'left': left_parsed,
            'right': right_parsed
        }

    return _parse_addition_subtraction(formula_string)

def _parse_bitwise_xor_expression(formula_string: str) -> Dict[str, Any]:
    """Parses the bitwise XOR operator (^)."""
    op_index, operator = _find_top_level_operator(formula_string, ['^'])

    if op_index != -1:
        left_str = formula_string[:op_index].strip()
        right_str = formula_string[op_index+len(operator):].strip()

        left_parsed = _parse_bitwise_xor_expression(left_str)
        if 'error' in left_parsed:
            return left_parsed

        right_parsed = _parse_bitwise_and_expression(right_str)
        if 'error' in right_parsed:
            return right_parsed

        return {
            'type': 'operation',
            'operator': operator,
            'left': left_parsed,
            'right': right_parsed
        }

    return _parse_bitwise_and_expression(formula_string)

def _parse_bitwise_or_expression(formula_string: str) -> Dict[str, Any]:
    """Parses the bitwise OR operator (|), which has the lowest precedence of the bitwise ops."""
    op_index, operator = _find_top_level_operator(formula_string, ['|'])

    if op_index != -1:
        left_str = formula_string[:op_index].strip()
        right_str = formula_string[op_index+len(operator):].strip()

        left_parsed = _parse_bitwise_or_expression(left_str)
        if 'error' in left_parsed:
            return left_parsed

        right_parsed = _parse_bitwise_xor_expression(right_str)
        if 'error' in right_parsed:
            return right_parsed

        return {
            'type': 'operation',
            'operator': operator,
            'left': left_parsed,
            'right': right_parsed
        }

    return _parse_bitwise_xor_expression(formula_string)

def _parse_comparison_expression(formula_string: str) -> Dict[str, Any]:
    """Parses comparison operators which have lower precedence than arithmetic operators."""
    op_index, operator = _find_top_level_operator(formula_string, [
        '>=', '<=', '==', '=' , '!=', '<>', '>' , '<'
    ])

    if op_index != -1:
        left_str = formula_string[:op_index].strip()
        right_str = formula_string[op_index+len(operator):].strip()

        left_parsed = _parse_bitwise_or_expression(left_str)
        if 'error' in left_parsed:
            return left_parsed

        right_parsed = _parse_bitwise_or_expression(right_str)
        if 'error' in right_parsed:
            return right_parsed

        return {
            'type': 'operation',
            'operator': operator,
            'left': left_parsed,
            'right': right_parsed
        }

    return _parse_bitwise_or_expression(formula_string)

def _parse_not_expression(formula_string: str) -> Dict[str, Any]:
    """Parses the NOT operator."""
    trimmed_string = formula_string.strip()

    op_index, operator = _find_top_level_operator(trimmed_string, ['NOT'])
    if op_index == 0 and operator == 'NOT': # NOT is a prefix operator
        operand_str = trimmed_string[len(operator):].strip()
        operand_parsed = _parse_not_expression(operand_str) # NOT can be chained
        if 'error' in operand_parsed:
            return operand_parsed
        return {
            'type': 'operation',
            'operator': 'NOT',
            'operand': operand_parsed
        }

    return _parse_comparison_expression(formula_string)

def _parse_and_expression(formula_string: str) -> Dict[str, Any]:
    """Parses the AND operator."""
    op_index, operator = _find_top_level_operator(formula_string, ['AND'])

    if op_index != -1:
        left_str = formula_string[:op_index].strip()
        right_str = formula_string[op_index+len(operator):].strip()

        left_parsed = _parse_and_expression(left_str)
        if 'error' in left_parsed:
            return left_parsed

        right_parsed = _parse_not_expression(right_str)
        if 'error' in right_parsed:
            return right_parsed

        return {
            'type': 'operation',
            'operator': 'AND',
            'left': left_parsed,
            'right': right_parsed
        }

    return _parse_not_expression(formula_string)

def _parse_xor_expression(formula_string: str) -> Dict[str, Any]:
    """Parses the XOR operator."""
    op_index, operator = _find_top_level_operator(formula_string, ['XOR'])

    if op_index != -1:
        left_str = formula_string[:op_index].strip()
        right_str = formula_string[op_index+len(operator):].strip()

        left_parsed = _parse_xor_expression(left_str)
        if 'error' in left_parsed:
            return left_parsed

        right_parsed = _parse_and_expression(right_str)
        if 'error' in right_parsed:
            return right_parsed

        return {
            'type': 'operation',
            'operator': 'XOR',
            'left': left_parsed,
            'right': right_parsed
        }

    return _parse_and_expression(formula_string)

def _parse_or_expression(formula_string: str) -> Dict[str, Any]:
    """Parses the OR operator."""
    op_index, operator = _find_top_level_operator(formula_string, ['OR'])

    if op_index != -1:
        left_str = formula_string[:op_index].strip()
        right_str = formula_string[op_index+len(operator):].strip()

        left_parsed = _parse_or_expression(left_str)
        if 'error' in left_parsed:
            return left_parsed

        right_parsed = _parse_xor_expression(right_str)
        if 'error' in right_parsed:
            return right_parsed

        return {
            'type': 'operation',
            'operator': 'OR',
            'left': left_parsed,
            'right': right_parsed
        }

    return _parse_xor_expression(formula_string)

def _parse_xand_expression(formula_string: str) -> Dict[str, Any]:
    """Parses the XAND operator (lowest logical precedence)."""
    op_index, operator = _find_top_level_operator(formula_string, ['XAND',
                                                                   'XNOR'])

    if op_index != -1:
        left_str = formula_string[:op_index].strip()
        right_str = formula_string[op_index+len(operator):].strip()

        left_parsed = _parse_xand_expression(left_str)
        if 'error' in left_parsed:
            return left_parsed

        right_parsed = _parse_or_expression(right_str)
        if 'error' in right_parsed:
            return right_parsed

        return {
            'type': 'operation',
            'operator': 'XAND',
            'left': left_parsed,
            'right': right_parsed
        }

    return _parse_or_expression(formula_string)

def _build_polars_expr(formula_dict: dict, func_type: str) -> polars.Expr:
    """Transforms a dictionary representation of a formula into a Polars expression."""
    if formula_dict['type'] == 'string':
        return formula_dict['value']

    if formula_dict['type'] == 'number':
        literal = formula_dict['value']
        literal = float(literal)
        if literal.is_integer():
            literal = int(literal)
        return literal

    if formula_dict['type'] == 'constant':
        return formula_dict['value']

    if formula_dict['type'] == 'table':
        raise Exception(f'Table reference is not yet supported')

    if formula_dict['type'] == 'table_column':
        raise Exception(f'Table column reference is not yet supported')

    if formula_dict['type'] == 'column':
        return polars.col(formula_dict['name'])

    if formula_dict['type'] in {'cell_range', 'cell_reference'}:
        raise Exception(f'Cell reference and range are not yet supported')

    if formula_dict['type'] == 'function':
        parsed_arguments = [_build_polars_expr(arg, func_type) for arg in formula_dict['arguments']]

        func_name = formula_dict['name'].upper()

        if func_type == 'formula':
            expression = _get_formula_expression(formula_dict['name'], parsed_arguments)
            if expression is None:
                raise Exception(f'{func_name}() is not found or not yet supported')
            return expression

        if func_type == 'dax':
            expression = _get_dax_expression(formula_dict['name'], parsed_arguments)
            if expression is None:
                raise Exception(f'{func_name}() is not found or not yet supported')
            return expression

    if formula_dict['type'] == 'expression':
        return eval(formula_dict['value'], MATH_EVAL_GLOBALS, {})

    if formula_dict['type'] == 'operation':
        operator = formula_dict['operator'].upper()

        if 'operand' in formula_dict:
            operand = copy.deepcopy(formula_dict['operand'])

            if operator == '-':
                operand['value'] = -operand['value']

            expr = _build_polars_expr(operand, func_type)

            if operator == 'NOT':
                return expr.not_()

            return expr

        left_expr = _build_polars_expr(formula_dict['left'], func_type)
        right_expr = _build_polars_expr(formula_dict['right'], func_type)

        if not isinstance(left_expr, (int, float, polars.Expr)):
            if dformat := utils.get_time_format_string(left_expr):
                left_expr = polars.lit(left_expr).cast(polars.String)
                left_expr = left_expr.str.strptime(polars.Time, dformat)

        if not isinstance(left_expr, (int, float, polars.Expr)):
            if dformat := utils.get_date_format_string(left_expr):
                left_expr = polars.lit(left_expr).cast(polars.String)
                left_expr = left_expr.str.strptime(polars.Datetime, dformat)

        if not isinstance(right_expr, (int, float, polars.Expr)):
            if dformat := utils.get_time_format_string(right_expr):
                right_expr = polars.lit(right_expr).cast(polars.String)
                right_expr = right_expr.str.strptime(polars.Time, dformat)

        if not isinstance(right_expr, (int, float, polars.Expr)):
            if dformat := utils.get_date_format_string(right_expr):
                right_expr = polars.lit(right_expr).cast(polars.String)
                right_expr = right_expr.str.strptime(polars.Datetime, dformat)

        if not isinstance(left_expr, polars.Expr):
            left_expr = polars.lit(left_expr)

        if not isinstance(right_expr, polars.Expr):
            right_expr = polars.lit(right_expr)

        return _get_operation_expression(left_expr, operator, right_expr)

    raise ValueError(f'Unsupported formula type: {formula_dict['type']}')

def parse_dax(expression: str, transform: bool = True) -> Dict[str, Any]:
    """
    Parses a DAX-like expression.

    This function can handle both the `Measure = Function(...)` syntax and
    Excel-like formulas starting with `= Function(...) + ...`.
    """
    expression_to_parse = expression.strip()

    # Case 1: Excel-like "= Formula"
    if expression_to_parse.startswith('='):
        formula_string = expression_to_parse[1:].strip()
        parsed_formula = _parse_xand_expression(formula_string)
        if 'error' in parsed_formula:
            return parsed_formula
        try:
            polars_expr = _build_polars_expr(parsed_formula, 'formula') \
                          if transform else None
        except Exception as e:
            return {'error': str(e)}
        return {
            'formula': parsed_formula,
            'expression': polars_expr
        }

    parts = re.split(r'\s*=\s*', expression_to_parse, maxsplit=1)

    # Case 2: DAX-like "Measure = Formula"
    if len(parts) == 2:
        measure_name = parts[0].strip()
        formula_string = parts[1].strip()
        parsed_formula = _parse_xand_expression(formula_string)
        if 'error' in parsed_formula:
            return parsed_formula
        try:
            polars_expr = _build_polars_expr(parsed_formula, 'dax') \
                          if transform else None
        except Exception as e:
            return {'error': str(e)}
        return {
            'measure': measure_name,
            'formula': parsed_formula,
            'expression': polars_expr
        }

    # Invalid syntax
    return {'error': 'Invalid syntax'}

#
# SQL Function Extensions
#

from duckdb import DuckDBPyConnection
from duckdb.typing import DOUBLE

def _sql_function_acot(x):
    return compute.atan(compute.divide(1, x))

SQL_FUNCTIONS = [
    ('ACOT', _sql_function_acot, [DOUBLE], DOUBLE),
]

def register_sql_functions(connection: DuckDBPyConnection) -> None:
    for name, function, params, rtype in SQL_FUNCTIONS:
        connection.create_function(name, function, params, rtype, type='arrow')