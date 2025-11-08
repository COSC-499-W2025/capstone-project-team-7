"""
Tests for consent persistence functionality.
Verifies that user consents are properly saved to and loaded from the database.
"""

import sys
from anyio import Path
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

# Add backend/src to path
backend_src = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

from auth import consent
from auth.consent_validator import ConsentValidator, ConsentRecord


class TestConsentPersistence:
    """Test suite for consent persistence to database."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup before each test."""
        # Clear in-memory store before each test
        consent._consent_store.clear()
        yield
        # Cleanup after test
        consent._consent_store.clear()
    
    def test_save_consent_to_memory_fallback(self):
        """Test that consent is saved to memory when database unavailable."""
        # Mock Supabase client as None (unavailable)
        original_client = consent._supabase_client
        consent._supabase_client = None
        
        try:
            result = consent.save_consent("user123", "external_services", True)
            
            assert result["status"] == "success"
            assert result["data"]["user_id"] == "user123"
            assert result["data"]["consent_given"] is True
            
            # Verify it's in memory
            stored = consent.get_consent("user123", "external_services")
            assert stored is not None
            assert stored["consent_given"] is True
        finally:
            consent._supabase_client = original_client
    
    def test_save_consent_to_database(self):
        """Test that consent is saved to Supabase database."""
        # Mock Supabase client
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        
        # Mock select query (no existing record)
        mock_select = MagicMock()
        mock_select.eq.return_value.execute.return_value.data = []
        mock_table.select.return_value = mock_select
        
        # Mock insert
        mock_insert = MagicMock()
        mock_insert.execute.return_value = MagicMock()
        mock_table.insert.return_value = mock_insert
        
        original_client = consent._supabase_client
        consent._supabase_client = mock_client
        
        try:
            result = consent.save_consent("user123", "file_analysis", True)
            
            assert result["status"] == "success"
            
            # Verify database was called
            mock_client.table.assert_called_with("consents_v1")
            mock_table.select.assert_called()
            mock_table.insert.assert_called_once()
            
            # Check insert payload
            insert_call = mock_table.insert.call_args[0][0]
            assert insert_call["user_id"] == "user123"
            assert insert_call["accepted"] is True
            assert "file_analysis" in insert_call["metadata"]
        finally:
            consent._supabase_client = original_client
    
    def test_update_existing_consent_in_database(self):
        """Test that existing consent is updated in database."""
        # Mock Supabase client
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        
        # Mock select query (existing record)
        existing_metadata = {"file_analysis": {"consent_given": True, "timestamp": "2024-01-01"}}
        mock_select = MagicMock()
        mock_select.eq.return_value.execute.return_value.data = [
            {
                "user_id": "user123",
                "accepted": True,
                "accepted_at": "2024-01-01T00:00:00",
                "metadata": existing_metadata
            }
        ]
        mock_table.select.return_value = mock_select
        
        # Mock update
        mock_update = MagicMock()
        mock_update_eq = MagicMock()
        mock_update_eq.execute.return_value = MagicMock()
        mock_update.eq.return_value = mock_update_eq
        mock_table.update.return_value = mock_update
        
        original_client = consent._supabase_client
        consent._supabase_client = mock_client
        
        try:
            result = consent.save_consent("user123", "external_services", True)
            
            assert result["status"] == "success"
            
            # Verify update was called
            mock_table.update.assert_called_once()
            
            # Check update payload
            update_call = mock_table.update.call_args[0][0]
            assert "metadata" in update_call
            assert "external_services" in update_call["metadata"]
        finally:
            consent._supabase_client = original_client
    
    def test_get_consent_from_database(self):
        """Test that consent is retrieved from database."""
        # Mock Supabase client
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        
        # Mock select query
        mock_select = MagicMock()
        mock_select.eq.return_value.execute.return_value.data = [
            {
                "user_id": "user123",
                "accepted": True,
                "accepted_at": "2024-01-01T00:00:00",
                "version": "v1.0",
                "metadata": {
                    "file_analysis": {
                        "consent_given": True,
                        "timestamp": "2024-01-01T00:00:00"
                    }
                }
            }
        ]
        mock_table.select.return_value = mock_select
        
        original_client = consent._supabase_client
        consent._supabase_client = mock_client
        
        try:
            result = consent.get_consent("user123", "file_analysis")
            
            assert result is not None
            assert result["user_id"] == "user123"
            assert result["consent_given"] is True
            
            # Verify database was called
            mock_client.table.assert_called_with("consents_v1")
            mock_table.select.assert_called()
        finally:
            consent._supabase_client = original_client
    
    def test_withdraw_consent_from_database(self):
        """Test that consent withdrawal is persisted to database."""
        # Mock Supabase client
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        
        # Mock select query
        mock_select = MagicMock()
        mock_select.eq.return_value.execute.return_value.data = [
            {
                "user_id": "user123",
                "accepted": True,
                "accepted_at": "2024-01-01T00:00:00",
                "metadata": {
                    "file_analysis": {"consent_given": True, "timestamp": "2024-01-01"},
                    "external_services": {"consent_given": True, "timestamp": "2024-01-01"}
                }
            }
        ]
        mock_table.select.return_value = mock_select
        
        # Mock update
        mock_update = MagicMock()
        mock_update_eq = MagicMock()
        mock_update_eq.execute.return_value = MagicMock()
        mock_update.eq.return_value = mock_update_eq
        mock_table.update.return_value = mock_update
        
        original_client = consent._supabase_client
        consent._supabase_client = mock_client
        
        try:
            consent.withdraw_consent("user123", "file_analysis")
            
            # Verify update was called
            mock_table.update.assert_called_once()
            
            # Check update payload
            update_call = mock_table.update.call_args[0][0]
            assert update_call["accepted"] is False
            assert "file_analysis" not in update_call["metadata"]
        finally:
            consent._supabase_client = original_client
    
    def test_load_user_consents(self):
        """Test loading all user consents into memory cache."""
        # Mock Supabase client
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        
        # Mock select query
        mock_select = MagicMock()
        mock_select.eq.return_value.execute.return_value.data = [
            {
                "user_id": "user123",
                "accepted": True,
                "accepted_at": "2024-01-01T00:00:00",
                "version": "v1.0",
                "metadata": {
                    "file_analysis": {"consent_given": True, "timestamp": "2024-01-01"},
                    "external_services": {"consent_given": False, "timestamp": "2024-01-01"}
                }
            }
        ]
        mock_table.select.return_value = mock_select
        
        original_client = consent._supabase_client
        consent._supabase_client = mock_client
        
        try:
            consent.load_user_consents("user123")
            
            # Verify consents are in memory
            file_consent = consent.get_consent("user123", "file_analysis")
            external_consent = consent.get_consent("user123", "external_services")
            
            assert file_consent is not None
            assert file_consent["consent_given"] is True
            assert external_consent is not None
            assert external_consent["consent_given"] is False
        finally:
            consent._supabase_client = original_client
    
    def test_clear_user_consents_cache(self):
        """Test clearing user consents from memory cache."""
        # Add some test data to memory
        consent._consent_store[("user123", "file_analysis")] = {
            "consent_given": True,
            "timestamp": "2024-01-01"
        }
        consent._consent_store[("user123", "external_services")] = {
            "consent_given": False,
            "timestamp": "2024-01-01"
        }
        consent._consent_store[("user456", "file_analysis")] = {
            "consent_given": True,
            "timestamp": "2024-01-01"
        }
        
        # Clear user123's consents
        consent.clear_user_consents_cache("user123")
        
        # Verify user123's consents are cleared
        assert consent.get_consent("user123", "file_analysis") is None
        assert consent.get_consent("user123", "external_services") is None
        
        # Verify user456's consents are intact
        assert consent.get_consent("user456", "file_analysis") is not None
    
    def test_get_all_consents(self):
        """Test retrieving all consents for a user."""
        # Mock Supabase client
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        
        # Mock select query
        mock_select = MagicMock()
        mock_select.eq.return_value.execute.return_value.data = [
            {
                "user_id": "user123",
                "accepted": True,
                "accepted_at": "2024-01-01T00:00:00",
                "version": "v1.0",
                "metadata": {
                    "file_analysis": {"consent_given": True, "timestamp": "2024-01-01"},
                    "external_services": {"consent_given": True, "timestamp": "2024-01-01"}
                }
            }
        ]
        mock_table.select.return_value = mock_select
        
        original_client = consent._supabase_client
        consent._supabase_client = mock_client
        
        try:
            all_consents = consent.get_all_consents("user123")
            
            assert all_consents is not None
            assert all_consents["user_id"] == "user123"
            assert all_consents["accepted"] is True
            assert "file_analysis" in all_consents["metadata"]
            assert "external_services" in all_consents["metadata"]
        finally:
            consent._supabase_client = original_client
    
    def test_consent_validator_persistence(self):
        """Test that ConsentValidator properly persists consents."""
        # Mock Supabase client
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        
        # Mock select query (no existing record)
        mock_select = MagicMock()
        mock_select.eq.return_value.execute.return_value.data = []
        mock_table.select.return_value = mock_select
        
        # Mock insert
        mock_insert = MagicMock()
        mock_insert.execute.return_value = MagicMock()
        mock_table.insert.return_value = mock_insert
        
        original_client = consent._supabase_client
        consent._supabase_client = mock_client
        
        try:
            validator = ConsentValidator(use_consent_storage=True)
            
            consent_data = {
                "analyze_uploaded_only": True,
                "process_store_metadata": True,
                "privacy_ack": True,
                "allow_external_services": True
            }
            
            record = validator.validate_upload_consent("user123", consent_data)
            
            assert record.user_id == "user123"
            assert record.analyze_uploaded_only is True
            assert record.allow_external_services is True
            
            # Verify persistence was attempted
            assert mock_client.table.called
        finally:
            consent._supabase_client = original_client


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
