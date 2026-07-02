"""
tools/export_tools.py

MCP tools for exporting the active document: export_step, export_iges,
export_stl.
"""

from __future__ import annotations

from catia.managers import export_manager
from core.tool_registry import tool_registry
from utils.error_handler import CatiaMcpError
from utils.logger import get_logger
from utils.response import fail, ok

logger = get_logger("tools.export")


@tool_registry.register(description="Export the active document to a STEP (.stp) file.")
def export_step(path: str) -> dict:
    """Export to STEP.

    Args:
        path: Destination file path (parent directories are created automatically).
    """
    try:
        return ok(export_manager.export_step(path))
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("export_step failed")
        return fail(f"Unexpected error: {exc}")


@tool_registry.register(
    description="Export the active document to an IGES (.igs) file."
)
def export_iges(path: str) -> dict:
    """Export to IGES.

    Args:
        path: Destination file path (parent directories are created automatically).
    """
    try:
        return ok(export_manager.export_iges(path))
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("export_iges failed")
        return fail(f"Unexpected error: {exc}")


@tool_registry.register(description="Export the active document to an STL (.stl) file.")
def export_stl(path: str) -> dict:
    """Export to STL.

    Args:
        path: Destination file path (parent directories are created automatically).
    """
    try:
        return ok(export_manager.export_stl(path))
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("export_stl failed")
        return fail(f"Unexpected error: {exc}")
