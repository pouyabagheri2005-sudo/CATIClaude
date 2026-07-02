"""
engine/intent_parser.py

Layer 4 - Intent Parser.

Claude Desktop (the LLM) is the primary natural-language understanding
engine for this system: for anything non-trivial it is expected to call
the atomic MCP tools directly (create_sketch, add_rectangle, pad, ...).

This module provides a deterministic, rule-based fallback used by the
single high-level `design_from_text` tool, so common requests
("L-bracket 120mm base, 10mm thickness, 2 mounting holes") can be turned
into geometry without any extra LLM round trip. It performs:
    - shape classification (bracket / plate / shaft / housing)
    - dimension extraction with unit normalization (mm default)
    - explicit, logged engineering assumptions for anything unspecified
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from utils.units import to_mm

SHAPE_KEYWORDS = {
    "bracket": ["l-bracket", "l bracket", "angle bracket", "bracket"],
    "shaft": ["shaft", "axle", "rod"],
    "housing": ["housing", "enclosure", "case"],
    "plate": ["plate", "panel", "flat plate", "box"],
}

_DIM_PATTERNS = {
    "base": re.compile(
        r"(\d+(?:\.\d+)?)\s*mm\s*base|base(?:\s+of)?\s*(\d+(?:\.\d+)?)\s*mm", re.I
    ),
    "length": re.compile(
        r"(\d+(?:\.\d+)?)\s*mm\s*(?:long|length)|length(?:\s+of)?\s*(\d+(?:\.\d+)?)\s*mm",
        re.I,
    ),
    "width": re.compile(
        r"(\d+(?:\.\d+)?)\s*mm\s*wide|width(?:\s+of)?\s*(\d+(?:\.\d+)?)\s*mm", re.I
    ),
    "height": re.compile(
        r"(\d+(?:\.\d+)?)\s*mm\s*(?:tall|high|height)|height(?:\s+of)?\s*(\d+(?:\.\d+)?)\s*mm",
        re.I,
    ),
    "thickness": re.compile(
        r"(\d+(?:\.\d+)?)\s*mm\s*thick(?:ness)?|thickness(?:\s+of)?\s*(\d+(?:\.\d+)?)\s*mm",
        re.I,
    ),
    "diameter": re.compile(
        r"(\d+(?:\.\d+)?)\s*mm\s*diameter|diameter(?:\s+of)?\s*(\d+(?:\.\d+)?)\s*mm",
        re.I,
    ),
}

_HOLE_COUNT_PATTERN = re.compile(r"(\d+)\s*(?:mounting\s*)?holes?", re.I)
_GENERIC_MM_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*mm")


@dataclass
class DesignIntent:
    shape: str
    dimensions: dict = field(default_factory=dict)
    hole_count: int = 0
    hole_diameter: Optional[float] = None
    assumptions: List[str] = field(default_factory=list)
    raw_text: str = ""


def classify_shape(text: str) -> str:
    lowered = text.lower()
    for shape, keywords in SHAPE_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return shape
    return "plate"  # safest generic default: a simple padded rectangle


def extract_dimensions(text: str) -> dict:
    dims = {}
    for key, pattern in _DIM_PATTERNS.items():
        match = pattern.search(text)
        if match:
            value = next((g for g in match.groups() if g), None)
            if value:
                dims[key] = to_mm(float(value))
    return dims


def extract_generic_numbers(text: str, already_used: List[float]) -> List[float]:
    all_numbers = [to_mm(float(v)) for v in _GENERIC_MM_PATTERN.findall(text)]
    used = list(already_used)
    remaining = []
    for n in all_numbers:
        if n in used:
            used.remove(n)
        else:
            remaining.append(n)
    return remaining


def extract_hole_info(text: str, dims: dict) -> Tuple[int, Optional[float]]:
    hole_count = 0
    match = _HOLE_COUNT_PATTERN.search(text)
    if match:
        hole_count = int(match.group(1))
    elif "hole" in text.lower():
        hole_count = 1
    hole_diameter = dims.get("diameter")
    return hole_count, hole_diameter


_ORDERED_KEYS_BY_SHAPE = {
    "bracket": ["base", "height", "thickness"],
    "plate": ["length", "width", "thickness"],
    "shaft": ["diameter", "length"],
    "housing": ["length", "width", "height", "thickness"],
}

_DEFAULTS_BY_SHAPE = {
    "bracket": {"base": 100.0, "height": 80.0, "thickness": 5.0, "width": 40.0},
    "plate": {"length": 100.0, "width": 60.0, "thickness": 5.0},
    "shaft": {"diameter": 20.0, "length": 100.0},
    "housing": {"length": 100.0, "width": 80.0, "height": 40.0, "thickness": 3.0},
}


def parse_intent(text: str) -> DesignIntent:
    """Convert a free-text design request into a structured DesignIntent.

    Any parameter that cannot be found in the text is filled with a
    documented, conservative engineering default (see `.assumptions`).
    """
    shape = classify_shape(text)
    dims = extract_dimensions(text)
    hole_count, hole_diameter = extract_hole_info(text, dims)
    assumptions: List[str] = []

    generic_numbers = extract_generic_numbers(text, list(dims.values()))

    # Assign any unlabeled numbers positionally to the most relevant missing
    # dimension for the detected shape, in a sensible engineering order.
    for key in _ORDERED_KEYS_BY_SHAPE.get(shape, []):
        if key not in dims and generic_numbers:
            dims[key] = generic_numbers.pop(0)

    defaults = _DEFAULTS_BY_SHAPE.get(shape, _DEFAULTS_BY_SHAPE["plate"])
    for key, default_value in defaults.items():
        if key not in dims:
            dims[key] = default_value
            assumptions.append(f"'{key}' not specified; assumed {default_value}mm.")

    if hole_count > 0 and hole_diameter is None:
        hole_diameter = 6.0
        assumptions.append(
            "Hole diameter not specified; assumed 6mm (standard M6 clearance)."
        )

    return DesignIntent(
        shape=shape,
        dimensions=dims,
        hole_count=hole_count,
        hole_diameter=hole_diameter,
        assumptions=assumptions,
        raw_text=text,
    )
