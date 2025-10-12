from __future__ import annotations

import warnings

warnings.warn(
    "mcp-django-shell is deprecated and will be removed in the next release. "
    "Shell functionality is now included in mcp-django>=0.10.0. "
    "Please uninstall mcp-django-shell and install mcp-django instead.",
    DeprecationWarning,
    stacklevel=2,
)

try:
    from mcp_django.code import filter_existing_imports
    from mcp_django.code import parse_code
    from mcp_django.output import DjangoShellOutput
    from mcp_django.output import ErrorOutput
    from mcp_django.output import ExceptionOutput
    from mcp_django.output import ExecutionStatus
    from mcp_django.output import ExpressionOutput
    from mcp_django.output import Output
    from mcp_django.output import StatementOutput
    from mcp_django.shell import DjangoShell
    from mcp_django.shell import ErrorResult
    from mcp_django.shell import ExpressionResult
    from mcp_django.shell import Result
    from mcp_django.shell import StatementResult
except ImportError:
    raise ImportError(
        "mcp-django>=0.10.0 must be installed for compatibility. "
        "Please install mcp-django>=0.10.0 and remove mcp-django-shell."
    )
