from __future__ import annotations

from enum import Enum
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from django.conf import settings
from django.test import override_settings
from fastmcp import Client
from fastmcp.exceptions import ToolError

from mcp_django.output import ExecutionStatus
from mcp_django.server import mcp
from mcp_django.shell import django_shell

pytestmark = pytest.mark.asyncio


class Tool(str, Enum):
    SHELL = "shell"
    LIST_ROUTES = "list_routes"


@pytest_asyncio.fixture(autouse=True)
async def initialize_and_reset():
    await mcp.initialize()
    async with Client(mcp.server) as client:
        await client.call_tool(Tool.SHELL, {"action": "reset"})


async def test_instructions_exist():
    instructions = mcp.server.instructions

    assert instructions is not None
    assert "Django project exploration" in instructions
    assert "Available Toolsets" in instructions


async def test_tool_listing():
    async with Client(mcp.server) as client:
        tools = await client.list_tools()
        tool_names = [tool.name for tool in tools]

        assert Tool.SHELL in tool_names
        assert Tool.LIST_ROUTES in tool_names

        django_shell_tool = next(t for t in tools if t.name == Tool.SHELL)
        assert django_shell_tool.description is not None
        assert "Useful exploration commands:" in django_shell_tool.description


async def test_get_apps_tool():
    async with Client(mcp.server) as client:
        result = await client.call_tool("get_apps", {})
        assert result.data is not None
        assert len(result.data) > 0


async def test_get_models_tool():
    async with Client(mcp.server) as client:
        result = await client.call_tool("get_models", {})
        assert result.data is not None
        assert len(result.data) > 0


async def test_get_project_tool_no_auth():
    async with Client(mcp.server) as client:
        result = await client.call_tool("get_project", {})
        assert result.data is not None


async def test_django_shell_tool():
    async with Client(mcp.server) as client:
        result = await client.call_tool(Tool.SHELL, {"code": "2 + 2"})
        assert result.data["status"] == ExecutionStatus.SUCCESS
        assert result.data["output"]["value"] == "4"


@override_settings(
    INSTALLED_APPS=settings.INSTALLED_APPS
    + [
        "django.contrib.auth",
        "django.contrib.contenttypes",
    ]
)
async def test_django_shell_tool_orm():
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            Tool.SHELL,
            {
                "code": "from django.contrib.auth import get_user_model; get_user_model().__name__"
            },
        )
        assert result.data["status"] == ExecutionStatus.SUCCESS


async def test_django_shell_tool_with_imports():
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            Tool.SHELL,
            {"code": "os.path.join('test', 'path')", "imports": "import os"},
        )
        assert result.data["status"] == ExecutionStatus.SUCCESS
        assert result.data["output"]["value"] == "'test/path'"


async def test_django_shell_tool_without_imports():
    async with Client(mcp.server) as client:
        result = await client.call_tool(Tool.SHELL, {"code": "2 + 2"})
        assert result.data["status"] == ExecutionStatus.SUCCESS
        assert result.data["output"]["value"] == "4"


async def test_django_shell_tool_with_multiple_imports():
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            Tool.SHELL,
            {
                "code": "datetime.datetime.now().year + math.floor(math.pi)",
                "imports": "import datetime\nimport math",
            },
        )
        assert result.data["status"] == ExecutionStatus.SUCCESS


async def test_django_shell_tool_with_empty_imports():
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            Tool.SHELL,
            {"code": "2 + 2", "imports": ""},
        )
        assert result.data["status"] == ExecutionStatus.SUCCESS
        assert result.data["output"]["value"] == "4"


async def test_django_shell_tool_imports_error():
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            Tool.SHELL,
            {"code": "2 + 2", "imports": "import nonexistent_module"},
        )
        assert result.data["status"] == ExecutionStatus.ERROR
        assert "ModuleNotFoundError" in str(
            result.data["output"]["exception"]["exc_type"]
        )


async def test_django_shell_tool_imports_optimization():
    async with Client(mcp.server) as client:
        # First call imports os
        result1 = await client.call_tool(
            Tool.SHELL,
            {"code": "os.path.join('test', 'first')", "imports": "import os"},
        )
        assert result1.data["status"] == ExecutionStatus.SUCCESS

        # Second call should not re-import os since it's already available
        # This tests that the optimization works (no duplicate import error)
        result2 = await client.call_tool(
            Tool.SHELL,
            {"code": "os.path.join('test', 'second')", "imports": "import os"},
        )
        assert result2.data["status"] == ExecutionStatus.SUCCESS
        assert result2.data["output"]["value"] == "'test/second'"


async def test_django_shell_error_output():
    async with Client(mcp.server) as client:
        result = await client.call_tool(Tool.SHELL, {"code": "1 / 0"})

        assert result.data["status"] == ExecutionStatus.ERROR.value
        assert "ZeroDivisionError" in str(
            result.data["output"]["exception"]["exc_type"]
        )
        assert "division by zero" in result.data["output"]["exception"]["message"]
        assert len(result.data["output"]["exception"]["traceback"]) > 0
        assert not any(
            "mcp_django/shell" in line
            for line in result.data["output"]["exception"]["traceback"]
        )


async def test_django_shell_tool_execute_without_code():
    async with Client(mcp.server) as client:
        with pytest.raises(ToolError) as exc_info:
            await client.call_tool(Tool.SHELL, {"action": "execute"})

        assert "Code parameter is required" in str(exc_info.value)


async def test_django_shell_tool_reset_with_code():
    async with Client(mcp.server) as client:
        with pytest.raises(ToolError) as exc_info:
            await client.call_tool(
                Tool.SHELL, {"action": "reset", "code": "print('test')"}
            )

        assert "Code parameter cannot be used with" in str(exc_info.value)
        assert "reset" in str(exc_info.value)


async def test_django_shell_tool_unexpected_error(monkeypatch):
    monkeypatch.setattr(
        django_shell, "execute", AsyncMock(side_effect=RuntimeError("Unexpected error"))
    )

    async with Client(mcp.server) as client:
        with pytest.raises(ToolError, match="Unexpected error"):
            await client.call_tool(Tool.SHELL, {"code": "2 + 2"})


async def test_django_reset_session():
    async with Client(mcp.server) as client:
        await client.call_tool(Tool.SHELL, {"code": "x = 42"})

        result = await client.call_tool(Tool.SHELL, {"action": "reset"})
        assert (
            "reset" in result.content[0].text.lower()
        )  # This one still returns a string

        result = await client.call_tool(Tool.SHELL, {"code": "print('x' in globals())"})
        # Check stdout contains "False"
        assert "False" in result.data["stdout"]


@override_settings(
    INSTALLED_APPS=settings.INSTALLED_APPS
    + [
        "django.contrib.auth",
        "django.contrib.contenttypes",
    ]
)
async def test_project_tool_with_auth():
    async with Client(mcp.server) as client:
        result = await client.call_tool("get_project", {})
        assert result.data is not None


async def test_list_routes_tool_returns_routes():
    async with Client(mcp.server) as client:
        result = await client.call_tool("list_routes", {})

        assert isinstance(result.data, list)
        assert len(result.data) > 0


async def test_list_routes_tool_with_filters():
    async with Client(mcp.server) as client:
        all_routes = await client.call_tool("list_routes", {})

        get_routes = await client.call_tool("list_routes", {"method": "GET"})
        assert len(get_routes.data) > 0
        assert len(get_routes.data) <= len(all_routes.data)

        if all_routes.data:
            pattern_routes = await client.call_tool(
                "list_routes", {"pattern": all_routes.data[0]["pattern"][:3]}
            )
            assert isinstance(pattern_routes.data, list)
