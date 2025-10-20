# API routes module
# Contains all API endpoint definitions

from .llm_routes import router as llm_router

__all__ = ["llm_router"]
