from __future__ import annotations

import logging
from typing import Annotated

from fastmcp import Context
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mcp_django.packages import CategoryResource
from mcp_django.packages import DjangoPackagesClient
from mcp_django.packages import GridResource
from mcp_django.packages import PackageDetailResource
from mcp_django.packages import SearchResultsResource

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="djangopackages.org",
    instructions="djangopackages.org is a curated directory of reusable Django apps, sites, and tools. Each package includes metadata like GitHub stars, PyPI info, documentation links, and which comparison grids it appears in.",
)

DJANGOPACKAGES_TOOLSET = "djangopackages"


@mcp.resource("django://category/{slug}", tags={DJANGOPACKAGES_TOOLSET})
async def get_category_resource(slug: str) -> CategoryResource:
    """Details for a specific category."""
    async with DjangoPackagesClient() as client:
        return await client.get_category(slug)


@mcp.tool(
    name="get_category",
    annotations=ToolAnnotations(
        title="djangopackages.org Category Details",
        readOnlyHint=True,
        idempotentHint=True,
    ),
    tags={DJANGOPACKAGES_TOOLSET},
)
async def get_category_tool(
    slug: Annotated[
        str,
        "The category slug (e.g., 'apps', 'projects')",
    ],
) -> CategoryResource:
    """Get details about a specific package category.

    Returns detailed information about a category including its description
    and metadata.
    """
    async with DjangoPackagesClient() as client:
        return await client.get_category(slug)


@mcp.resource("django://categories", tags={DJANGOPACKAGES_TOOLSET})
async def list_categories_resource() -> list[CategoryResource]:
    """All package categories from djangopackages.org."""
    async with DjangoPackagesClient() as client:
        return await client.list_categories()


@mcp.tool(
    name="list_categories",
    annotations=ToolAnnotations(
        title="List djangopackages.org Categories",
        readOnlyHint=True,
        idempotentHint=True,
    ),
    tags={DJANGOPACKAGES_TOOLSET},
)
async def list_categories_tool() -> list[CategoryResource]:
    """List all djangopackages.org categories.

    Categories organize packages into broad types like "Apps" (installable
    Django applications) and "Projects" (complete Django projects).
    """
    async with DjangoPackagesClient() as client:
        return await client.list_categories()


@mcp.resource("django://grid/{slug}", tags={DJANGOPACKAGES_TOOLSET})
async def get_grid_resource(slug: str) -> GridResource:
    """Comparison grid details with all packages for comparison."""
    async with DjangoPackagesClient() as client:
        return await client.get_grid(slug)


@mcp.tool(
    name="get_grid",
    annotations=ToolAnnotations(
        title="djangopackages.org Grid Details",
        readOnlyHint=True,
        idempotentHint=True,
    ),
    tags={DJANGOPACKAGES_TOOLSET},
)
async def get_grid_tool(
    slug: Annotated[
        str,
        "The grid slug (e.g., 'rest-frameworks', 'admin-interfaces')",
    ],
) -> GridResource:
    """Get a specific comparison grid with all its packages.

    Returns detailed information about a grid including all packages
    that belong to it, allowing for easy comparison of similar tools.
    """
    async with DjangoPackagesClient() as client:
        return await client.get_grid(slug)


@mcp.resource("django://grids", tags={DJANGOPACKAGES_TOOLSET})
async def list_grids_resource() -> list[GridResource]:
    """All comparison grids from djangopackages.org."""
    async with DjangoPackagesClient() as client:
        return await client.list_grids()


@mcp.tool(
    name="list_grids",
    annotations=ToolAnnotations(
        title="List djangopackages.org Grids",
        readOnlyHint=True,
        idempotentHint=True,
    ),
    tags={DJANGOPACKAGES_TOOLSET},
)
async def list_grids_tool() -> list[GridResource]:
    """List all djangopackages.org comparison grids.

    Grids are curated comparisons of packages in specific categories like
    "REST frameworks", "Admin interfaces", "Authentication", etc. Use these
    to explore and compare related packages.
    """
    async with DjangoPackagesClient() as client:
        return await client.list_grids()


@mcp.resource("django://package/{slug}", tags={DJANGOPACKAGES_TOOLSET})
async def get_package_resource(slug: str) -> PackageDetailResource:
    """Detailed package information including stats and metadata."""
    async with DjangoPackagesClient() as client:
        return await client.get_package(slug)


@mcp.tool(
    name="get_package",
    annotations=ToolAnnotations(
        title="djangopackages.org Package Details",
        readOnlyHint=True,
        idempotentHint=True,
    ),
    tags={DJANGOPACKAGES_TOOLSET},
)
async def get_package_tool(
    slug: Annotated[
        str,
        "The package slug (e.g., 'django-debug-toolbar', 'django-rest-framework')",
    ],
) -> PackageDetailResource:
    """Get detailed information about a specific Django package.

    Provides comprehensive package metadata including repository stats,
    PyPI information, documentation links, and grid memberships.
    """
    async with DjangoPackagesClient() as client:
        return await client.get_package(slug)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Search djangopackages.org",
        readOnlyHint=True,
        idempotentHint=True,
    ),
    tags={DJANGOPACKAGES_TOOLSET},
)
async def search(
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
    """Search djangopackages.org for third-party packages.

    Use this when you need packages for common Django tasks like authentication,
    admin interfaces, REST APIs, forms, caching, testing, deployment, etc.
    """
    logger.info(
        "djangopackages.org search called - request_id: %s, query: %s, max_results: %d, offset: %d",
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
        "djangopackages.org search completed - request_id: %s, results: %d",
        ctx.request_id,
        len(results.results),
    )

    return results
