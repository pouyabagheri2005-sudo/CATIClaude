"""
utils/units.py

Unit normalization utilities.

CATIA's COM API for Mechanical Design (Sketcher / Part Design) expects
lengths in millimeters when using the Factory2D / ShapeFactory calls used by
this project, regardless of the document's display units. This module
normalizes any user-supplied value (with an optional unit suffix) to that
convention, per the "normalize units (mm default)" requirement.
"""

from __future__ import annotations

import re

from utils.error_handler import GeometryValidationError

_UNIT_TO_MM = {
    "mm": 1.0,
    "cm": 10.0,
    "m": 1000.0,
    "in": 25.4,
    "inch": 25.4,
    "ft": 304.8,
}

_NUMERIC_WITH_UNIT = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*([a-zA-Z]*)\s*$")

DEFAULT_UNIT = "mm"


def to_mm(value, default_unit: str = DEFAULT_UNIT) -> float:
    """Normalize a number or a "12.5mm"-style string to millimeters (float)."""
    if isinstance(value, bool):
        raise GeometryValidationError("Boolean is not a valid numeric length.")
    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        match = _NUMERIC_WITH_UNIT.match(value)
        if not match:
            raise GeometryValidationError(f"Cannot parse numeric value from '{value}'")
        number, unit = match.groups()
        unit = (unit or default_unit).lower()
        if unit not in _UNIT_TO_MM:
            raise GeometryValidationError(f"Unsupported unit '{unit}' in '{value}'")
        return float(number) * _UNIT_TO_MM[unit]

    raise GeometryValidationError(f"Cannot convert value of type {type(value)} to mm")


def mm_to(value_mm: float, unit: str) -> float:
    unit = unit.lower()
    if unit not in _UNIT_TO_MM:
        raise GeometryValidationError(f"Unsupported unit '{unit}'")
    return value_mm / _UNIT_TO_MM[unit]
