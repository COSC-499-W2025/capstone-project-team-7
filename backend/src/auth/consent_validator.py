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
    

class ConsentValidator:
    # Validates user consent for various data processing operations.
    
    # This class provides methods to validate different types of consent
    # according to the system's privacy and data processing requirements.
    
    def __init__(self, supabase_client=None):
        
        # Initialize the ConsentValidator.
        
        # Args:
        #     supabase_client: Optional Supabase client for database operations.
        #                     If None, database operations will be mocked for testing.
        
        self.supabase_client = supabase_client
        self.logger = logging.getLogger(__name__)
        
    def validate_upload_consent(self, user_id: str, consent_data: Dict[str, Any]) -> ConsentRecord:
        # Validate consent data for file upload operations.
        
        # Args:
        #     user_id: The ID of the user requesting file upload
        #     consent_data: Dictionary containing consent fields
            
        # Returns:
        #     ConsentRecord: Validated consent record
            
        # Raises:
        #     ConsentError: If required consent is missing or invalid
        #     AuthorizationError: If user_id is invalid
        #     ValueError: If consent_data format is invalid
        
        if not user_id or not isinstance(user_id, str):
            raise AuthorizationError("Valid user ID is required")
            
        if not consent_data or not isinstance(consent_data, dict):
            raise ValueError("Consent data must be a valid dictionary")
        
        # Validate required consent fields
        required_fields = [
            'analyze_uploaded_only',
            'process_store_metadata', 
            'privacy_ack'
        ]
        
        for field in required_fields:
            if field not in consent_data:
                raise ConsentError(f"Required consent field '{field}' is missing")
            
            if not isinstance(consent_data[field], bool):
                raise ConsentError(f"Consent field '{field}' must be a boolean value")
            
            if not consent_data[field]:
                field_messages = {
                    'analyze_uploaded_only': "File analysis consent required",
                    'process_store_metadata': "Metadata processing consent required",
                    'privacy_ack': "Privacy policy acknowledgment required"
                }
                raise ConsentError(field_messages[field])
        
        # Optional external services consent (defaults to False)
        allow_external_services = consent_data.get('allow_external_services', False)
        if not isinstance(allow_external_services, bool):
            raise ConsentError("External services consent must be a boolean value")
        
        # Create consent record
        consent_record = ConsentRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            analyze_uploaded_only=consent_data['analyze_uploaded_only'],
            process_store_metadata=consent_data['process_store_metadata'],
            privacy_ack=consent_data['privacy_ack'],
            allow_external_services=allow_external_services,
            created_at=datetime.now()
        )
        
        self.logger.info(f"Consent validated for user {user_id}")
        return consent_record
    
    def check_required_consent(self, user_id: str) -> ConsentRecord:
        # Check if user has provided all required consent.
        
        # Args:
        #     user_id: The ID of the user to check
            
        # Returns:
        #     ConsentRecord: The user's current consent record
            
        # Raises:
        #     ConsentError: If required consent is missing
        #     AuthorizationError: If user is not found
        #     DatabaseError: If database operation fails
        
        if not user_id or not isinstance(user_id, str):
            raise AuthorizationError("Valid user ID is required")
        
        try:
            # Get the most recent consent record for the user
            consent_record = self._get_latest_consent_record(user_id)
            
            if not consent_record:
                raise ConsentError("No consent record found for user")
            
            # Validate all required consent fields
            if not consent_record.analyze_uploaded_only:
                raise ConsentError("File analysis consent required")
            
            if not consent_record.process_store_metadata:
                raise ConsentError("Metadata processing consent required")
            
            if not consent_record.privacy_ack:
                raise ConsentError("Privacy policy acknowledgment required")
            
            self.logger.info(f"Required consent validated for user {user_id}")
            return consent_record
            
        except Exception as e:
            if isinstance(e, (ConsentError, AuthorizationError)):
                raise
            self.logger.error(f"Database error checking consent for user {user_id}: {e}")
            raise DatabaseError("Unable to verify consent - try again")
    
    def validate_external_services_consent(self, user_id: str) -> bool:
        # Validate if user has consented to external services usage.
        
        # Args:
        #     user_id: The ID of the user to check
            
        # Returns:
        #     bool: True if external services are allowed, False otherwise
            
        # Raises:
        #     ExternalServiceError: If external services consent is required but not granted
        #     AuthorizationError: If user is not found
        #     DatabaseError: If database operation fails
        
        if not user_id or not isinstance(user_id, str):
            raise AuthorizationError("Valid user ID is required")
        
        try:
            consent_record = self._get_latest_consent_record(user_id)
            
            if not consent_record:
                raise ExternalServiceError("No consent record found - external services not allowed")
            
            if not consent_record.allow_external_services:
                self.logger.info(f"External services consent denied for user {user_id}")
                return False
            
            self.logger.info(f"External services consent granted for user {user_id}")
            return True
            
        except Exception as e:
            if isinstance(e, (ExternalServiceError, AuthorizationError)):
                raise
            self.logger.error(f"Database error checking external services consent for user {user_id}: {e}")
            raise DatabaseError("Unable to verify external services consent")
    
    def get_user_consent_record(self, user_id: str) -> Optional[ConsentRecord]:
        
        # Retrieve the current consent record for a user.
        
        # Args:
        #     user_id: The ID of the user
            
        # Returns:
        #     ConsentRecord or None: The user's consent record if found
            
        # Raises:
        #     AuthorizationError: If user_id is invalid
        #     DatabaseError: If database operation fails
        
        if not user_id or not isinstance(user_id, str):
            raise AuthorizationError("Valid user ID is required")
        
        try:
            consent_record = self._get_latest_consent_record(user_id)
            
            if consent_record:
                self.logger.info(f"Retrieved consent record for user {user_id}")
            else:
                self.logger.info(f"No consent record found for user {user_id}")
            
            return consent_record
            
        except Exception as e:
            self.logger.error(f"Database error retrieving consent for user {user_id}: {e}")
            raise DatabaseError("Unable to retrieve consent record")
    
    def is_file_processing_allowed(self, user_id: str) -> bool:
        # Check if file processing is allowed for a user.

        # Args:
        #     user_id: The ID of the user
            
        # Returns:
        #     bool: True if file processing is allowed, False otherwise
        
        try:
            consent_record = self.check_required_consent(user_id)
            return consent_record.analyze_uploaded_only and consent_record.process_store_metadata
        except (ConsentError, AuthorizationError, DatabaseError):
            return False
    
    def is_metadata_processing_allowed(self, user_id: str) -> bool:
        # Check if metadata processing is allowed for a user.
        
        # Args:
        #     user_id: The ID of the user
            
        # Returns:
        #     bool: True if metadata processing is allowed, False otherwise
        
        try:
            consent_record = self.check_required_consent(user_id)
            return consent_record.process_store_metadata
        except (ConsentError, AuthorizationError, DatabaseError):
            return False
    
    def _get_latest_consent_record(self, user_id: str) -> Optional[ConsentRecord]:
        # Get the latest consent record for a user from the database.
        
        # This is a private method that will be implemented with actual
        # Supabase database operations in the integration layer.
        
        # Args:
        #     user_id: The ID of the user

        # Returns:
        #     ConsentRecord or None: The latest consent record if found

        # TODO: Implement actual Supabase database query
        # For now, return None to indicate no database integration yet
        if self.supabase_client is None:
            self.logger.warning("No Supabase client configured - using mock data")
            return None
        
        # Placeholder for actual Supabase query implementation
        # This will be implemented in the Supabase integration deliverable
        try:
            # Example of what the query will look like:
            # result = self.supabase_client.table('consent_records') \
            #     .select('*') \
            #     .eq('user_id', user_id) \
            #     .order('created_at', desc=True) \
            #     .limit(1) \
            #     .execute()
            
            # if result.data:
            #     return ConsentRecord.from_dict(result.data[0])
            
            return None
            
        except Exception as e:
            self.logger.error(f"Database query failed for user {user_id}: {e}")
            raise DatabaseError("Database query failed")


def create_consent_validator(supabase_client=None) -> ConsentValidator:
    # Factory function to create a ConsentValidator instance.
    
    # Args:
    #     supabase_client: Optional Supabase client for database operations
        
    # Returns:
    #     ConsentValidator: Configured consent validator instance
    
    return ConsentValidator(supabase_client=supabase_client)