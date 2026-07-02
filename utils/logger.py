"""
utils/logger.py

Centralized logging configuration for the CATIA MCP server.

Because this server communicates with Claude Desktop over stdio, nothing
must ever be printed to stdout - that channel is reserved exclusively for
MCP protocol JSON-RPC messages. All logs go to rotating files instead (and,
for warnings/errors only, to stderr as well).
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys

LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"
)
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "catia_mcp.log")
TRACE_FILE = os.path.join(LOG_DIR, "tool_trace.log")

_configured = False
_trace_logger = None


def setup_logging(debug: bool = False) -> logging.Logger:
    """Configure the root 'catia_mcp' logger exactly once per process."""
    global _configured
    root = logging.getLogger("catia_mcp")
    if _configured:
        return root

    level = logging.DEBUG if debug else logging.INFO
    root.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(level)
    root.addHandler(file_handler)

    # stderr is safe for an MCP stdio server; stdout is NOT.
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(fmt)
    stderr_handler.setLevel(logging.WARNING)
    root.addHandler(stderr_handler)

    _configured = True
    return root


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(f"catia_mcp.{name}")


def trace_tool_call(tool_name: str, params: dict, result: dict) -> None:
    """Append a structured audit record of every MCP tool invocation."""
    global _trace_logger
    if _trace_logger is None:
        _trace_logger = logging.getLogger("catia_mcp.trace")
        handler = logging.handlers.RotatingFileHandler(
            TRACE_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
        _trace_logger.addHandler(handler)
        _trace_logger.setLevel(logging.INFO)
        _trace_logger.propagate = False

    success = result.get("success") if isinstance(result, dict) else None
    error = result.get("error") if isinstance(result, dict) else None
    _trace_logger.info(
        "CALL %s params=%s -> success=%s error=%s", tool_name, params, success, error
    )
