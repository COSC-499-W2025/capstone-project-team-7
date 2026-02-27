"""
Tests for ProjectOverridesService.

Tests the service layer for managing project override preferences:
- get_overrides
- get_overrides_for_projects (batch)
- upsert_overrides
- delete_overrides

Run with: pytest tests/test_project_overrides_service.py -v
"""

from unittest.mock import MagicMock, patch
import pytest

from services.project_overrides_service import (
    ProjectOverridesService,
    ProjectOverridesServiceError,
)


class TestServiceRoleKeyPriority:
    """Regression tests for Supabase key priority order (must use service role key first)."""

    def test_prefers_service_role_key_over_supabase_key(self):
        """SUPABASE_SERVICE_ROLE_KEY must take priority over SUPABASE_KEY.

        If SUPABASE_KEY is the anon key and SUPABASE_SERVICE_ROLE_KEY is the
        service role key, the service must pick the service role key so that
        RLS is bypassed for backend writes to project_overrides.
        """
        env = {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_KEY": "anon-key",
            "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
        }
        with patch.dict("os.environ", env, clear=True):
            with patch("services.project_overrides_service.create_client") as mock_create:
                mock_create.return_value = MagicMock()
                service = ProjectOverridesService()
                _, call_kwargs = mock_create.call_args
                used_key = mock_create.call_args[0][1]
                assert used_key == "service-role-key", (
                    "Service must use SUPABASE_SERVICE_ROLE_KEY over SUPABASE_KEY "
                    "to bypass RLS for backend writes"
                )

    def test_falls_back_to_supabase_key_when_no_service_role_key(self):
        """Falls back to SUPABASE_KEY when SUPABASE_SERVICE_ROLE_KEY is not set."""
        env = {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_KEY": "some-key",
        }
        with patch.dict("os.environ", env, clear=True):
            with patch("services.project_overrides_service.create_client") as mock_create:
                mock_create.return_value = MagicMock()
                service = ProjectOverridesService()
                used_key = mock_create.call_args[0][1]
                assert used_key == "some-key"


class DummyProjectOverridesService(ProjectOverridesService):
    """ProjectOverridesService that accepts an injected Supabase client for testing."""

    def __init__(self, client, encryption_service=None):
        self.client = client
        self._encryption = encryption_service


def _fake_supabase_client():
    """Create a mock Supabase client."""
    client = MagicMock()
    return client


class TestGetOverrides:
    """Tests for get_overrides method."""

    def test_get_overrides_returns_record(self):
        """Test that get_overrides returns decrypted record when found."""
        client = _fake_supabase_client()
        service = DummyProjectOverridesService(client)
        
        mock_record = {
            "id": "override-123",
            "user_id": "user-1",
            "project_id": "project-1",
            "role": "Lead Developer",
            "evidence": ["Built feature X", "Fixed bug Y"],
            "highlighted_skills": ["Python", "FastAPI"],
            "start_date_override": "2024-01-01",
            "end_date_override": "2024-06-30",
            "comparison_attributes": {"team_size": "5"},
            "custom_rank": 85.0,
            "thumbnail_url": "https://example.com/thumb.jpg",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-02T00:00:00Z",
        }
        
        (
            client.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .limit.return_value
            .execute.return_value
        ).data = [mock_record]
        
        result = service.get_overrides("user-1", "project-1")
        
        assert result is not None
        assert result["role"] == "Lead Developer"
        assert result["evidence"] == ["Built feature X", "Fixed bug Y"]
        assert result["highlighted_skills"] == ["Python", "FastAPI"]
        assert result["custom_rank"] == 85.0

    def test_get_overrides_returns_none_when_not_found(self):
        """Test that get_overrides returns None when no record exists."""
        client = _fake_supabase_client()
        service = DummyProjectOverridesService(client)
        
        (
            client.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .limit.return_value
            .execute.return_value
        ).data = []
        
        result = service.get_overrides("user-1", "nonexistent-project")
        
        assert result is None

    def test_get_overrides_raises_on_db_error(self):
        """Test that get_overrides raises ProjectOverridesServiceError on failure."""
        client = _fake_supabase_client()
        service = DummyProjectOverridesService(client)
        
        (
            client.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .limit.return_value
            .execute
        ).side_effect = Exception("Database connection failed")
        
        with pytest.raises(ProjectOverridesServiceError) as exc_info:
            service.get_overrides("user-1", "project-1")
        
        assert "Failed to retrieve overrides" in str(exc_info.value)


class TestGetOverridesForProjects:
    """Tests for get_overrides_for_projects batch method."""

    def test_batch_get_returns_mapping(self):
        """Test that batch get returns dict mapping project_id to overrides."""
        client = _fake_supabase_client()
        service = DummyProjectOverridesService(client)
        
        mock_records = [
            {
                "project_id": "project-1",
                "role": "Developer",
                "end_date_override": "2024-06-30",
            },
            {
                "project_id": "project-2",
                "role": "Lead",
                "end_date_override": "2024-12-31",
            },
        ]
        
        (
            client.table.return_value
            .select.return_value
            .eq.return_value
            .in_.return_value
            .execute.return_value
        ).data = mock_records
        
        result = service.get_overrides_for_projects("user-1", ["project-1", "project-2"])
        
        assert "project-1" in result
        assert "project-2" in result
        assert result["project-1"]["role"] == "Developer"
        assert result["project-2"]["role"] == "Lead"

    def test_batch_get_returns_empty_for_empty_input(self):
        """Test that batch get returns empty dict for empty project_ids list."""
        client = _fake_supabase_client()
        service = DummyProjectOverridesService(client)
        
        result = service.get_overrides_for_projects("user-1", [])
        
        assert result == {}
        client.table.assert_not_called()

    def test_batch_get_raises_on_db_error(self):
        """Test that batch get raises ProjectOverridesServiceError on failure."""
        client = _fake_supabase_client()
        service = DummyProjectOverridesService(client)
        
        (
            client.table.return_value
            .select.return_value
            .eq.return_value
            .in_.return_value
            .execute
        ).side_effect = Exception("Database error")
        
        with pytest.raises(ProjectOverridesServiceError):
            service.get_overrides_for_projects("user-1", ["project-1"])


class TestUpsertOverrides:
    """Tests for upsert_overrides method."""

    def test_upsert_creates_new_record(self):
        """Test that upsert creates a new record when none exists."""
        client = _fake_supabase_client()
        service = DummyProjectOverridesService(client)
        
        # First call (get_overrides) returns empty list (no existing record)
        (
            client.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .limit.return_value
            .execute.return_value
        ).data = []
        
        # Insert returns the new record
        new_record = {
            "id": "new-123",
            "user_id": "user-1",
            "project_id": "project-1",
            "role": "Developer",
            "evidence": [],
            "highlighted_skills": ["Python"],
            "created_at": "2025-01-01T00:00:00Z",
        }
        (
            client.table.return_value
            .insert.return_value
            .execute.return_value
        ).data = [new_record]
        
        result = service.upsert_overrides(
            "user-1",
            "project-1",
            role="Developer",
            highlighted_skills=["Python"],
        )
        
        assert result["role"] == "Developer"
        assert result["highlighted_skills"] == ["Python"]
        client.table.return_value.insert.assert_called_once()

    def test_upsert_updates_existing_record(self):
        """Test that upsert updates existing record with partial data."""
        client = _fake_supabase_client()
        service = DummyProjectOverridesService(client)
        
        # First call (get_overrides) returns existing record
        existing_record = {
            "id": "existing-123",
            "user_id": "user-1",
            "project_id": "project-1",
            "role": "Junior Developer",
            "evidence": ["Old evidence"],
            "highlighted_skills": ["JavaScript"],
        }
        (
            client.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .limit.return_value
            .execute.return_value
        ).data = [existing_record]
        
        # Update returns the updated record
        updated_record = {
            "id": "existing-123",
            "user_id": "user-1",
            "project_id": "project-1",
            "role": "Senior Developer",  # Updated
            "evidence": ["Old evidence"],  # Unchanged
            "highlighted_skills": ["JavaScript"],  # Unchanged
        }
        (
            client.table.return_value
            .update.return_value
            .eq.return_value
            .eq.return_value
            .execute.return_value
        ).data = [updated_record]
        
        result = service.upsert_overrides(
            "user-1",
            "project-1",
            role="Senior Developer",  # Only update role
        )
        
        assert result["role"] == "Senior Developer"
        client.table.return_value.update.assert_called_once()

    def test_upsert_handles_all_fields(self):
        """Test that upsert handles all override fields."""
        client = _fake_supabase_client()
        service = DummyProjectOverridesService(client)
        
        # No existing record
        (
            client.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .limit.return_value
            .execute.return_value
        ).data = []
        
        new_record = {
            "id": "new-456",
            "user_id": "user-1",
            "project_id": "project-1",
            "role": "Lead",
            "evidence": ["Built X", "Fixed Y"],
            "thumbnail_url": "https://example.com/img.jpg",
            "custom_rank": 90.0,
            "start_date_override": "2024-01-15",
            "end_date_override": "2024-08-20",
            "comparison_attributes": {"complexity": "high"},
            "highlighted_skills": ["Rust", "Go"],
        }
        (
            client.table.return_value
            .insert.return_value
            .execute.return_value
        ).data = [new_record]
        
        result = service.upsert_overrides(
            "user-1",
            "project-1",
            role="Lead",
            evidence=["Built X", "Fixed Y"],
            thumbnail_url="https://example.com/img.jpg",
            custom_rank=90.0,
            start_date_override="2024-01-15",
            end_date_override="2024-08-20",
            comparison_attributes={"complexity": "high"},
            highlighted_skills=["Rust", "Go"],
        )
        
        assert result["role"] == "Lead"
        assert result["evidence"] == ["Built X", "Fixed Y"]
        assert result["custom_rank"] == 90.0
        assert result["start_date_override"] == "2024-01-15"
        assert result["end_date_override"] == "2024-08-20"

    def test_upsert_raises_on_db_error(self):
        """Test that upsert raises ProjectOverridesServiceError on failure."""
        client = _fake_supabase_client()
        service = DummyProjectOverridesService(client)
        
        # get_overrides returns empty list (new record)
        (
            client.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .limit.return_value
            .execute.return_value
        ).data = []
        
        # Insert fails
        (
            client.table.return_value
            .insert.return_value
            .execute
        ).side_effect = Exception("Insert failed")
        
        with pytest.raises(ProjectOverridesServiceError):
            service.upsert_overrides("user-1", "project-1", role="Dev")


class TestDeleteOverrides:
    """Tests for delete_overrides method."""

    def test_delete_returns_true_when_record_exists(self):
        """Test that delete returns True when record was deleted."""
        client = _fake_supabase_client()
        service = DummyProjectOverridesService(client)
        
        # get_overrides returns existing record
        existing_record = {
            "id": "existing-123",
            "user_id": "user-1",
            "project_id": "project-1",
            "role": "Developer",
        }
        (
            client.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .limit.return_value
            .execute.return_value
        ).data = [existing_record]
        
        result = service.delete_overrides("user-1", "project-1")
        
        assert result is True
        client.table.return_value.delete.assert_called_once()

    def test_delete_returns_false_when_no_record(self):
        """Test that delete returns False when no record exists."""
        client = _fake_supabase_client()
        service = DummyProjectOverridesService(client)
        
        # get_overrides returns empty list (no existing record)
        (
            client.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .limit.return_value
            .execute.return_value
        ).data = []
        
        result = service.delete_overrides("user-1", "nonexistent-project")
        
        assert result is False
        client.table.return_value.delete.assert_not_called()

    def test_delete_raises_on_db_error(self):
        """Test that delete raises ProjectOverridesServiceError on failure."""
        client = _fake_supabase_client()
        service = DummyProjectOverridesService(client)
        
        # get_overrides returns existing record
        existing_record = {"id": "123", "user_id": "user-1", "project_id": "project-1"}
        (
            client.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .limit.return_value
            .execute.return_value
        ).data = [existing_record]
        
        # Delete fails
        (
            client.table.return_value
            .delete.return_value
            .eq.return_value
            .eq.return_value
            .execute
        ).side_effect = Exception("Delete failed")
        
        with pytest.raises(ProjectOverridesServiceError):
            service.delete_overrides("user-1", "project-1")


class TestEncryption:
    """Tests for encryption/decryption of sensitive fields."""

    def test_encrypted_fields_are_decrypted_on_read(self):
        """Test that encrypted fields (role, evidence, comparison_attributes) are decrypted."""
        client = _fake_supabase_client()
        
        # Create mock encryption service
        mock_encryption = MagicMock()
        mock_encryption.decrypt_json.return_value = "Decrypted Role"
        
        service = DummyProjectOverridesService(client, encryption_service=mock_encryption)
        
        # Simulate encrypted data in database
        encrypted_envelope = {"v": 1, "iv": "abc", "ct": "encrypted_data"}
        mock_record = {
            "id": "123",
            "user_id": "user-1",
            "project_id": "project-1",
            "role": encrypted_envelope,  # Encrypted
            "evidence": None,
            "highlighted_skills": ["Python"],
        }
        
        (
            client.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .limit.return_value
            .execute.return_value
        ).data = [mock_record]
        
        result = service.get_overrides("user-1", "project-1")
        
        # Verify decrypt_json was called for the encrypted field
        mock_encryption.decrypt_json.assert_called_with(encrypted_envelope)
        assert result["role"] == "Decrypted Role"

    def test_sensitive_fields_are_encrypted_on_write(self):
        """Test that sensitive fields are encrypted when saving."""
        client = _fake_supabase_client()
        
        # Create mock encryption service
        mock_encryption = MagicMock()
        encrypted_envelope = {"v": 1, "iv": "xyz", "ct": "encrypted_role"}
        mock_encryption.encrypt_json.return_value = MagicMock()
        mock_encryption.encrypt_json.return_value.to_dict.return_value = encrypted_envelope
        
        service = DummyProjectOverridesService(client, encryption_service=mock_encryption)
        
        # No existing record
        (
            client.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .limit.return_value
            .execute.return_value
        ).data = []
        
        # Insert returns record
        (
            client.table.return_value
            .insert.return_value
            .execute.return_value
        ).data = [{"id": "new", "role": encrypted_envelope}]
        
        service.upsert_overrides("user-1", "project-1", role="My Role")
        
        # Verify encrypt_json was called for the sensitive field
        mock_encryption.encrypt_json.assert_called()
