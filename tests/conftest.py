"""
Pytest configuration and fixtures
"""
from pathlib import Path
import sys
import importlib
import os
import json
import base64
import pytest
from fastapi import Header, HTTPException, status


# Define paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
LOCAL_ANALYSIS_DIR = BACKEND_ROOT / "src" / "local_analysis"
BACKEND_SRC = BACKEND_ROOT / "src"

# Ensure the project root is importable so `backend` resolves cleanly.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Make backend/src importable for modules that expect top-level packages.
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

# Add paths to sys.path
backend_local_analysis = Path(__file__).parent.parent / "backend" / "src" / "local_analysis"
# Add lib folder from backend/src/local_analysis/lib
lib_path = backend_local_analysis / "lib"
if lib_path.exists():
    sys.path.insert(0, str(lib_path))

# Add both backend and local-analysis to sys.path
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

if str(LOCAL_ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(LOCAL_ANALYSIS_DIR))

os.environ.setdefault("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
os.environ.setdefault("CAPSTONE_LOCAL_STORE", "1")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-service-role-key")

from main import app
from api.dependencies import AuthContext, get_auth_context


async def _test_auth_context(authorization: str | None = Header(default=None)) -> AuthContext:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Authorization header missing"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Authorization header must be Bearer token"},
        )

    access_token = parts[1].strip()
    if not access_token or access_token.count(".") < 2:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Invalid or expired access token"},
        )

    payload: dict[str, object] = {}
    token_parts = access_token.split(".")
    encoded_payload = token_parts[1]
    encoded_payload += "=" * (-len(encoded_payload) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(encoded_payload.encode()).decode())
    except Exception:
        payload = {}

    user_id = payload.get("sub") or payload.get("id")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Access token missing user id"},
        )

    email = payload.get("email")
    return AuthContext(
        user_id=user_id,
        access_token=access_token,
        email=email if isinstance(email, str) else None,
    )


_SENTINEL = object()


@pytest.fixture()
def project_test_auth_override():
    previous = app.dependency_overrides.get(get_auth_context, _SENTINEL)
    app.dependency_overrides[get_auth_context] = _test_auth_context
    yield
    if previous is _SENTINEL:
        app.dependency_overrides.pop(get_auth_context, None)
    else:
        app.dependency_overrides[get_auth_context] = previous


# IMPORTANT: Define this function BEFORE using it!
def import_from_local_analysis(module_name: str):
    """
    Import modules from local_analysis as a package so relative imports work.
    
    Args:
        module_name: Name of the module to import (e.g., 'code_parser')
    
    Returns:
        The imported module
    """
    return importlib.import_module(f"src.local_analysis.{module_name}")


# Now we can use the function to import code_parser
from src.local_analysis.code_parser import CodeAnalyzer


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
