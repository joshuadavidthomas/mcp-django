from __future__ import annotations

import logging
from typing import Annotated

from fastmcp import Context
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .code import parse_code
from .core import django_shell
from .output import DjangoShellOutput
from .output import ErrorOutput

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="Shell",
    instructions="Execute Python code in a stateless Django shell. Each execution uses fresh state - no variables or imports persist between calls. This ensures code changes always take effect. Use for ORM queries, model exploration, and testing. Export session history to save your work. Only synchronous operations supported.",
)

SHELL_TOOLSET = "shell"


@mcp.tool(
    annotations=ToolAnnotations(
        title="Django Shell", destructiveHint=True, openWorldHint=True
    ),
    tags={SHELL_TOOLSET},
)
async def execute(
    ctx: Context,
    code: Annotated[
        str,
        "Python code to be executed inside the Django shell session",
    ],
) -> DjangoShellOutput | str:
    """Execute Python code in a stateless Django shell session.

    Django is pre-configured and ready to use with your project. You can import and use any Django
    models, utilities, or Python libraries as needed. Each execution uses fresh state, so code changes
    always take effect immediately.

    Useful exploration commands:
    - To explore available models, use `django.apps.apps.get_models()`.
    - For configuration details, use `django.conf.settings`.

    **NOTE**: that only synchronous Django ORM operations are supported - use standard methods like
    `.filter()` and `.get()` rather than their async counterparts (`.afilter()`, `.aget()`).
    """

    logger.info(
        "django_shell execute action called - request_id: %s, client_id: %s, code: %s",
        ctx.request_id,
        ctx.client_id or "unknown",
        (code[:100] + "..." if len(code) > 100 else code).replace("\n", "\\n"),
    )
    logger.debug(
        "Full code for django_shell - request_id: %s: %s", ctx.request_id, code
    )

    parsed_code = parse_code(code)

    try:
        result = await django_shell.execute(parsed_code)
        output = DjangoShellOutput.from_result(result)

        logger.debug(
            "django_shell execution completed - request_id: %s, result type: %s",
            ctx.request_id,
            type(result).__name__,
        )
        if isinstance(output.output, ErrorOutput):
            await ctx.debug(f"Execution failed: {output.output.exception.message}")

        return output

    except Exception as e:
        logger.error(
            "Unexpected error in django_shell tool - request_id: %s: %s",
            ctx.request_id,
            e,
            exc_info=True,
        )
        raise


@mcp.tool(
    annotations=ToolAnnotations(
        title="Export Django Shell History",
        openWorldHint=True,
    ),
    tags={SHELL_TOOLSET},
)
async def export_history(
    ctx: Context,
    filename: Annotated[
        str | None,
        "Optional filename to save to (relative to project dir). If None, returns script as string.",
    ] = None,
) -> str:
    """Export shell session history as a Python script.

    Returns a Python script containing all successfully executed code from the
    current session. Failed execution attempts are excluded. Useful for saving
    debugging sessions or creating reproducible scripts from interactive exploration.

    The exported script will deduplicate import statements at the top of the script.
    Execution results and output are not included in the export.

    If filename is provided, the script is saved to a file in the project directory.
    If no filename is provided, the script content is returned as a string.
    """
    logger.info(
        "export_history called - request_id: %s, client_id: %s, filename: %s",
        ctx.request_id,
        ctx.client_id or "unknown",
        filename or "None",
    )

    try:
        result = django_shell.export_history(filename=filename)

        if filename:
            await ctx.debug(f"Exported history to {filename}")
        else:
            await ctx.debug("Exported history as string")

        logger.debug(
            "export_history completed - request_id: %s",
            ctx.request_id,
        )

        return result

    except Exception as e:
        logger.error(
            "Error exporting history - request_id: %s: %s",
            ctx.request_id,
            e,
            exc_info=True,
        )
        raise


@mcp.tool(
    annotations=ToolAnnotations(
        title="Clear Django Shell History",
        destructiveHint=True,
    ),
    tags={SHELL_TOOLSET},
)
async def clear_history(ctx: Context) -> str:
    """Clear the Django shell session history.

    Use this when you want to start with a clean history for the next export,
    or when the history has become cluttered with exploratory code. This is
    similar to the old reset() but only clears the execution history, not the
    execution state (which is already fresh for each call).
    """
    logger.info(
        "clear_history called - request_id: %s, client_id: %s",
        ctx.request_id,
        ctx.client_id or "unknown",
    )

    await ctx.debug("Django shell history cleared")

    django_shell.clear_history()

    logger.debug(
        "clear_history completed - request_id: %s",
        ctx.request_id,
    )

    return "Django shell history has been cleared."
