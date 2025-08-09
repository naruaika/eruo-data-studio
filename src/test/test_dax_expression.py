# test_dax_expression.py
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


import polars

from src.sheet_functions import parse_dax

def test_unary_minus():
    expression = '= -5 + 10'
    assert polars.select(parse_dax(expression)['expression']).item() == 5

def test_arithmetic_expression():
    expression = '= 5 ** 2 + 10 % 3 - 10 // 3'
    assert polars.select(parse_dax(expression)['expression']).item() == 23

def test_bitwise_expression():
    expression = '= 5 & 10 | 10 ^ 5'
    assert polars.select(parse_dax(expression)['expression']).item() == 15