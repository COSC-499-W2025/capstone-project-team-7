# Consent Validation Module
# This module provides comprehensive consent validation functionality for the
# portfolio analysis system, ensuring user consent is properly validated before
# any data processing operations.

from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from datetime import datetime
import logging
import uuid

# Set up logging
logger = logging.getLogger(__name__)


class ConsentError(Exception):
    # Raised when required consent is missing or invalid.
    pass


class ExternalServiceError(Exception):
    # Raised when external service consent is required but not granted.
    pass


class AuthorizationError(Exception):
    # Raised when user is not authorized for the requested operation.
    pass


class DatabaseError(Exception):
    # Raised when database operations fail.
    pass


@dataclass
class ConsentRecord:
    # Data class representing a user's consent record.
    
    # Attributes:
    #     id: Unique identifier for the consent record
    #     user_id: ID of the user who granted consent
    #     analyze_uploaded_only: Whether user consents to analyzing uploaded files only
    #     process_store_metadata: Whether user consents to metadata processing and storage
    #     privacy_ack: Whether user has acknowledged privacy policy
    #     allow_external_services: Whether user allows external service usage
    #     created_at: Timestamp when consent was granted
    
    id: str
    user_id: str
    analyze_uploaded_only: bool
    process_store_metadata: bool
    privacy_ack: bool
    allow_external_services: bool
    created_at: datetime
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConsentRecord':
        # Create ConsentRecord from dictionary data.
        return cls(
            id=data.get('id', ''),
            user_id=data.get('user_id', ''),
            analyze_uploaded_only=data.get('analyze_uploaded_only', False),
            process_store_metadata=data.get('process_store_metadata', False),
            privacy_ack=data.get('privacy_ack', False),
            allow_external_services=data.get('allow_external_services', False),
            created_at=data.get('created_at', datetime.now())
        )