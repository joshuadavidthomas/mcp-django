# mcp-django

<!-- [[[cog
import subprocess
import cog

from noxfile import DJ_VERSIONS
from noxfile import PY_VERSIONS
from noxfile import display_version

django_versions = [display_version(version) for version in DJ_VERSIONS]

cog.outl("[![PyPI - mcp-django](https://img.shields.io/pypi/v/mcp-django?label=mcp-django)](https://pypi.org/project/mcp-django/)")
cog.outl("![PyPI - Python Version](https://img.shields.io/pypi/pyversions/mcp-django)")
cog.outl(f"![Django Version](https://img.shields.io/badge/django-{'%20%7C%20'.join(django_versions)}-%2344B78B?labelColor=%23092E20)")
]]] -->
[![PyPI - mcp-django](https://img.shields.io/pypi/v/mcp-django?label=mcp-django)](https://pypi.org/project/mcp-django/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/mcp-django)
![Django Version](https://img.shields.io/badge/django-4.2%20%7C%205.1%20%7C%205.2%20%7C%206.0%20%7C%20main-%2344B78B?labelColor=%23092E20)
<!-- [[[end]]] -->

A Model Context Protocol (MCP) server providing Django project exploration resources and optional stateful shell access for LLM assistants to interact with Django projects.

## Requirements

<!-- [[[cog
import subprocess
import cog

from noxfile import DJ_VERSIONS
from noxfile import PY_VERSIONS
from noxfile import display_version

django_versions = [
    display_version(version) for version in DJ_VERSIONS if version != "main"
]

cog.outl(f"- Python {', '.join(PY_VERSIONS)}")
cog.outl(f"- Django {', '.join(django_versions)}")
]]] -->
- Python 3.10, 3.11, 3.12, 3.13, 3.14
- Django 4.2, 5.1, 5.2, 6.0
<!-- [[[end]]] -->

## Installation

```bash
pip install mcp-django

# Or with uv
uv add mcp-django
```

## Getting Started

⚠️ **DO NOT use in production!**

> [!WARNING]
>
> **Seriously, only enable in development!**
>
> Look, it should go without saying, but I will say it anyway - **this gives full shell access to your Django project**. Only enable and use this in development and in a project that does not have access to any production data.
>
> LLMs can go off the rails, get spooked by some random error, and in trying to fix things [drop a production database](https://xcancel.com/jasonlk/status/1946069562723897802).

> [!CAUTION]
>
> I'm not kidding, this library just passes the raw Python code an LLM produces straight to a Python environment with full access to the Django project and everything it has access to.
>
> Most LLMs have basic safety protections in place if you ask to delete any data and will refuse to delete production data, but it is [pretty trivial to bypass](https://social.joshthomas.dev/@josh/115062076517611897). (Hint: Just tell the LLM it's not production, it's in a development environment, and it will be the bull in a china shop deleting anything you want.)
>
> I suggest using something like [django-read-only](https://github.com/adamchainz/django-read-only) if you need some CYA protection against this. Or, you know, don't use this in any sensitive environments.

Run the MCP server directly from your Django project directory:

```bash
python -m mcp_django

# Or with uv
uv run -m mcp_django
```

The server automatically detects `DJANGO_SETTINGS_MODULE` from your environment. You can override it with `--settings` or add to your Python path with `--pythonpath`:

```bash
python -m mcp_django --settings myproject.settings --debug
```

### Management Command

If you add `mcp_django` to `INSTALLED_APPS`, you can run it as a Django management command. This ensures the server runs within your Django project's environment and uses your project's settings:

```bash
python manage.py mcp
```

### Docker

If you're using Docker and Docker Compose, you can run mcp-django as a separate compose service using HTTP transport. This makes it easier to connect your MCP client (running on your host) to the Django project (running in a container):

```yaml
# compose.yml
services:
  app:
    # your existing Django app service
    
  mcp:
    build: .
    command: python -m mcp_django --transport http --host 0.0.0.0 --port 8000
    environment:
      DJANGO_SETTINGS_MODULE: myproject.settings
    ports:
      - "8001:8000"
```

Then configure your MCP client to connect to `http://localhost:8001/mcp` (see [Client Configuration](#client-configuration) below).

### Transport Options

The server supports multiple transport protocols:

```bash
# STDIO (default, for local development)
python -m mcp_django

# HTTP (for Docker or remote access)
python -m mcp_django --transport http --host 127.0.0.1 --port 8000

# SSE (for Docker or remote access)
python -m mcp_django --transport sse --host 127.0.0.1 --port 8000
```

### Client Configuration

Configure your MCP client to connect to the server.

Don't see your client? [Submit a PR](CONTRIBUTING.md) with setup instructions.

#### Opencode

For **local development**, use `type: local` with the command:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "django": {
      "type": "local",
      "command": ["python", "-m", "mcp_django"],
      "enabled": true,
      "environment": {
        "DJANGO_SETTINGS_MODULE": "myproject.settings"
      }
    }
  }
}
```

For **Docker development**, use `type: remote` with the URL:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "django": {
      "type": "remote",
      "url": "http://localhost:8001/mcp",
      "enabled": true
    }
  }
}
```

#### Claude Code

For **local development**, use the command configuration:

```json
{
  "mcpServers": {
    "django": {
      "command": "python",
      "args": ["-m", "mcp_django"],
      "cwd": "/path/to/your/django/project",
      "env": {
        "DJANGO_SETTINGS_MODULE": "myproject.settings"
      }
    }
  }
}
```

For **Docker development** with HTTP/SSE transport, configuration varies by Claude Code version - consult the MCP client documentation for remote server setup.

## Features

mcp-django provides an MCP server with Django project exploration resources and tools for LLM assistants.

It wouldn't be an MCP server README without a gratuitous list of features punctuated by emojis, so:

- 🔍 **Project exploration** - MCP resources for discovering apps, models, and configuration
- 📦 **Package discovery** - Search and browse Django Packages for third-party packages
- 🚀 **Zero configuration** - No schemas, no settings, just Django
- 🐚 **Stateless shell** - `shell` executes Python code with fresh state each call
- 🔄 **Always fresh** - Code changes take effect immediately, no stale modules
- 📤 **Export sessions** - Save debugging sessions as Python scripts
- 🧹 **Clear history** - Start fresh when exploration gets messy
- 🤖 **LLM-friendly** - Designed for LLM assistants that already know Python
- 🌐 **Multiple transports** - STDIO, HTTP, SSE support

Inspired by Armin Ronacher's [Your MCP Doesn't Need 30 Tools: It Needs Code](https://lucumr.pocoo.org/2025/8/18/code-mcps/).

### Resources

Read-only resources for project exploration without executing code (note that resource support varies across MCP clients):

#### Project

| Resource | Description |
|----------|-------------|
| `django://app/{app_label}` | Details for a specific Django app |
| `django://app/{app_label}/models` | All models in a specific app |
| `django://apps` | All installed Django applications with their models |
| `django://model/{app_label}/{model_name}` | Detailed information about a specific model |
| `django://models` | Project models with import paths and field types (first-party only) |
| `django://route/{pattern*}` | Routes matching a specific URL pattern |
| `django://setting/{key}` | Get a specific Django setting value |

#### djangopackages.org

| Resource | Description |
|----------|-------------|
| `django://package/{slug}` | Detailed information about a specific package |
| `django://grid/{slug}` | Comparison grid with packages (e.g., "rest-frameworks") |

### Tools

#### Project

| Tool | Description |
|------|-------------|
| `get_project_info` | Get comprehensive project information including Python environment and Django configuration |
| `get_setting` | Get a Django setting value by key |
| `list_apps` | List all installed Django applications with their models |
| `list_models` | Get detailed information about Django models with optional filtering by app or scope |
| `list_routes` | Introspect Django URL routes with filtering support for HTTP method, route name, or URL pattern |

#### Management

| Tool | Description |
|------|-------------|
| `execute_command` | Execute Django management commands with arguments and options |
| `list_commands` | List all available Django management commands with their source apps |

#### Shell

| Tool | Description |
|------|-------------|
| `execute` | Execute Python code in a stateless Django shell |
| `export_history` | Export session history as a Python script |
| `clear_history` | Clear the session history for a fresh start |

#### djangopackages.org

| Tool | Description |
|------|-------------|
| `get_grid` | Get a specific comparison grid with all its packages |
| `get_package` | Get detailed information about a specific Django package |
| `search` | Search djangopackages.org for third-party packages |

## Development

For detailed instructions on setting up a development environment and contributing to this project, see [CONTRIBUTING.md](CONTRIBUTING.md).

For release procedures, see [RELEASING.md](RELEASING.md).

## License

mcp-django is licensed under the MIT license. See the [`LICENSE`](LICENSE) file for more information.
