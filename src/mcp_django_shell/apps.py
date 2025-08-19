from __future__ import annotations

from django.apps import AppConfig


class MCPShellConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mcp_django_shell"
    verbose_name = "MCP Shell"
