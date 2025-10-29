from __future__ import annotations

import httpx
import pytest
from respx import MockRouter

from mcp_django.toolsets.packages import DjangoPackagesClient
from mcp_django.toolsets.packages import PackageResource
from mcp_django.toolsets.packages import extract_slug_from_url
from mcp_django.toolsets.packages import extract_slugs_from_urls
from mcp_django.toolsets.packages import parse_participant_list


def test_extract_slug_from_url_with_none():
    assert extract_slug_from_url(None) is None


def test_extract_slugs_from_urls_with_none():
    assert extract_slugs_from_urls(None) is None


def test_parse_participant_list_with_none():
    assert parse_participant_list(None) is None


class TestDjangoPackagesClient:
    @pytest.mark.asyncio
    async def test_search(self, mock_packages_search_api, packages_client):
        async with packages_client as client:
            results = await client.search(query="auth")

        assert isinstance(results, list)
        assert len(results) == 3

        package_result = results[0]
        assert package_result.item_type == "package"
        assert package_result.slug == "django-allauth"
        assert package_result.repo_watchers == 8500
        assert package_result.last_committed == "2024-01-15T10:30:00"

        grid_result = results[2]
        assert grid_result.item_type == "grid"
        assert grid_result.slug == "authentication"
        assert grid_result.title == "Authentication"

    @pytest.mark.asyncio
    async def test_search_with_string_participants(self, respx_mock):
        mock_results = [
            {
                "id": 1,
                "title": "package-with-string-participants",
                "slug": "package-with-string-participants",
                "description": "Test package",
                "category": "App",
                "item_type": "package",
                "repo_watchers": 100,
                "participants": "user1,user2,user3",  # String format
                "last_committed": None,
                "last_released": None,
            },
        ]

        respx_mock.get("https://djangopackages.org/api/v4/search/").mock(
            return_value=httpx.Response(200, json=mock_results)
        )

        async with DjangoPackagesClient() as client:
            results = await client.search(query="test")
            assert len(results) == 1
            assert results[0].participants == 3

    @pytest.mark.asyncio
    async def test_get_package(self, mock_packages_package_detail_api, packages_client):
        async with packages_client as client:
            package = await client.get_package("django-debug-toolbar")

        assert isinstance(package, PackageResource)
        assert package.slug == "django-debug-toolbar"
        assert package.repo_watchers == 7937
        assert package.pypi_version == "4.3.0"
        assert package.grids == ["grid-21", "grid-11"]

    @pytest.mark.asyncio
    async def test_client_context_manager(
        self, respx_mock: MockRouter, packages_client
    ):
        respx_mock.get("https://djangopackages.org/api/v4/search/").mock(
            return_value=httpx.Response(200, json=[])
        )

        client = packages_client
        assert client.client is not None

        async with client:
            await client.search(query="test")

        assert client.client.is_closed
