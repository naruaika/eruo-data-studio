from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl
from polars.plugins import register_plugin_function

from eruo_strutil._internal import __version__ as __version__

if TYPE_CHECKING:
    from eruo_strutil.typing import IntoExprColumn

LIB = Path(__file__).parent


def pig_latinnify(expression: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        plugin_path=LIB,
        function_name='pig_latinnify',
        args=[expression],
        is_elementwise=True,
    )

def split_by_chars(expression: IntoExprColumn, characters: str) -> pl.Expr:
    return register_plugin_function(
        plugin_path=LIB,
        function_name='split_by_chars',
        args=[expression],
        kwargs={'characters': characters},
        is_elementwise=True,
    )

def to_sentence_case(expression: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        plugin_path=LIB,
        function_name='to_sentence_case',
        args=[expression],
        is_elementwise=True,
    )

def to_sponge_case(expression: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        plugin_path=LIB,
        function_name='to_sponge_case',
        args=[expression],
        is_elementwise=True,
    )