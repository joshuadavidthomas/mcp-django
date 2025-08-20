from __future__ import annotations

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
