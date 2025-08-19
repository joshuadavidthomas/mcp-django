from __future__ import annotations

import traceback
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
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

        def save_result(result: Result) -> Result:
            self.history.append(result)
            return result

        stdout = StringIO()
        stderr = StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                # Try as single expression
                if can_eval(code):
                    payload = eval(code, self.globals)
                    return save_result(
                        ExpressionResult(
                            code=code,
                            value=payload,
                            stdout=stdout.getvalue(),
                            stderr=stderr.getvalue(),
                        )
                    )

                # Check for multi-line with final expression
                lines = code.strip().splitlines()
                last_line = lines[-1] if lines else ""

                if can_eval(last_line):
                    # Execute setup lines, eval last line
                    if len(lines) > 1:
                        exec("\n".join(lines[:-1]), self.globals)
                    payload = eval(last_line, self.globals)
                    return save_result(
                        ExpressionResult(
                            code=code,
                            value=payload,
                            stdout=stdout.getvalue(),
                            stderr=stderr.getvalue(),
                        )
                    )

                # Execute as pure statements
                exec(code, self.globals)
                return save_result(
                    StatementResult(
                        code=code, stdout=stdout.getvalue(), stderr=stderr.getvalue()
                    )
                )

            except Exception as e:
                return save_result(
                    ErrorResult(
                        code=code,
                        exception=e,
                        stdout=stdout.getvalue(),
                        stderr=stderr.getvalue(),
                    )
                )


@dataclass
class ExpressionResult:
    code: str
    value: Any
    stdout: str
    stderr: str
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def output(self) -> str:
        value = repr(self.value)

        if (
            self.value is not None
            and not isinstance(self.value, Exception)
            and hasattr(self.value, "__iter__")
            and not isinstance(self.value, str | dict)
        ):
            # Format querysets and lists nicely
            try:
                items = list(self.value)
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


@dataclass
class StatementResult:
    code: str
    stdout: str
    stderr: str
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def output(self) -> str:
        return self.stdout if self.stdout else "OK"


@dataclass
class ErrorResult:
    code: str
    exception: Exception
    stdout: str
    stderr: str
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def output(self) -> str:
        error_type = type(self.exception).__name__
        tb = traceback.format_exc()

        # Try to extract just the relevant part of traceback
        tb_lines = tb.split("\n")
        relevant_tb = "\n".join(
            line for line in tb_lines if "mcp_django_shell" not in line
        )

        return f"{error_type}: {str(self.exception)}\n\nTraceback:\n{relevant_tb}"


Result = ExpressionResult | StatementResult | ErrorResult
