from __future__ import annotations

from django.apps import AppConfig


class MCPShellConfig(AppConfig):
    name = "mcp_django.shell"
    label = "mcp_django_shell"
    verbose_name = "MCP Shell"
