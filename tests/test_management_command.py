from __future__ import annotations

import pytest
import pytest_asyncio
from fastmcp import Client

from mcp_django.server import mcp

pytestmark = [pytest.mark.asyncio, pytest.mark.django_db]


@pytest_asyncio.fixture(autouse=True)
async def initialize_server():
    """Initialize the MCP server before tests."""
    await mcp.initialize()


async def test_management_command_check():
    """Test running the 'check' command (safe, read-only)."""
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            "management_execute_command",
            {
                "command": "check",
            },
        )

        assert result.data is not None
        assert result.data.status == "success"
        assert result.data.command == "check"
        assert result.data.args == []
        assert result.data.exception is None
        # The check command should produce some output to stderr
        assert (
            "System check identified" in result.data.stderr or result.data.stderr == ""
        )


async def test_management_command_with_args():
    """Test running a command with positional arguments."""
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            "management_execute_command",
            {
                "command": "showmigrations",
                "args": ["tests"],
            },
        )

        assert result.data is not None
        assert result.data.status == "success"
        assert result.data.command == "showmigrations"
        assert result.data.args == ["tests"]
        assert result.data.exception is None


async def test_management_command_with_options():
    """Test running a command with keyword options."""
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            "management_execute_command",
            {
                "command": "check",
                "options": {"verbosity": 2},
            },
        )

        assert result.data is not None
        assert result.data.status == "success"
        assert result.data.command == "check"
        assert result.data.exception is None


async def test_management_command_with_args_and_options():
    """Test running a command with both args and options."""
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            "management_execute_command",
            {
                "command": "showmigrations",
                "args": ["tests"],
                "options": {"verbosity": 0},
            },
        )

        assert result.data is not None
        assert result.data.status == "success"
        assert result.data.command == "showmigrations"
        assert result.data.args == ["tests"]
        assert result.data.exception is None


async def test_management_command_invalid_command():
    """Test running an invalid/non-existent command."""
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            "management_execute_command",
            {
                "command": "this_command_does_not_exist",
            },
        )

        assert result.data is not None
        assert result.data.status == "error"
        assert result.data.command == "this_command_does_not_exist"
        assert result.data.exception is not None
        assert result.data.exception.type in [
            "CommandError",
            "ManagementUtilityError",
        ]
        assert "Unknown command" in result.data.exception.message


async def test_management_command_makemigrations_dry_run():
    """Test running makemigrations with --dry-run (safe, read-only)."""
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            "management_execute_command",
            {
                "command": "makemigrations",
                "options": {"dry_run": True, "verbosity": 0},
            },
        )

        assert result.data is not None
        assert result.data.status == "success"
        assert result.data.command == "makemigrations"
        assert result.data.args == []
        assert result.data.exception is None


async def test_management_command_diffsettings():
    """Test running diffsettings command (read-only introspection)."""
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            "management_execute_command",
            {
                "command": "diffsettings",
                "options": {"all": True},
            },
        )

        assert result.data is not None
        assert result.data.status == "success"
        assert result.data.command == "diffsettings"
        # Should output settings
        assert len(result.data.stdout) > 0


async def test_management_command_stdout_capture():
    """Test that stdout is properly captured from commands."""
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            "management_execute_command",
            {
                "command": "check",
                "options": {"verbosity": 2},
            },
        )

        assert result.data is not None
        assert result.data.status == "success"
        # With higher verbosity, check should produce output
        assert isinstance(result.data.stdout, str)
        assert isinstance(result.data.stderr, str)


async def test_management_command_list_in_main_server():
    """Test that management_command tool is listed in main server tools."""
    async with Client(mcp.server) as client:
        tools = await client.list_tools()
        tool_names = [tool.name for tool in tools]

        assert "management_execute_command" in tool_names

        # Find the tool and check its metadata
        mgmt_tool = next(
            tool for tool in tools if tool.name == "management_execute_command"
        )
        assert mgmt_tool.description is not None
        assert "management command" in mgmt_tool.description.lower()


async def test_list_management_commands():
    """Test listing all available management commands."""
    async with Client(mcp.server) as client:
        result = await client.call_tool("management_list_commands", {})

        assert result.data is not None
        assert isinstance(result.data, list)
        assert len(result.data) > 0

        # Check that we have some standard Django commands
        command_names = [cmd["name"] for cmd in result.data]
        assert "check" in command_names
        assert "migrate" in command_names
        assert "showmigrations" in command_names

        # Verify structure of command info
        first_cmd = result.data[0]
        assert "name" in first_cmd
        assert "app_name" in first_cmd
        assert isinstance(first_cmd["name"], str)
        assert isinstance(first_cmd["app_name"], str)


async def test_list_management_commands_includes_custom_commands():
    """Test that custom management commands are included in the list."""
    async with Client(mcp.server) as client:
        result = await client.call_tool("management_list_commands", {})

        assert result.data is not None
        command_names = [cmd["name"] for cmd in result.data]

        # The mcp command from this project should be in the list
        assert "mcp" in command_names


async def test_list_management_commands_sorted():
    """Test that management commands are sorted alphabetically."""
    async with Client(mcp.server) as client:
        result = await client.call_tool("management_list_commands", {})

        assert result.data is not None
        command_names = [cmd["name"] for cmd in result.data]

        # Verify the list is sorted
        assert command_names == sorted(command_names)
