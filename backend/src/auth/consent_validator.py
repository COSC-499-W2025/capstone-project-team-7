# Consent Validation Module
# This module provides comprehensive consent validation functionality for the
# portfolio analysis system, ensuring user consent is properly validated before
# any data processing operations.
#
# This module integrates with consent.py to provide:
# - Structured validation of consent data
# - Storage and retrieval through consent.py's storage layer
# - Type-safe consent records with dataclasses

from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import uuid

# Import the consent storage module for integration
try:
    from . import consent
except ImportError:
    # Allow standalone execution
    import consent

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
    #     privacy_notice_version: Version of the privacy notice acknowledged
    
    id: str
    user_id: str
    analyze_uploaded_only: bool
    process_store_metadata: bool
    privacy_ack: bool
    allow_external_services: bool
    created_at: datetime
    privacy_notice_version: str = "v1.0"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConsentRecord':
        # Create ConsentRecord from dictionary data.
        # Handle both ISO format strings and datetime objects for created_at
        created_at = data.get('created_at', datetime.now())
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                created_at = datetime.now()
        
        return cls(
            id=data.get('id', ''),
            user_id=data.get('user_id', ''),
            analyze_uploaded_only=data.get('analyze_uploaded_only', False),
            process_store_metadata=data.get('process_store_metadata', False),
            privacy_ack=data.get('privacy_ack', False),
            allow_external_services=data.get('allow_external_services', False),
            created_at=created_at,
            privacy_notice_version=data.get('privacy_notice_version', 'v1.0')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        # Convert ConsentRecord to dictionary format.
        data = asdict(self)
        # Convert datetime to ISO format string for storage
        if isinstance(data['created_at'], datetime):
            data['created_at'] = data['created_at'].isoformat()
        return data
    

class ConsentValidator:
    # Validates user consent for various data processing operations.
    
    # This class provides methods to validate different types of consent
    # according to the system's privacy and data processing requirements.
    # 
    # Integration with consent.py:
    # - Uses consent.py for storage and retrieval operations
    # - Provides structured validation before storing
    # - Maintains type safety with ConsentRecord dataclass
    
    # Service name constants for external services
    SERVICE_EXTERNAL = "external_services"
    SERVICE_FILE_ANALYSIS = "file_analysis"
    SERVICE_METADATA = "metadata_processing"
    
    def __init__(self, supabase_client=None, use_consent_storage=True):
        
        # Initialize the ConsentValidator.
        
        # Args:
        #     supabase_client: Optional Supabase client for database operations.
        #                     If None and use_consent_storage is True, will use consent.py storage.
        #     use_consent_storage: If True, use the consent.py module for storage operations.
        
        self.supabase_client = supabase_client
        self.use_consent_storage = use_consent_storage
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
            created_at=datetime.now(),
            privacy_notice_version="v1.0"
        )
        
        # Store the consent record using consent.py storage
        if self.use_consent_storage:
            self._store_consent_record(consent_record)
        
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
        
        # This method integrates with consent.py for storage operations when
        # use_consent_storage is True, otherwise falls back to Supabase.
        
        # Args:
        #     user_id: The ID of the user

        # Returns:
        #     ConsentRecord or None: The latest consent record if found

        if self.use_consent_storage:
            # Use consent.py storage layer
            # Check for file analysis consent (primary record)
            stored_data = consent.get_consent(user_id, self.SERVICE_FILE_ANALYSIS)
            if stored_data:
                # Convert consent.py format to ConsentRecord
                return self._convert_consent_storage_to_record(user_id, stored_data)
            return None
        
        if self.supabase_client is None:
            self.logger.warning("No Supabase client configured and consent storage disabled")
            return None
        
        # Supabase integration for production use
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
    
    def _store_consent_record(self, consent_record: ConsentRecord) -> None:
        # Store a consent record using consent.py storage.
        
        # This method breaks down the ConsentRecord into individual service
        # consents that are stored in consent.py's storage layer.
        
        # Args:
        #     consent_record: The ConsentRecord to store
        
        if not self.use_consent_storage:
            return
        
        user_id = consent_record.user_id
        
        # Store file analysis consent
        consent.save_consent(
            user_id=user_id,
            service_name=self.SERVICE_FILE_ANALYSIS,
            consent_given=consent_record.analyze_uploaded_only
        )
        
        # Store metadata processing consent
        consent.save_consent(
            user_id=user_id,
            service_name=self.SERVICE_METADATA,
            consent_given=consent_record.process_store_metadata
        )
        
        # Store external services consent
        consent.save_consent(
            user_id=user_id,
            service_name=self.SERVICE_EXTERNAL,
            consent_given=consent_record.allow_external_services
        )
        
        # Store the complete consent record as well
        consent.save_consent(
            user_id=user_id,
            service_name="complete_record",
            consent_given=True  # This is metadata
        )
        
        self.logger.info(f"Stored consent record for user {user_id} in consent storage")
    
    def _convert_consent_storage_to_record(self, user_id: str, stored_data: Dict[str, Any]) -> ConsentRecord:
        # Convert consent.py storage format to ConsentRecord.
        
        # Args:
        #     user_id: The user ID
        #     stored_data: Data from consent.get_consent()
        
        # Returns:
        #     ConsentRecord: Reconstructed consent record
        
        # Get all service consents
        file_analysis = consent.get_consent(user_id, self.SERVICE_FILE_ANALYSIS)
        metadata = consent.get_consent(user_id, self.SERVICE_METADATA)
        external = consent.get_consent(user_id, self.SERVICE_EXTERNAL)
        
        return ConsentRecord(
            id=str(uuid.uuid4()),  # Generate new ID for retrieval
            user_id=user_id,
            analyze_uploaded_only=bool(file_analysis and file_analysis.get("consent_given", False)),
            process_store_metadata=bool(metadata and metadata.get("consent_given", False)),
            privacy_ack=True,  # If record exists, privacy was acknowledged
            allow_external_services=bool(external and external.get("consent_given", False)),
            created_at=datetime.fromisoformat(stored_data.get("consent_timestamp", datetime.now().isoformat())),
            privacy_notice_version=stored_data.get("privacy_notice_version", "v1.0")
        )


def create_consent_validator(supabase_client=None, use_consent_storage=True) -> ConsentValidator:
    # Factory function to create a ConsentValidator instance.
    
    # Args:
    #     supabase_client: Optional Supabase client for database operations
    #     use_consent_storage: If True, use consent.py for storage (default: True)
        
    # Returns:
    #     ConsentValidator: Configured consent validator instance
    
    return ConsentValidator(supabase_client=supabase_client, use_consent_storage=use_consent_storage)


def get_privacy_notice(user_id: str, service_name: str = "external_services") -> Dict[str, Any]:
    # Get the privacy notice for a user to review before granting consent.
    
    # This integrates with consent.py's request_consent functionality.
    
    # Args:
    #     user_id: The user requesting the privacy notice
    #     service_name: The service requiring consent (default: "external_services")
    
    # Returns:
    #     dict: Privacy notice information with service, notice text, and options
    
    return consent.request_consent(user_id, service_name)


def withdraw_user_consent(user_id: str, service_name: Optional[str] = None) -> None:
    # Withdraw consent for a user.
    
    # Args:
    #     user_id: The user withdrawing consent
    #     service_name: Specific service to withdraw (if None, withdraws all)
    
    if service_name:
        consent.withdraw_consent(user_id, service_name)
    else:
        # Withdraw all consents
        for service in [ConsentValidator.SERVICE_EXTERNAL, 
                       ConsentValidator.SERVICE_FILE_ANALYSIS,
                       ConsentValidator.SERVICE_METADATA,
                       "complete_record"]:
            consent.withdraw_consent(user_id, service)