from __future__ import annotations

import logging
from typing import Any

import httpx

from .models import GridResource
from .models import GridSearchResult
from .models import PackageResource
from .models import PackageSearchResult
from .models import SearchResultList

logger = logging.getLogger(__name__)


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
