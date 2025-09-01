# plugin_repository.py
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


import polars

try:
    import eruo_strutil as strx

    @polars.api.register_expr_namespace('strx')
    class ExpandedStringExpr:
        def __init__(self, expr: polars.Expr) -> None:
            self._expr = expr

        def pig_latinnify(self) -> polars.Expr:
            return strx.pig_latinnify(self._expr)

        def split_by_chars(self, characters: str) -> polars.Expr:
            return strx.split_by_chars(self._expr, characters)

        def to_sentence_case(self) -> polars.Expr:
            return strx.to_sentence_case(self._expr)

        def to_sponge_case(self) -> polars.Expr:
            return strx.to_sponge_case(self._expr)
except ModuleNotFoundError:
    pass