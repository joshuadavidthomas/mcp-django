from __future__ import annotations

import logging
from typing import Annotated

from fastmcp import Context
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .client import DjangoPackagesClient
from .client import GridResource
from .client import GridSearchResult
from .client import PackageResource
from .client import PackageSearchResult

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="djangopackages.org",
    instructions="Search and discover reusable Django apps, sites, and tools from the community. Access package metadata including GitHub stars, PyPI versions, documentation links, and comparison grids for evaluating similar packages.",
)

DJANGOPACKAGES_TOOLSET = "djangopackages"


async def get_grid(
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


mcp.resource(
    "django://grid/{slug}",
    name="Django Grid Details",
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={DJANGOPACKAGES_TOOLSET},
)(get_grid)

mcp.tool(
    name="get_grid",
    annotations=ToolAnnotations(
        title="djangopackages.org Grid Details",
        readOnlyHint=True,
        idempotentHint=True,
    ),
    tags={DJANGOPACKAGES_TOOLSET},
)(get_grid)


async def get_package(
    slug: Annotated[
        str,
        "The package slug (e.g., 'django-debug-toolbar', 'django-rest-framework')",
    ],
) -> PackageResource:
    """Get detailed information about a specific Django package.

    Provides comprehensive package metadata including repository stats,
    PyPI information, documentation links, and grid memberships.
    """
    async with DjangoPackagesClient() as client:
        return await client.get_package(slug)


mcp.resource(
    "django://package/{slug}",
    name="Django Package Details",
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={DJANGOPACKAGES_TOOLSET},
)(get_package)

mcp.tool(
    name="get_package",
    annotations=ToolAnnotations(
        title="djangopackages.org Package Details",
        readOnlyHint=True,
        idempotentHint=True,
    ),
    tags={DJANGOPACKAGES_TOOLSET},
)(get_package)


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
) -> list[PackageSearchResult | GridSearchResult]:
    """Search djangopackages.org for third-party packages.

    Use this when you need packages for common Django tasks like authentication,
    admin interfaces, REST APIs, forms, caching, testing, deployment, etc.
    """
    logger.info(
        "djangopackages.org search called - request_id: %s, query: %s",
        ctx.request_id,
        query,
    )

    async with DjangoPackagesClient() as client:
        results = await client.search(query=query)

    logger.debug(
        "djangopackages.org search completed - request_id: %s, results: %d",
        ctx.request_id,
        len(results),
    )

    return results
