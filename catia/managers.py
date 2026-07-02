"""
catia/managers.py

Process-wide singleton instances of every Layer 3 manager.

Both the atomic MCP tools (tools/*.py) and the high-level plan executor
(engine/executor.py) import these SAME instances, so session state (open
sketches, active bodies, etc.) stays consistent whether Claude calls atomic
tools one at a time or uses the `design_from_text` planner tool.
"""

from __future__ import annotations

from catia.analysis_manager import AnalysisManager
from catia.export_manager import ExportManager
from catia.feature_manager import FeatureManager
from catia.parameter_manager import ParameterManager
from catia.part_manager import PartManager
from catia.pycatia_wrapper import PycatiaWrapper
from catia.sketch_manager import SketchManager

wrapper = PycatiaWrapper()
part_manager = PartManager(wrapper)
sketch_manager = SketchManager(wrapper)
feature_manager = FeatureManager(wrapper, sketch_manager)
export_manager = ExportManager(wrapper)
parameter_manager = ParameterManager(wrapper)
analysis_manager = AnalysisManager(wrapper)
