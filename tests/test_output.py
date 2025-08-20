from __future__ import annotations

import traceback

from mcp_django_shell.output import DjangoShellOutput
from mcp_django_shell.output import ErrorOutput
from mcp_django_shell.output import ExceptionOutput
from mcp_django_shell.output import ExecutionStatus
from mcp_django_shell.output import ExpressionOutput
from mcp_django_shell.shell import ErrorResult
from mcp_django_shell.shell import ExpressionResult


def test_django_shell_output_from_expression_result():
    result = ExpressionResult(
        code="2 + 2",
        value=4,
        stdout="",
        stderr="",
    )

    output = DjangoShellOutput.from_result(result)

    assert output.status == ExecutionStatus.SUCCESS
    assert output.input == "2 + 2"
    assert isinstance(output.output, ExpressionOutput)
    assert output.output.value == 4
    assert output.output.value_type is int


def test_expression_with_none_value():
    result = ExpressionResult(
        code="None",
        value=None,
        stdout="",
        stderr="",
    )

    output = DjangoShellOutput.from_result(result)

    assert output.status == ExecutionStatus.SUCCESS
    assert isinstance(output.output, ExpressionOutput)

    serialized = output.output.model_dump(mode="json")

    assert serialized["value"] == "None"
    assert serialized["value_type"] == "NoneType"


def test_django_shell_output_from_error_result():
    exc = ZeroDivisionError("division by zero")

    result = ErrorResult(
        code="1 / 0",
        exception=exc,
        stdout="",
        stderr="",
    )

    output = DjangoShellOutput.from_result(result)

    assert output.status == ExecutionStatus.ERROR
    assert isinstance(output.output, ErrorOutput)
    assert output.output.exception.type is ZeroDivisionError
    assert "division by zero" in output.output.exception.message


def test_exception_output_serialization():
    exc = ValueError("test error")

    exc_output = ExceptionOutput(
        type=type(exc),
        message=str(exc),
        traceback=None,  # needs to be None since we didn't actually raise it
    )

    # Trigger serialization
    serialized = exc_output.model_dump(mode="json")

    assert serialized["type"] == "ValueError"
    assert serialized["message"] == "test error"
    assert serialized["traceback"] == []


def test_exception_output_with_real_traceback():
    try:
        # Do something that actually raises an error
        1 / 0
    except ZeroDivisionError as e:
        exc_output = ExceptionOutput(
            type=type(e),
            message=str(e),
            traceback=e.__traceback__,
        )

        serialized = exc_output.model_dump(mode="json")

        assert serialized["type"] == "ZeroDivisionError"
        assert "division by zero" in serialized["message"]
        assert isinstance(serialized["traceback"], list)
        assert len(serialized["traceback"]) > 0
        assert any("1 / 0" in line for line in serialized["traceback"])
        assert not any("mcp_django_shell" in line for line in serialized["traceback"])


def test_traceback_filtering():
    # Create a function that will appear in the traceback
    def mcp_django_shell_function():
        raise ValueError("test error")

    try:
        mcp_django_shell_function()
    except ValueError as e:
        exc_output = ExceptionOutput(
            type=type(e),
            message=str(e),
            traceback=e.__traceback__,
        )

        # the traceback should contain mcp_django_shell
        assert any(
            "mcp_django_shell_function" in line
            for line in traceback.format_tb(e.__traceback__)
        )

        serialized = exc_output.model_dump(mode="json")

        # The serialized traceback should NOT contain mcp_django_shell
        assert len(serialized["traceback"]) == 0 or not any(
            "mcp_django_shell" in line for line in serialized["traceback"]
        )
