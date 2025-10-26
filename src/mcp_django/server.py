from __future__ import annotations

import logging
from typing import Annotated
from typing import Literal

from django.apps import apps
from fastmcp import Context
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .code import filter_existing_imports
from .code import parse_code
from .output import DjangoShellOutput
from .output import ErrorOutput
from .packages import CategoryResource
from .packages import DjangoPackagesClient
from .packages import GridResource
from .packages import PackageDetailResource
from .packages import SearchResultsResource
from .resources import AppResource
from .resources import ModelResource
from .resources import ProjectResource
from .routing import RouteSchema
from .routing import ViewMethod
from .routing import filter_routes
from .routing import get_all_routes
from .shell import django_shell

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
- djangopackages.org://packages/{slug} - Detailed info about a specific package
- djangopackages.org://grids - List all package comparison grids
- djangopackages.org://grids/{slug} - Specific grid with packages (e.g., "rest-frameworks")
- djangopackages.org://categories - List all package categories
- djangopackages.org://categories/{slug} - Specific category details

TOOLS:
- list_routes - List all URL routes with filtering by method, name, or pattern
- search_djangopackages - Search Django Packages (djangopackages.org) for third-party packages.
  Use when discovering packages for authentication, admin, REST APIs, forms, caching, testing,
  deployment, etc. Supports pagination via offset parameter.
- shell - Execute Python code in a stateful Django shell or reset the session. The shell maintains
  state between calls - imports and variables persist. Use shell with action='reset' to clear
  state when variables get messy or you need a fresh start.

EXAMPLES:
The pattern: Resource → Import Path → Shell Operation.

Resources provide coordinates, shell does the work.

- Starting fresh? → Check django://project to understand environment and available apps
- Need information about a model? → Check django://models → Get import path →
  `from app.models import ModelName` in django_shell
- Need app structure? → Check django://apps for app labels and paths → Use paths in django_shell
- Need to query data? → Get model from django://models → Import in django_shell → Run queries
- Need to find a URL route? → Use list_routes with filters to find specific routes
- Need to reset the shell? → Use shell with action='reset' to clear all variables and imports
- Looking for auth packages? → search_djangopackages(query="authentication")
- Comparing REST frameworks? → Get djangopackages.org://grids/rest-frameworks
- Need package details? → Get djangopackages.org://packages/django-debug-toolbar
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


@mcp.resource(
    "djangopackages.org://packages/{slug}",
    name="Django Package Details",
    mime_type="application/json",
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def get_package_detail(slug: str) -> PackageDetailResource:
    """Get detailed information about a specific Django package.

    Provides comprehensive package metadata including repository stats,
    PyPI information, documentation links, and grid memberships.
    """
    async with DjangoPackagesClient() as client:
        return await client.get_package(slug)


@mcp.resource(
    "djangopackages.org://grids",
    name="Django Package Grids",
    mime_type="application/json",
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def get_grids() -> list[GridResource]:
    """List all Django Packages comparison grids.

    Grids are curated comparisons of packages in specific categories like
    "REST frameworks", "Admin interfaces", "Authentication", etc. Use these
    to explore and compare related packages.
    """
    async with DjangoPackagesClient() as client:
        return await client.list_grids()


@mcp.resource(
    "djangopackages.org://grids/{slug}",
    name="Django Package Grid Details",
    mime_type="application/json",
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def get_grid_detail(slug: str) -> GridResource:
    """Get a specific comparison grid with all its packages.

    Returns detailed information about a grid including all packages
    that belong to it, allowing for easy comparison of similar tools.
    """
    async with DjangoPackagesClient() as client:
        return await client.get_grid(slug)


@mcp.resource(
    "djangopackages.org://categories",
    name="Django Package Categories",
    mime_type="application/json",
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def get_categories() -> list[CategoryResource]:
    """List all Django Packages categories.

    Categories organize packages into broad types like "Apps" (installable
    Django applications) and "Projects" (complete Django projects).
    """
    async with DjangoPackagesClient() as client:
        return await client.list_categories()


@mcp.resource(
    "djangopackages.org://categories/{slug}",
    name="Django Package Category Details",
    mime_type="application/json",
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def get_category_detail(slug: str) -> CategoryResource:
    """Get details about a specific package category."""
    async with DjangoPackagesClient() as client:
        return await client.get_category(slug)


@mcp.tool(
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


@mcp.tool(
    annotations=ToolAnnotations(
        title="Search Django Packages",
        readOnlyHint=True,
        idempotentHint=True,
    ),
)
async def search_djangopackages(
    ctx: Context,
    query: Annotated[
        str,
        "Search term for packages (e.g., 'authentication', 'REST API', 'admin')",
    ],
    max_results: Annotated[
        int, "Maximum number of results to return (default: 10)"
    ] = 10,
    offset: Annotated[
        int,
        "Offset for pagination, use next_offset from previous response (default: 0)",
    ] = 0,
) -> SearchResultsResource:
    """Search Django Packages for third-party packages.

    Use this when you need packages for common Django tasks like authentication,
    admin interfaces, REST APIs, forms, caching, testing, deployment, etc.

    Django Packages (djangopackages.org) is a curated directory of reusable Django
    apps, sites, and tools. Each package includes metadata like GitHub stars, PyPI
    info, documentation links, and which comparison grids it appears in.

    For browsing by category or grid, use the djangopackages.org:// resources:
    - djangopackages.org://grids - Browse comparison grids like "REST frameworks"
    - djangopackages.org://categories - Browse categories like "Apps"

    Examples:
    - search_djangopackages(query="authentication") - Find auth packages
    - search_djangopackages(query="REST API") - Find REST framework packages
    - search_djangopackages(query="admin", max_results=5) - Find admin tools
    - search_djangopackages(query="forms", offset=10) - Get next page of results
    """
    logger.info(
        "search_djangopackages called - request_id: %s, query: %s, max_results: %d, offset: %d",
        ctx.request_id,
        query,
        max_results,
        offset,
    )

    async with DjangoPackagesClient() as client:
        results = await client.search_packages(
            query=query,
            limit=max_results,
            offset=offset,
        )

    logger.debug(
        "search_djangopackages completed - request_id: %s, results: %d",
        ctx.request_id,
        len(results.results),
    )

    return results
