# MCP-Django Consolidation Plan

## Context
- Repository currently publishes two workspace packages: `mcp-django` (primary resources) and `mcp-django-shell` (stateful shell tools).
- Goal is to ship a single `mcp-django` distribution that includes shell functionality while providing clear guidance for the final release and archival.

## Tasks for This Session (assistant-owned) ✅ COMPLETED
1. ✅ Relocate the shell implementation from `packages/mcp-django-shell/src/mcp_django_shell` into `src/mcp_django/shell/`.
2. ✅ Remove the workspace package wiring:
   - ✅ Drop the `shell` extra and workspace entries from `pyproject.toml`.
   - ✅ Point coverage, pytest, and tooling paths at the unified `src` tree.
3. ✅ Update imports, `INSTALLED_APPS`, configuration, and documentation references to the new module path (`mcp_django.shell`).
4. ✅ Ensure the `mcp_django.server` module imports the shell tools directly without `find_spec` guards.
   - **UPDATE**: Shell tools now fully integrated directly in `src/mcp_django/server.py` - no separate `shell/server.py` module.
5. ✅ Refresh supporting assets (`uv lock`, cog outputs if required) and run the standard validation commands (`just lint`, `just testall`, `just coverage`, `just types`).

## Post-Session Responsibilities (owner-owned)
1. Review the consolidated code, update any remaining documentation, and confirm the final API/CLI behavior.
2. Publish the consolidated `mcp-django` release (suggested version bump to signal packaging change) after validating wheels/sdists locally.
3. Optionally publish a final `mcp-django-shell` stub release that informs users to install `mcp-django` instead.
4. Add final release notes/announcements (README badge cleanup, CHANGELOG entries, external communication) reflecting the merger and pending archival.
5. Archive the GitHub repository and disable automation once the final release is confirmed.

## Notes
- Because external consumers are expected to run the MCP server, not import modules directly, compatibility shims are not required after the code move.
- Keep the Django app label aligned with the new module path (`mcp_django.shell`) and update tests/settings accordingly.

## Final Status (Sept 25, 2025)
- **Server consolidation complete**: Shell tools and instructions now integrated directly into `src/mcp_django/server.py`
- **Single unified server**: No separate shell server module - everything runs from one MCP instance
- **All validation passing**: `just lint`, `just test`, `just coverage` (100%), `just types` all green
- **Ready for owner review**: Single-package structure complete, pending final release steps
