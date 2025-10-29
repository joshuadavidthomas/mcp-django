from __future__ import annotations

from mcp_django.shell import SHELL_TOOLSET
from mcp_django.shell import mcp as shell_mcp

from .packages import DJANGOPACKAGES_TOOLSET
from .packages import mcp as packages_mcp

__all__ = [
    "TOOLSETS",
]

TOOLSETS = {
    DJANGOPACKAGES_TOOLSET: packages_mcp,
    SHELL_TOOLSET: shell_mcp,
}
