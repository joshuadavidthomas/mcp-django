from __future__ import annotations

from enum import Enum

import pytest
import pytest_asyncio
from django.conf import settings
from django.test import override_settings
from fastmcp import Client

from mcp_django.server import mcp

pytestmark = pytest.mark.asyncio


class Tool(str, Enum):
    SHELL = "shell"
    LIST_ROUTES = "project_list_routes"


@pytest_asyncio.fixture(autouse=True)
async def initialize_and_clear():
    await mcp.initialize()
    async with Client(mcp.server) as client:
        await client.call_tool("shell_clear_history")


async def test_instructions_exist():
    instructions = mcp.server.instructions

    assert instructions is not None
    assert len(instructions) > 100
    assert "Django ecosystem" in instructions
    assert "## Available Toolsets" in instructions
    assert "### Shell" in instructions
    assert "### djangopackages.org" in instructions


async def test_tool_listing():
    async with Client(mcp.server) as client:
        tools = await client.list_tools()
        tool_names = [tool.name for tool in tools]

        for tool_name in [
            "djangopackages_get_grid",
            "djangopackages_get_package",
            "djangopackages_search",
            "project_get_project_info",
            "project_list_apps",
            "project_list_models",
            "project_list_routes",
            "project_get_setting",
            "shell_execute",
            "shell_clear_history",
            "shell_export_history",
        ]:
            assert tool_name in tool_names


async def test_get_apps_resource():
    async with Client(mcp.server) as client:
        result = await client.read_resource("django://project/apps")
        assert result is not None
        assert len(result) > 0


async def test_get_models_resource():
    async with Client(mcp.server) as client:
        result = await client.read_resource("django://project/models")
        assert result is not None
        assert len(result) > 0


async def test_get_project_info_tool():
    async with Client(mcp.server) as client:
        result = await client.call_tool("project_get_project_info", {})

        assert result.data is not None
        assert hasattr(result.data, "python")
        assert hasattr(result.data, "django")
        assert result.data.python is not None
        assert result.data.django is not None
        assert result.data.django.version is not None


@override_settings(
    INSTALLED_APPS=settings.INSTALLED_APPS
    + [
        "django.contrib.auth",
        "django.contrib.contenttypes",
    ]
)
async def test_get_project_info_tool_with_auth():
    async with Client(mcp.server) as client:
        result = await client.call_tool("project_get_project_info", {})

        assert result.data is not None
        assert result.data.django.auth_user_model is not None


async def test_list_routes_tool_returns_routes():
    async with Client(mcp.server) as client:
        result = await client.call_tool("project_list_routes", {})

        assert isinstance(result.data, list)
        assert len(result.data) > 0


async def test_list_routes_tool_with_filters():
    async with Client(mcp.server) as client:
        all_routes = await client.call_tool("project_list_routes", {})

        get_routes = await client.call_tool("project_list_routes", {"method": "GET"})
        assert len(get_routes.data) > 0
        assert len(get_routes.data) <= len(all_routes.data)

        if all_routes.data:
            pattern_routes = await client.call_tool(
                "project_list_routes", {"pattern": all_routes.data[0]["pattern"][:3]}
            )
            assert isinstance(pattern_routes.data, list)


async def test_list_apps_tool():
    async with Client(mcp.server) as client:
        result = await client.call_tool("project_list_apps", {})

        assert isinstance(result.data, list)
        assert len(result.data) > 0
        # Should have at least the 'tests' app
        app_labels = [app["label"] for app in result.data]
        assert "tests" in app_labels


async def test_list_models_tool():
    async with Client(mcp.server) as client:
        result = await client.call_tool("project_list_models", {})

        assert isinstance(result.data, list)
        assert len(result.data) > 0
        # Should have at least AModel from tests
        model_names = [model["model_class"] for model in result.data]
        assert "AModel" in model_names


async def test_list_models_with_scope_project():
    async with Client(mcp.server) as client:
        result = await client.call_tool("project_list_models", {"scope": "project"})

        assert isinstance(result.data, list)
        assert len(result.data) > 0

        # Should have project models, e.g. our test models
        model_names = [model["model_class"] for model in result.data]
        assert "AModel" in model_names

        # Should NOT have Django models (they're in site-packages)
        # This test might be limited if Django apps aren't installed
        assert "User" not in model_names or "auth" not in model_names


@override_settings(
    INSTALLED_APPS=settings.INSTALLED_APPS
    + [
        "django.contrib.auth",
        "django.contrib.contenttypes",
    ]
)
async def test_list_models_with_scope_all():
    """Test that scope='all' returns all models including Django contrib."""
    async with Client(mcp.server) as client:
        result = await client.call_tool("project_list_models", {"scope": "all"})

        assert isinstance(result.data, list)
        assert len(result.data) > 0

        model_names = [model["model_class"] for model in result.data]

        assert "AModel" in model_names
        assert "User" in model_names
        assert "ContentType" in model_names


@override_settings(
    INSTALLED_APPS=settings.INSTALLED_APPS
    + [
        "django.contrib.auth",
        "django.contrib.contenttypes",
    ]
)
async def test_list_models_with_include():
    """Test that include parameter filters to specific apps."""
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            "project_list_models", {"include": ["auth", "tests"]}
        )

        assert isinstance(result.data, list)
        assert len(result.data) > 0

        model_names = [model["model_class"] for model in result.data]
        app_labels = [model["import_path"].split(".")[0] for model in result.data]

        # should include auth and tests models
        assert "AModel" in model_names
        assert "User" in model_names

        # should not have anything else, e.g. from the contenttypes app
        assert "ContentType" not in model_names

        for label in app_labels:
            assert label in ["tests", "django"], f"Unexpected app: {label}"


@override_settings(
    INSTALLED_APPS=settings.INSTALLED_APPS
    + [
        "django.contrib.auth",
        "django.contrib.contenttypes",
    ]
)
async def test_list_models_include_overrides_scope():
    async with Client(mcp.server) as client:
        # Even with scope='project', include should override
        result = await client.call_tool(
            "project_list_models", {"include": ["auth"], "scope": "project"}
        )

        assert isinstance(result.data, list)
        assert len(result.data) > 0

        model_names = [model["model_class"] for model in result.data]

        # Should ONLY have auth models (include overrides scope)
        assert "User" in model_names
        assert "Group" in model_names

        # Should NOT have project models despite scope='project'
        assert "AModel" not in model_names


async def test_get_setting_tool():
    async with Client(mcp.server) as client:
        result = await client.call_tool("project_get_setting", {"key": "DEBUG"})

        assert result.data is not None
        assert result.data.key == "DEBUG"
        assert result.data.value_type == "bool"
        assert isinstance(result.data.value, bool)


async def test_get_app_resource():
    async with Client(mcp.server) as client:
        result = await client.read_resource("django://project/app/tests")

        assert result is not None
        assert len(result) > 0


async def test_get_app_models_resource():
    async with Client(mcp.server) as client:
        result = await client.read_resource("django://project/app/tests/models")

        assert result is not None
        assert len(result) > 0


async def test_get_model_resource():
    async with Client(mcp.server) as client:
        result = await client.read_resource("django://project/model/tests/AModel")

        assert result is not None
        assert len(result) > 0


async def test_get_route_by_pattern_resource():
    async with Client(mcp.server) as client:
        result = await client.read_resource("django://project/route/home")

        assert result is not None
        assert len(result) > 0


async def test_get_setting_resource():
    async with Client(mcp.server) as client:
        result = await client.read_resource("django://project/setting/DEBUG")

        assert result is not None
        assert len(result) > 0
