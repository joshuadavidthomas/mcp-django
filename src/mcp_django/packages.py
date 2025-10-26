from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from django.core.cache.backends.filebased import FileBasedCache
from platformdirs import user_cache_dir
from pydantic import BaseModel
from pydantic import Field

logger = logging.getLogger(__name__)


class PackageResource(BaseModel):
    id: int
    title: str
    slug: str
    description: str
    category: str
    item_type: str  # "package" or "grid"
    pypi_url: str | None = None
    repo_url: str | None = None
    documentation_url: str | None = None
    repo_watchers: int = 0
    last_updated: str | None = None

    @classmethod
    def from_search(cls, item: dict[str, Any]) -> PackageResource:
        """Create PackageResource from search API response.

        The search endpoint returns basic package information. This method
        creates a PackageResource from that data without additional API calls.

        Args:
            item: Search result item dictionary

        Returns:
            PackageResource with basic information
        """
        return cls(
            id=item.get("id", 0),
            title=item.get("title", ""),
            slug=item.get("slug", ""),
            description=item.get("description", ""),
            category=normalize_category(item.get("category")),
            item_type=item.get("item_type", "package"),
            pypi_url=item.get("pypi_url"),
            repo_url=item.get("repo_url"),
            documentation_url=item.get("documentation_url"),
            repo_watchers=item.get("repo_watchers", 0),
            last_updated=item.get("last_committed") or item.get("last_released"),
        )

    @classmethod
    def from_detail(cls, data: dict[str, Any]) -> PackageResource:
        """Create PackageResource from package detail API response.

        The package detail endpoint returns comprehensive information including
        grids, participants, and repository statistics. This method extracts
        the fields needed for PackageResource directly from the API response.

        Args:
            data: Raw dictionary from /packages/{slug}/ endpoint

        Returns:
            PackageResource with enriched information
        """
        return cls(
            id=data.get("id", 0),
            title=data.get("title", ""),
            slug=data.get("slug", ""),
            description=data.get("repo_description", ""),
            category=normalize_category(data.get("category")),
            item_type="package",  # Package details are always packages
            pypi_url=data.get("pypi_url"),
            repo_url=data.get("repo_url"),
            documentation_url=data.get("documentation_url"),
            repo_watchers=data.get("repo_watchers", 0),
            last_updated=data.get("last_updated"),
        )


class PackageDetailResource(BaseModel):
    id: int
    title: str
    slug: str
    category: str
    grids: list[str]
    last_updated: str | None = None
    last_fetched: str | None = None
    repo_url: str | None = None
    pypi_version: str | None = None
    pypi_url: str | None = None
    documentation_url: str | None = None
    repo_forks: int = 0
    repo_description: str | None = None
    repo_watchers: int = 0
    commits_over_52: list[int] = Field(default_factory=list)
    participants: list[str] = Field(default_factory=list)
    created: str | None = None
    modified: str | None = None


class GridResource(BaseModel):
    id: int
    title: str
    slug: str
    description: str
    is_locked: bool
    packages: list[str]
    header: bool
    created: str
    modified: str


class CategoryResource(BaseModel):
    id: int
    title: str
    slug: str
    description: str
    title_plural: str
    show_pypi: bool
    created: str
    modified: str


CATEGORY_ID_TO_SLUG = {
    "1": "apps",
    "2": "frameworks",
    "3": "projects",
    "4": "other",
}

CATEGORY_TITLE_TO_SLUG = {
    "App": "apps",
    "Framework": "frameworks",
    "Project": "projects",
    "Other": "other",
}


def normalize_category(category: str | None) -> str:
    """Normalize category to slug format.

    Handles three formats:
    - URL: "https://djangopackages.org/api/v4/categories/1/" -> "apps"
    - Title: "App" -> "apps"
    - Slug: "apps" -> "apps"
    - None/empty: "" -> ""

    Args:
        category: Category string in any format

    Returns:
        Category slug (e.g., "apps", "frameworks", "projects", "other")
    """
    if not category:
        return ""

    parsed = urlparse(category)
    if parsed.scheme and parsed.netloc:
        category_id = parsed.path.rstrip("/").split("/")[-1]
        return CATEGORY_ID_TO_SLUG.get(category_id, "")

    if category in CATEGORY_TITLE_TO_SLUG:
        return CATEGORY_TITLE_TO_SLUG[category]

    return category.lower()


class SearchResultsResource(BaseModel):
    results: list[PackageResource]
    count: int
    next_offset: int | None
    has_more: bool


class DjangoPackagesClient:
    BASE_URL = "https://djangopackages.org/api/v4"
    CACHE_DIR = Path(user_cache_dir("mcp-django")) / "djangopackages"
    CACHE_TTL = 60 * 60 * 24  # 1 day
    TIMEOUT = 30.0

    def __init__(self, cache_dir: Path | None = None):
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=self.TIMEOUT,
            headers={"Content-Type": "application/json"},
        )

        cache_dir = cache_dir or self.CACHE_DIR
        cache_dir.mkdir(parents=True, exist_ok=True)

        self.cache = FileBasedCache(
            dir=str(cache_dir),
            params={
                "max_entries": 1000,
                "cull_frequency": 3,
            },
        )

        logger.debug(
            "Django Packages client initialized with cache at %s (TTL: %d days)",
            cache_dir,
            self.CACHE_TTL // 86400,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.client.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        response = await self.client.request(method, path, **kwargs)
        response.raise_for_status()
        return response.json()

    def _get_cached_package(self, slug: str) -> dict[str, Any] | None:
        cached = self.cache.get(f"pkg:{slug}")
        if cached:
            logger.debug("Cache hit for package: %s", slug)
        else:
            logger.debug("Cache miss for package: %s", slug)
        return cached

    def _cache_package(self, slug: str, data: dict[str, Any]):
        self.cache.set(f"pkg:{slug}", data, timeout=self.CACHE_TTL)
        logger.debug("Cached package: %s (TTL: %d days)", slug, self.CACHE_TTL // 86400)

    async def search_packages(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
    ) -> SearchResultsResource:
        """Search packages by query, enriching results with cached/fetched details.

        The search process:
        1. Fetch all search results from the API
        2. Transform to basic PackageResources
        3. Paginate the results
        4. Enrich only the paginated subset with full package details

        This approach minimizes API calls by only fetching full details for
        packages that will be returned, while still providing accurate pagination.

        Args:
            query: Search query string
            limit: Maximum number of results to return (default: 10)
            offset: Pagination offset (default: 0)

        Returns:
            SearchResultsResource with enriched package information
        """
        logger.debug(
            "Searching packages: query=%s, limit=%d, offset=%d", query, limit, offset
        )

        data = await self._request("GET", "/search/", params={"q": query})

        basic_results = [
            PackageResource.from_search(item)
            for item in data
            if item.get("slug")  # Skip items without slug
        ]

        total_count = len(basic_results)
        paginated_basic = basic_results[offset : offset + limit]
        has_more = (offset + limit) < total_count

        enriched_results = []
        for basic_pkg in paginated_basic:
            cached_data = self._get_cached_package(basic_pkg.slug)
            if not cached_data:
                cached_data = await self._request("GET", f"/packages/{basic_pkg.slug}/")
                self._cache_package(basic_pkg.slug, cached_data)

            enriched_pkg = PackageResource.from_detail(cached_data)

            if not enriched_pkg.last_updated:
                enriched_pkg.last_updated = basic_pkg.last_updated

            enriched_results.append(enriched_pkg)

        logger.debug(
            "Search complete: total=%d, returned=%d, has_more=%s",
            total_count,
            len(enriched_results),
            has_more,
        )

        return SearchResultsResource(
            results=enriched_results,
            count=total_count,
            next_offset=(offset + limit) if has_more else None,
            has_more=has_more,
        )

    async def get_package(self, slug: str) -> PackageDetailResource:
        logger.debug("Fetching package: %s", slug)

        cached_data = self._get_cached_package(slug)
        if cached_data:
            return PackageDetailResource(**cached_data)

        data = await self._request("GET", f"/packages/{slug}/")
        self._cache_package(slug, data)
        return PackageDetailResource(**data)

    async def list_grids(self, limit: int = 20, offset: int = 0) -> list[GridResource]:
        logger.debug("Listing grids: limit=%d, offset=%d", limit, offset)
        data = await self._request(
            "GET", "/grids/", params={"limit": limit, "offset": offset}
        )
        return [GridResource(**item) for item in data.get("results", [])]

    async def get_grid(self, slug: str) -> GridResource:
        logger.debug("Fetching grid: %s", slug)
        data = await self._request("GET", f"/grids/{slug}/")
        return GridResource(**data)

    async def list_categories(
        self, limit: int = 20, offset: int = 0
    ) -> list[CategoryResource]:
        logger.debug("Listing categories: limit=%d, offset=%d", limit, offset)
        data = await self._request(
            "GET", "/categories/", params={"limit": limit, "offset": offset}
        )
        return [CategoryResource(**item) for item in data.get("results", [])]

    async def get_category(self, slug: str) -> CategoryResource:
        logger.debug("Fetching category: %s", slug)
        data = await self._request("GET", f"/categories/{slug}/")
        return CategoryResource(**data)
