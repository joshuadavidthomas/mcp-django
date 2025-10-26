from __future__ import annotations

import httpx
import pytest
from respx import MockRouter


@pytest.fixture
def mock_packages_search_api(respx_mock: MockRouter):
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
    ]

    respx_mock.get("https://djangopackages.org/api/v4/search/").mock(
        return_value=httpx.Response(200, json=search_data)
    )

    for pkg_data in search_data:
        respx_mock.get(
            f"https://djangopackages.org/api/v4/packages/{pkg_data['slug']}/"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": pkg_data["id"],
                    "title": pkg_data["title"],
                    "slug": pkg_data["slug"],
                    "category": "https://djangopackages.org/api/v4/categories/1/",
                    "grids": [],
                    "repo_description": pkg_data["description"],
                    "pypi_url": pkg_data["pypi_url"],
                    "repo_url": pkg_data["repo_url"],
                    "documentation_url": pkg_data["documentation_url"],
                    "repo_watchers": pkg_data["repo_watchers"],
                    "repo_forks": 100,
                    "last_updated": pkg_data["last_committed"]
                    or pkg_data["last_released"],
                },
            )
        )

    return search_data


@pytest.fixture
def mock_packages_package_detail_api(respx_mock: MockRouter):
    package_data = {
        "id": 34,
        "title": "django-debug-toolbar",
        "slug": "django-debug-toolbar",
        "category": "https://djangopackages.org/api/v4/categories/1/",
        "grids": [
            "https://djangopackages.org/api/v4/grids/21/",
            "https://djangopackages.org/api/v4/grids/11/",
        ],
        "last_updated": "2024-06-01T07:50:28",
        "last_fetched": "2024-06-03T17:19:48.550707",
        "repo_url": "https://github.com/jazzband/django-debug-toolbar",
        "pypi_version": "4.3.0",
        "pypi_url": "http://pypi.python.org/pypi/django-debug-toolbar",
        "documentation_url": "https://readthedocs.org/projects/django-debug-toolbar",
        "repo_forks": 1027,
        "repo_description": "A configurable set of panels that display various debug information",
        "repo_watchers": 7937,
        "commits_over_52": [2, 1, 1, 3],
        "participants": ["user-1", "user-2"],
        "created": "2010-08-17T05:47:00.834356",
        "modified": "2024-06-03T17:19:49.078307",
    }

    respx_mock.get(
        "https://djangopackages.org/api/v4/packages/django-debug-toolbar/"
    ).mock(return_value=httpx.Response(200, json=package_data))

    return package_data


@pytest.fixture
def mock_packages_grids_api(respx_mock: MockRouter):
    grids_data = {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [
            {
                "id": 1,
                "title": "REST frameworks",
                "slug": "rest-frameworks",
                "description": "Packages for building REST APIs",
                "is_locked": False,
                "packages": [
                    "https://djangopackages.org/api/v4/packages/1/",
                    "https://djangopackages.org/api/v4/packages/2/",
                ],
                "header": False,
                "created": "2020-01-01T00:00:00",
                "modified": "2024-01-01T00:00:00",
            },
            {
                "id": 2,
                "title": "Admin interfaces",
                "slug": "admin-interfaces",
                "description": "Enhanced admin interfaces",
                "is_locked": False,
                "packages": ["https://djangopackages.org/api/v4/packages/3/"],
                "header": False,
                "created": "2020-01-01T00:00:00",
                "modified": "2024-01-01T00:00:00",
            },
        ],
    }

    respx_mock.get("https://djangopackages.org/api/v4/grids/").mock(
        return_value=httpx.Response(200, json=grids_data)
    )

    return grids_data


@pytest.fixture
def mock_packages_grid_detail_api(respx_mock: MockRouter):
    grid_data = {
        "id": 1,
        "title": "REST frameworks",
        "slug": "rest-frameworks",
        "description": "Packages for building REST APIs",
        "is_locked": False,
        "packages": [
            "https://djangopackages.org/api/v4/packages/1/",
            "https://djangopackages.org/api/v4/packages/2/",
        ],
        "header": False,
        "created": "2020-01-01T00:00:00",
        "modified": "2024-01-01T00:00:00",
    }

    respx_mock.get("https://djangopackages.org/api/v4/grids/rest-frameworks/").mock(
        return_value=httpx.Response(200, json=grid_data)
    )

    return grid_data


@pytest.fixture
def mock_packages_categories_api(respx_mock: MockRouter):
    categories_data = {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [
            {
                "id": 1,
                "title": "App",
                "slug": "apps",
                "description": "Small components used to build projects",
                "title_plural": "Apps",
                "show_pypi": True,
                "created": "2010-08-14T22:47:52",
                "modified": "2022-03-04T21:48:41.249944",
            },
            {
                "id": 2,
                "title": "Project",
                "slug": "projects",
                "description": "Complete Django projects",
                "title_plural": "Projects",
                "show_pypi": False,
                "created": "2010-08-14T22:47:52",
                "modified": "2022-03-04T21:48:41.249944",
            },
        ],
    }

    respx_mock.get("https://djangopackages.org/api/v4/categories/").mock(
        return_value=httpx.Response(200, json=categories_data)
    )

    return categories_data


@pytest.fixture
def mock_packages_category_detail_api(respx_mock: MockRouter):
    category_data = {
        "id": 1,
        "title": "App",
        "slug": "apps",
        "description": "Small components used to build projects",
        "title_plural": "Apps",
        "show_pypi": True,
        "created": "2010-08-14T22:47:52",
        "modified": "2022-03-04T21:48:41.249944",
    }

    respx_mock.get("https://djangopackages.org/api/v4/categories/apps/").mock(
        return_value=httpx.Response(200, json=category_data)
    )

    return category_data


@pytest.fixture
def mock_packages_search_single_api(respx_mock: MockRouter):
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

    package_detail = {
        "id": 1,
        "title": "django-allauth",
        "slug": "django-allauth",
        "category": "https://djangopackages.org/api/v4/categories/1/",
        "grids": [],
        "repo_description": "Authentication package",
        "repo_watchers": 8500,
        "last_updated": "2024-01-15T10:30:00",
    }

    respx_mock.get("https://djangopackages.org/api/v4/search/").mock(
        return_value=httpx.Response(200, json=search_data)
    )

    respx_mock.get("https://djangopackages.org/api/v4/packages/django-allauth/").mock(
        return_value=httpx.Response(200, json=package_detail)
    )

    return search_data
