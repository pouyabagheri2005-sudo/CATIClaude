"""
server.py

Entry point for the CATIA V5 MCP server.

Run this with a Python interpreter that has pycatia/pywin32 installed on a
Windows machine with CATIA V5 licensed and available. Communicates with
Claude Desktop (or any MCP client) over the stdio transport.

Usage:
    python server.py            # normal run
    python server.py --debug    # verbose debug logging to logs/catia_mcp.log
"""

from __future__ import annotations

import sys

from core.mcp_router import register_all_tools
from mcp.server.fastmcp import FastMCP
from utils.logger import get_logger, setup_logging

setup_logging(debug="--debug" in sys.argv)
logger = get_logger("server")

# Import tool modules purely for their side effect of registering with
# core.tool_registry. Order does not matter.
import tools.analysis_tools  # noqa: E402,F401
import tools.design_tools  # noqa: E402,F401
import tools.document_tools  # noqa: E402,F401
import tools.export_tools  # noqa: E402,F401
import tools.feature_tools  # noqa: E402,F401
import tools.parameter_tools  # noqa: E402,F401
import tools.sketch_tools  # noqa: E402,F401

mcp = FastMCP(
    "catia-mcp",
    instructions=(
        "Tools for controlling CATIA V5 through pyCATIA. Typical atomic "
        "workflow: create_part -> create_sketch -> add_rectangle/add_circle/"
        "add_line -> close_sketch -> pad/pocket -> (optional) fillet/chamfer "
        "-> export_step. A sketch MUST be closed with close_sketch() before "
        "pad/pocket will accept it. For common parts (bracket, plate, shaft, "
        "housing), design_from_text(description) runs the whole pipeline "
        "from a single natural-language request. Every tool returns "
        "{success, data, error, context} where `context` reports the "
        "current active document/part/sketch."
    ),
)

register_all_tools(mcp)


def main() -> None:
    logger.info("Starting CATIA MCP server (stdio transport)...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
