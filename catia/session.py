"""
catia/session.py

Layer 2 - CATIA Session Engine (critical).

This module owns the single COM connection to the running CATIA V5
application process. It is intentionally the ONLY place in the codebase
that touches `pycatia.catia()` at the application level; every other module
obtains the live Application/Document objects through
`CatiaSession.get_instance()`.

Responsibilities:
    - Start CATIA V5 automatically if it isn't running (pycatia's `catia()`
      factory does this transparently via COM activation semantics).
    - Attach to an already-running CATIA session instead of spawning a
      second instance.
    - Maintain a single active session (singleton pattern).
    - Detect COM crashes / closed sessions and transparently reconnect.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

from utils.error_handler import CatiaConnectionError, retry
from utils.logger import get_logger

logger = get_logger("session")

try:
    from pycatia import catia as _catia_factory

    PYCATIA_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised on non-Windows dev machines
    _catia_factory = None
    PYCATIA_AVAILABLE = False


class CatiaSession:
    """Singleton manager for the CATIA V5 COM application session."""

    _instance: Optional["CatiaSession"] = None
    _class_lock = threading.RLock()

    def __init__(self):
        if not PYCATIA_AVAILABLE:
            logger.warning(
                "pycatia/pywin32 is not available. CatiaSession will operate "
                "in OFFLINE mode; all CATIA calls will raise "
                "CatiaConnectionError. This is expected on non-Windows "
                "development/test machines."
            )
        self._application = None
        self._connect_lock = threading.RLock()
        self._last_connect_attempt = 0.0
        self._min_reconnect_interval_s = 2.0

    @classmethod
    def get_instance(cls) -> "CatiaSession":
        with cls._class_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------
    def _connect(self):
        if not PYCATIA_AVAILABLE:
            raise CatiaConnectionError(
                "pycatia/pywin32 is not installed, or this is not a Windows "
                "environment. Install requirements.txt on a Windows machine "
                "with a licensed CATIA V5 installation."
            )

        # Throttle reconnect attempts so a persistently-down CATIA process
        # can't be hammered by rapid retries.
        elapsed = time.time() - self._last_connect_attempt
        if 0 < elapsed < self._min_reconnect_interval_s:
            time.sleep(self._min_reconnect_interval_s - elapsed)
        self._last_connect_attempt = time.time()

        logger.info("Connecting to CATIA V5 (will start it if not already running)...")
        try:
            app = _catia_factory()
            try:
                app.visible = True
            except Exception:  # noqa: BLE001 - cosmetic, non-fatal
                pass
            logger.info("Connected to CATIA V5 successfully.")
            return app
        except Exception as exc:  # noqa: BLE001
            raise CatiaConnectionError(
                f"Failed to start/attach to CATIA V5: {exc}"
            ) from exc

    def is_alive(self) -> bool:
        """Cheap liveness probe that detects a crashed/closed CATIA process."""
        if self._application is None:
            return False
        try:
            _ = self._application.documents.count
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "CATIA session no longer responsive (probable crash/close): %s", exc
            )
            return False

    def get_application(self):
        """Return a live Application COM object, (re)connecting if necessary."""
        with self._connect_lock:
            if self._application is None or not self.is_alive():
                self._application = self._connect()
            return self._application

    def force_reconnect(self):
        with self._connect_lock:
            logger.info("Forcing CATIA reconnect.")
            self._application = None
            self._application = self._connect()
            return self._application

    # ------------------------------------------------------------------
    # Convenience accessors used by the pyCATIA abstraction layer
    # ------------------------------------------------------------------
    @retry(max_retries=2, delay_seconds=1.5)
    def get_documents(self):
        app = self.get_application()
        return app.documents

    def get_active_document(self):
        app = self.get_application()
        try:
            document = app.active_document
        except Exception as exc:  # noqa: BLE001
            raise CatiaConnectionError(f"No active CATIA document: {exc}") from exc
        if document is None:
            raise CatiaConnectionError(
                "No active CATIA document. Call create_part() or open_document() first."
            )
        return document

    def shutdown(self, close_catia: bool = False) -> None:
        """Release the session. Optionally quit the CATIA application entirely."""
        with self._connect_lock:
            if self._application is not None and close_catia:
                try:
                    self._application.quit()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Error while quitting CATIA: %s", exc)
            self._application = None
