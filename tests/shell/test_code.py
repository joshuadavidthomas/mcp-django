from __future__ import annotations

from mcp_django.shell.code import parse_code


def test_parse_code_returns_code_as_is():
    code = "x = 5"
    result = parse_code(code)

    assert result == "x = 5"


def test_parse_code_multiline():
    code = "x = 5\ny = 10\nprint(x + y)"
    result = parse_code(code)

    assert result == "x = 5\ny = 10\nprint(x + y)"


def test_parse_code_empty_string():
    result = parse_code("")

    assert result == ""


def test_parse_code_whitespace():
    code = "   \n  \t  "
    result = parse_code(code)

    assert result == "   \n  \t  "
