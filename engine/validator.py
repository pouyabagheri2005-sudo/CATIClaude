"""
engine/validator.py

Layer 4 support - Validator: geometry feasibility and logic checks, applied
both to individual manager calls (see catia/*.py, which raise
GeometryValidationError directly) and to whole CAD plans before execution.
"""

from __future__ import annotations

from typing import List

from utils.error_handler import GeometryValidationError


def validate_positive(name: str, value) -> None:
    if value is None or value <= 0:
        raise GeometryValidationError(
            f"'{name}' must be a positive number, got {value}."
        )


def validate_rectangle(width: float, height: float, thickness: float = None) -> None:
    validate_positive("width", width)
    validate_positive("height", height)
    if thickness is not None:
        validate_positive("thickness", thickness)
        if thickness > min(width, height):
            raise GeometryValidationError(
                "thickness cannot exceed the smallest base dimension "
                f"(thickness={thickness}, min(width,height)={min(width, height)})."
            )


def validate_hole_fits(
    diameter: float, host_width: float, host_height: float, margin: float = 2.0
) -> None:
    validate_positive("diameter", diameter)
    if diameter + margin * 2 > min(host_width, host_height):
        raise GeometryValidationError(
            f"Hole diameter {diameter}mm is too large for the host geometry "
            f"({host_width}x{host_height}mm) with a {margin}mm edge margin."
        )


def validate_plan(plan: List[dict]) -> List[str]:
    """Static, pre-execution sanity checks over a full CAD plan.

    Returns a list of warning strings (never raises); the caller decides
    whether any warning should block execution.
    """
    warnings: List[str] = []
    sketch_open = False

    for step in plan:
        action = step.get("action")
        params = step.get("params", {})

        if action == "create_sketch":
            if sketch_open:
                warnings.append(
                    f"Step {step.get('step')}: a previous sketch was never closed."
                )
            sketch_open = True
        elif action == "close_sketch":
            sketch_open = False
        elif action in ("pad", "pocket"):
            if sketch_open:
                warnings.append(
                    f"Step {step.get('step')}: '{action}' requested while a sketch is still open."
                )
            length_key = "length" if action == "pad" else "depth"
            if params.get(length_key, 0) <= 0:
                warnings.append(
                    f"Step {step.get('step')}: '{action}' {length_key} must be positive."
                )
        elif action == "add_rectangle":
            if params.get("width", 0) <= 0 or params.get("height", 0) <= 0:
                warnings.append(
                    f"Step {step.get('step')}: rectangle must have positive width/height."
                )
        elif action == "add_circle":
            if params.get("radius", 0) <= 0:
                warnings.append(
                    f"Step {step.get('step')}: circle must have positive radius."
                )
        elif action == "hole":
            if params.get("diameter", 0) <= 0 or params.get("depth", 0) <= 0:
                warnings.append(
                    f"Step {step.get('step')}: hole diameter/depth must be positive."
                )

    if sketch_open:
        warnings.append("Plan ends with an unclosed sketch.")

    return warnings
