from __future__ import annotations

import traceback
from enum import Enum
from types import TracebackType
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import field_serializer

from .shell import ErrorResult
from .shell import ExpressionResult
from .shell import Result
from .shell import StatementResult


class DjangoShellOutput(BaseModel):
    status: ExecutionStatus
    output: Output
    stdout: str
    stderr: str

    @classmethod
    def from_result(cls, result: Result) -> DjangoShellOutput:
        output: Output

        match result:
            case ExpressionResult():
                output = ExpressionOutput(
                    value=result.value,
                    value_type=type(result.value),
                )
            case StatementResult():
                output = StatementOutput()
            case ErrorResult():
                exception = ExceptionOutput(
                    exc_type=type(result.exception),
                    message=str(result.exception),
                    traceback=result.exception.__traceback__,
                )
                output = ErrorOutput(exception=exception)

        return cls(
            status=ExecutionStatus.from_output(output),
            output=output,
            stdout=result.stdout,
            stderr=result.stderr,
        )


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"

    @classmethod
    def from_output(cls, output: Output) -> ExecutionStatus:
        match output:
            case ExpressionOutput() | StatementOutput():
                return cls.SUCCESS
            case ErrorOutput():
                return cls.ERROR


class ExpressionOutput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    value: Any
    value_type: type

    @field_serializer("value")
    def serialize_value(self, val: Any) -> str:
        if val is None:
            return "None"
        return repr(val)

    @field_serializer("value_type")
    def serialize_value_type(self, typ: type) -> str:
        return typ.__name__


class StatementOutput(BaseModel):
    """Output from evaluating a Python statement.

    Statements by definition do not return values, just side effects such as
    setting variables or executing functions.

    This is empty for now, but defined to gain type safety (see the `Output`
    tagged union below) and as a holder for any potential future metadata.
    """


class ErrorOutput(BaseModel):
    exception: ExceptionOutput


class ExceptionOutput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    exc_type: type[Exception]
    message: str
    traceback: TracebackType | None

    @field_serializer("exc_type")
    def serialize_exception_type(self, exc_type: type[Exception]) -> str:
        return exc_type.__name__

    @field_serializer("traceback")
    def serialize_traceback(self, tb: TracebackType | None) -> list[str]:
        if tb is None:
            return []

        tb_lines = traceback.format_tb(tb)
        internal_markers = (
            "mcp_django/shell",
            "mcp_django.shell",
        )
        relevant_tb_lines = [
            line.strip()
            for line in tb_lines
            if line.strip()
            and not any(marker in line for marker in internal_markers)
        ]

        return relevant_tb_lines


Output = ExpressionOutput | StatementOutput | ErrorOutput
