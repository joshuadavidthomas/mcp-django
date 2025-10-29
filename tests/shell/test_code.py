from __future__ import annotations

import pytest

from mcp_django.shell.code import filter_existing_imports
from mcp_django.shell.code import parse_code


def test_parse_code_single_expression():
    code, setup, code_type = parse_code("2 + 2")

    assert code == "2 + 2"
    assert setup == ""
    assert code_type == "expression"


def test_parse_code_single_statement():
    code, setup, code_type = parse_code("x = 5")

    assert code == "x = 5"
    assert setup == ""
    assert code_type == "statement"


def test_parse_code_multiline_with_expression_basic():
    code, setup, code_type = parse_code("x = 5\ny = 10\nx + y")

    assert code == "x + y"
    assert setup == "x = 5\ny = 10"
    assert code_type == "expression"


def test_parse_code_multiline_statement_only():
    code, setup, code_type = parse_code("x = 5\ny = 10\nz = x + y")

    assert code == "x = 5\ny = 10\nz = x + y"
    assert setup == ""
    assert code_type == "statement"


def test_parse_code_empty_code():
    code, setup, code_type = parse_code("")

    assert code == ""
    assert setup == ""
    assert code_type == "statement"


def test_parse_code_whitespace_only():
    code, setup, code_type = parse_code("   \n  \t  ")

    assert code == "   \n  \t  "
    assert setup == ""
    assert code_type == "statement"


def test_parse_code_trailing_newlines_expression():
    code = """\
x = 5
y = 10
x + y


"""
    code, setup, code_type = parse_code(code)

    assert code == "x + y"
    # strip() removes leading/trailing empty lines
    assert setup == "x = 5\ny = 10"
    assert code_type == "expression"


def test_parse_code_trailing_whitespace_expression():
    code, setup, code_type = parse_code("2 + 2    \n\n   ")

    # strip() removes trailing whitespace
    assert code == "2 + 2"
    assert setup == ""
    assert code_type == "expression"


def test_parse_code_leading_newlines_expression():
    code, setup, code_type = parse_code("\n\n\n2 + 2")

    # Single expressions are returned as-is, not stripped
    assert code == "\n\n\n2 + 2"
    assert setup == ""
    assert code_type == "expression"


def test_parse_code_multiline_trailing_newlines():
    code, setup, code_type = parse_code("x = 5\nx + 10\n\n")

    assert code == "x + 10"
    assert setup == "x = 5"
    assert code_type == "expression"


def test_parse_code_empty_list():
    code, setup, code_type = parse_code("[]")

    assert code == "[]"
    assert setup == ""
    assert code_type == "expression"


def test_filter_existing_imports_star_import():
    result = filter_existing_imports("from os import *", {"os": True})

    assert result == "from os import *"


def test_filter_existing_imports_relative():
    result = filter_existing_imports(
        "from ..models import User\nfrom ...core import Base", {}
    )

    assert result == "from ..models import User\nfrom ...core import Base"


def test_filter_existing_imports_invalid_raises_error():
    with pytest.raises(ValueError, match="Input must contain only import statements"):
        filter_existing_imports("x = 5", {})
