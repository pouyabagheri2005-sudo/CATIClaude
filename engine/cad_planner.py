"""
engine/cad_planner.py

Layer 4 - CAD Planner: converts a structured DesignIntent (from the intent
parser) into an ordered, atomic list of CAD plan steps whose `action`/
`params` map 1:1 onto the MCP tool signatures. This is the JSON step list
described in the project specification:

    [{"step": 1, "action": "create_sketch", "params": {...}}, ...]
"""

from __future__ import annotations

from typing import List, Tuple

from utils.error_handler import PlanningError

from engine.intent_parser import DesignIntent
from engine.validator import validate_plan


class _StepBuilder:
    """Small helper that auto-increments the `step` counter for a plan."""

    def __init__(self):
        self._n = 1
        self.steps: List[dict] = []

    def add(self, action: str, params: dict) -> "_StepBuilder":
        self.steps.append({"step": self._n, "action": action, "params": params})
        self._n += 1
        return self


def _distribute_holes(
    count: int, span: float, cross_center: float, margin: float
) -> List[Tuple[float, float]]:
    """Evenly space `count` holes along a span of length `span`, centered at
    `cross_center` in the perpendicular direction.
    """
    usable_start = margin
    usable_end = span - margin
    if count == 1:
        xs = [(usable_start + usable_end) / 2.0]
    else:
        step = (usable_end - usable_start) / (count - 1)
        xs = [usable_start + i * step for i in range(count)]
    return [(x, cross_center) for x in xs]


def plan_bracket(intent: DesignIntent) -> List[dict]:
    base = intent.dimensions["base"]
    height = intent.dimensions["height"]
    thickness = intent.dimensions["thickness"]
    width = intent.dimensions.get("width", 40.0)

    b = _StepBuilder()
    b.add("create_part", {"name": "L_Bracket"})
    b.add("create_sketch", {"plane": "xy"})

    # L-profile: a horizontal leg (base x thickness) and a vertical leg
    # (thickness x height), drawn as a single closed 6-segment polyline.
    leg = thickness
    points = [
        (0, 0),
        (base, 0),
        (base, leg),
        (leg, leg),
        (leg, height),
        (0, height),
        (0, 0),
    ]
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        b.add("add_line", {"x1": x1, "y1": y1, "x2": x2, "y2": y2})

    b.add("close_sketch", {})
    b.add("pad", {"length": width})

    if intent.hole_count > 0:
        hole_diameter = (
            intent.hole_diameter if intent.hole_diameter is not None else 6.0
        )
        margin = max(hole_diameter, 8.0)
        for hx, hy in _distribute_holes(intent.hole_count, base, leg / 2.0, margin):
            b.add(
                "hole",
                {
                    "x": hx,
                    "y": hy,
                    "diameter": hole_diameter,
                    "depth": width + 1.0,
                },
            )

    b.add("export_step", {"path": "output/L_Bracket.stp"})
    return b.steps


def plan_plate(intent: DesignIntent) -> List[dict]:
    length = intent.dimensions["length"]
    width = intent.dimensions["width"]
    thickness = intent.dimensions["thickness"]

    b = _StepBuilder()
    b.add("create_part", {"name": "Plate"})
    b.add("create_sketch", {"plane": "xy"})
    b.add("add_rectangle", {"x": 0, "y": 0, "width": length, "height": width})
    b.add("close_sketch", {})
    b.add("pad", {"length": thickness})

    if intent.hole_count > 0:
        hole_diameter = (
            intent.hole_diameter if intent.hole_diameter is not None else 6.0
        )
        margin = max(hole_diameter, 8.0)
        for hx, hy in _distribute_holes(intent.hole_count, length, width / 2.0, margin):
            b.add(
                "hole",
                {
                    "x": hx,
                    "y": hy,
                    "diameter": hole_diameter,
                    "depth": thickness + 1.0,
                },
            )

    b.add("export_step", {"path": "output/Plate.stp"})
    return b.steps


def plan_shaft(intent: DesignIntent) -> List[dict]:
    diameter = intent.dimensions["diameter"]
    length = intent.dimensions["length"]

    b = _StepBuilder()
    b.add("create_part", {"name": "Shaft"})
    b.add("create_sketch", {"plane": "xy"})
    b.add("add_circle", {"x": 0, "y": 0, "radius": diameter / 2.0})
    b.add("close_sketch", {})
    b.add("pad", {"length": length})
    b.add("export_step", {"path": "output/Shaft.stp"})
    return b.steps


def plan_housing(intent: DesignIntent) -> List[dict]:
    length = intent.dimensions["length"]
    width = intent.dimensions["width"]
    height = intent.dimensions["height"]
    thickness = intent.dimensions["thickness"]

    b = _StepBuilder()
    b.add("create_part", {"name": "Housing"})

    # Outer shell.
    b.add("create_sketch", {"plane": "xy"})
    b.add("add_rectangle", {"x": 0, "y": 0, "width": length, "height": width})
    b.add("close_sketch", {})
    b.add("pad", {"length": height})

    # Hollow it out, leaving `thickness` walls on all sides and the floor.
    b.add("create_sketch", {"plane": "xy"})
    b.add(
        "add_rectangle",
        {
            "x": thickness,
            "y": thickness,
            "width": length - 2 * thickness,
            "height": width - 2 * thickness,
        },
    )
    b.add("close_sketch", {})
    b.add("pocket", {"depth": height - thickness})

    b.add("export_step", {"path": "output/Housing.stp"})
    return b.steps


_PLANNERS = {
    "bracket": plan_bracket,
    "plate": plan_plate,
    "shaft": plan_shaft,
    "housing": plan_housing,
}


def build_plan(intent: DesignIntent) -> Tuple[List[dict], List[str]]:
    planner = _PLANNERS.get(intent.shape)
    if planner is None:
        raise PlanningError(f"No CAD planner registered for shape '{intent.shape}'.")
    plan = planner(intent)
    warnings = validate_plan(plan)
    return plan, warnings
