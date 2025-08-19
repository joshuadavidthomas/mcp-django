from __future__ import annotations

import pytest
from django.apps import apps

from mcp_django_shell.shell import DjangoShell
from mcp_django_shell.shell import ErrorResult
from mcp_django_shell.shell import ExpressionResult
from mcp_django_shell.shell import StatementResult
from mcp_django_shell.shell import parse_code

from .models import AModel


@pytest.fixture
def shell():
    shell = DjangoShell()
    yield shell
    shell.reset()


class TestCodeParsing:
    def test_parse_single_expression(self, shell):
        code, setup, code_type = parse_code("2 + 2")

        assert code == "2 + 2"
        assert setup == ""
        assert code_type == "expression"

    def test_parse_single_statement(self, shell):
        code, setup, code_type = parse_code("x = 5")

        assert code == "x = 5"
        assert setup == ""
        assert code_type == "statement"

    def test_parse_multiline_with_expression_basic(self, shell):
        code, setup, code_type = parse_code("x = 5\ny = 10\nx + y")

        assert code == "x + y"
        assert setup == "x = 5\ny = 10"
        assert code_type == "expression"

    def test_parse_multiline_statement_only(self, shell):
        code, setup, code_type = parse_code("x = 5\ny = 10\nz = x + y")

        assert code == "x = 5\ny = 10\nz = x + y"
        assert setup == ""
        assert code_type == "statement"

    def test_parse_empty_code(self, shell):
        code, setup, code_type = parse_code("")

        assert code == ""
        assert setup == ""
        assert code_type == "statement"

    def test_parse_whitespace_only(self, shell):
        code, setup, code_type = parse_code("   \n  \t  ")

        assert code == "   \n  \t  "
        assert setup == ""
        assert code_type == "statement"

    def test_parse_trailing_newlines_expression(self, shell):
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

    def test_parse_trailing_whitespace_expression(self, shell):
        code, setup, code_type = parse_code("2 + 2    \n\n   ")

        # strip() removes trailing whitespace
        assert code == "2 + 2"
        assert setup == ""
        assert code_type == "expression"

    def test_parse_leading_newlines_expression(self, shell):
        code, setup, code_type = parse_code("\n\n\n2 + 2")

        # Single expressions are returned as-is, not stripped
        assert code == "\n\n\n2 + 2"
        assert setup == ""
        assert code_type == "expression"

    def test_parse_multiline_trailing_newlines(self, shell):
        code, setup, code_type = parse_code("x = 5\nx + 10\n\n")

        assert code == "x + 10"
        assert setup == "x = 5"
        assert code_type == "expression"

    def test_parse_empty_list(self, shell):
        code, setup, code_type = parse_code("[]")

        assert code == "[]"
        assert setup == ""
        assert code_type == "expression"


class TestCodeExecution:
    def test_execute_expression_returns_value(self, shell):
        result = shell._execute("2 + 2")

        assert isinstance(result, ExpressionResult)
        assert result.value == 4
        assert "4" in result.output

    def test_execute_statement_returns_ok(self, shell):
        result = shell._execute("x = 5")

        assert isinstance(result, StatementResult)
        assert result.output == "OK"

    def test_execute_multiline_expression_returns_last_value(self, shell):
        code = """\
x = 5
y = 10
x + y
"""
        result = shell._execute(code.strip())

        assert isinstance(result, ExpressionResult)
        assert result.value == 15
        assert "15" in result.output

    def test_execute_multiline_statements_returns_ok(self, shell):
        code = """\
x = 5
y = 10
z = x + y
"""
        result = shell._execute(code.strip())

        assert isinstance(result, StatementResult)
        assert result.output == "OK"

    def test_execute_print_captures_stdout(self, shell):
        result = shell._execute('print("Hello, World!")')

        assert isinstance(result, ExpressionResult)
        assert result.value is None
        assert "Hello, World!" in result.output

    def test_execute_invalid_code_returns_error(self, shell):
        result = shell._execute("1 / 0")

        assert isinstance(result, ErrorResult)
        assert "ZeroDivisionError" in result.output

    def test_execute_empty_string_returns_ok(self, shell):
        result = shell._execute("")

        assert isinstance(result, StatementResult)
        assert result.output == "OK"

    def test_execute_whitespace_only_returns_ok(self, shell):
        result = shell._execute("   \n  \t  ")

        assert isinstance(result, StatementResult)

    @pytest.mark.asyncio
    async def test_async_execute_returns_result(self):
        shell = DjangoShell()

        result = await shell.execute("2 + 2")

        assert isinstance(result, ExpressionResult)
        assert result.value == 4


@pytest.mark.django_db
class TestResultOutput:
    def test_format_large_queryset_truncates_at_10(self, shell):
        for i in range(15):
            AModel.objects.create(name=f"Item {i}", value=i)

        shell._execute("from tests.models import AModel")

        result = shell._execute("AModel.objects.all()")

        assert isinstance(result, ExpressionResult)
        assert "... and 5 more items" in result.output
        assert "Item 0" in result.output
        # Should show first 10, not the last 5
        assert "Item 9" in result.output
        assert "Item 14" not in result.output

    def test_format_small_queryset_shows_all(self, shell):
        for i in range(5):
            AModel.objects.create(name=f"Item {i}", value=i)

        shell._execute("from tests.models import AModel")

        result = shell._execute("AModel.objects.all()")

        assert isinstance(result, ExpressionResult)
        # Should show all items, no truncation message for <10 items
        assert "Item 0" in result.output
        assert "Item 4" in result.output
        assert "... and" not in result.output

    def test_format_empty_queryset_shows_message(self, shell):
        shell._execute("from tests.models import AModel")

        result = shell._execute("AModel.objects.none()")

        assert isinstance(result, ExpressionResult)
        assert "Empty queryset/list" in result.output

    def test_format_empty_list_shows_message(self, shell):
        """Integration test for empty list formatting."""
        result = shell._execute("[]")

        assert isinstance(result, ExpressionResult)
        assert "Empty queryset/list" in result.output

    def test_format_bad_iterable_uses_repr(self, shell):
        result = shell._execute("""\
class BadIterable:
    def __iter__(self):
        raise RuntimeError("Can't iterate")
    def __repr__(self):
        return "BadIterable()"
BadIterable()
""")

        assert isinstance(result, ExpressionResult)
        assert "BadIterable()" in result.output


class TestShellState:
    def test_init_django_setup_completes(self):
        shell = DjangoShell()

        assert apps.ready
        assert shell.globals == {}

    def test_globals_persist_across_executions(self, shell):
        shell._execute("x = 42")

        assert "x" in shell.globals

        result = shell._execute("x + 8")

        assert result.value == 50

    def test_reset_clears_globals_and_history(self, shell):
        shell._execute("x = 42")

        assert "x" in shell.globals
        assert len(shell.history) == 1

        shell.reset()

        assert shell.globals == {}
        assert len(shell.history) == 0

    def test_history_tracks_all_executions(self, shell):
        shell._execute("x = 1")
        shell._execute("y = 2")
        shell._execute("x + y")

        assert len(shell.history) == 3
        assert shell.history[0].code == "x = 1"
        assert shell.history[1].code == "y = 2"
        assert shell.history[2].code == "x + y"
        assert shell.history[2].value == 3
