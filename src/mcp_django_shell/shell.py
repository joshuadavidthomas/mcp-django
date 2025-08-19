from __future__ import annotations

import sys
import traceback
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from io import StringIO
from typing import Any

from asgiref.sync import sync_to_async


class DjangoShell:
    def __init__(self):
        from django import setup
        from django.apps import apps

        if not apps.ready:  # pragma: no cover
            setup()

        self.globals: dict[str, Any] = {}
        self.history: list[Result] = []

    def reset(self):
        self.globals = {}
        self.history = []

    async def execute(self, code: str, timeout: int | None = None) -> Result:
        """Execute Python code in the Django shell context (async wrapper).

        This async wrapper enables use from FastMCP and other async contexts.
        It delegates to `_execute()` for the actual execution logic.

        Note: FastMCP requires async methods, but Django ORM operations are
        synchronous. The `@sync_to_async` decorator runs the synchronous
        `_execute()` method in a thread pool to avoid `SynchronousOnlyOperation`
        errors.
        """

        return await sync_to_async(self._execute)(code, timeout)

    def _execute(self, code: str, timeout: int | None = None) -> Result:
        """Execute Python code in the Django shell context (synchronous).

        Attempts to evaluate code as an expression first (returning a value),
        falling back to exec for statements. Captures stdout and errors.

        Note: This synchronous method contains the actual execution logic.
        Use `execute()` for async contexts or `_execute()` for sync/testing.
        """

        def can_eval(code: str) -> bool:
            try:
                compile(code, "<stdin>", "eval")
                return True
            except SyntaxError:
                return False

        def make_result(
            execution_type: ExecutionType, payload: ResultPayload = None
        ) -> Result:
            result = Result(
                code=code,
                type=execution_type,
                payload=payload,
                stdout=captured_output.getvalue(),
            )
            self.history.append(result)
            return result

        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        try:
            # Try as single expression (e.g., "2 + 2")
            if can_eval(code):
                payload = eval(code, self.globals)
                return make_result(ExecutionType.EXPRESSION, payload)

            # Check for multi-line with final expression
            lines = code.strip().split("\n")
            last_line = lines[-1] if lines else ""

            if can_eval(last_line):
                # Execute setup lines, eval last line
                if len(lines) > 1:
                    exec("\n".join(lines[:-1]), self.globals)
                payload = eval(last_line, self.globals)
                return make_result(ExecutionType.EXPRESSION, payload)

            # Execute as pure statements
            exec(code, self.globals)
            return make_result(ExecutionType.STATEMENT)

        except Exception as e:
            return make_result(ExecutionType.ERROR, e)

        finally:
            sys.stdout = old_stdout


ResultPayload = Any | None | Exception


class ExecutionType(Enum):
    """Describes how code was executed in the Django shell.

    `EXPRESSION`: Code was evaluated with eval() and returned a value
    `STATEMENT`: Code was executed with exec() as one or more statements
    `ERROR`: Code execution failed and raised an exception
    """

    EXPRESSION = 0
    STATEMENT = 1
    ERROR = 2


@dataclass
class Result:
    code: str
    payload: ResultPayload
    stdout: str
    type: ExecutionType
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def output(self) -> str:
        match self.type:
            case ExecutionType.EXPRESSION:
                value = repr(self.payload)

                if (
                    self.payload is not None
                    and not isinstance(self.payload, Exception)
                    and hasattr(self.payload, "__iter__")
                    and not isinstance(self.payload, str | dict)
                ):
                    # Format querysets and lists nicely
                    try:
                        items = list(self.payload)
                        if len(items) == 0:
                            value = "Empty queryset/list"
                        elif len(items) > 10:
                            formatted = "\n".join(repr(item) for item in items[:10])
                            value = f"{formatted}\n... and {len(items) - 10} more items"
                        else:
                            value = "\n".join(repr(item) for item in items)
                    except Exception:
                        pass
                return self.stdout + value if self.stdout else value
            case ExecutionType.STATEMENT:
                return self.stdout if self.stdout else "OK"
            case ExecutionType.ERROR:
                error_type = type(self.payload).__name__
                tb = traceback.format_exc()

                # Try to extract just the relevant part of traceback
                tb_lines = tb.split("\n")
                relevant_tb = "\n".join(
                    line for line in tb_lines if "mcp_django_shell" not in line
                )

                return f"{error_type}: {str(self.payload)}\n\nTraceback:\n{relevant_tb}"
