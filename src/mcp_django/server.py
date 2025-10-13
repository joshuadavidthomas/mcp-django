from __future__ import annotations

import logging
from typing import Annotated

from django.apps import apps
from fastmcp import Context
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .code import filter_existing_imports
from .code import parse_code
from .output import DjangoShellOutput
from .output import ErrorOutput
from .resources import AppResource
from .resources import ModelResource
from .resources import ProjectResource
from .routing import RouteSchema
from .routing import ViewMethod
from .routing import filter_routes
from .routing import get_all_routes
from .shell import DjangoShell

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="Django",
    instructions="""Provides Django resource endpoints for project exploration and a stateful shell environment for executing Python code.

RESOURCES:
Use resources for orientation. Resources provide precise coordinates (import paths, file
locations) to avoid exploration overhead.

- django://project - Python/Django environment metadata (versions, settings, database config)
- django://apps - All Django apps with their file paths
- django://models - All models with import paths and source locations

TOOLS:
The shell maintains state between calls - imports and variables persist. Use django_shell_reset to
clear state when variables get messy or you need a fresh start.

- list_routes - List all URL routes with filtering by method, name, or pattern
- shell - Execute Python code in a stateful Django shell
- shell_reset - Reset the shell session

EXAMPLES:
The pattern: Resource → Import Path → Shell Operation. Resources provide coordinates, shell does
the work.

- Starting fresh? → Check django://project to understand environment and available apps
- Need information about a model? → Check django://models → Get import path →
  `from app.models import ModelName` in django_shell
- Need app structure? → Check django://apps for app labels and paths → Use paths in django_shell
- Need to query data? → Get model from django://models → Import in django_shell → Run queries
- Need to find a URL route? → Use list_routes with filters to find specific routes
""",
)


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


django_shell = DjangoShell()


@mcp.tool(
    annotations=ToolAnnotations(
        title="Django Shell", destructiveHint=True, openWorldHint=True
    ),
)
async def shell(
    ctx: Context,
    code: Annotated[str, "Python code to be executed inside the Django shell session"],
    imports: Annotated[
        str | None,
        "Optional import statements to execute before running the main code. Should contain all necessary imports for the code to run successfully, such as 'from django.contrib.auth.models import User\\nfrom myapp.models import MyModel'",
    ] = None,
) -> DjangoShellOutput:
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
        "django_shell tool called - request_id: %s, client_id: %s, code: %s, imports: %s",
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
            "Imports for django_shell - request_id: %s: %s", ctx.request_id, imports
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
        title="Reset Django Shell Session", destructiveHint=True, idempotentHint=True
    ),
)
async def shell_reset(ctx: Context) -> str:
    """Reset the Django shell session, clearing all variables and history.

    Use this when you want to start fresh or if the session state becomes corrupted.
    """
    logger.info(
        "django_shell_reset tool called - request_id: %s, client_id: %s",
        ctx.request_id,
        ctx.client_id or "unknown",
    )
    await ctx.debug("Django shell session reset")

    django_shell.reset()

    logger.debug(
        "Django shell session reset completed - request_id: %s", ctx.request_id
    )

    return "Django shell session has been reset. All previously set variables and history cleared."


@mcp.tool(
    annotations=ToolAnnotations(
        title="List Django Routes", readOnlyHint=True, idempotentHint=True
    ),
)
async def list_routes(
    ctx: Context,
    method: Annotated[
        ViewMethod | None,
        "Filter routes by HTTP method (e.g., 'GET', 'POST'). Uses contains matching - returns routes that support this method.",
    ] = None,
    name: Annotated[
        str | None,
        "Filter routes by name. Uses contains matching - returns routes whose name contains this string.",
    ] = None,
    pattern: Annotated[
        str | None,
        "Filter routes by URL pattern. Uses contains matching - returns routes whose pattern contains this string.",
    ] = None,
) -> list[RouteSchema]:
    """List all Django URL routes with optional filtering.

    Returns comprehensive route information including URL patterns, view details,
    HTTP methods, namespaces, and URL parameters. All filters use contains matching
    and are AND'd together.

    Examples:
    - list_routes() - Get all routes
    - list_routes(method="GET") - Get all routes accepting GET requests
    - list_routes(pattern="admin") - Get all admin routes
    - list_routes(name="blog") - Get all routes with "blog" in the name
    """
    logger.info(
        "list_routes tool called - request_id: %s, client_id: %s, method: %s, name: %s, pattern: %s",
        ctx.request_id,
        ctx.client_id or "unknown",
        method,
        name,
        pattern,
    )

    all_routes = get_all_routes()
    filtered = filter_routes(all_routes, method=method, name=name, pattern=pattern)

    logger.debug(
        "list_routes completed - request_id: %s, total_routes: %d, filtered_routes: %d",
        ctx.request_id,
        len(all_routes),
        len(filtered),
    )

    return filtered
