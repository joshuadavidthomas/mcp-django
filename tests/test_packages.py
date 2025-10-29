from __future__ import annotations

import httpx
import pytest
from respx import MockRouter

from mcp_django.toolsets.packages import DjangoPackagesClient
from mcp_django.toolsets.packages import GridResource
from mcp_django.toolsets.packages import GridSearchResult
from mcp_django.toolsets.packages import PackageResource
from mcp_django.toolsets.packages import PackageSearchResult


class TestDjangoPackagesClient:
    @pytest.mark.asyncio
    async def test_search(self, mock_packages_search_api, packages_client):
        async with packages_client as client:
            results = await client.search(query="auth")

        assert isinstance(results, list)
        assert len(results) == 3

        # First result is a package
        package_result = results[0]
        assert package_result.item_type == "package"
        assert package_result.slug == "django-allauth"
        assert package_result.repo_watchers == 8500
        assert package_result.last_committed == "2024-01-15T10:30:00"

        # Third result is a grid
        grid_result = results[2]
        assert grid_result.item_type == "grid"
        assert grid_result.slug == "authentication"
        assert grid_result.title == "Authentication"

    @pytest.mark.asyncio
    async def test_search_with_string_participants(self, respx_mock: MockRouter):
        """Test search handling of string participants (comma-separated)."""
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
            # Verify string participants were parsed to count
            assert results[0].participants == 3

    @pytest.mark.asyncio
    async def test_search_pagination(self, respx_mock: MockRouter, tmp_path):
        mock_results = [
            {
                "id": i,
                "title": f"package-{i}",
                "slug": f"package-{i}",
                "description": "Test package",
                "category": "App",
                "item_type": "package",
                "pypi_url": None,
                "repo_url": None,
                "documentation_url": None,
                "repo_watchers": 100,
                "last_committed": None,
                "last_released": None,
            }
            for i in range(1, 16)
        ]

        respx_mock.get("https://djangopackages.org/api/v4/search/").mock(
            return_value=httpx.Response(200, json=mock_results)
        )

        # Mock package detail endpoints - only for the packages that will be requested
        # This tests that we only enrich the paginated subset
        package_detail_routes = []
        for i in range(1, 16):
            route = respx_mock.get(
                f"https://djangopackages.org/api/v4/packages/package-{i}/"
            ).mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "id": i,
                        "title": f"package-{i}",
                        "slug": f"package-{i}",
                        "category": "https://djangopackages.org/api/v4/categories/1/",
                        "grids": [],
                        "repo_description": "Test package",
                        "pypi_url": None,
                        "repo_url": None,
                        "documentation_url": None,
                        "repo_watchers": 100,
                        "repo_forks": 50,
                        "last_updated": None,
                    },
                )
            )
            package_detail_routes.append(route)

        # Mock category enrichment endpoint
        respx_mock.get("https://djangopackages.org/api/v4/categories/1/").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": 1,
                    "slug": "apps",
                    "title": "App",
                    "description": "Small components used to build projects",
                    "title_plural": "Apps",
                },
            )
        )

        async with DjangoPackagesClient() as client:
            # Returns all search results
            results = await client.search(query="test")
            assert len(results) == 15

            # Verify we got all packages
            for i in range(15):
                assert results[i].slug == f"package-{i + 1}"

        # Search no longer calls package detail endpoints
        for route in package_detail_routes:
            assert route.call_count == 0

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


class TestValidators:
    """Test validator functions for edge cases."""

    def test_extract_slug_from_url_with_none(self):
        from mcp_django.toolsets.packages import extract_slug_from_url

        assert extract_slug_from_url(None) is None

    def test_extract_slug_from_url_with_int(self):
        from mcp_django.toolsets.packages import extract_slug_from_url

        assert extract_slug_from_url(123) == 123

    def test_extract_slugs_from_urls_with_non_list(self):
        from mcp_django.toolsets.packages import extract_slugs_from_urls

        assert extract_slugs_from_urls("not-a-list") == "not-a-list"

    def test_parse_comma_separated_count_with_non_string(self):
        from mcp_django.toolsets.packages import parse_comma_separated_count

        assert parse_comma_separated_count(123) == 123

    @pytest.mark.asyncio
    async def test_package_resource_with_non_dict(self):
        from mcp_django.toolsets.packages import PackageResource

        # Test that model validator handles non-dict gracefully
        # This would normally raise a validation error, but the validator
        # should pass through non-dict values unchanged
        with pytest.raises(Exception):  # Pydantic will raise validation error
            PackageResource.model_validate("not-a-dict")
