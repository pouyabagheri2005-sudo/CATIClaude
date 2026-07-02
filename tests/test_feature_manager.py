"""
Tests for FeatureManager guard rails (closed-sketch enforcement, positive
dimension validation) using fakes instead of a live CATIA session.
"""

from unittest.mock import MagicMock

import pytest

from catia.feature_manager import FeatureManager
from core.state_manager import state
from utils.error_handler import GeometryValidationError


@pytest.fixture(autouse=True)
def reset_state():
    state.reset()
    yield
    state.reset()


@pytest.fixture
def wrapper():
    fake_wrapper = MagicMock()
    fake_wrapper.get_part.return_value = MagicMock()
    fake_wrapper.update.return_value = None
    return fake_wrapper


@pytest.fixture
def sketch_manager():
    fake_sm = MagicMock()
    fake_sm.get_sketch_object.return_value = MagicMock()
    return fake_sm


def test_pad_rejects_zero_length(wrapper, sketch_manager):
    fm = FeatureManager(wrapper, sketch_manager)
    with pytest.raises(GeometryValidationError):
        fm.pad(sketch="Sketch.1", length=0)


def test_pad_rejects_open_sketch(wrapper, sketch_manager):
    state.set_active_sketch("Sketch.1", is_open=True)
    fm = FeatureManager(wrapper, sketch_manager)
    with pytest.raises(GeometryValidationError):
        fm.pad(sketch="Sketch.1", length=10)


def test_pad_succeeds_when_sketch_closed(wrapper, sketch_manager):
    state.set_active_sketch("Sketch.1", is_open=False)
    fake_pad = MagicMock()
    fake_pad.name = "Pad.1"
    wrapper.get_part.return_value.shape_factory.add_new_pad.return_value = fake_pad

    fm = FeatureManager(wrapper, sketch_manager)
    result = fm.pad(sketch="Sketch.1", length=10)

    assert result["feature"] == "Pad.1"
    assert state.last_feature_name == "Pad.1"


def test_pocket_rejects_negative_depth(wrapper, sketch_manager):
    state.set_active_sketch("Sketch.1", is_open=False)
    fm = FeatureManager(wrapper, sketch_manager)
    with pytest.raises(GeometryValidationError):
        fm.pocket(sketch="Sketch.1", depth=-1)


def test_hole_delegates_to_sketch_and_pocket(wrapper):
    fake_sm = MagicMock()
    fake_sm.create_sketch.return_value = {"sketch": "Sketch.2", "plane": "xy"}
    fake_sm.close_sketch.return_value = {"sketch": "Sketch.2", "closed": True}
    fake_sm.get_sketch_object.return_value = MagicMock()

    fake_pocket = MagicMock()
    fake_pocket.name = "Pocket.1"
    wrapper.get_part.return_value.shape_factory.add_new_pocket.return_value = (
        fake_pocket
    )
    fm = FeatureManager(wrapper, fake_sm)
    result = fm.hole(x=10, y=10, diameter=6, depth=5)

    fake_sm.add_circle.assert_called_once_with(10, 10, 3.0)
    assert result["type"] == "hole"
    assert result["feature"] == "Pocket.1"


def test_hole_rejects_non_positive_diameter(wrapper, sketch_manager):
    fm = FeatureManager(wrapper, sketch_manager)
    with pytest.raises(GeometryValidationError):
        fm.hole(x=0, y=0, diameter=0, depth=5)
