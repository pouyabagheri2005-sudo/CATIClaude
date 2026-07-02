"""
engine/executor.py

Layer 5 - MCP Tool Execution Engine.

Executes a CAD plan (list of atomic steps produced by the CAD Planner)
against the pyCATIA abstraction layer, recording a full operation history
in the StateManager and stopping (by default) at the first failure so
partial/broken geometry is never silently left half-built.

Per-operation retry (max 2 retries) is already implemented at the manager
level via `utils.error_handler.retry` on each `catia/*.py` method, so this
executor focuses purely on sequencing, bookkeeping, and error reporting.
"""

from __future__ import annotations

from typing import List

from catia.managers import export_manager, feature_manager, part_manager, sketch_manager
from core.state_manager import state
from utils.error_handler import CatiaMcpError
from utils.logger import get_logger

logger = get_logger("executor")


class PlanExecutor:
    def __init__(self):
        self._dispatch = {
            "create_part": lambda p: part_manager.create_part(**p),
            "open_document": lambda p: part_manager.open_document(**p),
            "save_document": lambda p: part_manager.save_document(**p),
            "close_document": lambda p: part_manager.close_document(),
            "create_sketch": lambda p: sketch_manager.create_sketch(**p),
            "add_line": lambda p: sketch_manager.add_line(**p),
            "add_circle": lambda p: sketch_manager.add_circle(**p),
            "add_rectangle": lambda p: sketch_manager.add_rectangle(**p),
            "close_sketch": lambda p: sketch_manager.close_sketch(**p),
            "pad": lambda p: feature_manager.pad(**p),
            "pocket": lambda p: feature_manager.pocket(**p),
            "hole": lambda p: feature_manager.hole(**p),
            "fillet": lambda p: feature_manager.fillet(**p),
            "chamfer": lambda p: feature_manager.chamfer(**p),
            "export_step": lambda p: export_manager.export_step(**p),
            "export_iges": lambda p: export_manager.export_iges(**p),
            "export_stl": lambda p: export_manager.export_stl(**p),
        }

    def execute_step(self, step: dict) -> dict:
        action = step.get("action")
        params = step.get("params", {}) or {}
        handler = self._dispatch.get(action)

        if handler is None:
            message = f"Unknown action '{action}'."
            state.log_operation(step.get("step", -1), action, params, False, message)
            return {"success": False, "error": message}

        try:
            data = handler(params)
            state.log_operation(step.get("step", -1), action, params, True, "ok")
            return {"success": True, "data": data}
        except CatiaMcpError as exc:
            message = str(exc)
            logger.error("Step %s (%s) failed: %s", step.get("step"), action, message)
            state.log_operation(step.get("step", -1), action, params, False, message)
            return {"success": False, "error": message}
        except Exception as exc:  # noqa: BLE001 - last-resort safety net per step
            message = f"Unexpected error: {exc}"
            logger.exception(
                "Step %s (%s) raised an unexpected exception", step.get("step"), action
            )
            state.log_operation(step.get("step", -1), action, params, False, message)
            return {"success": False, "error": message}

    def execute_plan(self, plan: List[dict], stop_on_error: bool = True) -> dict:
        results = []
        for step in plan:
            result = self.execute_step(step)
            results.append(
                {"step": step.get("step"), "action": step.get("action"), **result}
            )
            if not result["success"] and stop_on_error:
                return {
                    "success": False,
                    "completed_steps": results,
                    "failed_step": step,
                    "context": state.get_context(),
                }
        return {
            "success": all(r["success"] for r in results),
            "completed_steps": results,
            "context": state.get_context(),
        }
