from __future__ import annotations

import pytest
import pytest_asyncio
from fastmcp import Client

from mcp_django_shell.server import mcp

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
        assert "4" in result.data


async def test_django_shell_tool_orm():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "django_shell",
            {
                "code": "from django.contrib.auth import get_user_model; get_user_model().__name__"
            },
        )
        assert result.data is not None


async def test_django_reset_session():
    async with Client(mcp) as client:
        await client.call_tool("django_shell", {"code": "x = 42"})

        result = await client.call_tool("django_reset", {})
        assert "reset" in result.data.lower()

        result = await client.call_tool(
            "django_shell", {"code": "print('x' in globals())"}
        )
        assert "False" in result.data
