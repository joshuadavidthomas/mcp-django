from __future__ import annotations

import logging
from typing import Annotated
from typing import Literal

from django.apps import apps
from django.conf import settings
from fastmcp import Context
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .resources import AppResource
from .resources import ModelResource
from .resources import ProjectResource
from .resources import SettingResource
from .resources import filter_models
from .routing import RouteSchema
from .routing import ViewMethod
from .routing import filter_routes
from .routing import get_all_routes

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="Project",
    instructions="Inspect Django project structure, configuration, and URL routing. Access project metadata, installed apps, models, settings, and route definitions for understanding your Django application's architecture.",
)

PROJECT_TOOLSET = "project"


@mcp.tool(
    name="get_project_info",
    annotations=ToolAnnotations(
        title="Django Project Information",
        readOnlyHint=True,
        idempotentHint=True,
    ),
    tags={PROJECT_TOOLSET},
)
def get_project_info() -> ProjectResource:
    """Get comprehensive project information including Python environment and Django configuration.

    Use this to understand the project's runtime environment, installed apps, and database
    configuration.
    """
    return ProjectResource.from_env()


@mcp.resource(
    "django://app/{app_label}",
    name="Django App Details",
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={PROJECT_TOOLSET},
)
def get_app(
    app_label: Annotated[
        str, "Django app label (e.g., 'auth', 'contenttypes', 'myapp')"
    ],
) -> AppResource:
    """Get details for a specific Django app."""
    return AppResource.from_app(apps.get_app_config(app_label))


@mcp.resource(
    "django://app/{app_label}/models",
    name="Django App Models",
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={PROJECT_TOOLSET},
)
def get_app_models(
    app_label: Annotated[
        str, "Django app label (e.g., 'auth', 'contenttypes', 'myapp')"
    ],
) -> list[ModelResource]:
    """Get all models for a specific Django app."""
    app_config = apps.get_app_config(app_label)
    return [
        ModelResource.from_model(model)
        for model in app_config.get_models()
        if not model._meta.auto_created
    ]


def list_apps() -> list[AppResource]:
    """Get a list of all installed Django applications with their models.

    Use this to explore the project structure and available models without executing code.
    """
    return [AppResource.from_app(app) for app in apps.get_app_configs()]


mcp.resource(
    "django://apps",
    name="Installed Django Apps",
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={PROJECT_TOOLSET},
)(list_apps)

mcp.tool(
    name="list_apps",
    annotations=ToolAnnotations(
        title="List Django Apps",
        readOnlyHint=True,
        idempotentHint=True,
    ),
    tags={PROJECT_TOOLSET},
)(list_apps)


@mcp.resource(
    "django://model/{app_label}/{model_name}",
    name="Model Details",
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={PROJECT_TOOLSET},
)
def get_model(
    app_label: Annotated[
        str, "Django app label (e.g., 'auth', 'contenttypes', 'myapp')"
    ],
    model_name: Annotated[str, "Model name (e.g., 'User', 'Group', 'Permission')"],
) -> ModelResource:
    """Get details for a specific Django model."""
    model = apps.get_model(app_label, model_name)
    return ModelResource.from_model(model)


def list_models(
    ctx: Context,
    include: Annotated[
        list[str] | None,
        "Specific app labels to include (e.g., ['auth', 'myapp']). When provided, only models from these exact apps are returned (overrides scope).",
    ] = None,
    scope: Annotated[
        Literal["project", "all"],
        "Filter scope when include is not specified: 'project' (default) for your project's models only, 'all' for everything including Django and third-party packages.",
    ] = "project",
) -> list[ModelResource]:
    """Get detailed information about Django models with optional filtering.

    By default returns only models from your project directory. Use include for
    specific apps or scope='all' for everything including Django and third-party packages.
    When include is provided, it overrides the scope parameter.

    Use this for quick model introspection without shell access.
    """
    logger.info(
        "list_models called - request_id: %s, client_id: %s, include: %s, scope: %s",
        ctx.request_id,
        ctx.client_id or "unknown",
        include,
        scope,
    )

    all_models = list(apps.get_models())
    total_count = len(all_models)

    filtered_models = filter_models(all_models, include=include, scope=scope)
    result = [ModelResource.from_model(model) for model in filtered_models]

    logger.debug(
        "list_models completed - request_id: %s, total_models: %d, returned_models: %d",
        ctx.request_id,
        total_count,
        len(result),
    )

    return result


# TODO: Uncomment once upstream bug is fixed
# Resource templates with only optional query parameters don't work when called without
# query params.
# Ref: https://github.com/jlowin/fastmcp/pull/2323

# mcp.resource(
#     "django://models{?include,scope}",
#     name="Django Models",
#     annotations={"readOnlyHint": True, "idempotentHint": True},
#     tags={PROJECT_TOOLSET},
# )(list_models)

mcp.tool(
    name="list_models",
    annotations=ToolAnnotations(
        title="List Django Models",
        readOnlyHint=True,
        idempotentHint=True,
    ),
    tags={PROJECT_TOOLSET},
)(list_models)


@mcp.resource(
    "django://models",
    name="Django Models",
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={PROJECT_TOOLSET},
)
def list_models_resource() -> list[ModelResource]:
    """Resource endpoint without query parameters - uses default filtering (project scope)."""

    # TODO: Replace with query-param template once upstream bug is fixed.
    # This static resource provides access with default settings until the bug is fixed.
    # Use the list_models() tool for filtering options.
    # Ref: https://github.com/jlowin/fastmcp/pull/2323

    all_models = list(apps.get_models())
    filtered_models = filter_models(all_models, include=None, scope="project")
    return [ModelResource.from_model(model) for model in filtered_models]


@mcp.tool(
    name="list_routes",
    annotations=ToolAnnotations(
        title="List Django Routes", readOnlyHint=True, idempotentHint=True
    ),
    tags={PROJECT_TOOLSET},
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
    """
    logger.info(
        "list_routes called - request_id: %s, client_id: %s, method: %s, name: %s, pattern: %s",
        ctx.request_id,
        ctx.client_id or "unknown",
        method,
        name,
        pattern,
    )

    routes = get_all_routes()
    total_count = len(routes)

    if any([method, name, pattern]):
        routes = filter_routes(routes, method=method, name=name, pattern=pattern)

    logger.debug(
        "list_routes completed - request_id: %s, total_routes: %d, returned_routes: %d",
        ctx.request_id,
        total_count,
        len(routes),
    )

    return routes


@mcp.resource(
    "django://route/{pattern*}",
    name="Route by Pattern",
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={PROJECT_TOOLSET},
)
async def get_route_by_pattern(
    pattern: Annotated[
        str, "URL pattern to search for (e.g., 'admin', 'api', 'users')"
    ],
) -> list[RouteSchema]:
    """Get routes matching a specific URL pattern."""
    all_routes = get_all_routes()
    return filter_routes(all_routes, pattern=pattern)


def get_setting(
    key: Annotated[
        str, "Django setting key (e.g., 'DEBUG', 'DATABASES', 'INSTALLED_APPS')"
    ],
) -> SettingResource:
    """Get a Django setting by key.

    Returns the setting value along with type information. Raises AttributeError
    if the setting does not exist.
    """
    value = getattr(settings, key)  # Will raise AttributeError if missing
    return SettingResource(key=key, value=value, value_type=type(value).__name__)


mcp.resource(
    "django://setting/{key}",
    name="Django Setting",
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={PROJECT_TOOLSET},
)(get_setting)

mcp.tool(
    name="get_setting",
    annotations=ToolAnnotations(
        title="Get Django Setting",
        readOnlyHint=True,
        idempotentHint=True,
    ),
    tags={PROJECT_TOOLSET},
)(get_setting)
