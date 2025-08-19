from __future__ import annotations

from fastmcp import FastMCP

from .shell import DjangoShell

mcp = FastMCP(
    name="Django Shell",
    instructions="Provides a stateful Django shell environment for executing Python code, managing sessions, and exporting command history.",
)
shell = DjangoShell()


@mcp.tool
async def django_shell(code: str, timeout: int | None = None) -> str:
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
    result = await shell.execute(code, timeout=timeout)
    return result.output


@mcp.tool
def django_reset() -> str:
    """
    Reset the Django shell session, clearing all variables and history.

    Use this when you want to start fresh or if the session state becomes corrupted.
    """
    shell.reset()
    return "Django shell session has been reset. All previously set variables and history cleared."
