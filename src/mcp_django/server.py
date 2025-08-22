from __future__ import annotations

import logging

from django.apps import apps
from fastmcp import FastMCP

from .resources import AppResource
from .resources import ModelResource
from .resources import ProjectResource

mcp = FastMCP(
    name="Django",
    instructions="""Provides Django resource endpoints for project exploration.

RESOURCES:
Use resources for orientation. Resources provide precise coordinates (import paths, file
locations) to avoid exploration overhead.

- django://project - Python/Django environment metadata (versions, settings, database config)
- django://apps - All Django apps with their file paths
- django://models - All models with import paths and source locations
""",
)

logger = logging.getLogger(__name__)


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
