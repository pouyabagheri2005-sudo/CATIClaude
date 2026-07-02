"""
core/tool_registry.py

Layer 1 - Tool Registry.

A framework-agnostic collection point for MCP tool definitions. Each
`tools/*.py` module registers its functions here with
`@tool_registry.register(...)`. `server.py` then binds every registered
tool onto the real FastMCP instance via `core.mcp_router`. This indirection
keeps tool implementations importable and unit-testable without spinning up
an actual MCP server.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass
class ToolSpec:
    name: str
    func: Callable
    description: str


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, name: Optional[str] = None, description: str = ""):
        def decorator(func: Callable):
            tool_name = name or func.__name__
            self._tools[tool_name] = ToolSpec(
                name=tool_name,
                func=func,
                description=description or (func.__doc__ or ""),
            )
            return func

        return decorator

    def all(self) -> List[ToolSpec]:
        return list(self._tools.values())

    def get(self, name: str) -> ToolSpec:
        return self._tools[name]

    def clear(self) -> None:
        self._tools.clear()


tool_registry = ToolRegistry()
