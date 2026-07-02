"""
tools/feature_tools.py

MCP tools for 3D feature creation: pad, pocket, hole, fillet, chamfer.
"""

from __future__ import annotations

from typing import Optional

from catia.managers import feature_manager
from core.tool_registry import tool_registry
from utils.error_handler import CatiaMcpError
from utils.logger import get_logger
from utils.response import fail, ok

logger = get_logger("tools.feature")


@tool_registry.register(
    description="Extrude (pad) a closed sketch into a solid by `length` millimeters."
)
def pad(sketch: Optional[str] = None, length: float = 10.0) -> dict:
    """Pad a closed sketch.

    Args:
        sketch: Sketch name; defaults to the last closed sketch.
        length: Extrusion length in mm. Must be positive.
    """
    try:
        return ok(feature_manager.pad(sketch, length))
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("pad failed")
        return fail(f"Unexpected error: {exc}")


@tool_registry.register(
    description="Cut a pocket into the solid from a closed sketch to `depth` millimeters."
)
def pocket(sketch: Optional[str] = None, depth: float = 10.0) -> dict:
    """Cut a pocket from a closed sketch.

    Args:
        sketch: Sketch name; defaults to the last closed sketch.
        depth: Cut depth in mm. Must be positive.
    """
    try:
        return ok(feature_manager.pocket(sketch, depth))
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("pocket failed")
        return fail(f"Unexpected error: {exc}")


@tool_registry.register(
    description="Create a circular hole at (x, y) with the given diameter and depth."
)
def hole(x: float, y: float, diameter: float, depth: float, plane: str = "xy") -> dict:
    """Create a circular hole.

    Args:
        x, y: Hole center in mm, in `plane`'s local coordinates.
        diameter: Hole diameter in mm.
        depth: Hole depth in mm.
        plane: Plane to sketch the hole on ('xy', 'yz', 'zx').
    """
    try:
        return ok(feature_manager.hole(x, y, diameter, depth, plane))
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("hole failed")
        return fail(f"Unexpected error: {exc}")


@tool_registry.register(
    description="Apply a constant-radius fillet to an edge. Use get_edges() to discover edge_id values."
)
def fillet(edge_id: str, radius: float) -> dict:
    """Fillet an edge.

    Args:
        edge_id: Edge identifier from get_edges(), or a CATIA tree object name.
        radius: Fillet radius in mm.
    """
    try:
        return ok(feature_manager.fillet(edge_id, radius))
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("fillet failed")
        return fail(f"Unexpected error: {exc}")


@tool_registry.register(
    description="Apply a chamfer to an edge. Use get_edges() to discover edge_id values."
)
def chamfer(edge_id: str, value: float) -> dict:
    """Chamfer an edge.

    Args:
        edge_id: Edge identifier from get_edges(), or a CATIA tree object name.
        value: Chamfer leg length in mm.
    """
    try:
        return ok(feature_manager.chamfer(edge_id, value))
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("chamfer failed")
        return fail(f"Unexpected error: {exc}")
