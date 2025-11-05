from __future__ import annotations

import logging
from typing import Annotated

from fastmcp import Context
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .core import CommandInfo
from .core import ManagementCommandOutput
from .core import get_management_commands
from .core import management_command_executor

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="Management",
    instructions="Execute and discover Django management commands. Run commands with arguments and options, or list available commands to discover what's available in your project.",
)

MANAGEMENT_TOOLSET = "management"


@mcp.tool(
    name="execute_command",
    annotations=ToolAnnotations(
        title="Execute Django Management Command",
        destructiveHint=True,
        openWorldHint=True,
    ),
    tags={MANAGEMENT_TOOLSET},
)
async def execute_command(
    ctx: Context,
    command: Annotated[
        str,
        "Management command name (e.g., 'migrate', 'check', 'collectstatic')",
    ],
    args: Annotated[
        list[str] | None,
        "Positional arguments for the command",
    ] = None,
    options: Annotated[
        dict[str, str | int | bool] | None,
        "Keyword options for the command (use underscores for dashes, e.g., 'run_syncdb' for '--run-syncdb')",
    ] = None,
) -> ManagementCommandOutput:
    """Execute a Django management command.

    Calls Django's call_command() to run management commands. Arguments and options
    are passed directly to the command. Command output (stdout/stderr) is captured
    and returned.

    Examples:
    - Check for issues: command="check"
    - Show migrations: command="showmigrations", args=["myapp"]
    - Migrate with options: command="migrate", options={"verbosity": 2}
    - Check with tag: command="check", options={"tag": "security"}

    Note: Management commands can modify your database and project state. Use with
    caution, especially commands like migrate, flush, loaddata, etc.
    """
    logger.info(
        "management_command called - request_id: %s, client_id: %s, command: %s, args: %s, options: %s",
        ctx.request_id,
        ctx.client_id or "unknown",
        command,
        args,
        options,
    )

    try:
        result = await management_command_executor.execute(command, args, options)
        output = ManagementCommandOutput.from_result(result)

        logger.debug(
            "management_command completed - request_id: %s, status: %s",
            ctx.request_id,
            output.status,
        )

        if output.status == "error" and output.exception:
            await ctx.debug(
                f"Command failed: {output.exception.type}: {output.exception.message}"
            )

        return output

    except Exception as e:
        logger.error(
            "Unexpected error in management_command tool - request_id: %s: %s",
            ctx.request_id,
            e,
            exc_info=True,
        )
        raise


@mcp.tool(
    name="list_commands",
    annotations=ToolAnnotations(
        title="List Django Management Commands",
        readOnlyHint=True,
        idempotentHint=True,
    ),
    tags={MANAGEMENT_TOOLSET},
)
def list_commands(ctx: Context) -> list[CommandInfo]:
    """List all available Django management commands.

    Returns a list of all management commands available in the current Django
    project, including built-in Django commands and custom commands from
    installed apps. Each command includes its name and the app that provides it.

    Useful for discovering what commands are available before executing them
    with the execute_command tool.
    """
    logger.info(
        "list_management_commands called - request_id: %s, client_id: %s",
        ctx.request_id,
        ctx.client_id or "unknown",
    )

    commands = get_management_commands()

    logger.debug(
        "list_management_commands completed - request_id: %s, commands_count: %d",
        ctx.request_id,
        len(commands),
    )

    return commands
