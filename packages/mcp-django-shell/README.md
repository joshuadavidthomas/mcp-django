# mcp-django-shell

Django shell tools for the [mcp-django](https://github.com/joshuadavidthomas/mcp-django) Model Context Protocol server.

## ⚠️ Security Warning

This package provides unrestricted shell access to your Django project. It executes arbitrary Python code with full access to your database and file system.

**NEVER install this in production environments!**

## Installation

This package is distributed as an optional extra of the main `mcp-django` package:

```bash
pip install "mcp-django[shell]"
```

## Features

The `mcp-django-shell` package adds two tools to the base MCP server:

- **`django_shell`** - Execute Python code in a persistent Django shell session
- **`django_reset`** - Reset the session, clearing all variables and imports

These tools enable LLM assistants to:

- Write and execute Python code directly in your Django environment
- Maintain state between calls (imports, variables persist)
- Query and modify your database using the Django ORM
- Debug and test code interactively

## Documentation

For full documentation, configuration, and usage instructions, see the main package:

[https://github.com/joshuadavidthomas/mcp-django](https://github.com/joshuadavidthomas/mcp-django)

## License

mcp-django-shell is licensed under the MIT license. See the [LICENSE](https://github.com/joshuadavidthomas/mcp-django/blob/main/LICENSE) file for details.
