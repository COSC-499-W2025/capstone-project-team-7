"""
Pytest configuration and fixtures
"""
from pathlib import Path
import sys
import importlib.util
import pytest


# Define paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
LOCAL_ANALYSIS_DIR = BACKEND_ROOT / "src" / "local_analysis"

# Add paths to sys.path
backend_local_analysis = Path(__file__).parent.parent / "backend" / "src" / "local_analysis"
if backend_local_analysis.exists():
    sys.path.insert(0, str(backend_local_analysis))

# Add lib folder from backend/src/local_analysis/lib
lib_path = backend_local_analysis / "lib"
if lib_path.exists():
    sys.path.insert(0, str(lib_path))

# Add both backend and local-analysis to sys.path
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

if str(LOCAL_ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(LOCAL_ANALYSIS_DIR))


# IMPORTANT: Define this function BEFORE using it!
def import_from_local_analysis(module_name: str):
    """
    Helper function to import modules from the local-analysis directory.
    Handles the hyphenated directory name that can't be imported normally.
    
    Args:
        module_name: Name of the module to import (e.g., 'code_parser')
    
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


# Now we can use the function to import code_parser
code_parser = import_from_local_analysis("code_parser")
from code_parser import CodeAnalyzer


# Path fixtures
@pytest.fixture(scope="session")
def project_root() -> Path:
    """Fixture providing path to project root"""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def backend_root() -> Path:
    """Fixture providing path to backend directory"""
    return BACKEND_ROOT


@pytest.fixture(scope="session")
def local_analysis_dir() -> Path:
    """Fixture providing path to local-analysis directory"""
    return LOCAL_ANALYSIS_DIR


@pytest.fixture(scope="session")
def fixtures_dir():
    """Path to fixtures directory with test files"""
    fixtures_path = Path(__file__).parent / "fixtures"
    
    # Verify fixtures directory exists
    if not fixtures_path.exists():
        raise FileNotFoundError(
            f"Fixtures directory not found at {fixtures_path}\n"
            "Please create the 'fixtures' folder and add test files."
        )
    
    return fixtures_path


# Analyzer fixture
@pytest.fixture(scope="session")
def analyzer():
    """Create a CodeAnalyzer instance"""
    return CodeAnalyzer(
        max_file_mb=5.0,
        max_depth=10
    )


# File path fixtures
@pytest.fixture(scope="session")
def bad_python_file(fixtures_dir):
    """Path to bad Python file"""
    return fixtures_dir / "bad_code.py"


@pytest.fixture(scope="session")
def good_python_file(fixtures_dir):
    """Path to good Python file"""
    return fixtures_dir / "good_code.py"


@pytest.fixture(scope="session")
def javascript_file(fixtures_dir):
    """Path to JavaScript file"""
    return fixtures_dir / "medium_quality.js"


# Analyzed file fixtures
@pytest.fixture(scope="session")
def analyzed_bad_file(analyzer, bad_python_file):
    """Analyzed bad Python file"""
    return analyzer.analyze_file(bad_python_file)


@pytest.fixture(scope="session")
def analyzed_good_file(analyzer, good_python_file):
    """Analyzed good Python file"""
    return analyzer.analyze_file(good_python_file)


@pytest.fixture(scope="session")
def analyzed_js_file(analyzer, javascript_file):
    """Analyzed JavaScript file"""
    return analyzer.analyze_file(javascript_file)


@pytest.fixture(scope="session")
def analyzed_directory(analyzer, fixtures_dir):
    """Analyzed fixtures directory"""
    return analyzer.analyze_directory(fixtures_dir, recursive=False)