from __future__ import annotations

import logging
import os
import signal
import sys
from typing import Any

from django.core.management.base import BaseCommand

from mcp_django_shell.server import mcp

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the MCP Django Shell server"

    def add_arguments(self, parser):
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug logging",
        )

    def handle(self, *args: Any, **options: Any):
        if options.get("debug"):
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
            logger.debug("Debug logging enabled")

        logger.info("Starting MCP Django Shell server")
        logger.debug(
            "Django settings module: %s",
            os.environ.get("DJANGO_SETTINGS_MODULE", "Not set"),
        )

        def signal_handler(signum, frame):
            logger.info("Received signal %s, shutting down MCP server", signum)

            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            logger.info("MCP server ready and listening")

            mcp.run()

        except Exception as e:
            logger.error("MCP server crashed: %s", e, exc_info=True)

            raise

        finally:
            logger.info("MCP Django Shell server stopped")
