from __future__ import annotations

import logging
from typing import Annotated

from fastmcp import Context
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .code import filter_existing_imports
from .code import parse_code
from .core import django_shell
from .output import DjangoShellOutput
from .output import ErrorOutput

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="Shell",
    instructions="Execute Python code in a stateful Django shell or reset the session. Session state persists between calls - imports and variables are maintained. Use for ORM queries, model exploration, and testing. Reset when you need a fresh start. Only synchronous operations supported.",
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
        "Python code to be executed inside the Django shell session (required for 'execute' action)",
    ],
    imports: Annotated[
        str | None,
        "Optional import statements to execute before running the main code. Should contain all necessary imports for the code to run successfully, such as 'from django.contrib.auth.models import User\\nfrom myapp.models import MyModel'",
    ] = None,
) -> DjangoShellOutput | str:
    """Execute Python code in a stateful Django shell session.

    Django is pre-configured and ready to use with your project. You can import and use any Django
    models, utilities, or Python libraries as needed. The session maintains state between calls, so
    variables and imports persist across executions.

    Useful exploration commands:
    - To explore available models, use `django.apps.apps.get_models()`.
    - For configuration details, use `django.conf.settings`.

    **NOTE**: that only synchronous Django ORM operations are supported - use standard methods like
    `.filter()` and `.get()` rather than their async counterparts (`.afilter()`, `.aget()`).
    """

    logger.info(
        "django_shell execute action called - request_id: %s, client_id: %s, code: %s, imports: %s",
        ctx.request_id,
        ctx.client_id or "unknown",
        (code[:100] + "..." if len(code) > 100 else code).replace("\n", "\\n"),
        (imports[:50] + "..." if imports and len(imports) > 50 else imports or "None"),
    )
    logger.debug(
        "Full code for django_shell - request_id: %s: %s", ctx.request_id, code
    )
    if imports:
        logger.debug(
            "Imports for django_shell - request_id: %s: %s",
            ctx.request_id,
            imports,
        )

        filtered_imports = filter_existing_imports(imports, django_shell.globals)
        if filtered_imports.strip():
            code = f"{filtered_imports}\n{code}"

    parsed_code, setup, code_type = parse_code(code)

    try:
        result = await django_shell.execute(parsed_code, setup, code_type)
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
        title="Reset Django Shell Session", destructiveHint=True, openWorldHint=True
    ),
    tags={SHELL_TOOLSET},
)
async def reset(ctx: Context) -> str:
    """Reset the Django shell session, clearing all variables and history.

    Use this when you want to start fresh or if the session state becomes corrupted.
    """

    logger.info(
        "django_shell reset action called - request_id: %s, client_id: %s",
        ctx.request_id,
        ctx.client_id or "unknown",
    )
    await ctx.debug("Django shell session reset")

    django_shell.reset()

    logger.debug(
        "Django shell session reset completed - request_id: %s", ctx.request_id
    )

    return "Django shell session has been reset. All previously set variables and history cleared."
