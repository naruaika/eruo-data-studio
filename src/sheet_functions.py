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
import polars
from typing import List, Dict, Union, Any

from .utils import get_list_separator

def get_formula_expression(func_name: str, args: Any) -> polars.Expr:
    func_name = func_name.upper()

    match func_name:
        case 'ABS'                      : return None,
        case 'ACCRINT'                  : return None,
        case 'ACCRINTM'                 : return None,
        case 'ACOS'                     : return None,
        case 'ACOSH'                    : return None,
        case 'ACOT'                     : return None,
        case 'ACOTH'                    : return None,
        case 'AGGREGATE'                : return None,
        case 'ADDRESS'                  : return None,
        case 'AMORDEGRC'                : return None,
        case 'AMORLINC'                 : return None,
        case 'AND'                      : return None,
        case 'ARABIC'                   : return None,
        case 'AREAS'                    : return None,
        case 'ARRAYTOTEXT'              : return None,
        case 'ASC'                      : return None,
        case 'ASIN'                     : return None,
        case 'ASINH'                    : return None,
        case 'ATAN'                     : return None,
        case 'ATAN2'                    : return None,
        case 'ATANH'                    : return None,
        case 'AVEDEV'                   : return None,
        case 'AVERAGE'                  : return None,
        case 'AVERAGEA'                 : return None,
        case 'AVERAGEIF'                : return None,
        case 'AVERAGEIFS'               : return None,
        case 'BAHTTEXT'                 : return None,
        case 'BASE'                     : return None,
        case 'BESSELI'                  : return None,
        case 'BESSELJ'                  : return None,
        case 'BESSELK'                  : return None,
        case 'BESSELY'                  : return None,
        case 'BETADIST'                 : return None,
        case 'BETA.DIST'                : return None,
        case 'BETAINV'                  : return None,
        case 'BETA.INVn'                : return None,
        case 'BIN2DEC'                  : return None,
        case 'BIN2HEX'                  : return None,
        case 'BIN2OCT'                  : return None,
        case 'BINOMDIST'                : return None,
        case 'BINOM.DIST'               : return None,
        case 'BINOM.DIST.RANGE'         : return None,
        case 'BINOM.INV'                : return None,
        case 'BITAND'                   : return None,
        case 'BITLSHIFT'                : return None,
        case 'BITOR'                    : return None,
        case 'BITRSHIFT'                : return None,
        case 'BITXOR'                   : return None,
        case 'BYCOL'                    : return None,
        case 'BYROW'                    : return None,
        case 'CALL'                     : return None,
        case 'CEILING'                  : return None,
        case 'CEILING.MATH'             : return None,
        case 'CEILING.PRECISE'          : return None,
        case 'CELL'                     : return None,
        case 'CHAR'                     : return None,
        case 'CHIDIST'                  : return None,
        case 'CHIINV'                   : return None,
        case 'CHITEST'                  : return None,
        case 'CHISQ.DIST'               : return None,
        case 'CHISQ.DIST.RT'            : return None,
        case 'CHISQ.INV'                : return None,
        case 'CHISQ.INV.RT'             : return None,
        case 'CHISQ.TEST'               : return None,
        case 'CHOOSE'                   : return None,
        case 'CHOOSECOLS'               : return None,
        case 'CHOOSEROWS'               : return None,
        case 'CLEAN'                    : return None,
        case 'CODE'                     : return None,
        case 'COLUMN'                   : return None,
        case 'COLUMNS'                  : return None,
        case 'COMBIN'                   : return None,
        case 'COMBINA'                  : return None,
        case 'COMPLEX'                  : return None,
        case 'CONCAT'                   : return None,
        case 'CONCATENATE'              : return None,
        case 'CONFIDENCE'               : return None,
        case 'CONFIDENCE.NORM'          : return None,
        case 'CONFIDENCE.T'             : return None,
        case 'CONVERT'                  : return None,
        case 'CORREL'                   : return None,
        case 'COS'                      : return None,
        case 'COSH'                     : return None,
        case 'COT'                      : return None,
        case 'COTH'                     : return None,
        case 'COUNT'                    : return None,
        case 'COUNTA'                   : return None,
        case 'COUNTBLANK'               : return None,
        case 'COUNTIF'                  : return None,
        case 'COUNTIFS'                 : return None,
        case 'COUPDAYBS'                : return None,
        case 'COUPDAYS'                 : return None,
        case 'COUPDAYSNC'               : return None,
        case 'COUPNCD'                  : return None,
        case 'COUPNUM'                  : return None,
        case 'COUPPCD'                  : return None,
        case 'COVAR'                    : return None,
        case 'COVARIANCE.P'             : return None,
        case 'COVARIANCE.S'             : return None,
        case 'CRITBINOM'                : return None,
        case 'CSC'                      : return None,
        case 'CSCH'                     : return None,
        case 'CUBEKPIMEMBER'            : return None,
        case 'CUBEMEMBER'               : return None,
        case 'CUBEMEMBERPROPERTY'       : return None,
        case 'CUBERANKEDMEMBER'         : return None,
        case 'CUBESET'                  : return None,
        case 'CUBESETCOUNT'             : return None,
        case 'CUBEVALUE'                : return None,
        case 'CUMIPMT'                  : return None,
        case 'CUMPRINC'                 : return None,
        case 'DATE'                     : return None,
        case 'DATEDIF'                  : return None,
        case 'DATEVALUE'                : return None,
        case 'DAVERAGE'                 : return None,
        case 'DAY'                      : return None,
        case 'DAYS'                     : return None,
        case 'DAYS360'                  : return None,
        case 'DB'                       : return None,
        case 'DBCS'                     : return None,
        case 'DCOUNT'                   : return None,
        case 'DCOUNTA'                  : return None,
        case 'DDB'                      : return None,
        case 'DEC2BIN'                  : return None,
        case 'DEC2HEX'                  : return None,
        case 'DEC2OCT'                  : return None,
        case 'DECIMAL'                  : return None,
        case 'DEGREES'                  : return None,
        case 'DELTA'                    : return None,
        case 'DETECTLANGUAGE'           : return None,
        case 'DEVSQ'                    : return None,
        case 'DGET'                     : return None,
        case 'DISC'                     : return None,
        case 'DMAX'                     : return None,
        case 'DMIN'                     : return None,
        case 'DOLLAR'                   : return None,
        case 'DOLLARDE'                 : return None,
        case 'DOLLARFR'                 : return None,
        case 'DPRODUCT'                 : return None,
        case 'DROP'                     : return None,
        case 'DSTDEV'                   : return None,
        case 'DSTDEVP'                  : return None,
        case 'DSUM'                     : return None,
        case 'DURATION'                 : return None,
        case 'DVAR'                     : return None,
        case 'DVARP'                    : return None,
        case 'EDATE'                    : return None,
        case 'EFFECT'                   : return None,
        case 'ENCODEURL'                : return None,
        case 'EOMONTH'                  : return None,
        case 'ERF'                      : return None,
        case 'ERF.PRECISE'              : return None,
        case 'ERFC'                     : return None,
        case 'ERFC.PRECISE'             : return None,
        case 'ERROR.TYPE'               : return None,
        case 'EUROCONVERT'              : return None,
        case 'EVEN'                     : return None,
        case 'EXACT'                    : return None,
        case 'EXP'                      : return None,
        case 'EXPAND'                   : return None,
        case 'EXPON.DIST'               : return None,
        case 'EXPONDIST'                : return None,
        case 'FACT'                     : return None,
        case 'FACTDOUBLE'               : return None,
        case 'FALSE'                    : return None,
        case 'IST'                      : return None,
        case 'FDIST'                    : return None,
        case 'IST.RT'                   : return None,
        case 'FILTER'                   : return None,
        case 'FILTERXML'                : return None,
        case 'FIND'                     : return None,
        case 'FINDB'                    : return None,
        case 'NV'                       : return None,
        case 'NV.RT'                    : return None,
        case 'FINV'                     : return None,
        case 'FISHER'                   : return None,
        case 'FISHERINV'                : return None,
        case 'FIXED'                    : return None,
        case 'FLOOR'                    : return None,
        case 'FLOOR.MATH'               : return None,
        case 'FLOOR.PRECISE'            : return None,
        case 'FORECAST.LINEAR'          : return None,
        case 'FORECAST.ETS'             : return None,
        case 'FORECAST.ETS.CONFINT'     : return None,
        case 'FORECAST.ETS.SEASONALITY' : return None,
        case 'FORECAST.ETS.STAT'        : return None,
        case 'FORECAST.LINEAR'          : return None,
        case 'FORMULATEXT'              : return None,
        case 'FREQUENCY'                : return None,
        case 'EST'                      : return None,
        case 'FTEST'                    : return None,
        case 'FV'                       : return None,
        case 'FVSCHEDULE'               : return None,
        case 'GAMMA'                    : return None,
        case 'GAMMA.DIST'               : return None,
        case 'GAMMADIST'                : return None,
        case 'GAMMA.INV'                : return None,
        case 'GAMMAINV'                 : return None,
        case 'GAMMALN'                  : return None,
        case 'GAMMALN.PRECISE'          : return None,
        case 'GAUSS'                    : return None,
        case 'GCD'                      : return None,
        case 'GEOMEAN'                  : return None,
        case 'GESTEP'                   : return None,
        case 'GETPIVOTDATA'             : return None,
        case 'GROUPBY'                  : return None,
        case 'GROWTH'                   : return None,
        case 'HARMEAN'                  : return None,
        case 'HEX2BIN'                  : return None,
        case 'HEX2DEC'                  : return None,
        case 'HEX2OCT'                  : return None,
        case 'HLOOKUP'                  : return None,
        case 'HOUR'                     : return None,
        case 'HSTACK'                   : return None,
        case 'HYPERLINK'                : return None,
        case 'HYPGEOM.DIST'             : return None,
        case 'HYPGEOMDIST'              : return None,
        case 'IF'                       : return None,
        case 'IFERROR'                  : return None,
        case 'IFNA'                     : return None,
        case 'IFS'                      : return None,
        case 'IMABS'                    : return None,
        case 'IMAGE'                    : return None,
        case 'IMAGINARY'                : return None,
        case 'IMARGUMENT'               : return None,
        case 'IMCONJUGATE'              : return None,
        case 'IMCOS'                    : return None,
        case 'IMCOSH'                   : return None,
        case 'IMCOT'                    : return None,
        case 'IMCSC'                    : return None,
        case 'IMCSCH'                   : return None,
        case 'IMDIV'                    : return None,
        case 'IMEXP'                    : return None,
        case 'IMLN'                     : return None,
        case 'IMLOG10'                  : return None,
        case 'IMLOG2'                   : return None,
        case 'IMPOWER'                  : return None,
        case 'IMPRODUCT'                : return None,
        case 'IMREAL'                   : return None,
        case 'IMSEC'                    : return None,
        case 'IMSECH'                   : return None,
        case 'IMSIN'                    : return None,
        case 'IMSINH'                   : return None,
        case 'IMSQRT'                   : return None,
        case 'IMSUB'                    : return None,
        case 'IMSUM'                    : return None,
        case 'IMTAN'                    : return None,
        case 'INDEX'                    : return None,
        case 'INDIRECT'                 : return None,
        case 'INFO'                     : return None,
        case 'INT'                      : return None,
        case 'INTERCEPT'                : return None,
        case 'INTRATE'                  : return None,
        case 'IPMT'                     : return None,
        case 'IRR'                      : return None,
        case 'ISBLANK'                  : return None,
        case 'ISERR'                    : return None,
        case 'ISERROR'                  : return None,
        case 'ISEVEN'                   : return None,
        case 'ISFORMULA'                : return None,
        case 'ISLOGICAL'                : return None,
        case 'ISNA'                     : return None,
        case 'ISNONTEXT'                : return None,
        case 'ISNUMBER'                 : return None,
        case 'ISODD'                    : return None,
        case 'ISOMITTED'                : return None,
        case 'ISREF'                    : return None,
        case 'ISTEXT'                   : return None,
        case 'ISO.CEILING'              : return None,
        case 'ISOWEEKNUM'               : return None,
        case 'ISPMT'                    : return None,
        case 'JIS'                      : return None,
        case 'KURT'                     : return None,
        case 'LAMBDA'                   : return None,
        case 'LARGE'                    : return None,
        case 'LCM'                      : return None,
        case 'LEFT'                     : return None,
        case 'LEFTB'                    : return None,
        case 'LEN'                      : return None,
        case 'LENB'                     : return None,
        case 'LET'                      : return None,
        case 'LINEST'                   : return None,
        case 'LN'                       : return None,
        case 'LOG'                      : return None,
        case 'LOG10'                    : return None,
        case 'LOGEST'                   : return None,
        case 'LOGINV'                   : return None,
        case 'LOGNORM.DIST'             : return None,
        case 'LOGNORMDIST'              : return None,
        case 'LOGNORM.INV'              : return None,
        case 'LOOKUP'                   : return None,
        case 'LOWER'                    : return None,
        case 'MAKEARRAY'                : return None,
        case 'MAP'                      : return None,
        case 'MATCH'                    : return None,
        case 'MAX'                      : return None,
        case 'MAXA'                     : return None,
        case 'MAXIFS'                   : return None,
        case 'MDETERM'                  : return None,
        case 'MDURATION'                : return None,
        case 'MEDIAN'                   : return None,
        case 'MID, MIDB'                : return None,
        case 'MIN'                      : return None,
        case 'MINIFS'                   : return None,
        case 'MINA'                     : return None,
        case 'MINUTE'                   : return None,
        case 'MINVERSE'                 : return None,
        case 'MIRR'                     : return None,
        case 'MMULT'                    : return None,
        case 'MOD'                      : return None,
        case 'MODE'                     : return None,
        case 'MODE.MULT'                : return None,
        case 'MODE.SNGL'                : return None,
        case 'MONTH'                    : return None,
        case 'MROUND'                   : return None,
        case 'MULTINOMIAL'              : return None,
        case 'MUNIT'                    : return None,
        case 'NA'                       : return None,
        case 'NEGBINOM.DIST'            : return None,
        case 'NEGBINOMDIST'             : return None,
        case 'NETWORKDAYS'              : return None,
        case 'NETWORKDAYS.INTL'         : return None,
        case 'NOMINAL'                  : return None,
        case 'NORM.DIST'                : return None,
        case 'NORMDIST'                 : return None,
        case 'NORMINV'                  : return None,
        case 'NORM.INV'                 : return None,
        case 'NORM.S.DIST'              : return None,
        case 'NORMSDIST'                : return None,
        case 'NORM.S.INV'               : return None,
        case 'NORMSINV'                 : return None,
        case 'NOT'                      : return None,
        case 'NOW'                      : return None,
        case 'NPER'                     : return None,
        case 'NPV'                      : return None,
        case 'NUMBERVALUE'              : return None,
        case 'OCT2BIN'                  : return None,
        case 'OCT2DEC'                  : return None,
        case 'OCT2HEX'                  : return None,
        case 'ODD'                      : return None,
        case 'ODDFPRICE'                : return None,
        case 'ODDFYIELD'                : return None,
        case 'ODDLPRICE'                : return None,
        case 'ODDLYIELD'                : return None,
        case 'OFFSET'                   : return None,
        case 'OR'                       : return None,
        case 'PDURATION'                : return None,
        case 'PEARSON'                  : return None,
        case 'PERCENTILE.EXC'           : return None,
        case 'PERCENTILE.INC'           : return None,
        case 'PERCENTILE'               : return None,
        case 'PERCENTOF'                : return None,
        case 'PERCENTRANK.EXC'          : return None,
        case 'PERCENTRANK.INC'          : return None,
        case 'PERCENTRANK'              : return None,
        case 'PERMUT'                   : return None,
        case 'PERMUTATIONA'             : return None,
        case 'PHI'                      : return None,
        case 'PHONETIC'                 : return None,
        case 'PI'                       : return None,
        case 'PIVOTBY'                  : return None,
        case 'PMT'                      : return None,
        case 'POISSON.DIST'             : return None,
        case 'POISSON'                  : return None,
        case 'POWER'                    : return None,
        case 'PPMT'                     : return None,
        case 'PRICE'                    : return None,
        case 'PRICEDISC'                : return None,
        case 'PRICEMAT'                 : return None,
        case 'PROB'                     : return None,
        case 'PRODUCT'                  : return None,
        case 'PROPER'                   : return None,
        case 'PV'                       : return None,
        case 'QUARTILE'                 : return None,
        case 'QUARTILE.EXC'             : return None,
        case 'QUARTILE.INC'             : return None,
        case 'QUOTIENT'                 : return None,
        case 'RADIANS'                  : return None,
        case 'RAND'                     : return None,
        case 'RANDARRAY'                : return None,
        case 'RANDBETWEEN'              : return None,
        case 'RANK.AVG'                 : return None,
        case 'RANK.EQ'                  : return None,
        case 'RANK'                     : return None,
        case 'RATE'                     : return None,
        case 'RECEIVED'                 : return None,
        case 'REDUCE'                   : return None,
        case 'REGEXEXTRACT'             : return None,
        case 'REGEXREPLACE'             : return None,
        case 'REGEXTEST'                : return None,
        case 'REGISTER.ID'              : return None,
        case 'REPLACE'                  : return None,
        case 'REPLACEB'                 : return None,
        case 'REPT'                     : return None,
        case 'RIGHT'                    : return None,
        case 'RIGHTB'                   : return None,
        case 'ROMAN'                    : return None,
        case 'ROUND'                    : return None,
        case 'ROUNDDOWN'                : return None,
        case 'ROUNDUP'                  : return None,
        case 'ROW'                      : return None,
        case 'ROWS'                     : return None,
        case 'RRI'                      : return None,
        case 'RSQ'                      : return None,
        case 'RTD'                      : return None,
        case 'SCAN'                     : return None,
        case 'SEARCH'                   : return None,
        case 'SEARCHB'                  : return None,
        case 'SEC'                      : return None,
        case 'SECH'                     : return None,
        case 'SECOND'                   : return None,
        case 'SEQUENCE'                 : return None,
        case 'SERIESSUM'                : return None,
        case 'SHEET'                    : return None,
        case 'SHEETS'                   : return None,
        case 'SIGN'                     : return None,
        case 'SIN'                      : return None,
        case 'SINH'                     : return None,
        case 'SKEW'                     : return None,
        case 'SKEW.P'                   : return None,
        case 'SLN'                      : return None,
        case 'SLOPE'                    : return None,
        case 'SMALL'                    : return None,
        case 'SORT'                     : return None,
        case 'SORTBY'                   : return None,
        case 'SQRT'                     : return None,
        case 'SQRTPI'                   : return None,
        case 'STANDARDIZE'              : return None,
        case 'STOCKHISTORY'             : return None,
        case 'STDEV'                    : return None,
        case 'STDEV.P'                  : return None,
        case 'STDEV.S'                  : return None,
        case 'STDEVA'                   : return None,
        case 'STDEVP'                   : return None,
        case 'STDEVPA'                  : return None,
        case 'STEYX'                    : return None,
        case 'STOCKHISTORY'             : return None,
        case 'SUBSTITUTE'               : return None,
        case 'SUBTOTAL'                 : return None,
        case 'SUM'                      : return None,
        case 'SUMIF'                    : return None,
        case 'SUMIFS'                   : return None,
        case 'SUMPRODUCT'               : return None,
        case 'SUMSQ'                    : return None,
        case 'SUMX2MY2'                 : return None,
        case 'SUMX2PY2'                 : return None,
        case 'SUMXMY2'                  : return None,
        case 'SWITCH'                   : return None,
        case 'SYD'                      : return None,
        case 'TAN'                      : return None,
        case 'TANH'                     : return None,
        case 'TAKE'                     : return None,
        case 'TBILLEQ'                  : return None,
        case 'TBILLPRICE'               : return None,
        case 'TBILLYIELD'               : return None,
        case 'IST'                      : return None,
        case 'IST.2T'                   : return None,
        case 'IST.RT'                   : return None,
        case 'TDIST'                    : return None,
        case 'TEXT'                     : return None,
        case 'TEXTAFTER'                : return None,
        case 'TEXTBEFORE'               : return None,
        case 'TEXTJOIN'                 : return None,
        case 'TEXTSPLIT'                : return None,
        case 'TIME'                     : return None,
        case 'TIMEVALUE'                : return None,
        case 'NV'                       : return None,
        case 'NV.2T'                    : return None,
        case 'TINV'                     : return None,
        case 'TOCOL'                    : return None,
        case 'TOROW'                    : return None,
        case 'TODAY'                    : return None,
        case 'TRANSLATE'                : return None,
        case 'TRANSPOSE'                : return None,
        case 'TREND'                    : return None,
        case 'TRIM'                     : return None,
        case 'TRIMMEAN'                 : return None,
        case 'TRIMRANGE'                : return None,
        case 'TRUE'                     : return None,
        case 'TRUNC'                    : return None,
        case 'EST'                      : return None,
        case 'TTEST'                    : return None,
        case 'TYPE'                     : return None,
        case 'UNICHAR'                  : return None,
        case 'UNICODE'                  : return None,
        case 'UNIQUE'                   : return None,
        case 'UPPER'                    : return None,
        case 'VALUE'                    : return None,
        case 'VALUETOTEXT'              : return None,
        case 'VAR'                      : return None,
        case 'VAR.P'                    : return None,
        case 'VAR.S'                    : return None,
        case 'VARA'                     : return None,
        case 'VARP'                     : return None,
        case 'VARPA'                    : return None,
        case 'VDB'                      : return None,
        case 'VLOOKUP'                  : return None,
        case 'VSTACK'                   : return None,
        case 'WEBSERVICE'               : return None,
        case 'WEEKDAY'                  : return None,
        case 'WEEKNUM'                  : return None,
        case 'WEIBULL'                  : return None,
        case 'WEIBULL.DIST'             : return None,
        case 'WORKDAY'                  : return None,
        case 'WORKDAY.INTL'             : return None,
        case 'WRAPCOLS'                 : return None,
        case 'WRAPROWS'                 : return None,
        case 'XIRR'                     : return None,
        case 'XLOOKUP'                  : return None,
        case 'XMATCH'                   : return None,
        case 'XNPV'                     : return None,
        case 'XOR'                      : return None,
        case 'YEAR'                     : return None,
        case 'YEARFRAC'                 : return None,
        case 'YIELD'                    : return None,
        case 'YIELDDISC'                : return None,
        case 'YIELDMAT'                 : return None,
        case 'EST'                      : return None,
        case 'ZTEST'                    : return None,

    return polars.lit(False)


def get_dax_expression(func_name: str, args: Any) -> polars.Expr:
    func_name = func_name.upper()

    match func_name:
        # Aggregation
        case 'APPROXIMATEDISTINCTCOUNT'    : return None
        case 'AVERAGE'                     : return None
        case 'AVERAGEA'                    : return None
        case 'AVERAGEX'                    : return None
        case 'COUNT'                       : return None
        case 'COUNTA'                      : return None
        case 'COUNTAX'                     : return None
        case 'COUNTBLANK'                  : return None
        case 'COUNTROWS'                   : return None
        case 'COUNTX'                      : return None
        case 'DISTINCTCOUNT'               : return None
        case 'DISTINCTCOUNTNOBLANK'        : return None
        case 'MAX'                         : return None
        case 'MAXA'                        : return None
        case 'MAXX'                        : return None
        case 'MIN'                         : return None
        case 'MINA'                        : return None
        case 'MINX'                        : return None
        case 'PRODUCT'                     : return None
        case 'PRODUCTX'                    : return None
        case 'SUM'                         : return None
        case 'SUMX'                        : return None

        # Date and time
        case 'CALENDAR'                    : return None
        case 'CALENDARAUTO'                : return None
        case 'DATE'                        : return None
        case 'DATEDIFF'                    : return None
        case 'DATEVALUE'                   : return None
        case 'DAY'                         : return None
        case 'EDATE'                       : return None
        case 'EOMONTH'                     : return None
        case 'HOUR'                        : return None
        case 'MINUTE'                      : return None
        case 'MONTH'                       : return None
        case 'NETWORKDAYS'                 : return None
        case 'NOW'                         : return None
        case 'QUARTER'                     : return None
        case 'SECOND'                      : return None
        case 'TIME'                        : return None
        case 'TIMEVALUE'                   : return None
        case 'TODAY'                       : return None
        case 'UTCNOW'                      : return None
        case 'UTCTODAY'                    : return None
        case 'WEEKDAY'                     : return None
        case 'WEEKNUM'                     : return None
        case 'YEAR'                        : return None
        case 'YEARFRAC'                    : return None

        case 'CLOSINGBALANCEMONTH'         : return None
        case 'CLOSINGBALANCEQUARTER'       : return None
        case 'CLOSINGBALANCEYEAR'          : return None
        case 'DATEADD'                     : return None
        case 'DATESBETWEEN'                : return None
        case 'DATESINPERIOD'               : return None
        case 'DATESMTD'                    : return None
        case 'DATESQTD'                    : return None
        case 'DATESYTD'                    : return None
        case 'ENDOFMONTH'                  : return None
        case 'ENDOFQUARTER'                : return None
        case 'ENDOFYEAR'                   : return None
        case 'FIRSTDATE'                   : return None
        case 'LASTDATE'                    : return None
        case 'NEXTDAY'                     : return None
        case 'NEXTMONTH'                   : return None
        case 'NEXTQUARTER'                 : return None
        case 'NEXTYEAR'                    : return None
        case 'OPENINGBALANCEMONTH'         : return None
        case 'OPENINGBALANCEQUARTER'       : return None
        case 'OPENINGBALANCEYEAR'          : return None
        case 'PARALLELPERIOD'              : return None
        case 'PREVIOUSDAY'                 : return None
        case 'PREVIOUSMONTH'               : return None
        case 'PREVIOUSQUARTER'             : return None
        case 'PREVIOUSYEAR'                : return None
        case 'SAMEPERIODLASTYEAR'          : return None
        case 'STARTOFMONTH'                : return None
        case 'STARTOFQUARTER'              : return None
        case 'STARTOFYEAR'                 : return None
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
        case 'ACCRINT'                     : return None,
        case 'ACCRINTM'                    : return None,
        case 'AMORDEGRC'                   : return None,
        case 'AMORLINC'                    : return None,
        case 'COUPDAYBS'                   : return None,
        case 'COUPDAYS'                    : return None,
        case 'COUPDAYSNC'                  : return None,
        case 'COUPNCD'                     : return None,
        case 'COUPNUM'                     : return None,
        case 'COUPPCD'                     : return None,
        case 'CUMIPMT'                     : return None,
        case 'CUMPRINC'                    : return None,
        case 'DB'                          : return None,
        case 'DDB'                         : return None,
        case 'DISC'                        : return None,
        case 'DOLLARDE'                    : return None,
        case 'DOLLARFR'                    : return None,
        case 'DURATION'                    : return None,
        case 'EFFECT'                      : return None,
        case 'FV'                          : return None,
        case 'INTRATE'                     : return None,
        case 'IPMT'                        : return None,
        case 'ISPMT'                       : return None,
        case 'MDURATION'                   : return None,
        case 'NOMINAL'                     : return None,
        case 'NPER'                        : return None,
        case 'ODDFPRICE'                   : return None,
        case 'ODDFYIELD'                   : return None,
        case 'ODDLPRICE'                   : return None,
        case 'ODDLYIELD'                   : return None,
        case 'PDURATION'                   : return None,
        case 'PMT'                         : return None,
        case 'PPMT'                        : return None,
        case 'PRICE'                       : return None,
        case 'PRICEDISC'                   : return None,
        case 'PRICEMAT'                    : return None,
        case 'PV'                          : return None,
        case 'RATE'                        : return None,
        case 'RECEIVED'                    : return None,
        case 'RRI'                         : return None,
        case 'SLN'                         : return None,
        case 'SYD'                         : return None,
        case 'TBILLEQ'                     : return None,
        case 'TBILLPRICE'                  : return None,
        case 'TBILLYIELD'                  : return None,
        case 'VDB'                         : return None,
        case 'XIRR'                        : return None,
        case 'XNPV'                        : return None,
        case 'YIELD'                       : return None,
        case 'YIELDDISC'                   : return None,
        case 'YIELDMAT'                    : return None,

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
        case 'AND'                         : return None
        case 'BITAND'                      : return None
        case 'BITLSHIFT'                   : return None
        case 'BITOR'                       : return None
        case 'BITRSHIFT'                   : return None
        case 'BITXOR'                      : return None
        case 'COALESCE'                    : return None
        case 'FALSE'                       : return None
        case 'IF'                          : return None
        case 'IF.EAGER'                    : return None
        case 'IFERROR'                     : return None
        case 'NOT'                         : return None
        case 'OR'                          : return None
        case 'SWITCH'                      : return None
        case 'TRUE'                        : return None

        # Math and trigonometry
        case 'ABS'                         : return None
        case 'ACOS'                        : return None
        case 'ACOSH'                       : return None
        case 'ACOT'                        : return None
        case 'ACOTH'                       : return None
        case 'ASIN'                        : return None
        case 'ASINH'                       : return None
        case 'ATAN'                        : return None
        case 'ATANH'                       : return None
        case 'CEILING'                     : return None
        case 'CONVERT'                     : return None
        case 'COS'                         : return None
        case 'COSH'                        : return None
        case 'COT'                         : return None
        case 'COTH'                        : return None
        case 'CURRENCY'                    : return None
        case 'DEGREES'                     : return None
        case 'DIVIDE'                      : return None
        case 'EVEN'                        : return None
        case 'EXP'                         : return None
        case 'FACT'                        : return None
        case 'FLOOR'                       : return None
        case 'GCD'                         : return None
        case 'INT'                         : return None
        case 'ISO.CEILING'                 : return None
        case 'LCM'                         : return None
        case 'LN'                          : return None
        case 'LOG'                         : return None
        case 'LOG10'                       : return None
        case 'MOD'                         : return None
        case 'MROUND'                      : return None
        case 'ODD'                         : return None
        case 'PI'                          : return None
        case 'POWER'                       : return None
        case 'QUOTIENT'                    : return None
        case 'RADIANS'                     : return None
        case 'RAND'                        : return None
        case 'RANDBETWEEN'                 : return None
        case 'ROUND'                       : return None
        case 'ROUNDDOWN'                   : return None
        case 'ROUNDUP'                     : return None
        case 'SIGN'                        : return None
        case 'SIN'                         : return None
        case 'SINH'                        : return None
        case 'SQRT'                        : return None
        case 'SQRTPI'                      : return None
        case 'TAN'                         : return None
        case 'TANH'                        : return None
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
        case 'LEN'                         : return None
        case 'LOWER'                       : return None
        case 'MID'                         : return None
        case 'REPLACE'                     : return None
        case 'REPT'                        : return None
        case 'RIGHT'                       : return None
        case 'SEARCH'                      : return None
        case 'SUBSTITUTE'                  : return None
        case 'TRIM'                        : return None
        case 'UNICHAR'                     : return None
        case 'UNICODE'                     : return None
        case 'UPPER'                       : return None
        case 'VALUE'                       : return None

        # Other
        case 'BLANK'                       : return None

    return polars.lit(False)


def _split_top_level_arguments(arguments_string: str) -> List[str]:
    """
    Splits a string of function arguments by top-level commas.

    This function correctly handles nested parentheses, ensuring that commas
    inside nested function calls or expressions are not treated as separators.

    Args:
        arguments_string (str): A string containing function arguments.

    Returns:
        List[str]: A list of strings, where each string is a single argument.
    """
    arguments = []
    balance = 0
    square_bracket_balance = 0
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
                balance += 1
            elif char == ')':
                balance -= 1
            elif char == '[':
                square_bracket_balance += 1
            elif char == ']':
                square_bracket_balance -= 1
            elif char == get_list_separator() and balance == 0 and square_bracket_balance == 0:
                arguments.append(arguments_string[start:i].strip())
                start = i + 1
    arguments.append(arguments_string[start:].strip())
    return arguments

def _parse_term(arg_string: str) -> Dict[str, Any]:
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

    # Check for a literal string "text" or 'text'
    string_match_double = re.match(r'^"([^"]*)"$', arg_string)
    string_match_single = re.match(r"^'(.*)'$", arg_string)
    if string_match_double:
        return {'type': 'string', 'value': string_match_double.group(1)}
    if string_match_single:
        return {'type': 'string', 'value': string_match_single.group(1)}

    number_match = re.match(r'^-?\d+(\.\d+)?$', arg_string)
    if number_match:
        return {'type': 'number', 'value': float(number_match.group(0))}

    # Check for a nested function call
    nested_function_match = re.match(r'^([a-zA-Z_]+)\s*\((.*)\)\s*$', arg_string)
    if nested_function_match:
        nested_function_name = nested_function_match.group(1)
        nested_args_content = nested_function_match.group(2)
        parsed_nested_args = [
            # Recursively call _parse_xand_expression to handle operators within arguments
            _parse_xand_expression(arg) for arg in _split_top_level_arguments(nested_args_content)
        ]
        return {
            'type': 'function',
            'name': nested_function_name,
            'arguments': parsed_nested_args
        }

    # If it's a simple expression, store it as-is
    return {'type': 'expression', 'value': arg_string}

def _find_top_level_operator(formula_string: str, operators: List[Union[str, List[str]]]) -> tuple[int, str]:
    """
    Finds the rightmost top-level operator in a string, respecting quotes, parentheses, and square brackets.
    Returns (index, operator_string) or (-1, '').
    """
    balance = 0
    square_bracket_balance = 0
    in_single_quote = False
    in_double_quote = False

    # Define operators that should be treated as whole words
    WORD_OPERATORS = {'AND', 'OR', 'XOR', 'NOT', 'XAND'}

    # Sort operators by length descending to prioritize multi-character operators (e.g., '//' before '/')
    sorted_operators = sorted(operators, key=lambda x: len(x) if isinstance(x, str) else len(x[0]), reverse=True)

    for i in range(len(formula_string) - 1, -1, -1):
        char = formula_string[i]

        if char == "'":
            in_single_quote = not in_single_quote
        elif char == '"':
            in_double_quote = not in_double_quote

        if not in_single_quote and not in_double_quote:
            if char == '(':
                balance += 1
            elif char == ')':
                balance -= 1
            elif char == '[':
                square_bracket_balance += 1
            elif char == ']':
                square_bracket_balance -= 1

            if balance == 0 and square_bracket_balance == 0:
                for op in sorted_operators:
                    op_str = op[0] if isinstance(op, list) else op
                    op_len = len(op_str)

                    # Check for match
                    if i - op_len + 1 >= 0 and formula_string[i - op_len + 1 : i + 1].upper() == op_str.upper():
                        # If it's a word operator, check for word boundaries
                        if op_str.upper() in WORD_OPERATORS:
                            is_word_boundary_before = (i - op_len < 0) or (not formula_string[i - op_len].isalnum())
                            is_word_boundary_after = (i + 1 >= len(formula_string)) or (not formula_string[i + 1].isalnum())

                            if is_word_boundary_before and is_word_boundary_after:
                                return i - op_len + 1, op_str
                        else: # It's a symbol operator, no word boundary check needed
                            return i - op_len + 1, op_str
    return -1, ''

def _parse_value(formula_string: str) -> Dict[str, Any]:
    """Parses a simple value, a grouped expression, or a term."""
    trimmed_string = formula_string.strip()
    if trimmed_string.startswith('(') and trimmed_string.endswith(')'):
        inner_content = trimmed_string[1:-1].strip()
        return _parse_xand_expression(inner_content)

    return _parse_term(trimmed_string)

def _parse_exponentiation(formula_string: str) -> Dict[str, Any]:
    """Parses exponentiation, which has the highest precedence."""
    op_index, operator = _find_top_level_operator(formula_string, ['^'])

    if op_index != -1:
        left_str = formula_string[:op_index].strip()
        right_str = formula_string[op_index+len(operator):].strip()
        return {
            'type': 'operation',
            'operator': operator,
            'left': _parse_exponentiation(left_str),
            'right': _parse_value(right_str)
        }

    return _parse_value(formula_string)

def _parse_multiplication_division(formula_string: str) -> Dict[str, Any]:
    """Parses multiplication, division, modulo, and floor division."""
    op_index, operator = _find_top_level_operator(formula_string, ['//', '*', '/', '%'])

    if op_index != -1:
        left_str = formula_string[:op_index].strip()
        right_str = formula_string[op_index+len(operator):].strip()

        return {
            'type': 'operation',
            'operator': operator,
            'left': _parse_multiplication_division(left_str),
            'right': _parse_exponentiation(right_str)
        }

    return _parse_exponentiation(formula_string)

def _parse_addition_subtraction(formula_string: str) -> Dict[str, Any]:
    """Parses addition and subtraction, which have lower precedence than mul/div."""
    op_index, operator = _find_top_level_operator(formula_string, ['+', '-'])

    if op_index != -1:
        left_str = formula_string[:op_index].strip()
        right_str = formula_string[op_index+len(operator):].strip()
        return {
            'type': 'operation',
            'operator': operator,
            'left': _parse_addition_subtraction(left_str),
            'right': _parse_multiplication_division(right_str)
        }

    return _parse_multiplication_division(formula_string)

def _parse_not_expression(formula_string: str) -> Dict[str, Any]:
    """Parses the NOT operator."""
    trimmed_string = formula_string.strip()
    if trimmed_string.upper().startswith('NOT '):
        operand_str = trimmed_string[4:].strip()
        return {
            'type': 'operation',
            'operator': 'NOT',
            'operand': _parse_not_expression(operand_str) # NOT can be chained
        }
    return _parse_addition_subtraction(formula_string)

def _parse_and_expression(formula_string: str) -> Dict[str, Any]:
    """Parses the AND operator."""
    op_index, operator = _find_top_level_operator(formula_string, ['AND'])

    if op_index != -1:
        left_str = formula_string[:op_index].strip()
        right_str = formula_string[op_index+len(operator):].strip()
        return {
            'type': 'operation',
            'operator': 'AND',
            'left': _parse_and_expression(left_str),
            'right': _parse_not_expression(right_str)
        }
    return _parse_not_expression(formula_string)

def _parse_xor_expression(formula_string: str) -> Dict[str, Any]:
    """Parses the XOR operator."""
    op_index, operator = _find_top_level_operator(formula_string, ['XOR'])

    if op_index != -1:
        left_str = formula_string[:op_index].strip()
        right_str = formula_string[op_index+len(operator):].strip()
        return {
            'type': 'operation',
            'operator': 'XOR',
            'left': _parse_xor_expression(left_str),
            'right': _parse_and_expression(right_str)
        }
    return _parse_and_expression(formula_string)

def _parse_or_expression(formula_string: str) -> Dict[str, Any]:
    """Parses the OR operator."""
    op_index, operator = _find_top_level_operator(formula_string, ['OR'])

    if op_index != -1:
        left_str = formula_string[:op_index].strip()
        right_str = formula_string[op_index+len(operator):].strip()
        return {
            'type': 'operation',
            'operator': 'OR',
            'left': _parse_or_expression(left_str),
            'right': _parse_xor_expression(right_str)
        }
    return _parse_xor_expression(formula_string)

def _parse_xand_expression(formula_string: str) -> Dict[str, Any]:
    """Parses the XAND operator (lowest logical precedence)."""
    op_index, operator = _find_top_level_operator(formula_string, ['XAND'])

    if op_index != -1:
        left_str = formula_string[:op_index].strip()
        right_str = formula_string[op_index+len(operator):].strip()
        return {
            'type': 'operation',
            'operator': 'XAND',
            'left': _parse_xand_expression(left_str),
            'right': _parse_or_expression(right_str)
        }
    return _parse_or_expression(formula_string)

def _transform_formula_to_polars_expr(formula_dict: dict) -> polars.Expr:
    """
    Transforms a dictionary representation of a formula into a Polars expression.

    Args:
        formula_dict (dict): The dictionary representing the formula.

    Returns:
        polars.Expr: A Polars expression.

    Raises:
        ValueError: If an unsupported formula type or operator is encountered.
    """
    if formula_dict['type'] == 'column':
        return polars.col(formula_dict['name'])

    elif formula_dict['type'] == 'operation':
        operator = formula_dict['operator'].upper()

        if operator == 'NOT':
            operand_expr = _transform_formula_to_polars_expr(formula_dict['operand'])
            return operand_expr.not_()

        else:
            left_expr = _transform_formula_to_polars_expr(formula_dict['left'])
            right_expr = _transform_formula_to_polars_expr(formula_dict['right'])

            match operator:
                case 'AND'  : return left_expr.and_(right_expr)
                case 'OR'   : return left_expr.or_(right_expr)
                case 'XOR'  : return (left_expr.and_(right_expr.not_())).or_(left_expr.not_().and_(right_expr))
                case 'XAND' : return (left_expr.and_(right_expr)).or_(left_expr.not_().and_(right_expr.not_()))
                case '+'    : return left_expr.add(right_expr)
                case '-'    : return left_expr.sub(right_expr)
                case '*'    : return left_expr.mul(right_expr)
                case '/'    : return left_expr.truediv(right_expr)
                case '//'   : return left_expr.floordiv(right_expr)
                case '%'    : return left_expr.mod(right_expr)
                case '^'    : return left_expr.pow(right_expr)

            raise ValueError(f"Unsupported operator: {operator}")

    elif formula_dict['type'] == 'function':
        print(f"Warning: 'function' type encountered. "
              f"Name: {formula_dict['name']}, "
              f"Arguments: {formula_dict['arguments']}")
        raise NotImplementedError

    elif formula_dict['type'] == 'expression':
        print(f"Warning: 'expression' type encountered. "
              f"Value: {formula_dict['value']}")
        raise NotImplementedError

    else:
        raise ValueError(f"Unsupported formula type: {formula_dict['type']}")

def parse_dax(expression: str) -> Dict[str, Any]:
    """
    Parses a DAX-like expression.

    This function can handle both the `Measure = Function(...)` syntax and
    Excel-like formulas starting with `= Function(...) + ...`.

    Args:
        expression (str): The DAX or Excel-like expression string.

    Returns:
        dict: A dictionary with a structured representation of the parsed
              expression, or an error message.
    """
    expression_to_parse = expression.strip()

    try:
        # Case 1: Excel-like "= Formula"
        if expression_to_parse.startswith('='):
            formula_string = expression_to_parse[1:].strip()
            parsed_formula = _parse_xand_expression(formula_string) # Start parsing from the lowest logical precedence
            polars_expr = _transform_formula_to_polars_expr(parsed_formula)
            return {
                'formula': parsed_formula,
                'expression': polars_expr,
            }

        # Case 2: DAX-like "Measure = Formula"
        parts = re.split(r'\s*=\s*', expression_to_parse, maxsplit=1)
        if len(parts) == 2:
            measure_name = parts[0].strip()
            formula_string = parts[1].strip()
            parsed_formula = _parse_xand_expression(formula_string) # Start parsing from the lowest logical precedence
            polars_expr = _transform_formula_to_polars_expr(parsed_formula)
            return {
                'measure-name': measure_name,
                'formula': parsed_formula,
                'expression': polars_expr,
            }

    except Exception as e:
        print(e)

    # Invalid syntax
    return {'error': 'Invalid syntax'}