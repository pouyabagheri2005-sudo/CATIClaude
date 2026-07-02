"""
core/state_manager.py

Centralized, thread-safe application state for the running MCP server
process. This is the "memory" that lets Claude issue a sequence of atomic
tool calls (create_sketch -> add_rectangle -> pad) and have each call
implicitly operate on the object created by the previous one.

Tracks: active document, part, body, sketch, feature history, registered
edges (for fillet/chamfer), CATIA parameters, and a full operation log.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OperationRecord:
    step: int
    action: str
    params: dict
    success: bool
    message: str
    timestamp: float = field(default_factory=time.time)


class StateManager:
    """Process-wide singleton holding CATIA session/document/feature context."""

    _instance: Optional["StateManager"] = None
    _class_lock = threading.RLock()

    def __new__(cls):
        with cls._class_lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._init_state()
                cls._instance = instance
            return cls._instance

    def _init_state(self) -> None:
        self._lock = threading.RLock()
        self.active_document_name: Optional[str] = None
        self.active_document_path: Optional[str] = None
        self.active_part_name: Optional[str] = None
        self.active_body_name: Optional[str] = None
        self.active_sketch_name: Optional[str] = None
        self.active_sketch_open: bool = False
        self.last_feature_name: Optional[str] = None
        self.feature_history: list = []
        self.operation_log: list = []
        self.parameters: dict = {}
        self.edge_registry: dict = {}

    def reset(self) -> None:
        with self._lock:
            self._init_state()

    # ------------------------------------------------------------------
    # Document / part / body / sketch tracking
    # ------------------------------------------------------------------
    def set_active_document(self, name, path: Optional[str] = None) -> None:
        with self._lock:
            self.active_document_name = name
            self.active_document_path = path
            self.active_part_name = None
            self.active_body_name = None
            self.active_sketch_name = None
            self.active_sketch_open = False
            self.feature_history = []
            self.edge_registry = {}

    def set_active_part(self, name) -> None:
        with self._lock:
            self.active_part_name = name

    def set_active_body(self, name) -> None:
        with self._lock:
            self.active_body_name = name

    def set_active_sketch(self, name, is_open: bool = True) -> None:
        with self._lock:
            self.active_sketch_name = name
            self.active_sketch_open = is_open

    def close_active_sketch(self) -> None:
        with self._lock:
            self.active_sketch_open = False

    def register_feature(self, name) -> None:
        with self._lock:
            self.last_feature_name = name
            self.feature_history.append(name)

    def register_edge(self, edge_id, reference) -> None:
        with self._lock:
            self.edge_registry[edge_id] = reference

    def get_edge(self, edge_id):
        with self._lock:
            return self.edge_registry.get(edge_id)

    # ------------------------------------------------------------------
    # Operation log
    # ------------------------------------------------------------------
    def log_operation(self, step, action, params, success, message) -> OperationRecord:
        with self._lock:
            record = OperationRecord(
                step=step,
                action=action,
                params=params,
                success=success,
                message=message,
            )
            self.operation_log.append(record)
            return record

    def get_history(self, limit: int = 50) -> list:
        with self._lock:
            records = self.operation_log[-limit:]
            return [
                {
                    "step": r.step,
                    "action": r.action,
                    "params": r.params,
                    "success": r.success,
                    "message": r.message,
                    "timestamp": r.timestamp,
                }
                for r in records
            ]

    # ------------------------------------------------------------------
    # Context snapshot (embedded in every MCP tool response)
    # ------------------------------------------------------------------
    def get_context(self) -> dict:
        with self._lock:
            return {
                "active_document": self.active_document_name,
                "active_part": self.active_part_name,
                "active_body": self.active_body_name,
                "active_sketch": self.active_sketch_name
                if self.active_sketch_open
                else None,
                "last_feature": self.last_feature_name,
                "feature_count": len(self.feature_history),
            }


state = StateManager()
