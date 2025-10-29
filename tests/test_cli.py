from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock
from unittest.mock import Mock

from mcp_django.cli import main


def test_cli_no_django_settings(monkeypatch, caplog):
    monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)

    result = main([])

    assert result == 1
    assert "DJANGO_SETTINGS_MODULE not set" in caplog.text


def test_cli_with_settings_arg(monkeypatch):
    mock_mcp = Mock()
    monkeypatch.setattr("mcp_django.server.mcp", mock_mcp)

    result = main(["--settings", "myapp.settings"])

    assert os.environ["DJANGO_SETTINGS_MODULE"] == "myapp.settings"
    mock_mcp.run.assert_called_once()
    assert result == 0


def test_cli_server_crash(monkeypatch, caplog):
    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "tests.settings")

    mock_mcp = Mock()
    mock_mcp.run.side_effect = Exception("Server crashed!")
    monkeypatch.setattr("mcp_django.server.mcp", mock_mcp)

    result = main([])

    assert result == 1
    assert "MCP server crashed" in caplog.text


def test_cli_with_pythonpath(monkeypatch):
    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "tests.settings")

    mock_mcp = Mock()
    # mock_mcp.run is already a Mock()
    monkeypatch.setattr("mcp_django.server.mcp", mock_mcp)

    test_path = "/test/path"
    result = main(["--pythonpath", test_path])

    assert test_path in sys.path
    assert result == 0


def test_cli_with_debug(monkeypatch):
    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "tests.settings")

    mock_mcp = Mock()
    # mock_mcp.run is already a Mock()
    monkeypatch.setattr("mcp_django.server.mcp", mock_mcp)

    result = main(["--debug"])

    assert result == 0


def test_cli_with_http_transport(monkeypatch):
    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "tests.settings")

    mock_mcp = Mock()
    # mock_mcp.run is already a Mock()
    monkeypatch.setattr("mcp_django.server.mcp", mock_mcp)

    result = main(
        [
            "--transport",
            "http",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--path",
            "/mcp",
        ]
    )

    mock_mcp.run.assert_called_once_with(
        transport="http", host="127.0.0.1", port=8000, path="/mcp"
    )
    assert result == 0


def test_cli_with_sse_transport(monkeypatch):
    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "tests.settings")

    mock_mcp = Mock()
    # mock_mcp.run is already a Mock()
    monkeypatch.setattr("mcp_django.server.mcp", mock_mcp)

    result = main(["--transport", "sse", "--host", "0.0.0.0", "--port", "9000"])

    mock_mcp.run.assert_called_once_with(transport="sse", host="0.0.0.0", port=9000)
    assert result == 0
