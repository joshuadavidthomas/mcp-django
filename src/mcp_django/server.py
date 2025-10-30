from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastmcp import FastMCP

from mcp_django.packages import DJANGOPACKAGES_TOOLSET
from mcp_django.packages import mcp as packages_mcp
from mcp_django.project import PROJECT_TOOLSET
from mcp_django.project import mcp as project_mcp
from mcp_django.shell import SHELL_TOOLSET
from mcp_django.shell import mcp as shell_mcp

logger = logging.getLogger(__name__)

TOOLSETS = {
    DJANGOPACKAGES_TOOLSET: packages_mcp,
    PROJECT_TOOLSET: project_mcp,
    SHELL_TOOLSET: shell_mcp,
}


class DjangoMCP:
    NAME = "Django"
    INSTRUCTIONS = "Django ecosystem MCP server providing comprehensive project introspection, stateful code execution, and development tools. Supports exploring project structure, analyzing configurations, executing Python in persistent sessions, and accessing Django ecosystem resources."

    def __init__(self) -> None:
        instructions = [self.INSTRUCTIONS]

        instructions.append("## Available Toolsets")
        for toolset_server in TOOLSETS.values():
            instructions.append(f"### {toolset_server.name}")
            if toolset_server.instructions:
                instructions.append(toolset_server.instructions)

        self._server = FastMCP(name=self.NAME, instructions="\n\n".join(instructions))

    @property
    def server(self) -> FastMCP:
        return self._server

    async def initialize(self) -> None:
        for toolset_prefix, toolset_server in TOOLSETS.items():
            await self._server.import_server(toolset_server, prefix=toolset_prefix)

    def run(self, **kwargs: Any) -> None:  # pragma: no cover
        asyncio.run(self.initialize())
        self._server.run(**kwargs)


mcp = DjangoMCP()
