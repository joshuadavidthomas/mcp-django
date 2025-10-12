# Consolidation Plan: mcp-django-shell → mcp-django

## Overview

This plan consolidates the `mcp-django-shell` package into the main `mcp-django` package. The shell functionality will become part of the core package instead of being a separate optional dependency.

## Key Decisions

1. **Shell tools become part of core** - No longer optional via extras
2. **Tool names**: `django_shell` and `django_shell_reset` (removing `shell_` prefix from mounting)
3. **Module organization**: Flat structure in `src/mcp_django/`
4. **Backward compatibility**: Deprecation shim for one release cycle
5. **Version strategy**: Bump to 0.10.0 using SemVer (CalVer in .github/VERSION was previously used for coordinating multi-package releases, no longer needed after consolidation)
6. **Deprecation timeline**: Deprecate in 0.10.0, remove in 0.11.0
7. **Server integration**: Direct registration, unified server
8. **PyPI management**: Leave deprecated mcp-django-shell on PyPI with deprecation notices
9. **CI/CD**: Remove multi-package build logic immediately

---

## Release 0.10.0 - Consolidation with Deprecation

### 1. File Movements

**Move these files:**
```bash
packages/mcp-django-shell/src/mcp_django_shell/shell.py → src/mcp_django/shell.py
packages/mcp-django-shell/src/mcp_django_shell/code.py → src/mcp_django/code.py  
packages/mcp-django-shell/src/mcp_django_shell/output.py → src/mcp_django/output.py
```

### 2. Code Changes

#### `src/mcp_django/server.py` - Complete rewrite

Replace lines 17-91 with unified server implementation:

```python
from __future__ import annotations

import logging
from typing import Annotated

from django.apps import apps
from fastmcp import Context
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .code import filter_existing_imports
from .code import parse_code
from .output import DjangoShellOutput
from .output import ErrorOutput
from .resources import AppResource
from .resources import ModelResource
from .resources import ProjectResource
from .shell import DjangoShell

logger = logging.getLogger(__name__)
shell = DjangoShell()

mcp = FastMCP(
    name="Django",
    instructions="""Provides Django resource endpoints for project exploration and a stateful shell environment for executing Python code.

RESOURCES:
Use resources for orientation. Resources provide precise coordinates (import paths, file
locations) to avoid exploration overhead.

- django://project - Python/Django environment metadata (versions, settings, database config)
- django://apps - All Django apps with their file paths
- django://models - All models with import paths and source locations

TOOLS:
The shell maintains state between calls - imports and variables persist. Use django_shell_reset to
clear state when variables get messy or you need a fresh start.

- django_shell - Execute Python code in a stateful Django shell
- django_shell_reset - Reset the shell session

EXAMPLES:
The pattern: Resource → Import Path → Shell Operation. Resources provide coordinates, shell does
the work.

- Starting fresh? → Check django://project to understand environment and available apps
- Need information about a model? → Check django://models → Get import path →
  `from app.models import ModelName` in django_shell
- Need app structure? → Check django://apps for app labels and paths → Use paths in django_shell
- Need to query data? → Get model from django://models → Import in django_shell → Run queries
""",
)


@mcp.resource(
    "django://project",
    name="Django Project Information",
    mime_type="application/json",
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
def get_project() -> ProjectResource:
    """Get comprehensive project information including Python environment and Django configuration.

    Use this to understand the project's runtime environment, installed apps, and database
    configuration.
    """
    return ProjectResource.from_env()


@mcp.resource(
    "django://apps",
    name="Installed Django Apps",
    mime_type="application/json",
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
def get_apps() -> list[AppResource]:
    """Get a list of all installed Django applications with their models.

    Use this to explore the project structure and available models without executing code.
    """
    return [AppResource.from_app(app) for app in apps.get_app_configs()]


@mcp.resource(
    "django://models",
    name="Django Models",
    mime_type="application/json",
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
def get_models() -> list[ModelResource]:
    """Get detailed information about all Django models in the project.

    Use this for quick model introspection without shell access.
    """
    return [ModelResource.from_model(model) for model in apps.get_models()]


@mcp.tool(
    annotations=ToolAnnotations(
        title="Django Shell", destructiveHint=True, openWorldHint=True
    ),
)
async def django_shell(
    ctx: Context,
    code: Annotated[str, "Python code to be executed inside the Django shell session"],
    imports: Annotated[
        str | None,
        "Optional import statements to execute before running the main code. Should contain all necessary imports for the code to run successfully, such as 'from django.contrib.auth.models import User\\nfrom myapp.models import MyModel'",
    ] = None,
) -> DjangoShellOutput:
    """Execute Python code in a stateful Django shell session.

    Django is pre-configured and ready to use with your project. You can import and use any Django
    models, utilities, or Python libraries as needed. The session maintains state between calls, so
    variables and imports persist across executions.

    Useful exploration commands:
    - To explore available models, use `django.apps.apps.get_models()`.
    - For configuration details, use `django.conf.settings`.

    **NOTE**: that only synchronous Django ORM operations are supported - use standard methods like
    `.filter()` and `.get()` rather than their async counterparts (`.afilter()`, `.aget()`).
    """
    logger.info(
        "django_shell tool called - request_id: %s, client_id: %s, code: %s, imports: %s",
        ctx.request_id,
        ctx.client_id or "unknown",
        (code[:100] + "..." if len(code) > 100 else code).replace("\n", "\\n"),
        (imports[:50] + "..." if imports and len(imports) > 50 else imports or "None"),
    )
    logger.debug(
        "Full code for django_shell - request_id: %s: %s", ctx.request_id, code
    )
    if imports:
        logger.debug(
            "Imports for django_shell - request_id: %s: %s", ctx.request_id, imports
        )

        filtered_imports = filter_existing_imports(imports, shell.globals)
        if filtered_imports.strip():
            code = f"{filtered_imports}\n{code}"

    parsed_code, setup, code_type = parse_code(code)

    try:
        result = await shell.execute(parsed_code, setup, code_type)
        output = DjangoShellOutput.from_result(result)

        logger.debug(
            "django_shell execution completed - request_id: %s, result type: %s",
            ctx.request_id,
            type(result).__name__,
        )
        if isinstance(output.output, ErrorOutput):
            await ctx.debug(f"Execution failed: {output.output.exception.message}")

        return output

    except Exception as e:
        logger.error(
            "Unexpected error in django_shell tool - request_id: %s: %s",
            ctx.request_id,
            e,
            exc_info=True,
        )
        raise


@mcp.tool(
    annotations=ToolAnnotations(
        title="Reset Django Shell Session", destructiveHint=True, idempotentHint=True
    ),
)
async def django_shell_reset(ctx: Context) -> str:
    """Reset the Django shell session, clearing all variables and history.

    Use this when you want to start fresh or if the session state becomes corrupted.
    """
    logger.info(
        "django_shell_reset tool called - request_id: %s, client_id: %s",
        ctx.request_id,
        ctx.client_id or "unknown",
    )
    await ctx.debug("Django shell session reset")

    shell.reset()

    logger.debug(
        "Django shell session reset completed - request_id: %s", ctx.request_id
    )

    return "Django shell session has been reset. All previously set variables and history cleared."
```

### 3. Import Updates

#### `tests/shell/test_shell.py`
- Line 8: `from mcp_django_shell.code import parse_code` → `from mcp_django.code import parse_code`
- Lines 9-12: `from mcp_django_shell.shell import` → `from mcp_django.shell import`

#### `tests/shell/test_code.py`
- All imports: `mcp_django_shell.code` → `mcp_django.code`

#### `tests/shell/test_output.py`
- All imports: `mcp_django_shell.output` → `mcp_django.output`
- All imports: `mcp_django_shell.shell` → `mcp_django.shell`

#### `tests/test_server.py`
- Line 14: `from mcp_django_shell.output import ExecutionStatus` → `from mcp_django.output import ExecutionStatus`
- Line 15: Remove `from mcp_django_shell.server import shell`
- Line 29: `await client.call_tool("shell_django_reset", {})` → `await client.call_tool("django_shell_reset", {})`
- Update all `shell_` prefixed tool names to unprefixed versions

### 4. Configuration File Updates

> **Note**: Version updates (0.10.0) will be handled by `bumpver` tool, not manual edits.

#### `pyproject.toml` (root)

**Lines 79-85: DELETE entire optional-dependencies section**
```toml
# DELETE:
# [project.optional-dependencies]
# all = [
#   "mcp-django[shell]",
# ]
# shell = [
#   "mcp-django-shell>=0.8.0",
# ]
```

**Lines 111-114: Update omit paths**
```toml
omit = [
  "*/migrations/*",
  "src/mcp_django/management/commands/mcp.py",
  "src/mcp_django/__main__.py",
  "src/mcp_django/_typing.py",
  "tests/*"
]
```

**Lines 117-120: Update source paths**
```toml
source = [
  "src/mcp_django"
]
```

**Lines 163-166: Update pythonpath**
```toml
pythonpath = [
  "src",
  "."
]
```

**Lines 234-237: Update known-first-party**
```toml
known-first-party = [
  "mcp_django",
  "tests"
]
```

**Lines 251-254: DELETE workspace sources**
```toml
# DELETE:
# [tool.uv.sources]
# mcp-django = { workspace = true }
# mcp-django-shell = { workspace = true }
```

**Line 256: DELETE workspace members**
```toml
# DELETE:
# members = ["packages/*"]
```

#### `packages/mcp-django-shell/pyproject.toml`

**Line 54: Update description**
```toml
description = "[DEPRECATED - Use mcp-django instead] MCP server providing a stateful Django shell for LLM assistants."
```

> **Note**: Version will be updated by `bumpver` tool.

#### `packages/mcp-django-shell/src/mcp_django_shell/__init__.py`

Replace entire file with deprecation shim:
```python
from __future__ import annotations

import warnings

warnings.warn(
    "mcp-django-shell is deprecated and will be removed in the next release. "
    "Shell functionality is now included in mcp-django>=0.10.0. "
    "Please uninstall mcp-django-shell and install mcp-django instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Provide compatibility imports for any direct importers (unlikely for MCP server)
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
```

#### `packages/mcp-django-shell/README.md`

Add at the top (after line 1):
```markdown
> [!CAUTION]
> **This package is deprecated as of version 0.10.0**
> 
> The shell functionality has been integrated into the main `mcp-django` package.
> Please uninstall `mcp-django-shell` and install `mcp-django>=0.10.0` instead.
>
> ```bash
> pip uninstall mcp-django-shell
> pip install mcp-django>=0.10.0
> ```
```

### 5. CI/CD Updates

#### `.github/workflows/release.yml`

**Lines 27-35: Simplify build process**
```yaml
- name: Build package
  run: |
    uv build
```

Remove the multi-package build loop.

### 6. Documentation Updates

#### `README.md`

**Lines 39-94: Replace entire Installation section**
```markdown
## Installation

```bash
pip install mcp-django

# Or with uv
uv add mcp-django
```

> [!WARNING]
> This package includes shell tools that provide full Python code execution in your Django environment. 
> Only use in development environments, never in production!
```

**Lines 183-201: Update Features section**
Remove distinction between core and shell features. Combine into single feature list.

#### `CHANGELOG.md`

**Add at line 27 (under `## [Unreleased]`):**
```markdown
## [0.10.0]

### Changed
- **BREAKING**: Consolidated mcp-django-shell functionality into main mcp-django package
- Shell tools are now included by default (no longer optional)
- Tool names changed: `shell_django_shell` → `django_shell`, `shell_django_reset` → `django_shell_reset`

### Deprecated
- mcp-django-shell package is deprecated, functionality moved to mcp-django

### Removed
- Optional installation extras `[shell]` and `[all]` - shell is now always included

[0.10.0]: https://github.com/joshuadavidthomas/mcp-django/releases/tag/0.10.0
```

#### `RELEASING.md`

**Lines 5-6: Remove outdated note**

Update to reflect single package release process throughout.

---

## Release 0.11.0 - Complete Removal

### 1. Directory Removal
- Delete entire `packages/` directory

### 2. Final Cleanup
- Remove any remaining references to mcp-django-shell in docs
- Update CHANGELOG with removal notice
- Remove `.github/VERSION` file (CalVer no longer needed after consolidation)

---

## Implementation Plan

### Chunk 1: File Movements
**Goal**: Move shell modules from subpackage to main package

- [ ] Move `packages/mcp-django-shell/src/mcp_django_shell/shell.py` → `src/mcp_django/shell.py`
- [ ] Move `packages/mcp-django-shell/src/mcp_django_shell/code.py` → `src/mcp_django/code.py`
- [ ] Move `packages/mcp-django-shell/src/mcp_django_shell/output.py` → `src/mcp_django/output.py`
- [ ] **CHECKPOINT 1**: Verify file movements completed successfully

### Chunk 2: Server Integration
**Goal**: Rewrite server.py with unified implementation

- [ ] Rewrite `src/mcp_django/server.py` with consolidated server implementation
- [ ] **CHECKPOINT 2**: Verify server.py rewrite and tool registration

### Chunk 3: Test Updates
**Goal**: Update all test imports and tool names

- [ ] Update imports in `tests/shell/test_shell.py`
- [ ] Update imports in `tests/shell/test_code.py`
- [ ] Update imports in `tests/shell/test_output.py`
- [ ] Update `tests/test_server.py` for new tool names and imports
- [ ] **CHECKPOINT 3**: Run tests to verify all imports and functionality work

### Chunk 4: Configuration Cleanup
**Goal**: Update pyproject.toml files and add deprecation shim

- [ ] Update root `pyproject.toml` (remove workspace, extras, update paths)
- [ ] Create deprecation shim in `packages/mcp-django-shell/src/mcp_django_shell/__init__.py`
- [ ] Update `packages/mcp-django-shell/pyproject.toml` description
- [ ] **CHECKPOINT 4**: Verify package configuration and deprecation warnings

### Chunk 5: Documentation & CI/CD Updates
**Goal**: Update README, CHANGELOG, and CI workflows

- [ ] Update `README.md` installation and features sections
- [ ] Add 0.10.0 entry to `CHANGELOG.md`
- [ ] Add deprecation banner to `packages/mcp-django-shell/README.md`
- [ ] Simplify `.github/workflows/release.yml` for single package
- [ ] Update `RELEASING.md` for single package process
- [ ] **CHECKPOINT 5**: Review all documentation and CI/CD changes

### Chunk 6: Version Bump & Release
**Goal**: Prepare for release

- [ ] Run `bumpver` to update versions to 0.10.0
- [ ] Run full test suite to verify everything works
- [ ] **CHECKPOINT 6**: Final review before release
- [ ] Manually create final mcp-django-shell 0.10.0 release
- [ ] Create mcp-django 0.10.0 release
- [ ] Leave mcp-django-shell on PyPI with deprecation notices

---

## Notes

- No separate loggers needed - unified logging
- Tests remain in `tests/shell/` subdirectory
- No compatibility needed for MCP tool usage (LLMs call tools directly via MCP protocol)
- Security warnings in README are sufficient
- Manual release for final shell package (CI/CD simplified immediately)
