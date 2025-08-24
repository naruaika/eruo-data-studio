from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl
from polars.plugins import register_plugin_function

from eruo_strutil._internal import __version__ as __version__

if TYPE_CHECKING:
    from eruo_strutil.typing import IntoExprColumn

LIB = Path(__file__).parent


def pig_latinnify(expr: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name='pig_latinnify',
        is_elementwise=True,
    )

def to_sentence_case(expr: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name='to_sentence_case',
        is_elementwise=True,
    )

def to_sponge_case(expr: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name='to_sponge_case',
        is_elementwise=True,
    )