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
async def initialize_and_clear():
    await mcp.initialize()
    async with Client(mcp.server) as client:
        await client.call_tool("shell_clear_history")


async def test_shell_execute():
    async with Client(mcp.server) as client:
        result = await client.call_tool("shell_execute", {"code": "print(2 + 2)"})
        assert result.data["status"] == ExecutionStatus.SUCCESS
        assert result.data["stdout"] == "4\n"


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
            {"code": "import os\nprint(os.path.join('test', 'path'))"},
        )
        assert result.data["status"] == ExecutionStatus.SUCCESS
        assert result.data["stdout"] == "test/path\n"


async def test_shell_execute_without_imports():
    async with Client(mcp.server) as client:
        result = await client.call_tool("shell_execute", {"code": "print(2 + 2)"})
        assert result.data["status"] == ExecutionStatus.SUCCESS
        assert result.data["stdout"] == "4\n"


async def test_shell_execute_with_multiple_imports():
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            "shell_execute",
            {
                "code": "import datetime\nimport math\ndatetime.datetime.now().year + math.floor(math.pi)",
            },
        )
        assert result.data["status"] == ExecutionStatus.SUCCESS


async def test_shell_execute_imports_error():
    async with Client(mcp.server) as client:
        result = await client.call_tool(
            "shell_execute",
            {"code": "import nonexistent_module"},
        )
        assert result.data["status"] == ExecutionStatus.ERROR
        assert "ModuleNotFoundError" in str(
            result.data["output"]["exception"]["exc_type"]
        )


async def test_shell_execute_stateless():
    """Test that each execution uses fresh globals (stateless)."""
    async with Client(mcp.server) as client:
        # First call imports and uses os
        result1 = await client.call_tool(
            "shell_execute",
            {"code": "import os\nprint(os.path.join('test', 'first'))"},
        )
        assert result1.data["status"] == ExecutionStatus.SUCCESS

        # Second call should NOT have os available (fresh globals)
        result2 = await client.call_tool(
            "shell_execute",
            {"code": "print(os.path.join('test', 'second'))"},  # No import!
        )
        assert result2.data["status"] == ExecutionStatus.ERROR
        assert "NameError" in str(result2.data["output"]["exception"]["exc_type"])


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


async def test_shell_export_history_to_string():
    """Test that export_history returns script as string."""
    async with Client(mcp.server) as client:
        # Execute some code to create history
        await client.call_tool("shell_execute", {"code": "print(2 + 2)"})
        await client.call_tool("shell_execute", {"code": "x = 5"})

        # Export history
        result = await client.call_tool("shell_export_history")
        script = result.content[0].text

        # Verify script content
        assert "# Django Shell Session Export" in script
        assert "print(2 + 2)" in script
        assert "x = 5" in script


async def test_shell_export_history_excludes_errors():
    """Test that export_history excludes errors."""
    async with Client(mcp.server) as client:
        # Execute code with error
        await client.call_tool("shell_execute", {"code": "1 / 0"})

        # Export - errors should be excluded
        result = await client.call_tool("shell_export_history")
        script = result.content[0].text
        assert "1 / 0" not in script


async def test_shell_export_history_to_file(tmp_path):
    """Test that export_history can save to file."""
    import os
    old_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        async with Client(mcp.server) as client:
            # Execute some code
            await client.call_tool("shell_execute", {"code": "x = 42"})

            # Export to file
            result = await client.call_tool("shell_export_history", {"filename": "test_script"})
            output = result.content[0].text

            # Should mention the file
            assert "test_script.py" in output
            assert "Exported" in output

            # File should exist
            assert (tmp_path / "test_script.py").exists()
    finally:
        os.chdir(old_cwd)


async def test_shell_export_history_error_handling():
    """Test that export_history handles exceptions gracefully."""
    from unittest.mock import patch
    async with Client(mcp.server) as client:
        # Execute some code
        await client.call_tool("shell_execute", {"code": "x = 1"})

        # Mock export_history to raise an exception
        with patch.object(django_shell, "export_history", side_effect=ValueError("Test error")):
            with pytest.raises(ToolError, match="Test error"):
                await client.call_tool("shell_export_history")


async def test_shell_clear_history():
    """Test that clear_history clears the execution history."""
    async with Client(mcp.server) as client:
        # Execute some code to create history
        await client.call_tool("shell_execute", {"code": "print(2 + 2)"})
        await client.call_tool("shell_execute", {"code": "print(3 + 3)"})

        # Verify history exists
        assert len(django_shell.history) == 2

        # Clear history
        result = await client.call_tool("shell_clear_history")
        assert "cleared" in result.content[0].text.lower()

        # Verify history is empty
        assert len(django_shell.history) == 0
