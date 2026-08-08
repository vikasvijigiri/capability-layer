"""capability-layer: the agent capability layer, packaged.

Single source of the version string. `pyproject.toml`'s hatchling backend is
expected to read `__version__` from this file rather than duplicating it
elsewhere, so a release is one edit, not two that can drift apart.
"""

__version__ = "0.1.0"
