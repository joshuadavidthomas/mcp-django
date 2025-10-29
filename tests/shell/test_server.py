from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from django.conf import settings
from django.test import override_settings
from fastmcp import Client
from fastmcp.exceptions import ToolError

from mcp_django.server import mcp
from mcp_django.shell.core import django_shell
from mcp_django.shell.output import ExecutionStatus

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def initialize_and_reset():
    await mcp.initialize()
    async with Client(mcp.server) as client:
        await client.call_tool("shell_reset")


async def test_shell_execute():
    async with Client(mcp.server) as client:
        result = await client.call_tool("shell_execute", {"code": "2 + 2"})
        assert result.data["status"] == ExecutionStatus.SUCCESS
        assert result.data["output"]["value"] == "4"


@override_settings(
    INSTALLED_APPS=settings.INSTALLED_APPS
    + [
        "django.contrib.auth",
        "django.contrib.contenttypes",
    ]
)
async def test_shell_execute_orm():
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            "shell_execute",
            {
                "code": "from django.contrib.auth import get_user_model; get_user_model().__name__"
            },
        )
        assert result.data["status"] == ExecutionStatus.SUCCESS


async def test_shell_execute_with_imports():
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            "shell_execute",
            {"code": "os.path.join('test', 'path')", "imports": "import os"},
        )
        assert result.data["status"] == ExecutionStatus.SUCCESS
        assert result.data["output"]["value"] == "'test/path'"


async def test_shell_execute_without_imports():
    async with Client(mcp.server) as client:
        result = await client.call_tool("shell_execute", {"code": "2 + 2"})
        assert result.data["status"] == ExecutionStatus.SUCCESS
        assert result.data["output"]["value"] == "4"


async def test_shell_execute_with_multiple_imports():
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            "shell_execute",
            {
                "code": "datetime.datetime.now().year + math.floor(math.pi)",
                "imports": "import datetime\nimport math",
            },
        )
        assert result.data["status"] == ExecutionStatus.SUCCESS


async def test_shell_execute_with_empty_imports():
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            "shell_execute",
            {"code": "2 + 2", "imports": ""},
        )
        assert result.data["status"] == ExecutionStatus.SUCCESS
        assert result.data["output"]["value"] == "4"


async def test_shell_execute_imports_error():
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            "shell_execute",
            {"code": "2 + 2", "imports": "import nonexistent_module"},
        )
        assert result.data["status"] == ExecutionStatus.ERROR
        assert "ModuleNotFoundError" in str(
            result.data["output"]["exception"]["exc_type"]
        )


async def test_shell_execute_imports_optimization():
    async with Client(mcp.server) as client:
        # First call imports os
        result1 = await client.call_tool(
            "shell_execute",
            {"code": "os.path.join('test', 'first')", "imports": "import os"},
        )
        assert result1.data["status"] == ExecutionStatus.SUCCESS

        # Second call should not re-import os since it's already available
        # This tests that the optimization works (no duplicate import error)
        result2 = await client.call_tool(
            "shell_execute",
            {"code": "os.path.join('test', 'second')", "imports": "import os"},
        )
        assert result2.data["status"] == ExecutionStatus.SUCCESS
        assert result2.data["output"]["value"] == "'test/second'"


async def test_shell_execute_error_output():
    async with Client(mcp.server) as client:
        result = await client.call_tool("shell_execute", {"code": "1 / 0"})

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


async def test_shell_execute_unexpected_error(monkeypatch):
    monkeypatch.setattr(
        django_shell, "execute", AsyncMock(side_effect=RuntimeError("Unexpected error"))
    )

    async with Client(mcp.server) as client:
        with pytest.raises(ToolError, match="Unexpected error"):
            await client.call_tool("shell_execute", {"code": "2 + 2"})


async def test_shell_reset():
    async with Client(mcp.server) as client:
        await client.call_tool("shell_execute", {"code": "x = 42"})

        result = await client.call_tool("shell_reset")
        assert (
            "reset" in result.content[0].text.lower()
        )  # This one still returns a string

        result = await client.call_tool(
            "shell_execute", {"code": "print('x' in globals())"}
        )
        # Check stdout contains "False"
        assert "False" in result.data["stdout"]
