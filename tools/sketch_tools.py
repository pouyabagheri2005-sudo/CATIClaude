"""
tools/sketch_tools.py

MCP tools for 2D sketch creation: create_sketch, add_line, add_circle,
add_rectangle, close_sketch.
"""

from __future__ import annotations

from typing import Optional

from catia.managers import sketch_manager
from core.tool_registry import tool_registry
from utils.error_handler import CatiaMcpError
from utils.logger import get_logger
from utils.response import fail, ok

logger = get_logger("tools.sketch")


@tool_registry.register(
    description="Create a new sketch on a named plane ('xy', 'yz', or 'zx') and open it for editing."
)
def create_sketch(plane: str = "xy") -> dict:
    """Create and open a new sketch.

    Args:
        plane: One of 'xy', 'yz', 'zx' (aliases: top/front/right).
    """
    try:
        return ok(sketch_manager.create_sketch(plane))
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("create_sketch failed")
        return fail(f"Unexpected error: {exc}")


@tool_registry.register(
    description="Add a straight line segment to the currently open sketch."
)
def add_line(
    x1: float, y1: float, x2: float, y2: float, sketch: Optional[str] = None
) -> dict:
    """Add a line from (x1, y1) to (x2, y2) in sketch-plane millimeters.

    Args:
        x1, y1: Start point.
        x2, y2: End point.
        sketch: Optional sketch name; defaults to the currently active sketch.
    """
    try:
        return ok(sketch_manager.add_line(x1, y1, x2, y2, sketch))
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("add_line failed")
        return fail(f"Unexpected error: {exc}")


@tool_registry.register(description="Add a closed circle to the currently open sketch.")
def add_circle(x: float, y: float, radius: float, sketch: Optional[str] = None) -> dict:
    """Add a closed circle centered at (x, y) with the given radius (mm)."""
    try:
        return ok(sketch_manager.add_circle(x, y, radius, sketch))
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("add_circle failed")
        return fail(f"Unexpected error: {exc}")


@tool_registry.register(
    description="Add a closed rectangle to the currently open sketch."
)
def add_rectangle(
    x: float, y: float, width: float, height: float, sketch: Optional[str] = None
) -> dict:
    """Add a rectangle whose lower-left corner is at (x, y)."""
    try:
        return ok(sketch_manager.add_rectangle(x, y, width, height, sketch))
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("add_rectangle failed")
        return fail(f"Unexpected error: {exc}")


@tool_registry.register(
    description="Close the currently open sketch. Required before pad/pocket."
)
def close_sketch(sketch: Optional[str] = None) -> dict:
    """Close the sketch edition, validating that the profile forms a closed loop."""
    try:
        return ok(sketch_manager.close_sketch(sketch))
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("close_sketch failed")
        return fail(f"Unexpected error: {exc}")
