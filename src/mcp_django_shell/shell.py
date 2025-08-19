from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)


class DjangoShell:
    def __init__(self):
        logger.debug("Initializing %s", self.__class__.__name__)

        from django import setup
        from django.apps import apps

        if not apps.ready:  # pragma: no cover
            logger.info("Django not initialized, running django.setup()")

            setup()

            logger.debug("Django setup completed")
        else:
            logger.debug("Django already initialized, skipping setup")

        self.globals: dict[str, Any] = {}
        self.history: list[Result] = []

        logger.info("Shell initialized successfully")

    def reset(self):
        logger.info("Shell reset - clearing globals and history")

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
        code_preview = (code[:100] + "..." if len(code) > 100 else code).replace(
            "\n", "\\n"
        )
        logger.info("Executing code: %s", code_preview)

        stdout = StringIO()
        stderr = StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                code, setup, code_type = parse_code(code)

                logger.debug(
                    "Execution type: %s, has setup: %s", code_type, bool(setup)
                )
                logger.debug(
                    "Code to execute: %s",
                    code[:200] + "..." if len(code) > 200 else code,
                )

                # Execute setup, if any (only applicable to expressions)
                if setup:
                    logger.debug(
                        "Setup code: %s",
                        setup[:200] + "..." if len(setup) > 200 else setup,
                    )

                    exec(setup, self.globals)

                match code_type:
                    case "expression":
                        value = eval(code, self.globals)

                        logger.debug(
                            "Expression executed successfully, result type: %s",
                            type(value).__name__,
                        )

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

                        logger.debug("Statement executed successfully")

                        return self.save_result(
                            StatementResult(
                                code=code,
                                stdout=stdout.getvalue(),
                                stderr=stderr.getvalue(),
                            )
                        )

            except Exception as e:
                logger.error(
                    "Exception during code execution: %s - Code: %s",
                    f"{type(e).__name__}: {e}",
                    code_preview,
                )
                logger.debug("Full traceback for error:", exc_info=True)

                return self.save_result(
                    ErrorResult(
                        code=code,
                        exception=e,
                        stdout=stdout.getvalue(),
                        stderr=stderr.getvalue(),
                    )
                )

    def save_result(self, result: Result) -> Result:
        self.history.append(result)
        return result


def parse_code(code: str) -> tuple[str, str, Literal["expression", "statement"]]:
    """Determine how code should be executed.

    Returns:
        A tuple (main_code, setup_code, code_type), where:
        - main_code: The code to evaluate (expression) or execute (statement)
        - setup_code: Lines to execute before evaluating expressions (empty for statements)
        - code_type: "expression" or "statement"
    """

    def can_eval(code: str) -> bool:
        try:
            compile(code, "<stdin>", "eval")
            return True
        except SyntaxError:
            return False

    if can_eval(code):
        return code, "", "expression"

    lines = code.strip().splitlines()
    last_line = lines[-1] if lines else ""

    if can_eval(last_line):
        setup_code = "\n".join(lines[:-1])
        return last_line, setup_code, "expression"

    return code, "", "statement"


@dataclass
class ExpressionResult:
    code: str
    value: Any
    stdout: str
    stderr: str
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        logger.debug(
            "%s created - value type: %s",
            self.__class__.__name__,
            type(self.value).__name__,
        )
        logger.debug("%s.value: %s", self.__class__.__name__, repr(self.value)[:200])
        if self.stdout:
            logger.debug("%s.stdout: %s", self.__class__.__name__, self.stdout[:200])
        if self.stderr:
            logger.debug("%s.stderr: %s", self.__class__.__name__, self.stderr[:200])
        logger.debug(
            "%s output (for LLM): %s", self.__class__.__name__, self.output[:500]
        )

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

    def __post_init__(self):
        logger.debug("%s created", self.__class__.__name__)
        if self.stdout:
            logger.debug("%s.stdout: %s", self.__class__.__name__, self.stdout[:200])
        if self.stderr:
            logger.debug("%s.stderr: %s", self.__class__.__name__, self.stderr[:200])
        logger.debug(
            "%s output (for LLM): %s", self.__class__.__name__, self.output[:500]
        )

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

    def __post_init__(self):
        logger.debug(
            "%s created - exception type: %s",
            self.__class__.__name__,
            type(self.exception).__name__,
        )
        logger.debug("%s.message: %s", self.__class__.__name__, str(self.exception))
        if self.stdout:
            logger.debug("%s.stdout: %s", self.__class__.__name__, self.stdout[:200])
        if self.stderr:
            logger.debug("%s.stderr: %s", self.__class__.__name__, self.stderr[:200])
        logger.debug(
            "%s output (filtered for LLM): %s",
            self.__class__.__name__,
            self.output[:500],
        )

    @property
    def output(self) -> str:
        error_type = self.exception.__class__.__name__

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
