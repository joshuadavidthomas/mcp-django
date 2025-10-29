from __future__ import annotations

import httpx
import pytest
from respx import MockRouter


# ============================================================================
# REUSABLE RESOURCE MOCKS
# These mock individual resources accessible by BOTH slug and ID
# ============================================================================


@pytest.fixture
def mock_category_apps(respx_mock: MockRouter):
    """Mock category 'apps' (id=1) - accessible by both slug and ID."""
    category_data = {
        "id": 1,
        "slug": "apps",
        "title": "App",
        "description": "Small components used to build projects",
        "title_plural": "Apps",
        "show_pypi": True,
        "created": "2010-08-14T22:47:52",
        "modified": "2022-03-04T21:48:41.249944",
    }

    respx_mock.get("https://djangopackages.org/api/v4/categories/apps/").mock(
        return_value=httpx.Response(200, json=category_data)
    )
    respx_mock.get("https://djangopackages.org/api/v4/categories/1/").mock(
        return_value=httpx.Response(200, json=category_data)
    )

    return category_data


@pytest.fixture
def mock_category_projects(respx_mock: MockRouter):
    """Mock category 'projects' (id=2) - accessible by both slug and ID."""
    category_data = {
        "id": 2,
        "slug": "projects",
        "title": "Project",
        "description": "Complete Django projects",
        "title_plural": "Projects",
        "show_pypi": False,
        "created": "2010-08-14T22:47:52",
        "modified": "2022-03-04T21:48:41.249944",
    }

    respx_mock.get("https://djangopackages.org/api/v4/categories/projects/").mock(
        return_value=httpx.Response(200, json=category_data)
    )
    respx_mock.get("https://djangopackages.org/api/v4/categories/2/").mock(
        return_value=httpx.Response(200, json=category_data)
    )

    return category_data


@pytest.fixture
def mock_package_1(respx_mock: MockRouter):
    """Mock package-1 (id=1) - accessible by both slug and ID."""
    package_data = {
        "id": 1,
        "slug": "package-1",
        "title": "Package 1",
        "category": "https://djangopackages.org/api/v4/categories/1/",
        "grids": [],
        "repo_description": "Package 1 description",
        "repo_url": "https://github.com/example/package-1",
        "pypi_url": "https://pypi.org/project/package-1/",
        "documentation_url": "https://package-1.readthedocs.io/",
        "repo_watchers": 100,
        "repo_forks": 50,
        "last_updated": "2024-01-01T00:00:00",
        "participants": ["user1", "user2"],
    }

    respx_mock.get("https://djangopackages.org/api/v4/packages/package-1/").mock(
        return_value=httpx.Response(200, json=package_data)
    )
    respx_mock.get("https://djangopackages.org/api/v4/packages/1/").mock(
        return_value=httpx.Response(200, json=package_data)
    )

    return package_data


@pytest.fixture
def mock_package_2(respx_mock: MockRouter):
    """Mock package-2 (id=2) - accessible by both slug and ID."""
    package_data = {
        "id": 2,
        "slug": "package-2",
        "title": "Package 2",
        "category": "https://djangopackages.org/api/v4/categories/1/",
        "grids": [],
        "repo_description": "Package 2 description",
        "repo_url": "https://github.com/example/package-2",
        "pypi_url": "https://pypi.org/project/package-2/",
        "documentation_url": "https://package-2.readthedocs.io/",
        "repo_watchers": 200,
        "repo_forks": 100,
        "last_updated": "2024-01-01T00:00:00",
        "participants": ["user3", "user4"],
    }

    respx_mock.get("https://djangopackages.org/api/v4/packages/package-2/").mock(
        return_value=httpx.Response(200, json=package_data)
    )
    respx_mock.get("https://djangopackages.org/api/v4/packages/2/").mock(
        return_value=httpx.Response(200, json=package_data)
    )

    return package_data


@pytest.fixture
def mock_package_3(respx_mock: MockRouter):
    """Mock package-3 (id=3) - accessible by both slug and ID."""
    package_data = {
        "id": 3,
        "slug": "package-3",
        "title": "Package 3",
        "category": "https://djangopackages.org/api/v4/categories/1/",
        "grids": [],
        "repo_description": "Package 3 description",
        "repo_url": "https://github.com/example/package-3",
        "pypi_url": "https://pypi.org/project/package-3/",
        "documentation_url": "https://package-3.readthedocs.io/",
        "repo_watchers": 300,
        "repo_forks": 150,
        "last_updated": "2024-01-01T00:00:00",
        "participants": ["user5", "user6"],
    }

    respx_mock.get("https://djangopackages.org/api/v4/packages/package-3/").mock(
        return_value=httpx.Response(200, json=package_data)
    )
    respx_mock.get("https://djangopackages.org/api/v4/packages/3/").mock(
        return_value=httpx.Response(200, json=package_data)
    )

    return package_data


@pytest.fixture
def mock_grid_11(respx_mock: MockRouter):
    """Mock grid-11 (id=11) - accessible by both slug and ID."""
    grid_data = {
        "id": 11,
        "slug": "grid-11",
        "title": "Grid 11",
        "description": "Grid 11 description",
        "packages": [],
        "is_locked": False,
        "header": False,
        "created": "2020-01-01T00:00:00",
        "modified": "2024-01-01T00:00:00",
    }

    respx_mock.get("https://djangopackages.org/api/v4/grids/grid-11/").mock(
        return_value=httpx.Response(200, json=grid_data)
    )
    respx_mock.get("https://djangopackages.org/api/v4/grids/11/").mock(
        return_value=httpx.Response(200, json=grid_data)
    )

    return grid_data


@pytest.fixture
def mock_grid_21(respx_mock: MockRouter):
    """Mock grid-21 (id=21) - accessible by both slug and ID."""
    grid_data = {
        "id": 21,
        "slug": "grid-21",
        "title": "Grid 21",
        "description": "Grid 21 description",
        "packages": [],
        "is_locked": False,
        "header": False,
        "created": "2020-01-01T00:00:00",
        "modified": "2024-01-01T00:00:00",
    }

    respx_mock.get("https://djangopackages.org/api/v4/grids/grid-21/").mock(
        return_value=httpx.Response(200, json=grid_data)
    )
    respx_mock.get("https://djangopackages.org/api/v4/grids/21/").mock(
        return_value=httpx.Response(200, json=grid_data)
    )

    return grid_data


@pytest.fixture
def mock_package_django_allauth(respx_mock: MockRouter):
    """Mock django-allauth (id=1) - accessible by both slug and ID."""
    package_data = {
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
        "pypi_version": "0.50.0",
        "last_updated": "2024-01-15T10:30:00",
        "participants": ["user1", "user2"],
    }

    respx_mock.get("https://djangopackages.org/api/v4/packages/django-allauth/").mock(
        return_value=httpx.Response(200, json=package_data)
    )
    respx_mock.get("https://djangopackages.org/api/v4/packages/1/").mock(
        return_value=httpx.Response(200, json=package_data)
    )

    return package_data


@pytest.fixture
def mock_package_django_oauth_toolkit(respx_mock: MockRouter):
    """Mock django-oauth-toolkit (id=2) - accessible by both slug and ID."""
    package_data = {
        "id": 2,
        "slug": "django-oauth-toolkit",
        "title": "django-oauth-toolkit",
        "category": "https://djangopackages.org/api/v4/categories/1/",
        "grids": [],
        "repo_description": "OAuth2 goodies for Django",
        "pypi_url": "https://pypi.org/project/django-oauth-toolkit/",
        "repo_url": "https://github.com/jazzband/django-oauth-toolkit",
        "documentation_url": "https://django-oauth-toolkit.readthedocs.io/",
        "repo_watchers": 2900,
        "repo_forks": 700,
        "pypi_version": "2.0.0",
        "last_updated": "2024-01-10T14:20:00",
        "participants": ["user3", "user4"],
    }

    respx_mock.get(
        "https://djangopackages.org/api/v4/packages/django-oauth-toolkit/"
    ).mock(return_value=httpx.Response(200, json=package_data))
    respx_mock.get("https://djangopackages.org/api/v4/packages/2/").mock(
        return_value=httpx.Response(200, json=package_data)
    )

    return package_data


@pytest.fixture
def mock_package_django_debug_toolbar(respx_mock: MockRouter):
    """Mock django-debug-toolbar - v3 API format."""
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


@pytest.fixture
def mock_grid_rest_frameworks(respx_mock: MockRouter):
    """Mock rest-frameworks grid - v3 API format."""
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


@pytest.fixture
def mock_grid_admin_interfaces(respx_mock: MockRouter):
    """Mock admin-interfaces grid - v3 API format."""
    grid_data = {
        "slug": "admin-interfaces",
        "title": "Admin interfaces",
        "description": "Enhanced admin interfaces",
        "packages": ["/api/v3/packages/package-3/"],
        "is_locked": False,
        "header": False,
    }

    respx_mock.get("https://djangopackages.org/api/v3/grids/admin-interfaces/").mock(
        return_value=httpx.Response(200, json=grid_data)
    )

    return grid_data


# ============================================================================
# COMPOSITE TEST FIXTURES
# These compose reusable mocks for specific test scenarios
# ============================================================================


@pytest.fixture
def mock_packages_search_api(
    respx_mock: MockRouter,
    mock_category_apps,
    mock_package_django_allauth,
    mock_package_django_oauth_toolkit,
):
    """Mock search API with enrichment dependencies."""
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

    return search_data


@pytest.fixture
def mock_packages_package_detail_api(
    mock_package_django_debug_toolbar,
):
    """Mock package detail API - v3 format with slugs in grid URLs."""
    return mock_package_django_debug_toolbar


@pytest.fixture
def mock_packages_grid_detail_api(
    mock_grid_rest_frameworks,
):
    """Mock grid detail API - v3 format with slugs in package URLs."""
    return mock_grid_rest_frameworks


@pytest.fixture
def mock_packages_search_single_api(
    respx_mock: MockRouter,
    mock_category_apps,
    mock_package_django_allauth,
):
    """Mock single-result search API with enrichment dependencies."""
    search_data = [
        {
            "id": 1,
            "title": "django-allauth",
            "slug": "django-allauth",
            "description": "Authentication package",
            "category": "App",
            "item_type": "package",
            "repo_watchers": 8500,
            "last_committed": "2024-01-15T10:30:00",
        }
    ]

    respx_mock.get("https://djangopackages.org/api/v4/search/").mock(
        return_value=httpx.Response(200, json=search_data)
    )

    return search_data


# ============================================================================
# CLIENT FIXTURES
# ============================================================================


@pytest.fixture
def packages_client(tmp_path):
    """Provides a DjangoPackagesClient with isolated tmp_path cache."""
    from mcp_django.toolsets.packages import DjangoPackagesClient

    return DjangoPackagesClient()
