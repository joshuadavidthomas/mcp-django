set dotenv-load := true
set unstable := true

mod project ".just/project.just"

[private]
default:
    @just --list --list-submodules

[private]
cog:
    uv run --with cogapp cog -r CONTRIBUTING.md README.md pyproject.toml

[private]
fmt:
    @just --fmt
    @just project fmt

[private]
nox SESSION *ARGS:
    uv run nox --session "{{ SESSION }}" -- "{{ ARGS }}"

bootstrap:
    uv python install
    uv sync --all-extras --locked

coverage *ARGS:
    @just nox coverage {{ ARGS }}

lint:
    @just nox lint

lock *ARGS:
    uv lock {{ ARGS }}

manage *COMMAND:
    #!/usr/bin/env python
    import sys

    try:
        from django.conf import settings
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    settings.configure(INSTALLED_APPS=["mcp_django_shell"])
    execute_from_command_line(sys.argv + "{{ COMMAND }}".split(" "))

test *ARGS:
    @just nox test {{ ARGS }}

testall *ARGS:
    @just nox tests {{ ARGS }}

types *ARGS:
    @just nox types {{ ARGS }}
