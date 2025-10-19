# Authentication and consent management module.
# This module provides functionality for user consent validation and management,
# integrating with Supabase for persistent storage and user authentication.

from .consent_validator import  ConsentError, ExternalServiceError

__all__ = ["ConsentError", "ExternalServiceError"]