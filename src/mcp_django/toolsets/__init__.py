from __future__ import annotations

from .packages import DJANGOPACKAGES_TOOLSET
from .packages import mcp as packages_mcp

__all__ = ["TOOLSETS", "DJANGOPACKAGES_TOOLSET"]

TOOLSETS = {
    DJANGOPACKAGES_TOOLSET: packages_mcp,
}
