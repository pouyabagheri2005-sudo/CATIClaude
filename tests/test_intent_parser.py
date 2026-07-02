"""Tests for engine.intent_parser rule-based NL extraction."""

from engine.intent_parser import parse_intent


def test_parse_bracket_intent_from_spec_example():
    text = "Design a lightweight L-bracket with 120mm base, 10mm thickness, and 2 mounting holes"
    intent = parse_intent(text)
    assert intent.shape == "bracket"
    assert intent.dimensions["base"] == 120.0
    assert intent.dimensions["thickness"] == 10.0
    assert intent.hole_count == 2
    assert intent.hole_diameter == 6.0  # documented default assumption


def test_parse_shaft_intent():
    intent = parse_intent("Create a shaft 30mm diameter and 200mm length")
    assert intent.shape == "shaft"
    assert intent.dimensions["diameter"] == 30.0
    assert intent.dimensions["length"] == 200.0
    assert intent.assumptions == []


def test_parse_plate_defaults_when_unspecified():
    intent = parse_intent("Make a plate")
    assert intent.shape == "plate"
    assert "thickness" in intent.dimensions
    assert len(intent.assumptions) > 0


def test_parse_housing_intent():
    intent = parse_intent(
        "Design a housing 150mm long, 90mm wide, 60mm tall, 3mm thick"
    )
    assert intent.shape == "housing"
    assert intent.dimensions["length"] == 150.0
    assert intent.dimensions["width"] == 90.0
    assert intent.dimensions["height"] == 60.0
    assert intent.dimensions["thickness"] == 3.0


def test_no_holes_mentioned_means_zero_holes():
    intent = parse_intent("Make a plate 100mm x 50mm x 5mm")
    assert intent.hole_count == 0
    assert intent.hole_diameter is None
