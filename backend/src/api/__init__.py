# API routes module
# Contains all API endpoint definitions

from .auth_routes import router as auth_router
from .llm_routes import router as llm_router
from .spec_routes import router as spec_router

__all__ = ["auth_router", "llm_router", "spec_router"]
