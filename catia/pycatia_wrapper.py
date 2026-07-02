"""
catia/pycatia_wrapper.py

Layer 3 - thin, shared foundation for the pyCATIA abstraction layer.

All higher-level managers (PartManager, SketchManager, FeatureManager,
ExportManager, ParameterManager, AnalysisManager) are built on top of this
wrapper. No module outside `catia/` should ever import `pycatia` directly -
this is the seam that keeps raw COM calls contained, per the architecture.
"""

from __future__ import annotations

from typing import Optional

from utils.error_handler import CatiaOperationError, retry
from utils.logger import get_logger

from catia.session import CatiaSession

logger = get_logger("pycatia_wrapper")

PLANE_ALIASES = {
    "xy": "plane_xy",
    "top": "plane_xy",
    "yz": "plane_yz",
    "right": "plane_yz",
    "zx": "plane_zx",
    "xz": "plane_zx",
    "front": "plane_zx",
}


class PycatiaWrapper:
    """Shared low-level helpers for talking to the active CATIA part document."""

    def __init__(self, session: Optional[CatiaSession] = None):
        self.session = session or CatiaSession.get_instance()

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------
    @retry(max_retries=2, delay_seconds=1.0)
    def create_part_document(self):
        documents = self.session.get_documents()
        return documents.add("Part")

    @retry(max_retries=2, delay_seconds=1.0)
    def open_document(self, path: str):
        documents = self.session.get_documents()
        return documents.open(path)

    def get_active_part_document(self):
        document = self.session.get_active_document()
        if not hasattr(document, "part"):
            raise CatiaOperationError(
                "The active CATIA document is not a Part document (.CATPart)."
            )
        return document

    def get_part(self):
        return self.get_active_part_document().part

    # ------------------------------------------------------------------
    # Geometry references
    # ------------------------------------------------------------------
    def resolve_plane(self, plane_name: str):
        """Resolve a friendly plane name ('xy', 'yz', 'zx', ...) to a Reference."""
        part = self.get_part()
        key = (plane_name or "xy").strip().lower()
        attr = PLANE_ALIASES.get(key)
        if attr is None:
            raise CatiaOperationError(
                f"Unknown sketch plane '{plane_name}'. Use one of: xy, yz, zx."
            )
        origin_elements = part.origin_elements
        plane_obj = getattr(origin_elements, attr)
        return part.create_reference_from_object(plane_obj)

    def get_or_create_body(self, part=None, name: Optional[str] = None):
        part = part or self.get_part()
        bodies = part.bodies
        if name:
            try:
                return bodies.get_item_by_name(name)
            except Exception:  # noqa: BLE001
                body = bodies.add()
                body.name = name
                return body
        try:
            return bodies.item(1)
        except Exception as exc:  # noqa: BLE001
            raise CatiaOperationError(f"Part has no body: {exc}") from exc

    def resolve_named_object(self, name: str):
        """Resolve any named CATIA object (e.g. an edge/face shown in the
        specification tree) into a Reference, via the document selection.
        """
        part_document = self.get_active_part_document()
        part = part_document.part
        selection = part_document.selection
        selection.clear()
        try:
            selection.search(f"Name={name},all")
            if selection.count == 0:
                raise CatiaOperationError(
                    f"No geometry named '{name}' found in the active document."
                )
            obj = selection.item2(1).value
            return part.create_reference_from_object(obj)
        finally:
            selection.clear()

    def update(self, part=None) -> None:
        part = part or self.get_part()
        part.update()
