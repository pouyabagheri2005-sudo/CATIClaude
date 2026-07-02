"""
catia/export_manager.py

Layer 3 - ExportManager: STEP / IGES / STL export via Document.export_data.
"""

from __future__ import annotations

import os
from typing import Optional

from utils.error_handler import retry
from utils.logger import get_logger

from catia.pycatia_wrapper import PycatiaWrapper

logger = get_logger("export_manager")

_FORMAT_EXTENSIONS = {
    "step": "stp",
    "stp": "stp",
    "iges": "igs",
    "igs": "igs",
    "stl": "stl",
}


class ExportManager:
    def __init__(self, wrapper: Optional[PycatiaWrapper] = None):
        self.wrapper = wrapper or PycatiaWrapper()

    @retry(max_retries=2, delay_seconds=1.0)
    def _export(self, path: str, file_format: str) -> dict:
        document = self.wrapper.session.get_active_document()
        directory = os.path.dirname(path)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory, exist_ok=True)
        try:
            document.export_data(path, file_format, overwrite=True)
        except TypeError:
            # Older pycatia releases do not accept the `overwrite` kwarg.
            document.export_data(path, file_format)
        logger.info("Exported active document to '%s' (%s)", path, file_format)
        return {"path": path, "format": file_format}

    def export_step(self, path: str) -> dict:
        return self._export(path, _FORMAT_EXTENSIONS["step"])

    def export_iges(self, path: str) -> dict:
        return self._export(path, _FORMAT_EXTENSIONS["iges"])

    def export_stl(self, path: str) -> dict:
        return self._export(path, _FORMAT_EXTENSIONS["stl"])
