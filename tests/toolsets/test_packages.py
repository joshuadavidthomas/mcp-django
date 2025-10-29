from __future__ import annotations

import httpx
import pytest
import pytest_asyncio
from fastmcp import Client

from mcp_django.packages.models import extract_slug_from_url
from mcp_django.packages.models import extract_slugs_from_urls
from mcp_django.packages.models import parse_participant_list
from mcp_django.server import mcp


@pytest_asyncio.fixture(autouse=True)
async def initialize_mcp_server():
    await mcp.initialize()


def test_extract_slug_from_url_with_none():
    assert extract_slug_from_url(None) is None


def test_extract_slugs_from_urls_with_none():
    assert extract_slugs_from_urls(None) is None


def test_parse_participant_list_with_none():
    assert parse_participant_list(None) is None


@pytest.fixture
def mock_packages_grid_detail_api(respx_mock):
    grid_data = {
        "slug": "rest-frameworks",
        "title": "REST frameworks",
        "description": "Packages for building REST APIs",
        "packages": [
            "/api/v3/packages/package-1/",
            "/api/v3/packages/package-2/",
        ],
        "is_locked": False,
        "header": False,
    }

    respx_mock.get("https://djangopackages.org/api/v3/grids/rest-frameworks/").mock(
        return_value=httpx.Response(200, json=grid_data)
    )

    return grid_data


@pytest.mark.asyncio
async def test_get_grid_resource(mock_packages_grid_detail_api):
    async with Client(mcp.server) as client:
        contents = await client.read_resource(
            "django://djangopackages/grid/rest-frameworks"
        )
        assert isinstance(contents, list)
        assert len(contents) > 0


@pytest.mark.asyncio
async def test_get_grid_tool(mock_packages_grid_detail_api):
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            "djangopackages_get_grid", {"slug": "rest-frameworks"}
        )
        assert result.data is not None


@pytest.fixture
def mock_packages_package_detail_api(respx_mock):
    package_data = {
        "slug": "django-debug-toolbar",
        "title": "django-debug-toolbar",
        "category": "/api/v3/categories/apps/",
        "grids": [
            "/api/v3/grids/grid-21/",
            "/api/v3/grids/grid-11/",
        ],
        "modified": "2024-06-01T07:50:28",
        "repo_url": "https://github.com/jazzband/django-debug-toolbar",
        "pypi_version": "4.3.0",
        "pypi_url": "http://pypi.python.org/pypi/django-debug-toolbar",
        "documentation_url": "https://readthedocs.org/projects/django-debug-toolbar",
        "repo_forks": 1027,
        "repo_description": "A configurable set of panels that display various debug information",
        "repo_watchers": 7937,
        "participants": "user-1,user-2",
    }

    respx_mock.get(
        "https://djangopackages.org/api/v3/packages/django-debug-toolbar/"
    ).mock(return_value=httpx.Response(200, json=package_data))

    return package_data


@pytest.mark.asyncio
async def test_get_package_resource(mock_packages_package_detail_api):
    async with Client(mcp.server) as client:
        contents = await client.read_resource(
            "django://djangopackages/package/django-debug-toolbar"
        )
        assert isinstance(contents, list)
        assert len(contents) > 0


@pytest.mark.asyncio
async def test_get_package_tool(mock_packages_package_detail_api):
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            "djangopackages_get_package", {"slug": "django-debug-toolbar"}
        )
        assert result.data is not None


@pytest.mark.asyncio
async def test_search_djangopackages_tool(respx_mock):
    search_data = [
        {
            "id": 1,
            "title": "django-allauth",
            "slug": "django-allauth",
            "description": "Integrated set of Django applications addressing authentication",
            "category": "App",
            "item_type": "package",
            "pypi_url": "https://pypi.org/project/django-allauth/",
            "repo_url": "https://github.com/pennersr/django-allauth",
            "documentation_url": "https://docs.allauth.org/",
            "repo_watchers": 8500,
            "last_committed": "2024-01-15T10:30:00",
            "last_released": None,
        },
        {
            "id": 2,
            "title": "django-oauth-toolkit",
            "slug": "django-oauth-toolkit",
            "description": "OAuth2 goodies for Django",
            "category": "App",
            "item_type": "package",
            "pypi_url": "https://pypi.org/project/django-oauth-toolkit/",
            "repo_url": "https://github.com/jazzband/django-oauth-toolkit",
            "documentation_url": "https://django-oauth-toolkit.readthedocs.io/",
            "repo_watchers": 2900,
            "last_committed": None,
            "last_released": "2024-01-10T14:20:00",
        },
        {
            "id": 3,
            "title": "Authentication",
            "slug": "authentication",
            "description": "This is a grid of all packages for user authentication.",
            "item_type": "grid",
        },
    ]

    respx_mock.get("https://djangopackages.org/api/v4/search/").mock(
        return_value=httpx.Response(200, json=search_data)
    )
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            "djangopackages_search", {"query": "authentication"}
        )
        assert result.data is not None
        assert len(result.data) > 0
