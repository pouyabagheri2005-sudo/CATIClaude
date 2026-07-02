"""
catia/feature_manager.py

Layer 3 - FeatureManager: 3D feature creation (pad, pocket, hole, fillet,
chamfer) built from previously closed sketches or existing solid edges.
"""

from __future__ import annotations

from typing import Optional

from core.state_manager import state
from utils.error_handler import CatiaOperationError, GeometryValidationError, retry
from utils.logger import get_logger

from catia.pycatia_wrapper import PycatiaWrapper
from catia.sketch_manager import SketchManager

logger = get_logger("feature_manager")


class FeatureManager:
    def __init__(
        self,
        wrapper: Optional[PycatiaWrapper] = None,
        sketch_manager: Optional[SketchManager] = None,
    ):
        self.wrapper = wrapper or PycatiaWrapper()
        self.sketch_manager = sketch_manager

    def _get_sketch_manager(self) -> SketchManager:
        if self.sketch_manager is None:
            raise CatiaOperationError(
                "FeatureManager requires a SketchManager instance."
            )
        return self.sketch_manager

    def _assert_sketch_closed(self, sketch_name: Optional[str], action: str) -> str:
        sketch_name = sketch_name or state.active_sketch_name
        if not sketch_name:
            raise CatiaOperationError(
                f"No sketch available for {action}(). Create and close a sketch first."
            )
        if state.active_sketch_open and sketch_name == state.active_sketch_name:
            raise GeometryValidationError(
                f"Sketch '{sketch_name}' is still open. Call close_sketch() before {action}()."
            )
        return sketch_name

    # ------------------------------------------------------------------
    @retry(max_retries=2, delay_seconds=1.0)
    def pad(self, sketch: Optional[str] = None, length: float = 10.0) -> dict:
        if length <= 0:
            raise GeometryValidationError("Pad length must be positive.")
        sketch_name = self._assert_sketch_closed(sketch, "pad")
        sketch_obj = self._get_sketch_manager().get_sketch_object(sketch_name)

        part = self.wrapper.get_part()
        pad_feature = part.shape_factory.add_new_pad(sketch_obj, length)
        self.wrapper.update(part)

        feature_name = getattr(pad_feature, "name", "Pad")
        state.register_feature(feature_name)
        logger.info(
            "Created pad '%s' (length=%s) from sketch '%s'",
            feature_name,
            length,
            sketch_name,
        )
        return {
            "feature": feature_name,
            "type": "pad",
            "sketch": sketch_name,
            "length": length,
        }

    @retry(max_retries=2, delay_seconds=1.0)
    def pocket(self, sketch: Optional[str] = None, depth: float = 10.0) -> dict:
        if depth <= 0:
            raise GeometryValidationError("Pocket depth must be positive.")
        sketch_name = self._assert_sketch_closed(sketch, "pocket")
        sketch_obj = self._get_sketch_manager().get_sketch_object(sketch_name)

        part = self.wrapper.get_part()
        pocket_feature = part.shape_factory.add_new_pocket(sketch_obj, depth)
        self.wrapper.update(part)

        feature_name = getattr(pocket_feature, "name", "Pocket")
        state.register_feature(feature_name)
        logger.info(
            "Created pocket '%s' (depth=%s) from sketch '%s'",
            feature_name,
            depth,
            sketch_name,
        )
        return {
            "feature": feature_name,
            "type": "pocket",
            "sketch": sketch_name,
            "depth": depth,
        }

    @retry(max_retries=2, delay_seconds=1.0)
    def hole(
        self, x: float, y: float, diameter: float, depth: float, plane: str = "xy"
    ) -> dict:
        """Create a circular hole centered at (x, y) on `plane`.

        Implemented as a dedicated circle sketch + pocket rather than
        ShapeFactory.AddNewHole(...): the native Hole feature's COM
        signature differs across CATIA V5 releases, while sketch+pocket is
        stable across all of them and produces an equivalent, fully
        parametric cut.
        """
        if diameter <= 0:
            raise GeometryValidationError("Hole diameter must be positive.")
        if depth <= 0:
            raise GeometryValidationError("Hole depth must be positive.")

        sketch_manager = self._get_sketch_manager()
        sketch_manager.create_sketch(plane)
        sketch_manager.add_circle(x, y, diameter / 2.0)
        close_result = sketch_manager.close_sketch()
        sketch_name = close_result["sketch"]

        result = self.pocket(sketch=sketch_name, depth=depth)
        logger.info(
            "Created hole at (%s,%s) d=%s depth=%s via pocket '%s'",
            x,
            y,
            diameter,
            depth,
            result["feature"],
        )
        return {
            "feature": result["feature"],
            "type": "hole",
            "x": x,
            "y": y,
            "diameter": diameter,
            "depth": depth,
            "plane": plane,
        }

    def _resolve_edge(self, edge_id: str):
        reference = state.get_edge(edge_id)
        if reference is None:
            # Fall back to resolving a live CATIA object by its tree name
            # (e.g. "Edge.12"), in case the caller didn't run get_edges() first.
            reference = self.wrapper.resolve_named_object(edge_id)
        return reference

    @retry(max_retries=2, delay_seconds=1.0)
    def fillet(self, edge_id: str, radius: float) -> dict:
        if radius <= 0:
            raise GeometryValidationError("Fillet radius must be positive.")
        edge_reference = self._resolve_edge(edge_id)

        part = self.wrapper.get_part()
        shape_factory = part.shape_factory
        try:
            from pycatia.enumeration.enumeration_types import cat_edge_propagation

            propagation = cat_edge_propagation.index("catTangencyEdgePropagation")
        except Exception:  # noqa: BLE001
            propagation = 0

        fillet_feature = shape_factory.add_new_edge_fillet_with_constant_radius(
            radius, propagation, edge_reference
        )
        self.wrapper.update(part)

        feature_name = getattr(fillet_feature, "name", "EdgeFillet")
        state.register_feature(feature_name)
        logger.info(
            "Created fillet '%s' r=%s on edge '%s'", feature_name, radius, edge_id
        )
        return {
            "feature": feature_name,
            "type": "fillet",
            "edge_id": edge_id,
            "radius": radius,
        }

    @retry(max_retries=2, delay_seconds=1.0)
    def chamfer(self, edge_id: str, value: float) -> dict:
        if value <= 0:
            raise GeometryValidationError("Chamfer value must be positive.")
        edge_reference = self._resolve_edge(edge_id)

        part = self.wrapper.get_part()
        shape_factory = part.shape_factory
        # mode=1 (catLengthAngleChamfer... concretely a two-length chamfer
        # here since angle is 0), side=1 -> equal legs of `value` mm.
        chamfer_feature = shape_factory.add_new_chamfer(
            [edge_reference], 1, value, 0.0, 1
        )
        self.wrapper.update(part)

        feature_name = getattr(chamfer_feature, "name", "Chamfer")
        state.register_feature(feature_name)
        logger.info(
            "Created chamfer '%s' value=%s on edge '%s'", feature_name, value, edge_id
        )
        return {
            "feature": feature_name,
            "type": "chamfer",
            "edge_id": edge_id,
            "value": value,
        }
