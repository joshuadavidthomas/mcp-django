from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Sequence
from typing import Any

from .server import mcp

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
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "http", "sse"],
        help="Transport protocol to use (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to for HTTP/SSE transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to for HTTP/SSE transport (default: 8000)",
    )
    parser.add_argument(
        "--path",
        default="/mcp",
        help="Path for HTTP transport endpoint (default: /mcp)",
    )
    args = parser.parse_args(argv)

    debug: bool = args.debug
    settings: str | None = args.settings
    pythonpath: str | None = args.pythonpath
    transport: str = args.transport
    host: str = args.host
    port: int = args.port
    path: str = args.path

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

    logger.info("Starting MCP Django server")
    logger.debug("Django settings module: %s", django_settings)
    logger.debug("Transport: %s", transport)
    if transport in ["http", "sse"]:
        logger.info(
            "Server will be available at %s:%s%s",
            host,
            port,
            path if transport == "http" else "",
        )

    try:
        logger.info("MCP server ready and listening")

        kwargs: dict[str, Any] = {"transport": transport}

        if transport in ["http", "sse"]:
            kwargs["host"] = host
            kwargs["port"] = port

        if transport == "http":
            kwargs["path"] = path

        mcp.run(**kwargs)

    except Exception as e:
        logger.error("MCP server crashed: %s", e, exc_info=True)
        return 1

    finally:
        logger.info("MCP Django server stopped")

    return 0
