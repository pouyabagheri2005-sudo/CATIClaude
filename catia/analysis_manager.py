"""
catia/analysis_manager.py

Layer 3 - AnalysisManager: read-only introspection of the active part
(feature tree, edges, mass properties, distance measurement) plus a
lightweight geometry validation pass.
"""

from __future__ import annotations

from typing import Optional

from core.state_manager import state
from utils.error_handler import CatiaOperationError, retry
from utils.logger import get_logger

from catia.pycatia_wrapper import PycatiaWrapper

logger = get_logger("analysis_manager")


class AnalysisManager:
    def __init__(self, wrapper: Optional[PycatiaWrapper] = None):
        self.wrapper = wrapper or PycatiaWrapper()

    def get_tree(self) -> dict:
        part = self.wrapper.get_part()
        bodies_info = []
        bodies = part.bodies
        try:
            count = bodies.count
        except Exception:  # noqa: BLE001
            count = 0

        for i in range(1, count + 1):
            body = bodies.item(i)
            sketches_info = []
            try:
                sketches = body.sketches
                for j in range(1, sketches.count + 1):
                    sketches_info.append(sketches.item(j).name)
            except Exception:  # noqa: BLE001
                pass
            bodies_info.append(
                {"name": getattr(body, "name", f"Body{i}"), "sketches": sketches_info}
            )

        return {
            "document": state.active_document_name,
            "part": state.active_part_name,
            "bodies": bodies_info,
            "features": state.feature_history,
            "last_feature": state.last_feature_name,
        }

    def get_edges(self, max_edges: int = 200) -> dict:
        """Enumerate solid edges and register them under short, stable ids
        (E1, E2, ...) so `fillet()`/`chamfer()` tools can reference them.
        """
        part_document = self.wrapper.get_active_part_document()
        part = part_document.part
        selection = part_document.selection
        selection.clear()
        edges = []
        try:
            selection.search("Topology.Edge,all")
            count = min(selection.count, max_edges)
            for i in range(1, count + 1):
                item = selection.item2(i)
                name = getattr(item.value, "name", f"Edge.{i}")
                edge_id = f"E{i}"
                reference = part.create_reference_from_object(item.value)
                state.register_edge(edge_id, reference)
                edges.append({"edge_id": edge_id, "name": name})
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Edge enumeration failed (CATIA release may use a different search syntax): %s",
                exc,
            )
        finally:
            selection.clear()
        return {"edges": edges}

    @retry(max_retries=2, delay_seconds=1.0)
    def measure_distance(self, obj1: str, obj2: str) -> dict:
        part_document = self.wrapper.get_active_part_document()
        part = part_document.part
        spa_workbench = part_document.spa_workbench()

        ref1 = self.wrapper.resolve_named_object(obj1)
        ref2 = self.wrapper.resolve_named_object(obj2)

        measurable = spa_workbench.get_measurable(ref1)
        distance = measurable.get_min_distance(ref2)
        return {"obj1": obj1, "obj2": obj2, "distance_mm": distance}

    @retry(max_retries=2, delay_seconds=1.0)
    def get_mass_properties(self) -> dict:
        part_document = self.wrapper.get_active_part_document()
        part = part_document.part
        spa_workbench = part_document.spa_workbench()
        body = self.wrapper.get_or_create_body(part, state.active_body_name)
        reference = part.create_reference_from_object(body)
        measurable = spa_workbench.get_measurable(reference)

        mass = _safe_attr(measurable, "mass")
        volume = _safe_attr(measurable, "volume")
        try:
            cog = measurable.get_cog()
        except Exception:  # noqa: BLE001
            cog = None

        return {"mass_g": mass, "volume_mm3": volume, "center_of_gravity_mm": cog}

    def validate_geometry(self) -> dict:
        part = self.wrapper.get_part()
        issues = []
        try:
            part.update()
        except Exception as exc:  # noqa: BLE001
            issues.append(f"Part update failed (feature tree may be broken): {exc}")
        try:
            body = self.wrapper.get_or_create_body(part, state.active_body_name)
            _ = body.shape
        except Exception as exc:  # noqa: BLE001
            issues.append(f"No valid solid shape found on the active body: {exc}")
        return {"valid": len(issues) == 0, "issues": issues}


def _safe_attr(obj, name):
    try:
        return getattr(obj, name)
    except Exception:  # noqa: BLE001
        return None
