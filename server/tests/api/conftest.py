"""
Conftest for tests/api/ — fixes 'api' package namespace collision.

With --import-mode=importlib and __init__.py in tests/api/, pytest registers
tests/api/ as the 'api' package, shadowing server/api/. This conftest pre-loads
the real server api modules by file path so subsequent imports work correctly.
"""
import importlib
import sys
from pathlib import Path

import pytest

_SERVER_DIR = Path(__file__).parent.parent.parent  # server/


@pytest.fixture(autouse=True, scope="session")
def _preload_real_api():
    """Ensure real server/api modules are registered before any test runs."""
    # Add server dir to sys.path if not present
    server_dir = str(_SERVER_DIR)
    if server_dir not in sys.path:
        sys.path.insert(0, server_dir)

    # Remove any stale 'api*' entries that point to tests/
    for key in list(sys.modules.keys()):
        mod = sys.modules[key]
        if key == "api" or key.startswith("api."):
            mod_file = getattr(mod, "__file__", "") or ""
            if "tests" in mod_file:
                del sys.modules[key]

    # Now import the real ones
    importlib.import_module("api.documents.service")
    importlib.import_module("api.chunks.service")
    importlib.import_module("api.kb.service")
    importlib.import_module("api.search.service")
