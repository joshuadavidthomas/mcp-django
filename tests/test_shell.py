from __future__ import annotations

import pytest

from mcp_django_shell.shell import DjangoShell
from mcp_django_shell.shell import ExecutionType

from .models import AModel


@pytest.fixture
def shell():
    shell = DjangoShell()
    yield shell
    shell.reset()


def test_single_expression(shell):
    result = shell._execute("2 + 2")

    assert result.type == ExecutionType.EXPRESSION
    assert result.payload == 4
    assert "4" in result.output


def test_single_statement(shell):
    result = shell._execute("x = 5")

    assert result.type == ExecutionType.STATEMENT
    assert result.output == "OK"


def test_multiline_with_expression(shell):
    code = """
x = 5
y = 10
x + y
"""
    result = shell._execute(code.strip())

    assert result.type == ExecutionType.EXPRESSION
    assert result.payload == 15
    assert "15" in result.output


def test_multiline_statement_only(shell):
    code = """
x = 5
y = 10
z = x + y
"""
    result = shell._execute(code.strip())

    assert result.type == ExecutionType.STATEMENT
    assert result.output == "OK"


def test_print_output(shell):
    result = shell._execute('print("Hello, World!")')

    assert result.type == ExecutionType.EXPRESSION
    assert result.payload is None
    assert "Hello, World!" in result.output


def test_error_handling(shell):
    result = shell._execute("1 / 0")

    assert result.type == ExecutionType.ERROR
    assert "ZeroDivisionError" in result.output


def test_django_initialized_on_creation():
    from django.apps import apps

    shell = DjangoShell()

    assert apps.ready
    assert shell.globals == {}


def test_globals_persist_between_executions(shell):
    shell._execute("x = 42")

    assert "x" in shell.globals

    result = shell._execute("x + 8")

    assert result.payload == 50


def test_reset_clears_state(shell):
    shell._execute("x = 42")

    assert "x" in shell.globals
    assert len(shell.history) == 1

    shell.reset()

    assert shell.globals == {}
    assert len(shell.history) == 0


def test_empty_code(shell):
    result = shell._execute("")

    assert result.type == ExecutionType.STATEMENT
    assert result.output == "OK"


def test_whitespace_only_code(shell):
    result = shell._execute("   \n  \t  ")

    assert result.type == ExecutionType.STATEMENT


@pytest.mark.django_db
def test_large_queryset_formatting(shell):
    for i in range(15):
        AModel.objects.create(name=f"Item {i}", value=i)

    shell._execute("from tests.models import AModel")

    result = shell._execute("AModel.objects.all()")

    assert result.type == ExecutionType.EXPRESSION
    assert "... and 5 more items" in result.output
    assert "Item 0" in result.output
    # Should show first 10, not the last 5
    assert "Item 9" in result.output
    assert "Item 14" not in result.output


@pytest.mark.django_db
def test_medium_queryset_formatting(shell):
    for i in range(5):
        AModel.objects.create(name=f"Item {i}", value=i)

    shell._execute("from tests.models import AModel")

    result = shell._execute("AModel.objects.all()")

    assert result.type == ExecutionType.EXPRESSION
    # Should show all items, no truncation message for <10 items
    assert "Item 0" in result.output
    assert "Item 4" in result.output
    assert "... and" not in result.output


@pytest.mark.django_db
def test_empty_queryset_formatting(shell):
    shell._execute("from tests.models import AModel")

    result = shell._execute("AModel.objects.none()")

    assert result.type == ExecutionType.EXPRESSION
    assert "Empty queryset/list" in result.output


def test_empty_iterable_formatting(shell):
    result = shell._execute("[]")

    assert result.type == ExecutionType.EXPRESSION
    assert "Empty queryset/list" in result.output


def test_iterable_formatting_exception(shell):
    result = shell._execute("""
class BadIterable:
    def __iter__(self):
        raise RuntimeError("Can't iterate")
    def __repr__(self):
        return "BadIterable()"
BadIterable()
""")

    assert result.type == ExecutionType.EXPRESSION
    assert "BadIterable()" in result.output


def test_history_tracking(shell):
    shell._execute("x = 1")
    shell._execute("y = 2")
    shell._execute("x + y")

    assert len(shell.history) == 3
    assert shell.history[0].code == "x = 1"
    assert shell.history[1].code == "y = 2"
    assert shell.history[2].code == "x + y"
    assert shell.history[2].payload == 3


@pytest.mark.asyncio
async def test_execute_async():
    shell = DjangoShell()

    result = await shell.execute("2 + 2")

    assert result.type == ExecutionType.EXPRESSION
    assert result.payload == 4
