from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
from collections.abc import Sequence
from typing import Any

logger = logging.getLogger(__name__)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the MCP Django Shell server")
    parser.add_argument(
        "--settings",
        help="Django settings module (overrides DJANGO_SETTINGS_MODULE env var)",
    )
    parser.add_argument(
        "--pythonpath",
        help="Python path to add for Django project imports",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args(argv)

    debug: bool = args.debug
    settings: str | None = args.settings
    pythonpath: str | None = args.pythonpath

    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        logger.debug("Debug logging enabled")

    if settings:
        os.environ["DJANGO_SETTINGS_MODULE"] = settings

    if pythonpath:
        sys.path.insert(0, pythonpath)

    django_settings = os.environ.get("DJANGO_SETTINGS_MODULE")
    if not django_settings:
        logger.error(
            "DJANGO_SETTINGS_MODULE not set. Use --settings or set environment variable."
        )
        return 1

    logger.info("Starting MCP Django Shell server")
    logger.debug("Django settings module: %s", django_settings)

    def signal_handler(signum: int, _frame: Any):  # pragma: no cover
        logger.info("Received signal %s, shutting down MCP server", signum)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        logger.info("MCP server ready and listening")

        from .server import mcp

        mcp.run()

    except Exception as e:
        logger.error("MCP server crashed: %s", e, exc_info=True)
        return 1

    finally:
        logger.info("MCP Django Shell server stopped")

    return 0
