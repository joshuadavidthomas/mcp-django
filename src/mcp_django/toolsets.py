from __future__ import annotations

from mcp_django.packages import DJANGOPACKAGES_TOOLSET
from mcp_django.packages import mcp as packages_mcp
from mcp_django.project import PROJECT_TOOLSET
from mcp_django.project import mcp as project_mcp
from mcp_django.shell import SHELL_TOOLSET
from mcp_django.shell import mcp as shell_mcp

__all__ = [
    "TOOLSETS",
]

TOOLSETS = {
    DJANGOPACKAGES_TOOLSET: packages_mcp,
    PROJECT_TOOLSET: project_mcp,
    SHELL_TOOLSET: shell_mcp,
}
