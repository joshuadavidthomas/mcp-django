from __future__ import annotations

import asyncio
import logging
from importlib.util import find_spec

from django.apps import apps
from fastmcp import FastMCP

from .resources import AppResource
from .resources import ModelResource
from .resources import ProjectResource

logger = logging.getLogger(__name__)


async def create_mcp() -> FastMCP:
    instructions = [
        """Provides Django resource endpoints for project exploration.

RESOURCES:
Use resources for orientation. Resources provide precise coordinates (import paths, file
locations) to avoid exploration overhead.

- django://project - Python/Django environment metadata (versions, settings, database config)
- django://apps - All Django apps with their file paths
- django://models - All models with import paths and source locations
"""
    ]

    if find_spec("mcp_django_shell"):
        from mcp_django_shell.server import mcp as shell_mcp

        if shell_mcp.instructions is not None:
            instructions.append(shell_mcp.instructions)

    mcp = FastMCP(name="Django", instructions="\n".join(instructions))

    if find_spec("mcp_django_shell"):
        from mcp_django_shell.server import mcp as shell_mcp

        await mcp.import_server(shell_mcp, prefix="shell")

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
