"""
utils/error_handler.py

Custom exception hierarchy and resilience decorators (retry) shared by the
CATIA abstraction layer and the CAD engine layer.
"""

from __future__ import annotations

import functools
import time

from utils.logger import get_logger

logger = get_logger("error_handler")


class CatiaMcpError(Exception):
    """Base class for all deliberate, well-understood errors in this system."""


class CatiaConnectionError(CatiaMcpError):
    """Raised when CATIA cannot be started, attached to, or has crashed."""


class CatiaOperationError(CatiaMcpError):
    """Raised when a CATIA/pyCATIA operation fails (COM error, invalid state)."""


class GeometryValidationError(CatiaMcpError):
    """Raised when a requested geometric operation is invalid or infeasible."""


class PlanningError(CatiaMcpError):
    """Raised when natural-language intent cannot be converted into a valid plan."""


def retry(max_retries: int = 2, delay_seconds: float = 1.0, exceptions=(Exception,)):
    """Retry a function up to `max_retries` additional times on failure.

    Total attempts = 1 + max_retries, matching the "max 2 retries" requirement.
    Validation errors (bad input) are never worth retrying, so callers should
    raise `GeometryValidationError` *before* touching CATIA where possible.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except GeometryValidationError:
                    raise  # never retry a validation failure
                except exceptions as exc:  # noqa: BLE001 - intentional boundary catch
                    last_exc = exc
                    logger.warning(
                        "Attempt %s/%s failed for %s: %s",
                        attempt + 1,
                        max_retries + 1,
                        func.__name__,
                        exc,
                    )
                    if attempt < max_retries:
                        time.sleep(delay_seconds)
            logger.error(
                "All %s attempts failed for %s", max_retries + 1, func.__name__
            )
            raise last_exc

        return wrapper

    return decorator


def safe_call(default=None):
    """Swallow exceptions and log them, returning `default` instead of raising.

    Only ever use this for best-effort, non-critical operations (e.g.
    cosmetic renaming) where failure must not abort the calling operation.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "safe_call suppressed exception in %s: %s", func.__name__, exc
                )
                return default

        return wrapper

    return decorator
