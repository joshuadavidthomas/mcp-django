# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project attempts to adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!--
## [${version}]

_For multi-package releases, list package versions here_

### Added - for new features
### Changed - for changes in existing functionality
### Deprecated - for soon-to-be removed features
### Removed - for now removed features
### Fixed - for any bug fixes
### Security - in case of vulnerabilities

For multi-package releases, use package names as subsections:
### package-name
#### Added/Changed/etc...

[${version}]: https://github.com/joshuadavidthomas/mcp-django/releases/tag/${tag}
-->

## [Unreleased]

After splitting into separate packages in v2025.8.1 for security isolation, we're consolidating back into a single package, for a few reasons:

- It seemed like a good idea, but it's early and the extra complexity adds unnecessary friction
- While production deployment would be nice eventually, the current focus is developer tooling and building a damn good MCP server for Django

The GitHub releases were previously using calendar versioning (e.g., v2025.8.1) while individual packages used semantic versioning. With the consolidation to a single package, GitHub releases will now use the package version directly. The consolidated package will be v0.10.0, continuing from the highest version among the previous packages (mcp-django-shell was at 0.9.0).

### Added

- Added support for Python 3.14

### Changed

- **BREAKING**: Consolidated mcp-django-shell functionality into main mcp-django package
- Shell tools are now included by default (no longer optional via extras)
- Tool names changed: `shell_django_shell` → `django_shell`, `shell_django_reset` → `django_shell_reset`

### Deprecated

- mcp-django-shell package is deprecated, functionality moved to mcp-django

### Removed

- Optional installation extras `[shell]` and `[all]` - shell is now always included

## [2025.8.1]

- mcp-django: 0.2.0
- mcp-django-shell: 0.9.0

**🚨 BREAKING RELEASE 🚨**

This release restructures the project from a single package to a workspace with multiple packages for better separation of concerns. 

The dev only shell functionality is now an optional extra that must be explicitly installed, while the read-only resources are available in the base package. 

This should allow for safer production deployments where shell access can be completely excluded, as well as allow for future expansion with additional tool packages that can be selectively installed based on environment needs.

> **Note**: All releases prior to this one are for mcp-django-shell only.

### Changed

- Migrated to workspace structure with multiple packages
- Repository renamed from mcp-django-shell to mcp-django
- **Internal**: Git tags now use package-prefixed format: `mcp-django-shell-vX.Y.Z`
- **🚨 BREAKING CHANGE 🚨**: Main entry point changed from `python -m mcp_django_shell` to `python -m mcp_django`
- Shell functionality now installed via extras: `pip install "mcp-django[shell]"`
- **🚨 BREAKING CHANGE 🚨**: Management command moved from mcp-django-shell to mcp-django package and renamed from `mcp_shell` to `mcp`

### mcp-django (new)

- Initial release as root package providing core MCP server functionality
- Includes the read-only resources for project exploration, previously included as a part of mcp-django-shell

### mcp-django-shell

- Moved to workspace package under `packages/` directory
- Now distributed as optional extra of mcp-django
- Now only includes the two shell tools
## [0.8.0]

### Added

- Optional `imports` parameter to `django_shell` tool for providing import statements separately from main code execution.

## [0.7.0]

### Added

- MCP resources for exploring the project environment, Django apps, and models without shell execution.

### Changed

- Updated server instructions to guide LLMs to use resources for project orientation before shell operations.

### Removed

- Removed redundant input field from `django_shell` tool response to reduce output verbosity.

## [0.6.0]

### Added

- Pydantic is now an explicit dependency of the library. Previously, it was a transitive dependency via FastMCP.

### Changed

- The `code` argument to the `django_shell` MCP tool now has a helpful description.
- `django_shell` now returns structured output with execution status, error details, and filtered tracebacks instead of plain strings.
- MCP tools now provide annotations hints via `fastmcp.ToolAnnotations`.

## [0.5.0]

### Added

- Support for HTTP and SSE transport protocols via CLI arguments (`--transport`, `--host`, `--port`, `--path`).

## [0.4.0]

### Added

- Standalone CLI via `python -m mcp_django_shell`.

### Deprecated

- Soft-deprecation of the management command `manage.py mcp_shell`. It's now just a wrapper around the CLI, so there's no harm in keeping it, but the recommended usage will be the standalone CLI going forward.

## [0.3.1]

### Removed

- Removed unused `timeout` parameter from django_shell tool, to prevent potential robot confusion.

## [0.3.0]

### Changed

- Removed custom formatting for QuerySets and iterables in shell output. QuerySets now display as `<QuerySet [...]>` and lists show their standard `repr()` instead of truncated displays with "... and X more items". This makes output consistent with standard Django/Python shell behavior and should hopefully not confuse the robots.

### Fixed

- Django shell no longer shows `None` after print statements. Expression values are now only displayed when code doesn't print output, matching Python script execution behavior.

## [0.2.0]

### Added

- Comprehensive logging for debugging MCP/LLM interactions
- `--debug` flag for the `mcp_shell` management command to enable detailed logging
- Request and client ID tracking in server logs

### Changed

- **Internal**: Refactored results to use separate dataclasses and a tagged union
- Changed to using `contextlib` and its stdout/stderr output redirection context managers when executing code
- Swapped out `.split("\n")` usage for `.splitlines()` for better cross-platform line ending handling (h/t to [@jefftriplett] for the tip 🎉)

## [0.1.0]

### Added

- Django management command `mcp_shell` for MCP server integration
- `django_shell` MCP tool for executing Python code in persistent Django shell
- `django_reset` MCP tool for clearing session state

### New Contributors

- Josh Thomas <josh@joshthomas.dev> (maintainer)

[unreleased]: https://github.com/joshuadavidthomas/mcp-django/compare/2025.8.1...HEAD
[2025.8.1]: https://github.com/joshuadavidthomas/mcp-django/releases/tag/2025.8.1
[0.1.0]: https://github.com/joshuadavidthomas/mcp-django/releases/tag/mcp-django-shell-v0.1.0
[0.2.0]: https://github.com/joshuadavidthomas/mcp-django/releases/tag/mcp-django-shell-v0.2.0
[0.3.0]: https://github.com/joshuadavidthomas/mcp-django/releases/tag/mcp-django-shell-v0.3.0
[0.3.1]: https://github.com/joshuadavidthomas/mcp-django/releases/tag/mcp-django-shell-v0.3.1
[0.4.0]: https://github.com/joshuadavidthomas/mcp-django/releases/tag/mcp-django-shell-v0.4.0
[0.5.0]: https://github.com/joshuadavidthomas/mcp-django/releases/tag/mcp-django-shell-v0.5.0
[0.6.0]: https://github.com/joshuadavidthomas/mcp-django/releases/tag/mcp-django-shell-v0.6.0
[0.7.0]: https://github.com/joshuadavidthomas/mcp-django/releases/tag/mcp-django-shell-v0.7.0
[0.8.0]: https://github.com/joshuadavidthomas/mcp-django/releases/tag/mcp-django-shell-v0.8.0
