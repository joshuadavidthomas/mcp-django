from __future__ import annotations

import logging
from enum import Enum
from typing import Annotated
from typing import Any
from typing import Literal

import httpx
from pydantic import BaseModel
from pydantic import BeforeValidator
from pydantic import Discriminator
from pydantic import TypeAdapter
from pydantic import model_validator

logger = logging.getLogger(__name__)


def extract_slug_from_url(value: str | None) -> str | None:
    if value is None:
        return None
    return value.rstrip("/").split("/")[-1]


def extract_slugs_from_urls(value: list[str] | None) -> list[str] | None:
    if value is None:
        return None
    slugs = [extract_slug_from_url(url) for url in value if url]
    return [s for s in slugs if s is not None]


def parse_participant_list(value: str | list[str] | None) -> int | None:
    if value is None:
        return None
    participants = value.split(",") if isinstance(value, str) else value
    return len([p.strip() for p in participants if p.strip()])


CategorySlug = Annotated[str, BeforeValidator(extract_slug_from_url)]
GridSlugs = Annotated[list[str] | None, BeforeValidator(extract_slugs_from_urls)]
PackageSlugs = Annotated[list[str] | int, BeforeValidator(extract_slugs_from_urls)]
ParticipantCount = Annotated[int | None, BeforeValidator(parse_participant_list)]


class PackageResource(BaseModel):
    category: CategorySlug
    slug: str
    title: str
    description: str | None = None
    documentation_url: str | None = None
    grids: GridSlugs = None
    last_updated: str | None = None
    participants: ParticipantCount = None
    pypi_url: str | None = None
    pypi_version: str | None = None
    repo_description: str | None = None
    repo_forks: int | None = None
    repo_url: str | None = None
    repo_watchers: int = 0

    @model_validator(mode="before")
    @classmethod
    def transform_v3_api_response(cls, data: Any) -> Any:
        if "modified" in data:
            data["last_updated"] = data.pop("modified")

        if not data.get("description"):
            data["description"] = data.get("repo_description")

        return data


class GridResource(BaseModel):
    title: str
    slug: str
    description: str
    packages: PackageSlugs


class SearchItemType(str, Enum):
    GRID = "grid"
    PACKAGE = "package"


class PackageSearchResult(BaseModel):
    item_type: Literal[SearchItemType.PACKAGE] = SearchItemType.PACKAGE
    slug: str
    title: str
    description: str | None = None
    repo_watchers: int = 0
    repo_forks: int = 0
    participants: ParticipantCount = None
    last_committed: str | None = None
    last_released: str | None = None


class GridSearchResult(BaseModel):
    item_type: Literal[SearchItemType.GRID] = SearchItemType.GRID
    slug: str
    title: str
    description: str | None = None


SearchResultList = TypeAdapter(
    list[Annotated[PackageSearchResult | GridSearchResult, Discriminator("item_type")]]
)


class DjangoPackagesClient:
    BASE_URL_V3 = "https://djangopackages.org/api/v3"
    BASE_URL_V4 = "https://djangopackages.org/api/v4"
    TIMEOUT = 30.0

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=self.TIMEOUT,
            headers={"Content-Type": "application/json"},
        )
        logger.debug("Django Packages client initialized")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: Any):
        await self.client.aclose()

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        response = await self.client.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    async def search(
        self,
        query: str,
    ) -> list[PackageSearchResult | GridSearchResult]:
        logger.debug("Searching: query=%s", query)
        response = await self._request(
            "GET", f"{self.BASE_URL_V4}/search/", params={"q": query}
        )
        results = SearchResultList.validate_json(response.content)
        logger.debug("Search complete: returned=%d", len(results))
        return results

    async def get_package(self, slug_or_id: str) -> PackageResource:
        logger.debug("Fetching package: %s", slug_or_id)
        response = await self._request(
            "GET", f"{self.BASE_URL_V3}/packages/{slug_or_id}/"
        )
        return PackageResource.model_validate_json(response.content)

    async def get_grid(self, slug_or_id: str) -> GridResource:
        logger.debug("Fetching grid: %s", slug_or_id)
        response = await self._request("GET", f"{self.BASE_URL_V3}/grids/{slug_or_id}/")
        return GridResource.model_validate_json(response.content)
