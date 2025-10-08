from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from django.apps import apps
from fastmcp import Context
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .resources import AppResource
from .resources import ModelResource
from .resources import ProjectResource
from .shell.code import filter_existing_imports
from .shell.code import parse_code
from .shell.output import DjangoShellOutput
from .shell.output import ErrorOutput
from .shell.shell import DjangoShell

logger = logging.getLogger(__name__)
shell = DjangoShell()

INSTRUCTIONS = """Provides Django resource endpoints for project exploration and a stateful shell environment.

RESOURCES:
Use resources for orientation. Resources provide precise coordinates (import paths, file
locations) to avoid exploration overhead.

- django://project - Python/Django environment metadata (versions, settings, database config)
- django://apps - All Django apps with their file paths
- django://models - All models with import paths and source locations

TOOLS:
The shell maintains state between calls - imports and variables persist. Use shell_django_reset to
clear state when variables get messy or you need a fresh start.

- shell - Execute Python code in a stateful Django shell
- shell_reset - Reset the shell session

EXAMPLES:
The pattern: Resource → Import Path → Shell Operation. Resources provide coordinates, shell does
the work.

- Starting fresh? → Check django://project to understand environment and available apps
- Need information about a model? → Check django://models → Get import path →
  `from app.models import ModelName` in shell_django_shell
- Need app structure? → Check django://apps for app labels and paths → Use paths in shell_django_shell
- Need to query data? → Get model from django://models → Import in shell_django_shell → Run queries
"""


async def create_mcp() -> FastMCP:
    mcp = FastMCP(name="Django", instructions=INSTRUCTIONS)

    return mcp


mcp = asyncio.run(create_mcp())


@mcp.resource(
    "django://project",
    name="Django Project Information",
    mime_type="application/json",
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
def get_project() -> ProjectResource:
    """Get comprehensive project information including Python environment and Django configuration.

    Use this to understand the project's runtime environment, installed apps, and database
    configuration.
    """
    return ProjectResource.from_env()


@mcp.resource(
    "django://apps",
    name="Installed Django Apps",
    mime_type="application/json",
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
def get_apps() -> list[AppResource]:
    """Get a list of all installed Django applications with their models.

    Use this to explore the project structure and available models without executing code.
    """
    return [AppResource.from_app(app) for app in apps.get_app_configs()]


@mcp.resource(
    "django://models",
    name="Django Models",
    mime_type="application/json",
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
def get_models() -> list[ModelResource]:
    """Get detailed information about all Django models in the project.

    Use this for quick model introspection without shell access.
    """
    return [ModelResource.from_model(model) for model in apps.get_models()]


@mcp.tool(
    name="shell",
    annotations=ToolAnnotations(
        title="Django Shell", destructiveHint=True, openWorldHint=True
    ),
)
async def django_shell(
    ctx: Context,
    code: Annotated[str, "Python code to be executed inside the Django shell session"],
    imports: Annotated[
        str | None,
        "Optional import statements to execute before running the main code. Should contain all necessary imports for the code to run successfully, such as 'from django.contrib.auth.models import User\\nfrom myapp.models import MyModel'",
    ] = None,
) -> DjangoShellOutput:
    """Execute Python code in a stateful Django shell session."""
    logger.info(
        "shell tool called - request_id: %s, client_id: %s, code: %s, imports: %s",
        ctx.request_id,
        ctx.client_id or "unknown",
        (code[:100] + "..." if len(code) > 100 else code).replace("\n", "\\n"),
        (imports[:50] + "..." if imports and len(imports) > 50 else imports or "None"),
    )
    logger.debug("Full code for shell - request_id: %s: %s", ctx.request_id, code)
    if imports:
        logger.debug("Imports for shell - request_id: %s: %s", ctx.request_id, imports)

        filtered_imports = filter_existing_imports(imports, shell.globals)
        if filtered_imports.strip():
            code = f"{filtered_imports}\n{code}"

    parsed_code, setup, code_type = parse_code(code)

    try:
        result = await shell.execute(parsed_code, setup, code_type)
        output = DjangoShellOutput.from_result(result)

        logger.debug(
            "shell execution completed - request_id: %s, result type: %s",
            ctx.request_id,
            type(result).__name__,
        )
        if isinstance(output.output, ErrorOutput):
            await ctx.debug(f"Execution failed: {output.output.exception.message}")

        return output

    except Exception as exc:  # pragma: no cover - re-raised for FastMCP handling
        logger.error(
            "Unexpected error in shell tool - request_id: %s: %s",
            ctx.request_id,
            exc,
            exc_info=True,
        )
        raise


@mcp.tool(
    name="shell_reset",
    annotations=ToolAnnotations(
        title="Reset Django Shell Session", destructiveHint=True, idempotentHint=True
    ),
)
async def django_shell_reset(ctx: Context) -> str:
    """Reset the Django shell session, clearing all variables and history."""
    logger.info(
        "shell_reset tool called - request_id: %s, client_id: %s",
        ctx.request_id,
        ctx.client_id or "unknown",
    )
    await ctx.debug("Django shell session reset")

    shell.reset()

    logger.debug(
        "Django shell session reset completed - request_id: %s", ctx.request_id
    )

    return "Django shell session has been reset. All previously set variables and history cleared."
