from __future__ import annotations

import httpx
import pytest
from respx import MockRouter

from mcp_django.packages import CategoryResource
from mcp_django.packages import DjangoPackagesClient
from mcp_django.packages import GridResource
from mcp_django.packages import PackageDetailResource
from mcp_django.packages import SearchResultsResource
from mcp_django.packages import normalize_category


@pytest.mark.parametrize(
    "input_value,expected",
    [
        # None and empty cases
        (None, ""),
        ("", ""),
        # URL format with valid IDs
        ("https://djangopackages.org/api/v4/categories/1/", "apps"),
        ("https://djangopackages.org/api/v4/categories/2/", "frameworks"),
        ("https://djangopackages.org/api/v4/categories/3/", "projects"),
        ("https://djangopackages.org/api/v4/categories/4/", "other"),
        # URL format with unknown ID
        ("https://djangopackages.org/api/v4/categories/999/", ""),
        # Title format
        ("App", "apps"),
        ("Framework", "frameworks"),
        ("Project", "projects"),
        ("Other", "other"),
        # Slug format (already normalized)
        ("apps", "apps"),
        ("frameworks", "frameworks"),
        ("projects", "projects"),
        # Unknown/arbitrary strings
        ("SomeRandomCategory", "somerandomcategory"),
        ("custom-slug", "custom-slug"),
    ],
)
def test_normalize_category(input_value, expected):
    assert normalize_category(input_value) == expected


class TestDjangoPackagesClient:
    @pytest.mark.asyncio
    async def test_search_packages(self, mock_packages_search_api):
        async with DjangoPackagesClient() as client:
            results = await client.search_packages(query="auth", limit=10, offset=0)

        assert isinstance(results, SearchResultsResource)
        assert len(results.results) == 2
        assert results.count == 2
        assert results.has_more is False
        assert results.next_offset is None
        assert results.results[0].slug == "django-allauth"
        assert results.results[0].repo_watchers == 8500
        assert results.results[0].category == "apps"
        assert results.results[0].last_updated == "2024-01-15T10:30:00"

    @pytest.mark.asyncio
    async def test_search_packages_pagination(self, respx_mock: MockRouter, tmp_path):
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

        async with DjangoPackagesClient(cache_dir=tmp_path / "cache1") as client:
            # First page - should only fetch details for first 10 packages
            page1 = await client.search_packages(query="test", limit=10, offset=0)
            assert len(page1.results) == 10
            assert page1.count == 15
            assert page1.has_more is True
            assert page1.next_offset == 10

            for i in range(10):
                assert package_detail_routes[i].call_count == 1, (
                    f"package-{i + 1} should have been called once"
                )
            for i in range(10, 15):
                assert package_detail_routes[i].call_count == 0, (
                    f"package-{i + 1} should not have been called yet"
                )

        # Use a new client with different cache to test second page
        async with DjangoPackagesClient(cache_dir=tmp_path / "cache2") as client:
            page2 = await client.search_packages(query="test", limit=10, offset=10)
            assert len(page2.results) == 5
            assert page2.count == 15
            assert page2.has_more is False
            assert page2.next_offset is None

            for i in range(10, 15):
                assert package_detail_routes[i].call_count == 1, (
                    f"package-{i + 1} should have been called once"
                )

    @pytest.mark.asyncio
    async def test_get_package(self, mock_packages_package_detail_api):
        async with DjangoPackagesClient() as client:
            package = await client.get_package("django-debug-toolbar")

        assert isinstance(package, PackageDetailResource)
        assert package.slug == "django-debug-toolbar"
        assert package.repo_watchers == 7937
        assert package.pypi_version == "4.3.0"
        assert len(package.grids) == 2

    @pytest.mark.asyncio
    async def test_list_grids(self, mock_packages_grids_api):
        async with DjangoPackagesClient() as client:
            grids = await client.list_grids()

        assert isinstance(grids, list)
        assert len(grids) == 2
        assert all(isinstance(g, GridResource) for g in grids)
        assert grids[0].slug == "rest-frameworks"
        assert grids[1].slug == "admin-interfaces"

    @pytest.mark.asyncio
    async def test_get_grid(self, mock_packages_grid_detail_api):
        async with DjangoPackagesClient() as client:
            grid = await client.get_grid("rest-frameworks")

        assert isinstance(grid, GridResource)
        assert grid.slug == "rest-frameworks"
        assert len(grid.packages) == 2

    @pytest.mark.asyncio
    async def test_list_categories(self, mock_packages_categories_api):
        async with DjangoPackagesClient() as client:
            categories = await client.list_categories()

        assert isinstance(categories, list)
        assert len(categories) == 2
        assert all(isinstance(c, CategoryResource) for c in categories)
        assert categories[0].slug == "apps"
        assert categories[1].slug == "projects"

    @pytest.mark.asyncio
    async def test_get_category(self, mock_packages_category_detail_api):
        async with DjangoPackagesClient() as client:
            category = await client.get_category("apps")

        assert isinstance(category, CategoryResource)
        assert category.slug == "apps"
        assert category.title_plural == "Apps"

    @pytest.mark.asyncio
    async def test_client_context_manager(self, respx_mock: MockRouter):
        respx_mock.get("https://djangopackages.org/api/v4/search/").mock(
            return_value=httpx.Response(200, json=[])
        )

        client = DjangoPackagesClient()
        assert client.client is not None

        async with client:
            await client.search_packages(query="test")

        assert client.client.is_closed


class TestCachingBehavior:
    @pytest.mark.asyncio
    async def test_search_caches_package_details(
        self, respx_mock: MockRouter, tmp_path
    ):
        respx_mock.get("https://djangopackages.org/api/v4/search/").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "id": 1,
                        "slug": "django-allauth",
                        "title": "django-allauth",
                        "description": "Auth package",
                        "category": "App",
                        "item_type": "package",
                        "repo_watchers": 8500,
                        "last_committed": "2024-01-15T10:30:00",
                        "last_released": None,
                    }
                ],
            )
        )

        package_detail_route = respx_mock.get(
            "https://djangopackages.org/api/v4/packages/django-allauth/"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": 1,
                    "slug": "django-allauth",
                    "title": "django-allauth",
                    "category": "https://djangopackages.org/api/v4/categories/1/",
                    "grids": [],
                    "repo_description": "Integrated Django authentication",
                    "pypi_url": "https://pypi.org/project/django-allauth/",
                    "repo_url": "https://github.com/pennersr/django-allauth",
                    "documentation_url": "https://docs.allauth.org/",
                    "repo_watchers": 8500,
                    "repo_forks": 2000,
                    "last_updated": "2024-01-15T10:30:00",
                },
            )
        )

        async with DjangoPackagesClient(cache_dir=tmp_path) as client:
            # First search - should fetch from API and cache
            result1 = await client.search_packages("auth")
            assert len(result1.results) == 1
            assert (
                result1.results[0].pypi_url
                == "https://pypi.org/project/django-allauth/"
            )
            assert (
                result1.results[0].repo_url
                == "https://github.com/pennersr/django-allauth"
            )

            # Second search - should use cache, no API call to package details
            result2 = await client.search_packages("auth")
            assert len(result2.results) == 1
            assert (
                result2.results[0].pypi_url
                == "https://pypi.org/project/django-allauth/"
            )

        assert package_detail_route.call_count == 1

    @pytest.mark.asyncio
    async def test_get_package_uses_cache(
        self, mock_packages_package_detail_api, tmp_path
    ):
        async with DjangoPackagesClient(cache_dir=tmp_path) as client:
            # First call - fetches from API
            pkg1 = await client.get_package("django-debug-toolbar")
            assert pkg1.slug == "django-debug-toolbar"

            # Second call - should use cache
            pkg2 = await client.get_package("django-debug-toolbar")
            assert pkg2.slug == "django-debug-toolbar"
