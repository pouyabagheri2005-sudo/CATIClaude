"""
core/mcp_router.py

Layer 1 - MCP Router.

Binds every tool registered in `core.tool_registry` onto a live FastMCP
server instance, adding:
    - a global execution lock (single CATIA COM session -> serialized tool
      calls, satisfying the "async-safe execution model" requirement even
      if the MCP runtime were to dispatch calls concurrently), and
    - uniform trace logging / last-resort exception -> error-response
      conversion, so a bug in one tool can never crash the whole server.

`functools.wraps` is used (not a manual `*args, **kwargs` passthrough) so
that `inspect.signature()` - which FastMCP relies on to build each tool's
JSON schema - still sees the wrapped function's real parameters via the
`__wrapped__` attribute.
"""

from __future__ import annotations

import functools
import threading

from utils.logger import get_logger, trace_tool_call
from utils.response import fail

from core.tool_registry import tool_registry

logger = get_logger("mcp_router")

_execution_lock = threading.RLock()


def _wrap(tool_name: str, func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        logger.info("Tool call: %s(%s)", tool_name, kwargs or args)
        with _execution_lock:
            try:
                result = func(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - last-resort safety net
                logger.exception("Unhandled exception in tool '%s'", tool_name)
                result = fail(f"Internal server error in '{tool_name}': {exc}")
        trace_tool_call(tool_name, kwargs or {"args": args}, result)
        return result

    return wrapped


def register_all_tools(mcp_app) -> int:
    """Register every tool in the global registry onto `mcp_app` (a FastMCP instance)."""
    count = 0
    for spec in tool_registry.all():
        mcp_app.tool(name=spec.name, description=spec.description)(
            _wrap(spec.name, spec.func)
        )
        count += 1
    logger.info("Registered %s MCP tools.", count)
    return count
