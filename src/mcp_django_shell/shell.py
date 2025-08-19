from __future__ import annotations

import traceback
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from io import StringIO
from typing import Any
from typing import Literal

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
        stdout = StringIO()
        stderr = StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                code, setup, code_type = self.parse_code(code)

                # Execute setup, if any (only applicable to expressions)
                if setup:
                    exec("\n".join(setup), self.globals)

                match code_type:
                    case "expression":
                        value = eval(code, self.globals)
                        return self.save_result(
                            ExpressionResult(
                                code=code,
                                value=value,
                                stdout=stdout.getvalue(),
                                stderr=stderr.getvalue(),
                            )
                        )
                    case "statement":
                        exec(code, self.globals)
                        return self.save_result(
                            StatementResult(
                                code=code,
                                stdout=stdout.getvalue(),
                                stderr=stderr.getvalue(),
                            )
                        )

            except Exception as e:
                return self.save_result(
                    ErrorResult(
                        code=code,
                        exception=e,
                        stdout=stdout.getvalue(),
                        stderr=stderr.getvalue(),
                    )
                )

    def parse_code(
        self, code: str
    ) -> tuple[str, list[str], Literal["expression", "statement"]]:
        """Determine how code should be executed.

        Returns:
            (main_code, setup_code, code_type)
        """

        def can_eval(code: str) -> bool:
            try:
                compile(code, "<stdin>", "eval")
                return True
            except SyntaxError:
                return False

        if can_eval(code):
            return code, [], "expression"

        lines = code.strip().splitlines()
        last_line = lines[-1] if lines else ""

        if can_eval(last_line):
            return last_line, lines[:-1], "expression"

        return code, [], "statement"

    def save_result(self, result: Result) -> Result:
        self.history.append(result)
        return result


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
            and hasattr(self.value, "__iter__")
            and not isinstance(self.value, str | dict)
        ):
            # Format querysets and lists nicely, overwriting `value` if successful
            try:
                items = list(self.value)
                match len(items):
                    case 0:
                        value = "Empty queryset/list"
                    case n if n > 10:
                        formatted = "\n".join(repr(item) for item in items[:10])
                        value = f"{formatted}\n... and {n - 10} more items"
                    case _:
                        value = "\n".join(repr(item) for item in items)
            except Exception:
                # If iteration fails for any reason, just use the repr
                pass

        return self.stdout + value or value


@dataclass
class StatementResult:
    code: str
    stdout: str
    stderr: str
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def output(self) -> str:
        return self.stdout or "OK"


@dataclass
class ErrorResult:
    code: str
    exception: Exception
    stdout: str
    stderr: str
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def output(self) -> str:
        error_type = self.exception.__class__.__name__

        # Format the stored exception's traceback
        tb_str = "".join(
            traceback.format_exception(
                type(self.exception), self.exception, self.exception.__traceback__
            )
        )

        # Filter out framework lines
        tb_lines = tb_str.splitlines()
        relevant_tb = "\n".join(
            line for line in tb_lines if "mcp_django_shell" not in line
        )

        return f"{error_type}: {self.exception}\n\nTraceback:\n{relevant_tb}"


Result = ExpressionResult | StatementResult | ErrorResult
