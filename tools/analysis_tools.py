"""
tools/analysis_tools.py

MCP tools for read-only introspection: get_tree, get_edges, measure_distance,
get_mass_properties, validate_geometry.
"""

from __future__ import annotations

from catia.managers import analysis_manager
from core.tool_registry import tool_registry
from utils.error_handler import CatiaMcpError
from utils.logger import get_logger
from utils.response import fail, ok

logger = get_logger("tools.analysis")


@tool_registry.register(
    description="Return the active part's feature tree (bodies, sketches, features)."
)
def get_tree() -> dict:
    """Return the active part's specification tree summary."""
    try:
        return ok(analysis_manager.get_tree())
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_tree failed")
        return fail(f"Unexpected error: {exc}")


@tool_registry.register(
    description="Enumerate solid edges and register short edge_id values for use with fillet()/chamfer()."
)
def get_edges() -> dict:
    """List edges of the active solid, registering short ids (E1, E2, ...)."""
    try:
        return ok(analysis_manager.get_edges())
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_edges failed")
        return fail(f"Unexpected error: {exc}")


@tool_registry.register(
    description="Measure the minimum distance between two named CATIA objects."
)
def measure_distance(obj1: str, obj2: str) -> dict:
    """Measure distance between two named objects in the active document."""
    try:
        return ok(analysis_manager.measure_distance(obj1, obj2))
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("measure_distance failed")
        return fail(f"Unexpected error: {exc}")


@tool_registry.register(
    description="Compute mass, volume, and center of gravity for the active part's main body."
)
def get_mass_properties() -> dict:
    """Return mass properties (mass, volume, center of gravity) of the active body."""
    try:
        return ok(analysis_manager.get_mass_properties())
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_mass_properties failed")
        return fail(f"Unexpected error: {exc}")


@tool_registry.register(
    description="Validate that the active part updates cleanly and has a valid solid shape."
)
def validate_geometry() -> dict:
    """Run a lightweight validation pass over the active part."""
    try:
        return ok(analysis_manager.validate_geometry())
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("validate_geometry failed")
        return fail(f"Unexpected error: {exc}")
