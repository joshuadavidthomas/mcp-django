from __future__ import annotations

import ast
import logging
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any
from typing import Literal

import django
from asgiref.sync import sync_to_async
from django.apps import apps

logger = logging.getLogger(__name__)


class DjangoShell:
    def __init__(self):
        logger.debug("Initializing %s", self.__class__.__name__)

        if not apps.ready:  # pragma: no cover
            logger.info("Django not initialized, running django.setup()")

            django.setup()

            logger.debug("Django setup completed")
        else:
            logger.debug("Django already initialized, skipping setup")

        self.history: list[Result] = []

        logger.info("Shell initialized successfully")

    def clear_history(self):
        """Clear the execution history.

        Use this when you want to start with a clean history for the next
        export, or when the history has become cluttered with exploratory code.
        """
        logger.info("Clearing shell history - previous entries: %s", len(self.history))
        self.history = []

    def export_history(
        self,
        filename: str | None = None,
        include_errors: bool = False,
    ) -> str:
        """Export shell session history as a Python script.

        Args:
            filename: Optional filename to save to (relative to project dir).
                      If None, returns script content as string.
            include_errors: Include failed attempts in export

        Returns:
            If filename is None: The Python script as a string
            If filename provided: Confirmation message with preview
        """
        logger.info(
            "Exporting history - entries: %s, filename: %s",
            len(self.history),
            filename or "None",
        )

        if not self.history:
            return "# No history to export\n"

        # Collect imports and code
        imports_set = set()
        steps = []

        for i, result in enumerate(self.history, 1):
            # Skip errors if not including them
            if isinstance(result, ErrorResult) and not include_errors:
                continue

            code = result.code

            # Extract and deduplicate imports
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        imports_set.add(ast.unparse(node))
            except SyntaxError:
                pass  # If can't parse, include code as-is

            # Add step comment
            steps.append(f"# Step {i}")
            steps.append(code)
            steps.append("")  # Blank line between steps

        # Build script
        script_parts = [
            "# Django Shell Session Export",
            f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        if imports_set:
            script_parts.extend(sorted(imports_set))
            script_parts.append("")

        script_parts.extend(steps)

        script = "\n".join(script_parts)

        # Save to file if requested
        if filename:
            # Security: only allow relative paths
            if Path(filename).is_absolute():
                raise ValueError("Absolute paths not allowed for security reasons")

            # Ensure .py extension
            if not filename.endswith(".py"):
                filename += ".py"

            filepath = Path(filename)

            # Write file
            filepath.write_text(script)

            logger.info("Exported history to file: %s", filepath)

            # Return confirmation with preview
            line_count = len(script.split("\n"))
            preview_lines = script.split("\n")[:20]
            preview = "\n".join(preview_lines)
            if line_count > 20:
                preview += f"\n... ({line_count - 20} more lines)"

            return f"Exported {line_count} lines to {filename}\n\n{preview}"

        # Return script content
        return script

    async def execute(
        self, code: str, setup: str, code_type: Literal["expression", "statement"]
    ) -> Result:
        """Execute Python code in the Django shell context (async wrapper).

        This async wrapper enables use from FastMCP and other async contexts.
        It delegates to `_execute()` for the actual execution logic.

        Note: FastMCP requires async methods, but Django ORM operations are
        synchronous. The `@sync_to_async` decorator runs the synchronous
        `_execute()` method in a thread pool to avoid `SynchronousOnlyOperation`
        errors.
        """

        return await sync_to_async(self._execute)(code, setup, code_type)

    def _execute(
        self, code: str, setup: str, code_type: Literal["expression", "statement"]
    ) -> Result:
        """Execute Python code in the Django shell context (synchronous).

        Each execution uses fresh globals for stateless behavior. This ensures
        code changes always take effect and no stale modules persist.

        Note: This synchronous method contains the actual execution logic.
        Use `execute()` for async contexts or `_execute()` for sync/testing.
        """

        code_preview = (code[:100] + "..." if len(code) > 100 else code).replace(
            "\n", "\\n"
        )
        logger.info("Executing code: %s", code_preview)

        stdout = StringIO()
        stderr = StringIO()

        # Use fresh globals for THIS execution only (stateless)
        execution_globals: dict[str, Any] = {}

        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                logger.debug(
                    "Execution type: %s, has setup: %s", code_type, bool(setup)
                )
                logger.debug(
                    "Code to execute: %s",
                    code[:200] + "..." if len(code) > 200 else code,
                )

                if setup:
                    logger.debug(
                        "Setup code: %s",
                        setup[:200] + "..." if len(setup) > 200 else setup,
                    )

                    exec(setup, execution_globals)

                match code_type:
                    case "expression":
                        value = eval(code, execution_globals)

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
                        exec(code, execution_globals)

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


Result = ExpressionResult | StatementResult | ErrorResult

django_shell = DjangoShell()
