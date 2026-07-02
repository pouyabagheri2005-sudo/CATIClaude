"""
catia/part_manager.py

Layer 3 - PartManager: document/part lifecycle (create, open, save, close)
and body bootstrapping.
"""

from __future__ import annotations

from typing import Optional

from core.state_manager import state
from utils.error_handler import retry
from utils.logger import get_logger

from catia.pycatia_wrapper import PycatiaWrapper

logger = get_logger("part_manager")


class PartManager:
    def __init__(self, wrapper: Optional[PycatiaWrapper] = None):
        self.wrapper = wrapper or PycatiaWrapper()

    @retry(max_retries=2, delay_seconds=1.0)
    def create_part(self, name: str = "Part1") -> dict:
        part_document = self.wrapper.create_part_document()
        part = part_document.part

        try:
            part_document.product.part_number = name
        except Exception:  # noqa: BLE001 - cosmetic naming, non-fatal
            pass
        try:
            part.update()
        except Exception:  # noqa: BLE001
            pass

        doc_name = getattr(part_document, "name", name)
        state.set_active_document(doc_name)
        state.set_active_part(name)

        body = self.wrapper.get_or_create_body(part)
        state.set_active_body(getattr(body, "name", "PartBody"))

        logger.info("Created new CATPart '%s' (document '%s')", name, doc_name)
        return {
            "document_name": doc_name,
            "part_name": name,
            "body_name": state.active_body_name,
        }

    @retry(max_retries=2, delay_seconds=1.0)
    def open_document(self, path: str) -> dict:
        part_document = self.wrapper.open_document(path)
        doc_name = getattr(part_document, "name", path)
        state.set_active_document(doc_name, path=path)

        try:
            part = part_document.part
            body = self.wrapper.get_or_create_body(part)
            state.set_active_body(getattr(body, "name", "PartBody"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Opened document is not a Part or has no body yet: %s", exc)

        logger.info("Opened document '%s' from '%s'", doc_name, path)
        return {"document_name": doc_name, "path": path}

    @retry(max_retries=2, delay_seconds=1.0)
    def save_document(self, path: Optional[str] = None) -> dict:
        document = self.wrapper.session.get_active_document()
        if path:
            document.save_as(path)
            state.active_document_path = path
        else:
            document.save()
        target = path or state.active_document_path or "(original location)"
        logger.info("Saved document to '%s'", target)
        return {"path": path or state.active_document_path}

    def close_document(self) -> dict:
        document = self.wrapper.session.get_active_document()
        name = state.active_document_name
        document.close()
        state.reset()
        logger.info("Closed document '%s'", name)
        return {"closed": name}
