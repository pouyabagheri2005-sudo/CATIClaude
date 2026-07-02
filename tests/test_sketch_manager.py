"""
Tests for SketchManager's closed-loop detection logic, using fake pyCATIA
objects so no real CATIA connection is required.
"""

from unittest.mock import MagicMock

import pytest
from catia.sketch_manager import SketchManager
from utils.error_handler import GeometryValidationError


class FakeFactory2D:
    def create_line(self, x1, y1, x2, y2):
        return MagicMock()

    def create_closed_circle(self, x, y, r):
        return MagicMock()


class FakeSketch:
    def __init__(self, name):
        self.name = name
        self.closed = False

    def open_edition(self):
        return FakeFactory2D()

    def close_edition(self):
        self.closed = True


class FakeSketches:
    def __init__(self):
        self._n = 0

    def add(self, reference):
        self._n += 1
        return FakeSketch(f"Sketch.{self._n}")


class FakeBody:
    def __init__(self):
        self.sketches = FakeSketches()


@pytest.fixture
def wrapper():
    fake_wrapper = MagicMock()
    fake_wrapper.get_part.return_value = MagicMock()
    fake_wrapper.get_or_create_body.return_value = FakeBody()
    fake_wrapper.resolve_plane.return_value = MagicMock()
    fake_wrapper.update.return_value = None
    return fake_wrapper


def test_create_sketch_opens_edition(wrapper):
    manager = SketchManager(wrapper)
    result = manager.create_sketch("xy")
    assert result["sketch"] == "Sketch.1"
    assert result["plane"] == "xy"


def test_rectangle_is_closed(wrapper):
    manager = SketchManager(wrapper)
    manager.create_sketch("xy")
    manager.add_rectangle(0, 0, 100, 50)
    result = manager.close_sketch()
    assert result["closed"] is True


def test_circle_is_closed(wrapper):
    manager = SketchManager(wrapper)
    manager.create_sketch("xy")
    manager.add_circle(0, 0, 5)
    result = manager.close_sketch()
    assert result["closed"] is True


def test_open_lines_raise_on_close(wrapper):
    manager = SketchManager(wrapper)
    manager.create_sketch("xy")
    manager.add_line(0, 0, 10, 0)
    manager.add_line(10, 0, 10, 10)
    # Missing the two closing segments -> not a closed loop.
    with pytest.raises(GeometryValidationError):
        manager.close_sketch()


def test_closed_polygon_via_four_lines(wrapper):
    manager = SketchManager(wrapper)
    manager.create_sketch("xy")
    manager.add_line(0, 0, 10, 0)
    manager.add_line(10, 0, 10, 10)
    manager.add_line(10, 10, 0, 10)
    manager.add_line(0, 10, 0, 0)
    result = manager.close_sketch()
    assert result["closed"] is True


def test_negative_radius_rejected(wrapper):
    manager = SketchManager(wrapper)
    manager.create_sketch("xy")
    with pytest.raises(GeometryValidationError):
        manager.add_circle(0, 0, -5)
