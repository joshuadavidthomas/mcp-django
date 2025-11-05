from __future__ import annotations

import logging
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from io import StringIO

from asgiref.sync import sync_to_async
from django.core.management import call_command
from django.core.management import get_commands
from pydantic import BaseModel
from pydantic import ConfigDict

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    command: str
    args: tuple[str, ...]
    options: dict[str, str | int | bool]
    stdout: str
    stderr: str
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        logger.debug(
            "%s created for command: %s", self.__class__.__name__, self.command
        )
        if self.stdout:
            logger.debug("%s.stdout: %s", self.__class__.__name__, self.stdout[:200])
        if self.stderr:
            logger.debug("%s.stderr: %s", self.__class__.__name__, self.stderr[:200])


@dataclass
class CommandErrorResult:
    command: str
    args: tuple[str, ...]
    options: dict[str, str | int | bool]
    exception: Exception
    stdout: str
    stderr: str
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        logger.debug(
            "%s created for command: %s - exception type: %s",
            self.__class__.__name__,
            self.command,
            type(self.exception).__name__,
        )
        logger.debug("%s.message: %s", self.__class__.__name__, str(self.exception))
        if self.stdout:
            logger.debug("%s.stdout: %s", self.__class__.__name__, self.stdout[:200])
        if self.stderr:
            logger.debug("%s.stderr: %s", self.__class__.__name__, self.stderr[:200])


Result = CommandResult | CommandErrorResult


class ManagementCommandOutput(BaseModel):
    status: str  # "success" or "error"
    command: str
    args: list[str]
    options: dict[str, str | int | bool]
    stdout: str
    stderr: str
    exception: ExceptionInfo | None = None

    @classmethod
    def from_result(cls, result: Result) -> ManagementCommandOutput:
        match result:
            case CommandResult():
                return cls(
                    status="success",
                    command=result.command,
                    args=list(result.args),
                    options=result.options,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exception=None,
                )
            case CommandErrorResult():
                return cls(
                    status="error",
                    command=result.command,
                    args=list(result.args),
                    options=result.options,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exception=ExceptionInfo(
                        type=type(result.exception).__name__,
                        message=str(result.exception),
                    ),
                )


class ExceptionInfo(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    type: str
    message: str


class ManagementCommandExecutor:
    async def execute(
        self,
        command: str,
        args: list[str] | None = None,
        options: dict[str, str | int | bool] | None = None,
    ) -> Result:
        """Execute a Django management command asynchronously.

        Args:
            command: The management command name (e.g., 'migrate', 'check')
            args: Positional arguments for the command
            options: Keyword options for the command

        Returns:
            CommandResult if successful, CommandErrorResult if an exception occurred
        """
        return await sync_to_async(self._execute)(command, args, options)

    def _execute(
        self,
        command: str,
        args: list[str] | None = None,
        options: dict[str, str | int | bool] | None = None,
    ) -> Result:
        """Execute a Django management command synchronously.

        Captures stdout and stderr from the command execution.

        Args:
            command: The management command name
            args: Positional arguments for the command
            options: Keyword options for the command

        Returns:
            CommandResult if successful, CommandErrorResult if an exception occurred
        """
        args = args or []
        options = options or {}

        args_tuple = tuple(args)
        options_dict = dict(options)

        logger.info(
            "Executing management command: %s with args=%s, options=%s",
            command,
            args_tuple,
            options_dict,
        )

        stdout = StringIO()
        stderr = StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                call_command(command, *args_tuple, **options_dict)

                logger.debug("Management command executed successfully: %s", command)

                return CommandResult(
                    command=command,
                    args=args_tuple,
                    options=options_dict,
                    stdout=stdout.getvalue(),
                    stderr=stderr.getvalue(),
                )

            except Exception as e:
                logger.error(
                    "Exception during management command execution: %s - Command: %s",
                    f"{type(e).__name__}: {e}",
                    command,
                )
                logger.debug("Full traceback for error:", exc_info=True)

                return CommandErrorResult(
                    command=command,
                    args=args_tuple,
                    options=options_dict,
                    exception=e,
                    stdout=stdout.getvalue(),
                    stderr=stderr.getvalue(),
                )


management_command_executor = ManagementCommandExecutor()


class CommandInfo(BaseModel):
    name: str
    app_name: str


def get_management_commands() -> list[CommandInfo]:
    """Get list of all available Django management commands.

    Returns a list of management commands with their app origins,
    sorted alphabetically by command name.

    Returns:
        List of CommandInfo objects containing command name and source app.
    """
    logger.info("Fetching available management commands")

    commands = get_commands()
    command_list = [
        CommandInfo(name=name, app_name=app_name)
        for name, app_name in sorted(commands.items())
    ]

    logger.debug("Found %d management commands", len(command_list))

    return command_list
