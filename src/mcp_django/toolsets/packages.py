from __future__ import annotations

import logging
from typing import Annotated
from typing import Any

import httpx
from fastmcp import Context
from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PackageResource(BaseModel):
    category: str
    slug: str
    title: str
    description: str | None = None
    documentation_url: str | None = None
    grids: list[str] | None = None
    last_updated: str | None = None
    participants: int | None = None
    pypi_url: str | None = None
    pypi_version: str | None = None
    repo_description: str | None = None
    repo_forks: int | None = None
    repo_url: str | None = None
    repo_watchers: int = 0


class GridResource(BaseModel):
    title: str
    slug: str
    description: str
    packages: list[str] | int


class PackageSearchResult(BaseModel):
    item_type: str = "package"
    slug: str
    title: str
    description: str | None = None
    repo_watchers: int = 0
    repo_forks: int = 0
    participants: int | None = None
    last_committed: str | None = None
    last_released: str | None = None


class GridSearchResult(BaseModel):
    item_type: str = "grid"
    slug: str
    title: str
    description: str | None = None


class DjangoPackagesClient:
    BASE_URL_V4 = "https://djangopackages.org/api/v4"
    BASE_URL_V3 = "https://djangopackages.org/api/v3"
    TIMEOUT = 30.0

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=self.TIMEOUT,
            headers={"Content-Type": "application/json"},
        )
        logger.debug("Django Packages client initialized")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.client.aclose()

    async def _request(self, method: str, url: str, **kwargs) -> Any:
        response = await self.client.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    async def search(
        self,
        query: str,
    ) -> list[PackageSearchResult | GridSearchResult]:
        logger.debug("Searching: query=%s", query)

        data = await self._request(
            "GET", f"{self.BASE_URL_V4}/search/", params={"q": query}
        )

        filtered_data = [item for item in data if item.get("slug")]

        results: list[PackageSearchResult | GridSearchResult] = []
        for item in filtered_data:
            item_type = item.get("item_type", "package")

            if item_type == "grid":
                result = GridSearchResult(
                    slug=item["slug"],
                    title=item["title"],
                    description=item.get("description"),
                )
            else:
                participants = None
                if item.get("participants") and isinstance(item["participants"], str):
                    participants = len(
                        [
                            p.strip()
                            for p in item["participants"].split(",")
                            if p.strip()
                        ]
                    )

                result = PackageSearchResult(
                    slug=item["slug"],
                    title=item["title"],
                    description=item.get("description"),
                    repo_watchers=item.get("repo_watchers", 0),
                    repo_forks=item.get("repo_forks", 0),
                    participants=participants,
                    last_committed=item.get("last_committed"),
                    last_released=item.get("last_released"),
                )

            results.append(result)

        logger.debug(
            "Search complete: returned=%d",
            len(results),
        )

        return results

    async def get_package(self, slug_or_id: str) -> PackageResource:
        logger.debug("Fetching package: %s", slug_or_id)

        data = await self._request("GET", f"{self.BASE_URL_V3}/packages/{slug_or_id}/")

        if "modified" in data:
            data["last_updated"] = data.pop("modified")

        if (
            "category" in data
            and isinstance(data["category"], str)
            and data["category"]
        ):
            data["category"] = data["category"].rstrip("/").split("/")[-1]

        if "grids" in data and isinstance(data["grids"], list):
            data["grids"] = [url.rstrip("/").split("/")[-1] for url in data["grids"]]

        if "participants" in data and isinstance(data["participants"], str):
            data["participants"] = len(
                [p.strip() for p in data["participants"].split(",") if p.strip()]
            )

        if "description" not in data or not data.get("description"):
            data["description"] = data.get("repo_description")

        return PackageResource(**data)

    async def get_grid(self, slug_or_id: str) -> GridResource:
        logger.debug("Fetching grid: %s", slug_or_id)

        data = await self._request("GET", f"{self.BASE_URL_V3}/grids/{slug_or_id}/")

        if "packages" in data and isinstance(data["packages"], list):
            data["packages"] = [
                url.rstrip("/").split("/")[-1] for url in data["packages"]
            ]

        return GridResource(**data)


mcp = FastMCP(
    name="djangopackages.org",
    instructions="djangopackages.org is a curated directory of reusable Django apps, sites, and tools. Each package includes metadata like GitHub stars, PyPI info, documentation links, and which comparison grids it appears in.",
)

DJANGOPACKAGES_TOOLSET = "djangopackages"


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


@mcp.resource("django://package/{slug}", tags={DJANGOPACKAGES_TOOLSET})
async def get_package_resource(slug: str) -> PackageResource:
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
) -> PackageResource:
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
