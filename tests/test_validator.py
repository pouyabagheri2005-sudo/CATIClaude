"""Tests for engine.validator geometry feasibility checks."""

import pytest
from engine.validator import validate_hole_fits, validate_plan, validate_rectangle
from utils.error_handler import GeometryValidationError


def test_validate_rectangle_ok():
    validate_rectangle(100, 50, 5)  # should not raise


def test_validate_rectangle_negative_width():
    with pytest.raises(GeometryValidationError):
        validate_rectangle(-10, 50)


def test_validate_rectangle_thickness_too_large():
    with pytest.raises(GeometryValidationError):
        validate_rectangle(10, 50, 20)


def test_validate_hole_fits_ok():
    validate_hole_fits(diameter=6, host_width=40, host_height=40)


def test_validate_hole_fits_too_big():
    with pytest.raises(GeometryValidationError):
        validate_hole_fits(diameter=50, host_width=40, host_height=40)


def test_validate_plan_flags_unclosed_sketch_before_pad():
    plan = [
        {"step": 1, "action": "create_sketch", "params": {}},
        {"step": 2, "action": "pad", "params": {"length": 10}},
    ]
    warnings = validate_plan(plan)
    assert any("still open" in w for w in warnings)


def test_validate_plan_flags_negative_lengths():
    plan = [
        {"step": 1, "action": "create_sketch", "params": {}},
        {"step": 2, "action": "add_rectangle", "params": {"width": 0, "height": 10}},
        {"step": 3, "action": "close_sketch", "params": {}},
        {"step": 4, "action": "pad", "params": {"length": -5}},
    ]
    warnings = validate_plan(plan)
    assert any("rectangle" in w for w in warnings)
    assert any("pad" in w for w in warnings)


def test_validate_plan_clean_plan_has_no_warnings():
    plan = [
        {"step": 1, "action": "create_sketch", "params": {}},
        {"step": 2, "action": "add_rectangle", "params": {"width": 10, "height": 10}},
        {"step": 3, "action": "close_sketch", "params": {}},
        {"step": 4, "action": "pad", "params": {"length": 5}},
    ]
    assert validate_plan(plan) == []
