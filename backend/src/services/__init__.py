"""Services package for portfolio scanner API.

Compatibility note:
Historically service modules were imported as ``services.<module>``.
After migrating implementation files into ``services/services`` we keep
those import paths working by registering submodules here.
"""

from importlib import import_module
import sys

_SERVICE_MODULES = (
    "ai_service",
    "analysis_api_service",
    "auth_api_service",
    "code_analysis_service",
    "config_api_service",
    "consent_api_service",
    "contribution_analysis_service",
    "duplicate_detection_service",
    "encryption",
    "export_service",
    "portfolio_item_service",
    "portfolio_timeline_service",
    "preferences_service",
    "project_overrides_service",
    "projects_api_service",
    "projects_service",
    "resume_api_service",
    "resume_generation_service",
    "resume_storage_service",
    "scan_api_client",
    "scan_service",
    "search_service",
    "selection_service",
    "session_service",
    "skills_analysis_service",
    "upload_api_service",
)

for _name in _SERVICE_MODULES:
    try:
        sys.modules[f"{__name__}.{_name}"] = import_module(f".services.{_name}", __name__)
    except Exception:
        # Some modules have optional dependencies; load lazily when imported directly.
        continue
