"""
catia/parameter_manager.py

Layer 3 - ParameterManager: read/write CATIA Part parameters, enabling
named-dimension-driven, parametric design instead of hard-coded numbers.
"""

from __future__ import annotations

from typing import Optional

from core.state_manager import state
from utils.error_handler import retry
from utils.logger import get_logger

from catia.pycatia_wrapper import PycatiaWrapper

logger = get_logger("parameter_manager")


class ParameterManager:
    def __init__(self, wrapper: Optional[PycatiaWrapper] = None):
        self.wrapper = wrapper or PycatiaWrapper()

    @retry(max_retries=2, delay_seconds=1.0)
    def set_parameter(self, name: str, value: float) -> dict:
        part = self.wrapper.get_part()
        parameters = part.parameters
        try:
            parameter = parameters.get_item(name)
            parameter.value = value
        except Exception:  # noqa: BLE001
            parameter = parameters.create_dimension(name, "LENGTH", value)
        self.wrapper.update(part)
        state.parameters[name] = value
        logger.info("Set parameter '%s' = %s", name, value)
        return {"name": name, "value": value}

    @retry(max_retries=2, delay_seconds=1.0)
    def get_parameter(self, name: str) -> dict:
        part = self.wrapper.get_part()
        parameter = part.parameters.get_item(name)
        return {"name": name, "value": parameter.value}

    def list_parameters(self) -> dict:
        part = self.wrapper.get_part()
        parameters = part.parameters
        names = []
        try:
            for i in range(1, parameters.count + 1):
                names.append(parameters.item(i).name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not enumerate parameters: %s", exc)
        return {"parameters": names}
