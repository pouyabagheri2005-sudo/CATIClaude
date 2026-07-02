"""
tools/design_tools.py

High-level natural-language design tool. Wraps the full pipeline:

    Intent Parser -> CAD Planner -> Validator -> Executor -> pyCATIA -> CATIA V5

This is the tool that most directly answers prompts like:
    "Design a lightweight L-bracket with 120mm base, 10mm thickness,
     and 2 mounting holes"

Supported shapes: bracket, plate, shaft, housing. For anything else, Claude
is expected to compose the atomic tools (create_sketch, add_*, pad/pocket,
...) directly, which gives it full flexibility beyond these four presets.
"""

from __future__ import annotations

from core.tool_registry import tool_registry
from engine.cad_planner import build_plan
from engine.executor import PlanExecutor
from engine.intent_parser import parse_intent
from utils.error_handler import CatiaMcpError
from utils.logger import get_logger
from utils.response import fail, ok

logger = get_logger("tools.design")
_executor = PlanExecutor()


@tool_registry.register(
    description=(
        "Design a part directly from a natural-language description "
        "(bracket, plate, shaft, or housing). Parses intent, builds a CAD "
        "plan with explicit engineering assumptions, validates it, and "
        "(unless execute=False) runs it end-to-end in CATIA V5."
    )
)
def design_from_text(description: str, execute: bool = True) -> dict:
    """Turn a natural-language design request into real CATIA geometry.

    Args:
        description: Free-text engineering request, e.g. "Design a
            lightweight L-bracket with 120mm base, 10mm thickness, and 2
            mounting holes".
        execute: If False, only returns the generated plan without running
            it (useful for review/dry-run before touching CATIA).
    """
    try:
        intent = parse_intent(description)
        plan, warnings = build_plan(intent)

        result = {
            "shape": intent.shape,
            "dimensions": intent.dimensions,
            "hole_count": intent.hole_count,
            "hole_diameter": intent.hole_diameter,
            "assumptions": intent.assumptions,
            "warnings": warnings,
            "plan": plan,
        }

        if not execute:
            return ok(result)

        execution = _executor.execute_plan(plan, stop_on_error=True)
        result["execution"] = execution
        if execution["success"]:
            return ok(result)

        failed_step = execution.get("failed_step", {}) or {}
        return fail(
            f"Plan execution stopped at step {failed_step.get('step')}.", data=result
        )
    except CatiaMcpError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("design_from_text failed")
        return fail(f"Unexpected error: {exc}")
