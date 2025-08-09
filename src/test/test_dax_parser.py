# test_dax_parser.py
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


from src.sheet_functions import parse_dax

def test_unary_minus():
    expression = '= -5 + 10'
    expected_output = {
        'formula': {
            'type': 'operation',
            'operator': '+',
            'left': {
                'type': 'operation',
                'operator': '-',
                'operand': {
                    'type': 'number',
                    'value': 5.0
                }
            },
            'right': {
                'type': 'number',
                'value': 10.0
            }
        },
        'expression': None
    }
    assert parse_dax(expression, transform=False) == expected_output

def test_mixed_precedence_operators():
    expression = '= 1 + 2 * 3 / (4 - 1)'
    expected_output = {
        "formula": {
            "type": "operation",
            "operator": "+",
            "left": {"type": "number", "value": 1.0},
            "right": {
                "type": "operation",
                "operator": "/",
                "left": {
                    "type": "operation",
                    "operator": "*",
                    "left": {"type": "number", "value": 2.0},
                    "right": {"type": "number", "value": 3.0}
                },
                "right": {
                    "type": "operation",
                    "operator": "-",
                    "left": {"type": "number", "value": 4.0},
                    "right": {"type": "number", "value": 1.0}
                }
            }
        },
        'expression': None
    }
    assert parse_dax(expression, transform=False) == expected_output

def test_parse_bitwise_operators():
    """Test to ensure bitwise operators are parsed correctly with precedence."""
    expression = "= 5 & 10 | 10 ^ 5"
    expected_output = {
        "formula": {
            "type": "operation",
            "operator": "|",
            "left": {
                "type": "operation",
                "operator": "&",
                "left": {"type": "number", "value": 5},
                "right": {"type": "number", "value": 10}
            },
            "right": {
                "type": "operation",
                "operator": "^",
                "left": {"type": "number", "value": 10},
                "right": {"type": "number", "value": 5}
            }
        },
        'expression': None
    }
    assert parse_dax(expression, transform=False) == expected_output

def test_arithmetic_operators():
    expression = '= 5 ** 2 + 10 % 3 - 10 // 3'
    expected_output = {
        "formula": {
            "type": "operation",
            "operator": "-",
            "left": {
                "type": "operation",
                "operator": "+",
                "left": {
                    "type": "operation",
                    "operator": "**",
                    "left": {"type": "number", "value": 5.0},
                    "right": {"type": "number", "value": 2.0}
                },
                "right": {
                    "type": "operation",
                    "operator": "%",
                    "left": {"type": "number", "value": 10.0},
                    "right": {"type": "number", "value": 3.0}
                }
            },
            "right": {
                "type": "operation",
                "operator": "//",
                "left": {"type": "number", "value": 10.0},
                "right": {"type": "number", "value": 3.0}
            }
        },
        'expression': None
    }
    assert parse_dax(expression, transform=False) == expected_output

def test_logical_expression():
    expression = '= NOT (TRUE() AND FALSE()) OR (10 > 5)'
    expected_output = {
        'formula': {
            'type': 'operation',
            'operator': 'OR',
            'left': {
                'type': 'operation',
                'operator': 'NOT',
                'operand': {
                    'type': 'operation',
                    'operator': 'AND',
                    'left': {
                        'type': 'function',
                        'name': 'TRUE',
                        'arguments': [],
                    },
                    'right': {
                        'type': 'function',
                        'name': 'FALSE',
                        'arguments': [],
                    }
                }
            },
            'right': {
                'type': 'operation',
                'operator': '>',
                'left': {'type': 'number', 'value': 10},
                'right': {'type': 'number', 'value': 5}
            }
        },
        'expression': None
    }
    assert parse_dax(expression, transform=False) == expected_output

def test_excel_style_formula_with_numbers():
    expression = '= SUM(1, 2, 3, 4, 5) + 1 + (2 + 3)'
    expected_output = {
        "formula": {
            "type": "operation",
            "operator": "+",
            "left": {
                "type": "operation",
                "operator": "+",
                "left": {
                    "type": "function",
                    "name": "SUM",
                    "arguments": [
                        {"type": "number", "value": 1.0},
                        {"type": "number", "value": 2.0},
                        {"type": "number", "value": 3.0},
                        {"type": "number", "value": 4.0},
                        {"type": "number", "value": 5.0}
                    ]
                },
                "right": {"type": "number", "value": 1.0}
            },
            "right": {
                "type": "operation",
                "operator": "+",
                "left": {"type": "number", "value": 2.0},
                "right": {"type": "number", "value": 3.0}
            }
        },
        'expression': None
    }
    assert parse_dax(expression, transform=False) == expected_output

def test_dax_measure_with_nested_function():
    expression = 'Total Sales = CALCULATE(SUM([Sales Amount]), \'Sales\'[City] = "Cimahi")'
    expected_output = {
        "measure": "Total Sales",
        "formula": {
            "type": "function",
            "name": "CALCULATE",
            "arguments": [
                {
                    "type": "function",
                    "name": "SUM",
                    "arguments": [
                        {
                            "type": "column",
                            "name": "Sales Amount"
                        }
                    ]
                },
                {
                    "type": "operation",
                    "operator": "=",
                    "left": {
                        "type": "table_column",
                        "table": "Sales",
                        "column": "City"
                    },
                    "right": {
                        "type": "string",
                        "value": "Cimahi"
                    }
                }
            ]
        },
        'expression': None
    }
    assert parse_dax(expression, transform=False) == expected_output

def test_quoted_table_and_column_name():
    expression = 'Total Sales = SUM(\'Sales Data\'[Sales Amount])'
    expected_output = {
        "measure": "Total Sales",
        "formula": {
            "type": "function",
            "name": "SUM",
            "arguments": [
                {
                    "type": "table_column",
                    "table": "Sales Data",
                    "column": "Sales Amount"
                }
            ]
        },
        'expression': None
    }
    assert parse_dax(expression, transform=False) == expected_output

def test_sumx_with_filter_and_unquoted_table():
    expression = 'Total Value = SUMX(FILTER(Sales, Sales[Region] = \'North\'), [OrderValue])'
    expected_output = {
        "measure": "Total Value",
        "formula": {
            "type": "function",
            "name": "SUMX",
            "arguments": [
                {
                    "type": "function",
                    "name": "FILTER",
                    "arguments": [
                        {"type": "table", "name": "Sales"},
                        {
                            "type": "operation",
                            "operator": "=",
                            "left": {
                                "type": "table_column",
                                "table": "Sales",
                                "column": "Region"
                            },
                            "right": {"type": "string", "value": "North"}
                        }
                    ]
                },
                {"type": "column", "name": "OrderValue"}
            ]
        },
        'expression': None
    }
    assert parse_dax(expression, transform=False) == expected_output

def test_nested_functions_and_operators_in_arguments():
    expression = 'Total Value = SUM(1, 2, 3, 4, 5) + 1 + SUM(2 + SUM(9, 10))'
    expected_output = {
        "measure": "Total Value",
        "formula": {
            "type": "operation",
            "operator": "+",
            "left": {
                "type": "operation",
                "operator": "+",
                "left": {
                    "type": "function",
                    "name": "SUM",
                    "arguments": [
                        {"type": "number", "value": 1.0},
                        {"type": "number", "value": 2.0},
                        {"type": "number", "value": 3.0},
                        {"type": "number", "value": 4.0},
                        {"type": "number", "value": 5.0}
                    ]
                },
                "right": {"type": "number", "value": 1.0}
            },
            "right": {
                "type": "function",
                "name": "SUM",
                "arguments": [
                    {
                        "type": "operation",
                        "operator": "+",
                        "left": {"type": "number", "value": 2.0},
                        "right": {
                            "type": "function",
                            "name": "SUM",
                            "arguments": [
                                {"type": "number", "value": 9.0},
                                {"type": "number", "value": 10.0}
                            ]
                        }
                    }
                ]
            }
        },
        'expression': None
    }
    assert parse_dax(expression, transform=False) == expected_output

def test_invalid_syntax():
    expression = 'Lorem ipsum dolor sit amet.'
    expected_output = {'error': 'Invalid syntax'}
    assert parse_dax(expression, transform=False) == expected_output