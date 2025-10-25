from pathlib import Path
import sys
import importlib.util

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
LOCAL_ANALYSIS_DIR = BACKEND_ROOT / "src" / "local-analysis"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def backend_root() -> Path:
    return BACKEND_ROOT


@pytest.fixture(scope="session")
def local_analysis_dir() -> Path:
    """Fixture providing path to local-analysis directory"""
    return LOCAL_ANALYSIS_DIR


def import_from_local_analysis(module_name: str):
    """
    Helper function to import modules from the local-analysis directory.
    Handles the hyphenated directory name that can't be imported normally.
    
    Args:
        module_name: Name of the module to import (e.g., 'pdf_parser')
    
    Returns:
        The imported module
    """
    module_path = LOCAL_ANALYSIS_DIR / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module {module_name} from {module_path}")
    
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
