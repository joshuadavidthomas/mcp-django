from __future__ import annotations

import re
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from django.conf import settings
from django.test import override_settings
from fastmcp import Client
from fastmcp.exceptions import ToolError

from mcp_django_shell.output import ExecutionStatus
from mcp_django_shell.server import mcp
from mcp_django_shell.server import shell

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def reset_client_session():
    async with Client(mcp) as client:
        await client.call_tool("django_reset", {})


async def test_instructions_match_registered_items():
    async with Client(mcp) as client:
        resources = await client.list_resources()
        templates = await client.list_resource_templates()
        tools = await client.list_tools()

        instructions = mcp.instructions

        assert instructions is not None

        for resource in resources:
            uri = str(resource.uri)
            pattern = rf"\b{re.escape(uri)}\b"
            assert re.search(pattern, instructions), (
                f"Resource {uri} not found in instructions"
            )

        for template in templates:
            uri = template.uriTemplate
            # Escape the template but keep the placeholders as wildcards
            # django://apps/{app_label} -> django://apps/\{app_label\}
            pattern = re.escape(uri)
            assert re.search(pattern, instructions), (
                f"Resource template {uri} not found in instructions"
            )

        for tool in tools:
            pattern = rf"\b{re.escape(tool.name)}\b"
            assert re.search(pattern, instructions), (
                f"Tool {tool.name} not found in instructions"
            )


async def test_tool_listing():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        tool_names = [tool.name for tool in tools]

        assert "django_shell" in tool_names
        assert "django_reset" in tool_names

        django_shell_tool = next(t for t in tools if t.name == "django_shell")
        assert django_shell_tool.description is not None
        assert "Useful exploration commands:" in django_shell_tool.description


async def test_django_shell_tool():
    async with Client(mcp) as client:
        result = await client.call_tool("django_shell", {"code": "2 + 2"})
        assert result.data.status == ExecutionStatus.SUCCESS
        assert result.data.output.value == "4"


@override_settings(
    INSTALLED_APPS=settings.INSTALLED_APPS
    + [
        "django.contrib.auth",
        "django.contrib.contenttypes",
    ]
)
async def test_django_shell_tool_orm():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "django_shell",
            {
                "code": "from django.contrib.auth import get_user_model; get_user_model().__name__"
            },
        )
        assert result.data.status == ExecutionStatus.SUCCESS


async def test_django_shell_tool_with_imports():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "django_shell",
            {"code": "os.path.join('test', 'path')", "imports": "import os"},
        )
        assert result.data.status == ExecutionStatus.SUCCESS
        assert result.data.output.value == "'test/path'"


async def test_django_shell_tool_without_imports():
    """Test that the tool still works when imports parameter is not provided"""
    async with Client(mcp) as client:
        result = await client.call_tool("django_shell", {"code": "2 + 2"})
        assert result.data.status == ExecutionStatus.SUCCESS
        assert result.data.output.value == "4"


async def test_django_shell_tool_with_multiple_imports():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "django_shell",
            {
                "code": "datetime.datetime.now().year + math.floor(math.pi)",
                "imports": "import datetime\nimport math",
            },
        )
        assert result.data.status == ExecutionStatus.SUCCESS


async def test_django_shell_tool_with_empty_imports():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "django_shell",
            {"code": "2 + 2", "imports": ""},
        )
        assert result.data.status == ExecutionStatus.SUCCESS
        assert result.data.output.value == "4"


async def test_django_shell_tool_imports_error():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "django_shell",
            {"code": "2 + 2", "imports": "import nonexistent_module"},
        )
        assert result.data.status == ExecutionStatus.ERROR
        assert "ModuleNotFoundError" in str(result.data.output.exception.exc_type)


async def test_django_shell_tool_imports_optimization():
    """Test that imports are optimized - already imported modules are skipped"""
    async with Client(mcp) as client:
        # First call imports os
        result1 = await client.call_tool(
            "django_shell",
            {"code": "os.path.join('test', 'first')", "imports": "import os"},
        )
        assert result1.data.status == ExecutionStatus.SUCCESS

        # Second call should not re-import os since it's already available
        # This tests that the optimization works (no duplicate import error)
        result2 = await client.call_tool(
            "django_shell",
            {"code": "os.path.join('test', 'second')", "imports": "import os"},
        )
        assert result2.data.status == ExecutionStatus.SUCCESS
        assert result2.data.output.value == "'test/second'"


async def test_django_shell_error_output():
    async with Client(mcp) as client:
        result = await client.call_tool("django_shell", {"code": "1 / 0"})

        assert result.data.status == ExecutionStatus.ERROR.value
        assert "ZeroDivisionError" in str(result.data.output.exception.exc_type)
        assert "division by zero" in result.data.output.exception.message
        assert len(result.data.output.exception.traceback) > 0
        assert not any(
            "mcp_django_shell" in line
            for line in result.data.output.exception.traceback
        )


async def test_django_shell_tool_unexpected_error(monkeypatch):
    monkeypatch.setattr(
        shell, "execute", AsyncMock(side_effect=RuntimeError("Unexpected error"))
    )

    async with Client(mcp) as client:
        with pytest.raises(ToolError, match="Unexpected error"):
            await client.call_tool("django_shell", {"code": "2 + 2"})


async def test_django_reset_session():
    async with Client(mcp) as client:
        await client.call_tool("django_shell", {"code": "x = 42"})

        result = await client.call_tool("django_reset", {})
        assert "reset" in result.data.lower()  # This one still returns a string

        result = await client.call_tool(
            "django_shell", {"code": "print('x' in globals())"}
        )
        # Check stdout contains "False"
        assert "False" in result.data.stdout


async def test_get_apps_resource():
    async with Client(mcp) as client:
        result = await client.read_resource("django://apps")
        assert result is not None
        assert len(result) > 0


async def test_get_models_resource():
    async with Client(mcp) as client:
        result = await client.read_resource("django://models")
        assert result is not None
        assert len(result) > 0


async def test_get_project_resource_no_auth():
    async with Client(mcp) as client:
        result = await client.read_resource("django://project")
        assert result is not None


@override_settings(
    INSTALLED_APPS=settings.INSTALLED_APPS
    + [
        "django.contrib.auth",
        "django.contrib.contenttypes",
    ]
)
async def test_project_resource_with_auth():
    async with Client(mcp) as client:
        result = await client.read_resource("django://project")
        assert result is not None
