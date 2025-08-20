# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project attempts to adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!--
## [${version}]
### Added - for new features
### Changed - for changes in existing functionality
### Deprecated - for soon-to-be removed features
### Removed - for now removed features
### Fixed - for any bug fixes
### Security - in case of vulnerabilities
[${version}]: https://github.com/joshuadavidthomas/mcp-django-shell/releases/tag/v${version}
-->

## [Unreleased]

### Changed

- The `code` argument to the `django_shell` MCP tool now has a helpful description.

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

[unreleased]: https://github.com/joshuadavidthomas/mcp-django-shell/compare/v0.5.0...HEAD
[0.1.0]: https://github.com/joshuadavidthomas/mcp-django-shell/releases/tag/v0.1.0
[0.2.0]: https://github.com/joshuadavidthomas/mcp-django-shell/releases/tag/v0.2.0
[0.3.0]: https://github.com/joshuadavidthomas/mcp-django-shell/releases/tag/v0.3.0
[0.3.1]: https://github.com/joshuadavidthomas/mcp-django-shell/releases/tag/v0.3.1
[0.4.0]: https://github.com/joshuadavidthomas/mcp-django-shell/releases/tag/v0.4.0
[0.5.0]: https://github.com/joshuadavidthomas/mcp-django-shell/releases/tag/v0.5.0
