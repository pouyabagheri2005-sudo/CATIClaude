"""
tools/document_tools.py

MCP tools for CATIA document/part lifecycle: create, open, save, close.
"""

from __future__ import annotations

from typing import Optional

from catia.managers import part_manager
from core.tool_registry import tool_registry
from utils.error_handler import CatiaMcpError
from utils.logger import get_logger
from utils.response import fail, ok

logger = get_logger("tools.document")


@tool_registry.register(
    description="Create a new CATIA Part document (.CATPart) and make it the active part."
)
def create_part(name: str = "Part1") -> dict:
    """Create a new .CATPart document.

    Args:
        name: Human-readable name to assign to the new part.
    """
    try:
        return ok(part_manager.create_part(name))
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("create_part failed")
        return fail(f"Unexpected error: {exc}")


@tool_registry.register(
    description="Open an existing CATIA document (.CATPart/.CATProduct) from disk."
)
def open_document(path: str) -> dict:
    """Open an existing CATIA document.

    Args:
        path: Absolute filesystem path to the .CATPart/.CATProduct file.
    """
    try:
        return ok(part_manager.open_document(path))
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("open_document failed")
        return fail(f"Unexpected error: {exc}")


@tool_registry.register(
    description="Save the active CATIA document, optionally to a new path."
)
def save_document(path: Optional[str] = None) -> dict:
    """Save the currently active document.

    Args:
        path: Optional new path to 'Save As'. If omitted, saves in place.
    """
    try:
        return ok(part_manager.save_document(path))
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("save_document failed")
        return fail(f"Unexpected error: {exc}")


@tool_registry.register(
    description="Close the active CATIA document and clear session state."
)
def close_document() -> dict:
    """Close the currently active document."""
    try:
        return ok(part_manager.close_document())
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("close_document failed")
        return fail(f"Unexpected error: {exc}")
