from __future__ import annotations

import logging
from typing import Any

import httpx
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


class SearchResultsResource(BaseModel):
    results: list[PackageSearchResult | GridSearchResult]
    count: int
    next_offset: int | None
    has_more: bool


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
        limit: int = 10,
        offset: int = 0,
    ) -> SearchResultsResource:
        logger.debug("Searching: query=%s, limit=%d, offset=%d", query, limit, offset)

        data = await self._request(
            "GET", f"{self.BASE_URL_V4}/search/", params={"q": query}
        )

        filtered_data = [item for item in data if item.get("slug")]

        total_count = len(filtered_data)
        paginated_data = filtered_data[offset : offset + limit]
        has_more = (offset + limit) < total_count

        results: list[PackageSearchResult | GridSearchResult] = []
        for item in paginated_data:
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
            "Search complete: total=%d, returned=%d, has_more=%s",
            total_count,
            len(results),
            has_more,
        )

        return SearchResultsResource(
            results=results,
            count=total_count,
            next_offset=(offset + limit) if has_more else None,
            has_more=has_more,
        )

    async def get_package(self, slug_or_id: str) -> PackageResource:
        """Get package details using v3 API (returns slugs in grid URLs)."""
        logger.debug("Fetching package: %s", slug_or_id)

        # Fetch from v3 API
        data = await self._request("GET", f"{self.BASE_URL_V3}/packages/{slug_or_id}/")

        # Map v3 fields to our model
        if "modified" in data:
            data["last_updated"] = data.pop("modified")

        # Extract category slug from v3 URL
        if (
            "category" in data
            and isinstance(data["category"], str)
            and data["category"]
        ):
            data["category"] = data["category"].rstrip("/").split("/")[-1]

        # Extract slugs from v3 grid URLs (simple string parsing - no API calls!)
        if "grids" in data and isinstance(data["grids"], list):
            data["grids"] = [url.rstrip("/").split("/")[-1] for url in data["grids"]]

        # Parse participants
        if "participants" in data and isinstance(data["participants"], str):
            # v3 returns comma-separated string
            data["participants"] = len(
                [p.strip() for p in data["participants"].split(",") if p.strip()]
            )

        # v3 doesn't have description field at package level, use repo_description
        if "description" not in data or not data.get("description"):
            data["description"] = data.get("repo_description")

        return PackageResource(**data)

    async def get_grid(self, slug_or_id: str) -> GridResource:
        """Get grid details using v3 API (returns slugs in package URLs)."""
        logger.debug("Fetching grid: %s", slug_or_id)

        # Fetch from v3 API
        data = await self._request("GET", f"{self.BASE_URL_V3}/grids/{slug_or_id}/")

        # Extract slugs from v3 URLs (simple string parsing - no API calls!)
        if "packages" in data and isinstance(data["packages"], list):
            data["packages"] = [
                url.rstrip("/").split("/")[-1] for url in data["packages"]
            ]

        return GridResource(**data)
