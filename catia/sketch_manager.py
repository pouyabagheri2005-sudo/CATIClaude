"""
catia/sketch_manager.py

Layer 3 - SketchManager: 2D sketch creation and geometry (lines, circles,
rectangles) plus closed-loop tracking so the FeatureManager can enforce
"a sketch must be closed before pad/pocket".
"""

from __future__ import annotations

from collections import Counter
from typing import Optional

from core.state_manager import state
from utils.error_handler import CatiaOperationError, GeometryValidationError, retry
from utils.logger import get_logger

from catia.pycatia_wrapper import PycatiaWrapper

logger = get_logger("sketch_manager")


class SketchManager:
    def __init__(self, wrapper: Optional[PycatiaWrapper] = None):
        self.wrapper = wrapper or PycatiaWrapper()
        self._open_sketches: dict = {}
        self._open_factories: dict = {}
        self._sketch_geometry: dict = {}

    # ------------------------------------------------------------------
    @retry(max_retries=2, delay_seconds=1.0)
    def create_sketch(self, plane: str = "xy") -> dict:
        part = self.wrapper.get_part()
        body = self.wrapper.get_or_create_body(part, state.active_body_name)
        reference = self.wrapper.resolve_plane(plane)
        sketch = body.sketches.add(reference)
        sketch_name = sketch.name

        part.in_work_object = sketch
        factory_2d = sketch.open_edition()

        self._open_sketches[sketch_name] = sketch
        self._open_factories[sketch_name] = factory_2d
        self._sketch_geometry[sketch_name] = []

        state.set_active_sketch(sketch_name, is_open=True)
        logger.info("Created sketch '%s' on plane '%s'", sketch_name, plane)
        return {"sketch": sketch_name, "plane": plane}

    def _require_open_sketch(self, sketch_name: Optional[str] = None):
        sketch_name = sketch_name or state.active_sketch_name
        if not sketch_name or sketch_name not in self._open_factories:
            raise CatiaOperationError(
                "No open sketch to draw into. Call create_sketch() first."
            )
        return sketch_name, self._open_factories[sketch_name]

    @retry(max_retries=2, delay_seconds=0.5)
    def add_line(
        self, x1: float, y1: float, x2: float, y2: float, sketch: Optional[str] = None
    ) -> dict:
        sketch_name, factory_2d = self._require_open_sketch(sketch)
        factory_2d.create_line(x1, y1, x2, y2)
        self._sketch_geometry[sketch_name].append(
            {"type": "line", "points": [(x1, y1), (x2, y2)]}
        )
        logger.debug(
            "Added line (%s,%s)->(%s,%s) to sketch '%s'", x1, y1, x2, y2, sketch_name
        )
        return {"sketch": sketch_name, "element": "line"}

    @retry(max_retries=2, delay_seconds=0.5)
    def add_circle(
        self, x: float, y: float, radius: float, sketch: Optional[str] = None
    ) -> dict:
        if radius <= 0:
            raise GeometryValidationError("Circle radius must be positive.")
        sketch_name, factory_2d = self._require_open_sketch(sketch)
        factory_2d.create_closed_circle(x, y, radius)
        self._sketch_geometry[sketch_name].append(
            {"type": "circle", "center": (x, y), "radius": radius, "closed": True}
        )
        logger.debug(
            "Added circle at (%s,%s) r=%s to sketch '%s'", x, y, radius, sketch_name
        )
        return {"sketch": sketch_name, "element": "circle", "closed": True}

    @retry(max_retries=2, delay_seconds=0.5)
    def add_rectangle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        sketch: Optional[str] = None,
    ) -> dict:
        if width <= 0 or height <= 0:
            raise GeometryValidationError("Rectangle width/height must be positive.")
        sketch_name, factory_2d = self._require_open_sketch(sketch)

        x1, y1 = x, y
        x2, y2 = x + width, y
        x3, y3 = x + width, y + height
        x4, y4 = x, y + height

        # Coordinates are shared literally between consecutive segments, so
        # CATIA's geometric analysis sees exactly-coincident endpoints and
        # therefore a valid closed contour usable directly by Pad/Pocket.
        factory_2d.create_line(x1, y1, x2, y2)
        factory_2d.create_line(x2, y2, x3, y3)
        factory_2d.create_line(x3, y3, x4, y4)
        factory_2d.create_line(x4, y4, x1, y1)

        self._sketch_geometry[sketch_name].append(
            {
                "type": "rectangle",
                "origin": (x, y),
                "width": width,
                "height": height,
                "closed": True,
            }
        )
        logger.debug(
            "Added rectangle at (%s,%s) %sx%s to sketch '%s'",
            x,
            y,
            width,
            height,
            sketch_name,
        )
        return {"sketch": sketch_name, "element": "rectangle", "closed": True}

    # ------------------------------------------------------------------
    # Closure detection ("ensure sketch closure before 3D operations")
    # ------------------------------------------------------------------
    def is_closed(self, sketch_name: Optional[str] = None) -> bool:
        sketch_name = sketch_name or state.active_sketch_name
        elements = self._sketch_geometry.get(sketch_name, [])
        if not elements:
            return False
        if all(el["type"] in ("circle", "rectangle") for el in elements):
            return True
        return self._lines_form_closed_loop(elements)

    @staticmethod
    def _lines_form_closed_loop(elements) -> bool:
        if not all(el["type"] == "line" for el in elements):
            return False
        points = []
        for el in elements:
            points.extend(el["points"])
        if len(points) < 4:
            return False
        rounded = [(round(p[0], 6), round(p[1], 6)) for p in points]
        counts = Counter(rounded)
        # A simple closed polygon: every vertex is shared by exactly 2 segment endpoints.
        return all(c == 2 for c in counts.values())

    @retry(max_retries=2, delay_seconds=1.0)
    def close_sketch(self, sketch: Optional[str] = None) -> dict:
        sketch_name = sketch or state.active_sketch_name
        if not sketch_name or sketch_name not in self._open_sketches:
            raise CatiaOperationError("No open sketch to close.")

        if not self.is_closed(sketch_name):
            raise GeometryValidationError(
                f"Sketch '{sketch_name}' geometry does not form a closed profile. "
                "Pad/Pocket operations require a fully closed contour."
            )

        sketch_obj = self._open_sketches[sketch_name]
        sketch_obj.close_edition()
        self.wrapper.update()

        state.close_active_sketch()
        logger.info("Closed sketch '%s'", sketch_name)
        return {"sketch": sketch_name, "closed": True}

    def get_sketch_object(self, sketch_name: Optional[str] = None):
        sketch_name = sketch_name or state.active_sketch_name
        sketch = self._open_sketches.get(sketch_name)
        if sketch is None:
            raise CatiaOperationError(f"Unknown sketch '{sketch_name}'.")
        return sketch
