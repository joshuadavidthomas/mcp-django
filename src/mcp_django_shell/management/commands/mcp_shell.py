from __future__ import annotations

from typing import Any
from typing import final

from django.core.management.base import ArgumentParser
from django.core.management.base import BaseCommand

from mcp_django_shell._typing import override
from mcp_django_shell.cli import main


@final
class Command(BaseCommand):
    help = "Run the MCP Django Shell server"

    @override
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug logging",
        )

    @override
    def handle(self, *args: Any, **options: Any) -> int:
        argv: list[str] = []
        if options.get("debug"):
            argv.append("--debug")

        return main(argv)
