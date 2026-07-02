"""
tests/conftest.py

Ensures the project root is importable (so `import catia.session`,
`import engine.cad_planner`, etc. work) regardless of the current working
directory pytest was invoked from.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
