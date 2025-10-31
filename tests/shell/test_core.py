from __future__ import annotations

import logging

import pytest
from django.apps import apps

from mcp_django.shell.code import parse_code
from mcp_django.shell.core import DjangoShell
from mcp_django.shell.core import ErrorResult
from mcp_django.shell.core import ExpressionResult
from mcp_django.shell.core import StatementResult


@pytest.fixture
def shell():
    shell = DjangoShell()
    yield shell
    shell.clear_history()


class TestCodeExecution:
    def test_execute_expression_returns_value(self, shell):
        parsed_code, setup, code_type = parse_code("2 + 2")

        result = shell._execute(parsed_code, setup, code_type)

        assert isinstance(result, ExpressionResult)
        assert result.value == 4

    def test_execute_statement_returns_ok(self, shell):
        result = parsed_code, setup, code_type = parse_code("x = 5")
        result = shell._execute(parsed_code, setup, code_type)

        assert isinstance(result, StatementResult)

    def test_execute_multiline_expression_returns_last_value(self, shell):
        code = """\
x = 5
y = 10
x + y
"""
        parsed_code, setup, code_type = parse_code(code.strip())
        result = shell._execute(parsed_code, setup, code_type)

        assert isinstance(result, ExpressionResult)
        assert result.value == 15

    def test_execute_multiline_statements_returns_ok(self, shell):
        code = """\
x = 5
y = 10
z = x + y
"""
        parsed_code, setup, code_type = parse_code(code.strip())
        result = shell._execute(parsed_code, setup, code_type)

        assert isinstance(result, StatementResult)

    def test_execute_print_captures_stdout(self, shell):
        result = parsed_code, setup, code_type = parse_code('print("Hello, World!")')
        result = shell._execute(parsed_code, setup, code_type)

        assert isinstance(result, ExpressionResult)
        assert result.value is None

    def test_multiline_ending_with_print_no_none(self, shell):
        code = """
x = 5
y = 10
print(f"Sum: {x + y}")
"""
        parsed_code, setup, code_type = parse_code(code.strip())
        result = shell._execute(parsed_code, setup, code_type)

        assert isinstance(result, ExpressionResult)
        assert result.value is None

    def test_execute_invalid_code_returns_error(self, shell):
        result = parsed_code, setup, code_type = parse_code("1 / 0")
        result = shell._execute(parsed_code, setup, code_type)

        assert isinstance(result, ErrorResult)

    def test_execute_empty_string_returns_ok(self, shell):
        parsed_code, setup, code_type = parse_code("")
        result = shell._execute(parsed_code, setup, code_type)

        assert isinstance(result, StatementResult)

    def test_execute_whitespace_only_returns_ok(self, shell):
        result = parsed_code, setup, code_type = parse_code("   \n  \t  ")
        result = shell._execute(parsed_code, setup, code_type)

        assert isinstance(result, StatementResult)

    @pytest.mark.asyncio
    async def test_async_execute_returns_result(self):
        shell = DjangoShell()

        parsed_code, setup, code_type = parse_code("2 + 2")
        result = await shell.execute(parsed_code, setup, code_type)

        assert isinstance(result, ExpressionResult)
        assert result.value == 4


class TestShellState:
    def test_init_django_setup_completes(self):
        shell = DjangoShell()

        assert apps.ready
        assert shell.history == []

    def test_execution_uses_fresh_globals(self, shell):
        """Verify each execution uses fresh globals (stateless)."""
        # First execution
        parsed_code, setup, code_type = parse_code("x = 42")
        result = shell._execute(parsed_code, setup, code_type)
        assert isinstance(result, StatementResult)

        # Second execution should NOT have access to 'x' (fresh globals)
        parsed_code, setup, code_type = parse_code("x + 8")
        result = shell._execute(parsed_code, setup, code_type)
        assert isinstance(result, ErrorResult)
        assert isinstance(result.exception, NameError)

    def test_clear_history_clears_history_only(self, shell):
        """Verify clear_history clears the execution history."""
        parsed_code, setup, code_type = parse_code("x = 42")
        shell._execute(parsed_code, setup, code_type)

        assert len(shell.history) == 1

        shell.clear_history()

        assert len(shell.history) == 0


class TestLoggingCoverage:
    @pytest.fixture(autouse=True)
    def debug_loglevel(self, caplog):
        caplog.set_level(logging.DEBUG)
        yield

    def test_expression_result_with_stderr(self, shell, caplog):
        code = """
import sys
sys.stderr.write("Warning message\\n")
42
"""
        parsed_code, setup, code_type = parse_code(code.strip())
        result = shell._execute(parsed_code, setup, code_type)

        assert isinstance(result, ExpressionResult)
        assert result.value == 42
        assert result.stderr == "Warning message\n"
        assert "ExpressionResult.stderr: Warning message" in caplog.text

    def test_statement_result_with_stdout_and_stderr(self, shell, caplog):
        code = """
import sys
sys.stdout.write("Output message\\n")
sys.stderr.write("Error message\\n")
x = 42
"""
        parsed_code, setup, code_type = parse_code(code.strip())
        result = shell._execute(parsed_code, setup, code_type)

        assert isinstance(result, StatementResult)
        assert result.stdout == "Output message\n"
        assert result.stderr == "Error message\n"
        assert "StatementResult.stdout: Output message" in caplog.text
        assert "StatementResult.stderr: Error message" in caplog.text

    def test_error_result_with_stdout_and_stderr(self, shell, caplog):
        code = """
import sys
sys.stdout.write("Before error\\n")
sys.stderr.write("Warning before error\\n")
1 / 0
"""
        parsed_code, setup, code_type = parse_code(code.strip())
        result = shell._execute(parsed_code, setup, code_type)

        assert isinstance(result, ErrorResult)
        assert result.stdout == "Before error\n"
        assert result.stderr == "Warning before error\n"
        assert "ErrorResult.stdout: Before error" in caplog.text
        assert "ErrorResult.stderr: Warning before error" in caplog.text
