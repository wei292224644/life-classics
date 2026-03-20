"""
Conftest for tests/api/ — fixes 'api' package namespace collision.

With --import-mode=importlib and __init__.py in tests/api/, pytest registers
tests/api/ as the 'api' package, shadowing server/api/. This conftest pre-loads
the real server api modules by file path so subsequent imports work correctly.
"""
import importlib.util
import sys
from pathlib import Path

_SERVER_DIR = Path(__file__).parent.parent.parent  # server/


def _load_real_api_module(dotted_name: str) -> None:
    """Load a module from the real server/api directory into sys.modules."""
    if dotted_name in sys.modules:
        return
    rel_path = dotted_name.replace(".", "/") + ".py"
    file_path = _SERVER_DIR / rel_path
    if not file_path.exists():
        # Try as a package (__init__.py)
        file_path = _SERVER_DIR / dotted_name.replace(".", "/") / "__init__.py"
    spec = importlib.util.spec_from_file_location(dotted_name, file_path)
    if spec is None:
        return
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted_name] = mod
    spec.loader.exec_module(mod)


# Pre-register parent packages so sub-module imports resolve correctly
# We override what pytest registered with the real server packages.
def pytest_configure(config):
    pass  # pre-loading done via autouse fixture to ensure correct order


import pytest

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
    import importlib
    importlib.import_module("api.documents.service")
    importlib.import_module("api.chunks.service")
    importlib.import_module("api.kb.service")
