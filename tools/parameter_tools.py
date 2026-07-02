"""
tools/parameter_tools.py

MCP tools for CATIA Part parameters (named, driving dimensions), enabling
parametric follow-up edits after a part has been created.
"""

from __future__ import annotations

from catia.managers import parameter_manager
from core.tool_registry import tool_registry
from utils.error_handler import CatiaMcpError
from utils.logger import get_logger
from utils.response import fail, ok

logger = get_logger("tools.parameter")


@tool_registry.register(
    description="Create or update a named CATIA Part parameter (a driving dimension)."
)
def set_parameter(name: str, value: float) -> dict:
    """Set (creating if necessary) a length parameter on the active part."""
    try:
        return ok(parameter_manager.set_parameter(name, value))
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("set_parameter failed")
        return fail(f"Unexpected error: {exc}")


@tool_registry.register(
    description="Read the current value of a named CATIA Part parameter."
)
def get_parameter(name: str) -> dict:
    """Get the current value of a parameter on the active part."""
    try:
        return ok(parameter_manager.get_parameter(name))
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_parameter failed")
        return fail(f"Unexpected error: {exc}")


@tool_registry.register(
    description="List all parameter names defined on the active part."
)
def list_parameters() -> dict:
    """List all parameter names on the active part."""
    try:
        return ok(parameter_manager.list_parameters())
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("list_parameters failed")
        return fail(f"Unexpected error: {exc}")
