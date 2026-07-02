"""Tests for engine.cad_planner step generation."""

from engine.cad_planner import build_plan
from engine.intent_parser import parse_intent


def test_bracket_plan_structure_and_holes():
    intent = parse_intent("L-bracket with 120mm base, 10mm thickness, 2 mounting holes")
    plan, warnings = build_plan(intent)
    actions = [s["action"] for s in plan]

    assert actions[0] == "create_part"
    assert "create_sketch" in actions
    assert "close_sketch" in actions
    assert "pad" in actions
    assert actions.count("hole") == 2
    assert actions[-1] == "export_step"
    assert warnings == []

    # Steps must be sequentially numbered starting at 1.
    assert [s["step"] for s in plan] == list(range(1, len(plan) + 1))


def test_plate_plan_has_rectangle_and_pad():
    intent = parse_intent("Make a plate 100mm x 60mm x 5mm thick")
    plan, _ = build_plan(intent)
    actions = [s["action"] for s in plan]
    assert "add_rectangle" in actions
    assert "pad" in actions


def test_shaft_plan_has_circle_and_pad():
    intent = parse_intent("Shaft 20mm diameter, 150mm length")
    plan, _ = build_plan(intent)
    actions = [s["action"] for s in plan]
    assert "add_circle" in actions
    assert "pad" in actions


def test_housing_plan_has_pocket_for_hollowing():
    intent = parse_intent("Housing 150mm long, 90mm wide, 60mm tall, 3mm thick")
    plan, _ = build_plan(intent)
    actions = [s["action"] for s in plan]
    assert actions.count("create_sketch") == 2
    assert "pocket" in actions
