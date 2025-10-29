from __future__ import annotations

import asyncio
import logging
from typing import Annotated
from typing import Any

from django.apps import apps
from fastmcp import Context
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .resources import AppResource
from .resources import ModelResource
from .resources import ProjectResource
from .routing import RouteSchema
from .routing import ViewMethod
from .routing import filter_routes
from .routing import get_all_routes
from .toolsets import TOOLSETS

logger = logging.getLogger(__name__)


class DjangoMCP:
    NAME = "Django"
    INSTRUCTIONS = "Django ecosystem MCP server providing comprehensive project introspection, stateful code execution, and development tools. Supports exploring project structure, analyzing configurations, executing Python in persistent sessions, and accessing Django ecosystem resources."

    def __init__(self) -> None:
        instructions = [self.INSTRUCTIONS]

        instructions.append("## Available Toolsets")
        for toolset_server in TOOLSETS.values():
            instructions.append(f"### {toolset_server.name}")
            if toolset_server.instructions:
                instructions.append(toolset_server.instructions)

        self._server = FastMCP(name=self.NAME, instructions="\n\n".join(instructions))

    @property
    def server(self) -> FastMCP:
        return self._server

    async def initialize(self) -> None:
        for toolset_prefix, toolset_server in TOOLSETS.items():
            await self._server.import_server(toolset_server, prefix=toolset_prefix)

    def run(self, **kwargs: Any) -> None:  # pragma: no cover
        asyncio.run(self.initialize())
        self._server.run(**kwargs)


mcp = DjangoMCP()


@mcp.server.resource(
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


@mcp.server.resource(
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


@mcp.server.resource(
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
