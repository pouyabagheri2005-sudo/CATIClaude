"""Tests for utils.units normalization."""

import pytest
from utils.error_handler import GeometryValidationError
from utils.units import to_mm


def test_to_mm_plain_number():
    assert to_mm(10) == 10.0
    assert to_mm(2.5) == 2.5


def test_to_mm_string_with_unit():
    assert to_mm("2cm") == 20.0
    assert to_mm("1in") == 25.4
    assert to_mm("0.1m") == 100.0


def test_to_mm_default_unit_is_mm():
    assert to_mm("15") == 15.0


def test_to_mm_rejects_garbage():
    with pytest.raises(GeometryValidationError):
        to_mm("not-a-number")


def test_to_mm_rejects_unknown_unit():
    with pytest.raises(GeometryValidationError):
        to_mm("10furlongs")
