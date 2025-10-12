from __future__ import annotations

import warnings

warnings.warn(
    "mcp-django-shell is deprecated and will be removed in the next release. "
    "Shell functionality is now included in mcp-django>=0.10.0. "
    "Please uninstall mcp-django-shell and install mcp-django instead.",
    DeprecationWarning,
    stacklevel=2,
)
