from __future__ import annotations

import asyncio
import logging
from typing import Annotated
from typing import Any
from typing import Literal

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
from .shell import django_shell
from .toolsets import TOOLSETS

logger = logging.getLogger(__name__)


class DjangoMCP:
    NAME = "Django"
    INSTRUCTIONS = "Provides Django project exploration and management tools, including a stateful shell environment for executing Python code."

    def __init__(self) -> None:
        instructions = [self.INSTRUCTIONS]

        instructions.append("## Available Toolsets")
        for toolset_server in TOOLSETS.values():
            instructions.append(f"### {toolset_server.name}")
            if toolset_server.instructions:
                instructions.append(toolset_server.instructions)

        self._server = mcp = FastMCP(
            name=self.NAME, instructions="\n\n".join(instructions)
        )

    @property
    def server(self) -> FastMCP:
        return self._server

    async def initialize(self) -> None:
        for toolset_prefix, toolset_server in TOOLSETS.items():
            await self._server.import_server(toolset_server, prefix=toolset_prefix)

    def run(self, **kwargs: Any) -> None:  # pragma: no cover
        # CLI entry point - tested via management command integration tests
        asyncio.run(self.initialize())
        self._server.run(**kwargs)


mcp = DjangoMCP()


@mcp.server.tool(
    annotations=ToolAnnotations(
        title="Get Django Project Information",
        readOnlyHint=True,
        idempotentHint=True,
    ),
)
async def get_project(ctx: Context) -> ProjectResource:
    """Get comprehensive project information including Python environment and Django configuration.

    Returns metadata about the project's runtime environment, installed apps, and database
    configuration.
    """
    return ProjectResource.from_env()


@mcp.server.tool(
    annotations=ToolAnnotations(
        title="Get Installed Django Apps",
        readOnlyHint=True,
        idempotentHint=True,
    ),
)
async def get_apps(ctx: Context) -> list[AppResource]:
    """Get a list of all installed Django applications with their models.

    Use this to explore the project structure and available models without executing code.
    """
    return [AppResource.from_app(app) for app in apps.get_app_configs()]


@mcp.server.tool(
    annotations=ToolAnnotations(
        title="Get Django Models",
        readOnlyHint=True,
        idempotentHint=True,
    ),
)
async def get_models(ctx: Context) -> list[ModelResource]:
    """Get detailed information about all Django models in the project.

    Returns comprehensive model information including import paths, source locations,
    and field definitions.
    """
    return [ModelResource.from_model(model) for model in apps.get_models()]


@mcp.server.tool(
    annotations=ToolAnnotations(
        title="Django Shell", destructiveHint=True, openWorldHint=True
    ),
)
async def shell(
    ctx: Context,
    action: Annotated[
        Literal["execute", "reset"],
        "Action to perform: 'execute' (default) runs Python code, 'reset' clears the shell session",
    ] = "execute",
    code: Annotated[
        str | None,
        "Python code to be executed inside the Django shell session (required for 'execute' action)",
    ] = None,
    imports: Annotated[
        str | None,
        "Optional import statements to execute before running the main code. Should contain all necessary imports for the code to run successfully, such as 'from django.contrib.auth.models import User\\nfrom myapp.models import MyModel'",
    ] = None,
) -> DjangoShellOutput | str:
    """Execute Python code in a stateful Django shell session or reset the session.

    Django is pre-configured and ready to use with your project. You can import and use any Django
    models, utilities, or Python libraries as needed. The session maintains state between calls, so
    variables and imports persist across executions.

    Actions:
    - 'execute' (default): Run Python code in the shell session
    - 'reset': Clear all variables and imports from the session

    Useful exploration commands:
    - To explore available models, use `django.apps.apps.get_models()`.
    - For configuration details, use `django.conf.settings`.

    **NOTE**: that only synchronous Django ORM operations are supported - use standard methods like
    `.filter()` and `.get()` rather than their async counterparts (`.afilter()`, `.aget()`).
    """

    match action:
        case "reset":
            if code is not None:
                raise ValueError(
                    "Code parameter cannot be used with `'reset'` action. Use `action='execute'` to run code or omit the code parameter when resetting."
                )

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

        case "execute":
            if code is None:
                raise ValueError("Code parameter is required for 'execute' action")

            logger.info(
                "django_shell execute action called - request_id: %s, client_id: %s, code: %s, imports: %s",
                ctx.request_id,
                ctx.client_id or "unknown",
                (code[:100] + "..." if len(code) > 100 else code).replace("\n", "\\n"),
                (
                    imports[:50] + "..."
                    if imports and len(imports) > 50
                    else imports or "None"
                ),
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

                filtered_imports = filter_existing_imports(
                    imports, django_shell.globals
                )
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
                    await ctx.debug(
                        f"Execution failed: {output.output.exception.message}"
                    )

                return output

            except Exception as e:
                logger.error(
                    "Unexpected error in django_shell tool - request_id: %s: %s",
                    ctx.request_id,
                    e,
                    exc_info=True,
                )
                raise


@mcp.server.tool(
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
