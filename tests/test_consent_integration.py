# Integration tests for consent_validator.py and consent.py
# Tests the integration between the validation layer and storage layer

import pytest
import sys
from pathlib import Path
from datetime import datetime

# Add backend src to path
backend_src = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

from auth.consent_validator import (
    ConsentValidator,
    ConsentRecord,
    ConsentError,
    AuthorizationError,
    create_consent_validator,
    get_privacy_notice,
    withdraw_user_consent
)
from auth import consent


class TestConsentIntegration:
    """Test the integration between consent_validator and consent modules."""
    
    @pytest.fixture(autouse=True)
    def clear_consent_store(self):
        """Clear the consent store before each test."""
        consent._consent_store.clear()
        yield
        consent._consent_store.clear()
    
    @pytest.fixture
    def validator(self):
        """Create a validator with consent storage enabled."""
        return create_consent_validator(use_consent_storage=True)
    
    def test_validate_and_store_consent(self, validator):
        """Test that validating consent stores it in consent.py storage."""
        user_id = "integration_user_1"
        consent_data = {
            "analyze_uploaded_only": True,
            "process_store_metadata": True,
            "privacy_ack": True,
            "allow_external_services": True
        }
        
        # Validate and store consent
        result = validator.validate_upload_consent(user_id, consent_data)
        
        # Verify ConsentRecord was returned
        assert isinstance(result, ConsentRecord)
        assert result.user_id == user_id
        
        # Verify data was stored in consent.py storage
        assert consent.has_consent(user_id, ConsentValidator.SERVICE_FILE_ANALYSIS) is True
        assert consent.has_consent(user_id, ConsentValidator.SERVICE_METADATA) is True
        assert consent.has_consent(user_id, ConsentValidator.SERVICE_EXTERNAL) is True
    
    def test_retrieve_stored_consent(self, validator):
        """Test retrieving consent that was stored via validation."""
        user_id = "integration_user_2"
        consent_data = {
            "analyze_uploaded_only": True,
            "process_store_metadata": True,
            "privacy_ack": True,
            "allow_external_services": False
        }
        
        # Store consent
        validator.validate_upload_consent(user_id, consent_data)
        
        # Retrieve consent
        retrieved = validator.get_user_consent_record(user_id)
        
        assert retrieved is not None
        assert retrieved.user_id == user_id
        assert retrieved.analyze_uploaded_only is True
        assert retrieved.process_store_metadata is True
        assert retrieved.allow_external_services is False
    
    def test_check_required_consent_integration(self, validator):
        """Test checking required consent uses stored data."""
        user_id = "integration_user_3"
        consent_data = {
            "analyze_uploaded_only": True,
            "process_store_metadata": True,
            "privacy_ack": True,
            "allow_external_services": False
        }
        
        # Store consent
        validator.validate_upload_consent(user_id, consent_data)
        
        # Check required consent
        consent_record = validator.check_required_consent(user_id)
        
        assert consent_record is not None
        assert consent_record.analyze_uploaded_only is True
        assert consent_record.process_store_metadata is True
    
    def test_validate_external_services_consent(self, validator):
        """Test external services consent validation."""
        user_id = "integration_user_4"
        
        # Store consent with external services enabled
        consent_data = {
            "analyze_uploaded_only": True,
            "process_store_metadata": True,
            "privacy_ack": True,
            "allow_external_services": True
        }
        validator.validate_upload_consent(user_id, consent_data)
        
        # Validate external services consent
        has_external = validator.validate_external_services_consent(user_id)
        assert has_external is True
        
        # Test without external services
        user_id_2 = "integration_user_5"
        consent_data["allow_external_services"] = False
        validator.validate_upload_consent(user_id_2, consent_data)
        
        has_external_2 = validator.validate_external_services_consent(user_id_2)
        assert has_external_2 is False
    
    def test_file_processing_allowed(self, validator):
        """Test file processing permission check."""
        user_id = "integration_user_6"
        consent_data = {
            "analyze_uploaded_only": True,
            "process_store_metadata": True,
            "privacy_ack": True,
            "allow_external_services": False
        }
        
        validator.validate_upload_consent(user_id, consent_data)
        
        assert validator.is_file_processing_allowed(user_id) is True
        assert validator.is_metadata_processing_allowed(user_id) is True
    
    def test_privacy_notice_retrieval(self):
        """Test getting privacy notice through integrated function."""
        user_id = "integration_user_7"
        
        notice = get_privacy_notice(user_id, "LLM")
        
        assert notice["service"] == "LLM"
        assert "privacy_notice" in notice
        assert "external services" in notice["privacy_notice"]
        assert "options" in notice
        assert "agree" in notice["options"]
        assert "decline" in notice["options"]
    
    def test_withdraw_consent_integration(self, validator):
        """Test withdrawing consent removes it from storage."""
        user_id = "integration_user_8"
        consent_data = {
            "analyze_uploaded_only": True,
            "process_store_metadata": True,
            "privacy_ack": True,
            "allow_external_services": True
        }
        
        # Store consent
        validator.validate_upload_consent(user_id, consent_data)
        assert consent.has_consent(user_id, ConsentValidator.SERVICE_EXTERNAL) is True
        
        # Withdraw specific consent
        withdraw_user_consent(user_id, ConsentValidator.SERVICE_EXTERNAL)
        assert consent.has_consent(user_id, ConsentValidator.SERVICE_EXTERNAL) is False
        
        # Other consents should still exist
        assert consent.has_consent(user_id, ConsentValidator.SERVICE_FILE_ANALYSIS) is True
    
    def test_withdraw_all_consents(self, validator):
        """Test withdrawing all consents for a user."""
        user_id = "integration_user_9"
        consent_data = {
            "analyze_uploaded_only": True,
            "process_store_metadata": True,
            "privacy_ack": True,
            "allow_external_services": True
        }
        
        # Store consent
        validator.validate_upload_consent(user_id, consent_data)
        
        # Withdraw all
        withdraw_user_consent(user_id)
        
        # All consents should be withdrawn
        assert consent.has_consent(user_id, ConsentValidator.SERVICE_EXTERNAL) is False
        assert consent.has_consent(user_id, ConsentValidator.SERVICE_FILE_ANALYSIS) is False
        assert consent.has_consent(user_id, ConsentValidator.SERVICE_METADATA) is False
    
    def test_consent_with_disabled_storage(self):
        """Test validator works with consent storage disabled."""
        validator = create_consent_validator(use_consent_storage=False)
        user_id = "integration_user_10"
        consent_data = {
            "analyze_uploaded_only": True,
            "process_store_metadata": True,
            "privacy_ack": True,
            "allow_external_services": False
        }
        
        # Should validate but not store
        result = validator.validate_upload_consent(user_id, consent_data)
        assert isinstance(result, ConsentRecord)
        
        # Should not be in storage
        assert consent.has_consent(user_id, ConsentValidator.SERVICE_FILE_ANALYSIS) is False
    
    def test_privacy_notice_version_stored(self, validator):
        """Test that privacy notice version is stored correctly."""
        user_id = "integration_user_11"
        consent_data = {
            "analyze_uploaded_only": True,
            "process_store_metadata": True,
            "privacy_ack": True,
            "allow_external_services": True
        }
        
        validator.validate_upload_consent(user_id, consent_data)
        
        # Check that version is stored
        stored = consent.get_consent(user_id, ConsentValidator.SERVICE_FILE_ANALYSIS)
        assert stored is not None
        assert stored["privacy_notice_version"] == "v1.0"
    
    def test_complete_user_workflow(self, validator):
        """Test complete user consent workflow."""
        user_id = "workflow_user"
        
        # Step 1: User requests privacy notice
        notice = get_privacy_notice(user_id, "LLM")
        assert "privacy_notice" in notice
        
        # Step 2: User agrees and provides consent
        consent_data = {
            "analyze_uploaded_only": True,
            "process_store_metadata": True,
            "privacy_ack": True,
            "allow_external_services": True
        }
        consent_record = validator.validate_upload_consent(user_id, consent_data)
        assert consent_record.user_id == user_id
        
        # Step 3: System checks if user has required consent
        assert validator.is_file_processing_allowed(user_id) is True
        assert validator.is_metadata_processing_allowed(user_id) is True
        
        # Step 4: System checks external services consent
        has_external = validator.validate_external_services_consent(user_id)
        assert has_external is True
        
        # Step 5: User withdraws consent
        withdraw_user_consent(user_id)
        
        # Step 6: System checks consent again (should fail)
        assert validator.is_file_processing_allowed(user_id) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
