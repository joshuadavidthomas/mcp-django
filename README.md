# mcp-django-shell

<!-- [[[cog
import subprocess
import cog

from noxfile import DJ_VERSIONS
from noxfile import PY_VERSIONS

cog.outl("[![PyPI](https://img.shields.io/pypi/v/mcp-django-shell)](https://pypi.org/project/mcp-django-shell/)")
cog.outl("![PyPI - Python Version](https://img.shields.io/pypi/pyversions/mcp-django-shell)")
cog.outl(f"![Django Version](https://img.shields.io/badge/django-{'%20%7C%20'.join(DJ_VERSIONS)}-%2344B78B?labelColor=%23092E20)")
]]] -->
[![PyPI](https://img.shields.io/pypi/v/mcp-django-shell)](https://pypi.org/project/mcp-django-shell/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/mcp-django-shell)
![Django Version](https://img.shields.io/badge/django-4.2%20%7C%205.1%20%7C%205.2%20%7C%20main-%2344B78B?labelColor=%23092E20)
<!-- [[[end]]] -->

A Model Context Protocol (MCP) server providing a stateful Django shell for AI assistants to interact with Django projects.

## Requirements

<!-- [[[cog
import subprocess
import cog

from noxfile import DJ_VERSIONS
from noxfile import PY_VERSIONS

cog.outl(f"- Python {', '.join([version for version in PY_VERSIONS])}")
cog.outl(f"- Django {', '.join([version for version in DJ_VERSIONS if version != 'main'])}")
]]] -->
- Python 3.10, 3.11, 3.12, 3.13
- Django 4.2, 5.1, 5.2
<!-- [[[end]]] -->

## Installation

1. Install the package from [PyPI](https://pypi.org/project/mcp-django-shell).

    ```bash
    python -m pip install mcp-django-shell

    # or if you like the new hotness

    uv add mcp-django-shell
    uv sync
    ```

2. Add to your Django project's `INSTALLED_APPS`:

   ```python
   DEBUG = ...

   if DEBUG:
       INSTALLED_APPS.append("mcp_django_shell")
   ```

> [!WARNING]
>
> **Only enable in development!** 
> 
> Look, it should go without saying, but I will say it anyway - **this gives full shell access to your Django project**. Only enable and use this in development and in a project that does not have access to any production data. LLMs can go off the rails, get spooked by some random error, and in trying to fix things [drop a production database](https://xcancel.com/jasonlk/status/1946069562723897802).

## Getting Started

mcp-django-shell provides a Django management command that MCP clients can connect to. Configure your client using one of the examples below.

Don't see your client? [Submit a PR](CONTRIBUTING.md) with setup instructions.

### Claude Code

```json
{
  "mcpServers": {
    "django_shell": {
      "command": "python",
      "args": ["manage.py", "mcp_shell"],
      "cwd": "/path/to/your/django/project"
    }
  }
}
```

### Opencode

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "django_shell": {
      "type": "local",
      "command": ["python", "manage.py", "mcp_shell"],
      "enabled": true
    }
  }
}
```

## Usage

mcp-django-shell provides an MCP server with a stateful Django shell for AI assistants. It sets up Django, maintains session state between calls, and lets the AI write and execute Python code directly against your project.

The MCP server comes with just two tools:

- `django_shell` - Execute Python code in a persistent Django shell session
- `django_reset` - Reset the session, clearing all variables and imports

Imports and variables persist between calls, so the AI can work iteratively - exploring your models, testing queries, debugging issues.

It wouldn't be an MCP server README without a gratuitous list of features punctuated by emojis, so:

- 🐚 **One tool** - `django_shell` executes Python code in your Django environment
- 🔄 **Persistent state** - Imports and variables stick around between calls
- 🧹 **Reset when needed** - `django_reset` clears the session when things get weird
- 🚀 **Zero configuration** - No schemas, no settings, just Django
- 🤖 **LLM-friendly** - Designed for AI assistants that already know Python
- 📦 **Minimal dependencies** - Just FastMCP and Django (you already have Django)
- 🎯 **Does one thing well** - Runs code. That's it. That's the feature.

Inspired by Armin Ronacher's [Your MCP Doesn't Need 30 Tools: It Needs Code](https://lucumr.pocoo.org/2025/8/18/code-mcps/).

## Development

For detailed instructions on setting up a development environment and contributing to this project, see [CONTRIBUTING.md](CONTRIBUTING.md).

For release procedures, see [RELEASING.md](RELEASING.md).

## License

mcp-django-shell is licensed under the MIT license. See the [`LICENSE`](LICENSE) file for more information.
