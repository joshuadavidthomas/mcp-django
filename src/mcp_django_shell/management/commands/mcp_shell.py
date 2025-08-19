from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from mcp_django_shell.server import mcp


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any):
        mcp.run()
