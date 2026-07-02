"""
utils/response.py

The standard MCP tool response envelope mandated by the project spec:

    {
        "success": true/false,
        "data": {},
        "error": null,
        "context": {"active_part": "", "active_sketch": "", ...}
    }

Every tool function in `tools/*.py` must return the result of `ok(...)` or
`fail(...)` so Claude always receives a consistent, structured payload.
"""

from __future__ import annotations

from typing import Any, Optional

from core.state_manager import state


def make_response(success: bool, data: Any = None, error: Optional[str] = None) -> dict:
    return {
        "success": success,
        "data": data if data is not None else {},
        "error": error,
        "context": state.get_context(),
    }


def ok(data: Any = None) -> dict:
    return make_response(True, data=data, error=None)


def fail(error: str, data: Any = None) -> dict:
    return make_response(False, data=data, error=error)
