# Unit tests for the ConsentValidator module.

# This test suite validates the consent validation functionality implemented in
# the ConsentValidator class.

import pytest
import json
import os
from datetime import datetime
from unittest.mock import Mock
from pathlib import Path

# Add the backend src directory to the path for imports
import sys
from pathlib import Path
backend_src = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

from auth.consent_validator import (
    ConsentValidator,
    ConsentRecord,
    ConsentError,
    ExternalServiceError,
    AuthorizationError,
    DatabaseError,
    create_consent_validator
)


class TestConsentRecord:
    # Test cases for the ConsentRecord dataclass.
    
    def test_consent_record_creation(self):
        # Test creating a ConsentRecord with all fields.
        record = ConsentRecord(
            id="test-id",
            user_id="user-123",
            analyze_uploaded_only=True,
            process_store_metadata=True,
            privacy_ack=True,
            allow_external_services=False,
            created_at=datetime.now()
        )
        
        assert record.id == "test-id"
        assert record.user_id == "user-123"
        assert record.analyze_uploaded_only is True
        assert record.process_store_metadata is True
        assert record.privacy_ack is True
        assert record.allow_external_services is False
        assert isinstance(record.created_at, datetime)
    
    def test_consent_record_from_dict(self):
        # Test creating ConsentRecord from dictionary data.
        data = {
            'id': 'test-id-123',
            'user_id': 'user-456',
            'analyze_uploaded_only': True,
            'process_store_metadata': True,
            'privacy_ack': True,
            'allow_external_services': True,
            'created_at': datetime.now()
        }
        
        record = ConsentRecord.from_dict(data)
        
        assert record.id == 'test-id-123'
        assert record.user_id == 'user-456'
        assert record.allow_external_services is True


class TestConsentValidator:
    # Test cases for the ConsentValidator class.
    
    @pytest.fixture
    def validator(self):
        # Create a ConsentValidator instance for testing.
        return ConsentValidator()
    
    @pytest.fixture
    def mock_supabase_client(self):
        # Create a mock Supabase client.
        return Mock()
    
    @pytest.fixture
    def test_data(self):
        # Load test data from fixtures.
        fixtures_path = Path(__file__).parent / "fixtures" / "consent_test_data.json"
        with open(fixtures_path, 'r') as f:
            return json.load(f)
    
    def test_validator_initialization(self):
        # Test ConsentValidator initialization.
        validator = ConsentValidator()
        assert validator.supabase_client is None
        
        mock_client = Mock()
        validator_with_client = ConsentValidator(supabase_client=mock_client)
        assert validator_with_client.supabase_client == mock_client
    
    def test_create_consent_validator_factory(self):
        # Test the factory function for creating validators.
        validator = create_consent_validator()
        assert isinstance(validator, ConsentValidator)
        assert validator.supabase_client is None
        
        mock_client = Mock()
        validator_with_client = create_consent_validator(supabase_client=mock_client)
        assert validator_with_client.supabase_client == mock_client


class TestValidateUploadConsent:
    # Test cases for validate_upload_consent method.
    
    @pytest.fixture
    def validator(self):
        return ConsentValidator()
    
    @pytest.fixture
    def test_data(self):
        fixtures_path = Path(__file__).parent / "fixtures" / "consent_test_data.json"
        with open(fixtures_path, 'r') as f:
            return json.load(f)
    
    def test_valid_consent_data(self, validator, test_data):
        # Test validation with valid consent data.
        user_id = test_data["sample_user_ids"]["valid_user"]
        consent_data = test_data["valid_consent_data"]
        
        result = validator.validate_upload_consent(user_id, consent_data)
        
        assert isinstance(result, ConsentRecord)
        assert result.user_id == user_id
        assert result.analyze_uploaded_only is True
        assert result.process_store_metadata is True
        assert result.privacy_ack is True
        assert result.allow_external_services is False
        assert result.id is not None
        assert isinstance(result.created_at, datetime)
    
    def test_valid_consent_with_external_services(self, validator, test_data):
        # Test validation with external services enabled.
        user_id = test_data["sample_user_ids"]["valid_user"]
        consent_data = test_data["valid_consent_with_external"]
        
        result = validator.validate_upload_consent(user_id, consent_data)
        
        assert result.allow_external_services is True
    
    def test_missing_user_id(self, validator, test_data):
        # Test validation fails with missing user ID.
        consent_data = test_data["valid_consent_data"]
        
        with pytest.raises(AuthorizationError, match="Valid user ID is required"):
            validator.validate_upload_consent("", consent_data)
        
        with pytest.raises(AuthorizationError):
            validator.validate_upload_consent(None, consent_data)
    
    def test_invalid_consent_data_format(self, validator):
        # Test validation fails with invalid consent data format.
        user_id = "test-user-123"
        
        with pytest.raises(ValueError, match="Consent data must be a valid dictionary"):
            validator.validate_upload_consent(user_id, None)
        
        with pytest.raises(ValueError):
            validator.validate_upload_consent(user_id, "invalid")
    
    def test_missing_required_fields(self, validator, test_data):
        # Test validation fails when required fields are missing.
        user_id = test_data["sample_user_ids"]["valid_user"]
        consent_data = test_data["missing_required_field"]
        
        with pytest.raises(ConsentError, match="Required consent field 'privacy_ack' is missing"):
            validator.validate_upload_consent(user_id, consent_data)
    
    def test_invalid_boolean_values(self, validator, test_data):
        # Test validation fails with non-boolean values.
        user_id = test_data["sample_user_ids"]["valid_user"]
        consent_data = test_data["invalid_boolean_values"]
        
        with pytest.raises(ConsentError, match="Consent field 'analyze_uploaded_only' must be a boolean value"):
            validator.validate_upload_consent(user_id, consent_data)
    
    def test_refused_required_consent(self, validator, test_data):
        # Test validation fails when required consent is refused.
        user_id = test_data["sample_user_ids"]["valid_user"]
        consent_data = test_data["refused_consent"]
        
        with pytest.raises(ConsentError, match="File analysis consent required"):
            validator.validate_upload_consent(user_id, consent_data)
    
    def test_specific_consent_error_messages(self, validator):
        # Test specific error messages for each required field.
        user_id = "test-user"
        
        # Test analyze_uploaded_only error
        consent_data = {
            "analyze_uploaded_only": False,
            "process_store_metadata": True,
            "privacy_ack": True
        }
        with pytest.raises(ConsentError, match="File analysis consent required"):
            validator.validate_upload_consent(user_id, consent_data)
        
        # Test process_store_metadata error
        consent_data = {
            "analyze_uploaded_only": True,
            "process_store_metadata": False,
            "privacy_ack": True
        }
        with pytest.raises(ConsentError, match="Metadata processing consent required"):
            validator.validate_upload_consent(user_id, consent_data)
        
        # Test privacy_ack error
        consent_data = {
            "analyze_uploaded_only": True,
            "process_store_metadata": True,
            "privacy_ack": False
        }
        with pytest.raises(ConsentError, match="Privacy policy acknowledgment required"):
            validator.validate_upload_consent(user_id, consent_data)


class TestCheckRequiredConsent:
    # Test cases for check_required_consent method.
    
    @pytest.fixture
    def validator(self):
        return ConsentValidator()
    
    def test_invalid_user_id(self, validator):
        # Test check fails with invalid user ID.
        with pytest.raises(AuthorizationError, match="Valid user ID is required"):
            validator.check_required_consent("")
        
        with pytest.raises(AuthorizationError):
            validator.check_required_consent(None)
    
    def test_no_supabase_client_returns_consent_error(self, validator):
        # Test that missing Supabase client raises ConsentError.
        with pytest.raises(ConsentError, match="No consent record found for user"):
            validator.check_required_consent("test-user")


class TestValidateExternalServicesConsent:
    # Test cases for validate_external_services_consent method.
    
    @pytest.fixture
    def validator(self):
        return ConsentValidator()
    
    def test_invalid_user_id(self, validator):
        # Test validation fails with invalid user ID.
        with pytest.raises(AuthorizationError, match="Valid user ID is required"):
            validator.validate_external_services_consent("")
        
        with pytest.raises(AuthorizationError):
            validator.validate_external_services_consent(None)
    
    def test_no_consent_record_raises_external_service_error(self, validator):
        # Test that missing consent record raises ExternalServiceError.
        with pytest.raises(ExternalServiceError, match="No consent record found - external services not allowed"):
            validator.validate_external_services_consent("test-user")


class TestGetUserConsentRecord:
    # Test cases for get_user_consent_record method.
    
    @pytest.fixture
    def validator(self):
        return ConsentValidator()
    
    def test_invalid_user_id(self, validator):
        # Test retrieval fails with invalid user ID.
        with pytest.raises(AuthorizationError, match="Valid user ID is required"):
            validator.get_user_consent_record("")
        
        with pytest.raises(AuthorizationError):
            validator.get_user_consent_record(None)
    
    def test_no_consent_record_returns_none(self, validator):
        # Test that missing consent record returns None.
        result = validator.get_user_consent_record("test-user")
        assert result is None


class TestUtilityMethods:
    # Test cases for utility methods.
    
    @pytest.fixture
    def validator(self):
        return ConsentValidator()
    
    def test_is_file_processing_allowed_no_consent(self, validator):
        # Test file processing check with no consent.
        result = validator.is_file_processing_allowed("test-user")
        assert result is False
    
    def test_is_metadata_processing_allowed_no_consent(self, validator):
        # Test metadata processing check with no consent.
        result = validator.is_metadata_processing_allowed("test-user")
        assert result is False


class TestIntegrationScenarios:
    # Integration test scenarios for common use cases.
    
    @pytest.fixture
    def validator(self):
        return ConsentValidator()
    
    @pytest.fixture
    def test_data(self):
        fixtures_path = Path(__file__).parent / "fixtures" / "consent_test_data.json"
        with open(fixtures_path, 'r') as f:
            return json.load(f)
    
    def test_complete_upload_workflow(self, validator, test_data):
        # Test complete upload consent workflow.
        user_id = test_data["sample_user_ids"]["valid_user"]
        consent_data = test_data["valid_consent_data"]
        
        # Validate upload consent
        consent_record = validator.validate_upload_consent(user_id, consent_data)
        assert isinstance(consent_record, ConsentRecord)
        
        # Verify all required fields are set correctly
        assert consent_record.analyze_uploaded_only is True
        assert consent_record.process_store_metadata is True
        assert consent_record.privacy_ack is True
        assert consent_record.allow_external_services is False
    
    def test_external_services_workflow(self, validator, test_data):
        # Test external services consent workflow.
        user_id = test_data["sample_user_ids"]["valid_user"]
        consent_data = test_data["valid_consent_with_external"]
        
        # Validate consent with external services enabled
        consent_record = validator.validate_upload_consent(user_id, consent_data)
        assert consent_record.allow_external_services is True


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])