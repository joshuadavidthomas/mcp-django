from __future__ import annotations

import logging

import pytest
from django.apps import apps

from mcp_django_shell.shell import DjangoShell
from mcp_django_shell.shell import ErrorResult
from mcp_django_shell.shell import ExpressionResult
from mcp_django_shell.shell import StatementResult
from mcp_django_shell.shell import parse_code


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

    def test_execute_statement_returns_ok(self, shell):
        result = shell._execute("x = 5")

        assert isinstance(result, StatementResult)

    def test_execute_multiline_expression_returns_last_value(self, shell):
        code = """\
x = 5
y = 10
x + y
"""
        result = shell._execute(code.strip())

        assert isinstance(result, ExpressionResult)
        assert result.value == 15

    def test_execute_multiline_statements_returns_ok(self, shell):
        code = """\
x = 5
y = 10
z = x + y
"""
        result = shell._execute(code.strip())

        assert isinstance(result, StatementResult)

    def test_execute_print_captures_stdout(self, shell):
        result = shell._execute('print("Hello, World!")')

        assert isinstance(result, ExpressionResult)
        assert result.value is None

    def test_multiline_ending_with_print_no_none(self, shell):
        code = """
x = 5
y = 10
print(f"Sum: {x + y}")
"""
        result = shell._execute(code.strip())

        assert isinstance(result, ExpressionResult)
        assert result.value is None

    def test_execute_invalid_code_returns_error(self, shell):
        result = shell._execute("1 / 0")

        assert isinstance(result, ErrorResult)

    def test_execute_empty_string_returns_ok(self, shell):
        result = shell._execute("")

        assert isinstance(result, StatementResult)

    def test_execute_whitespace_only_returns_ok(self, shell):
        result = shell._execute("   \n  \t  ")

        assert isinstance(result, StatementResult)

    @pytest.mark.asyncio
    async def test_async_execute_returns_result(self):
        shell = DjangoShell()

        result = await shell.execute("2 + 2")

        assert isinstance(result, ExpressionResult)
        assert result.value == 4


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


class TestLoggingCoverage:
    @pytest.fixture(autouse=True)
    def debug_loglevel(self, caplog):
        caplog.set_level(logging.DEBUG)
        yield

    def test_expression_result_with_stderr(self, shell, caplog):
        result = shell._execute("""
import sys
sys.stderr.write("Warning message\\n")
42
""")

        assert isinstance(result, ExpressionResult)
        assert result.value == 42
        assert result.stderr == "Warning message\n"
        assert "ExpressionResult.stderr: Warning message" in caplog.text

    def test_statement_result_with_stdout_and_stderr(self, shell, caplog):
        result = shell._execute("""
import sys
sys.stdout.write("Output message\\n")
sys.stderr.write("Error message\\n")
x = 42
""")

        assert isinstance(result, StatementResult)
        assert result.stdout == "Output message\n"
        assert result.stderr == "Error message\n"
        assert "StatementResult.stdout: Output message" in caplog.text
        assert "StatementResult.stderr: Error message" in caplog.text

    def test_error_result_with_stdout_and_stderr(self, shell, caplog):
        result = shell._execute("""
import sys
sys.stdout.write("Before error\\n")
sys.stderr.write("Warning before error\\n")
1 / 0
""")

        assert isinstance(result, ErrorResult)
        assert result.stdout == "Before error\n"
        assert result.stderr == "Warning before error\n"
        assert "ErrorResult.stdout: Before error" in caplog.text
        assert "ErrorResult.stderr: Warning before error" in caplog.text
