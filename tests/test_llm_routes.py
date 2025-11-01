# Unit tests for LLM API routes

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import sys
from pathlib import Path

backend_src = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

from main import app
from analyzer.llm.client import LLMClient, LLMError, InvalidAPIKeyError
from auth.consent_validator import ExternalServiceError
import api.llm_routes as routes


class TestLLMRoutes:
    """Test cases for LLM API routes."""
    
    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        return TestClient(app)
    
    @pytest.fixture
    def valid_request(self):
        """Create a valid API key request."""
        return {
            "api_key": "sk-test123",
            "user_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    
    @pytest.fixture
    def clear_llm_clients(self):
        """Clear all user LLM clients before and after each test."""
        routes._user_clients.clear()
        yield
        routes._user_clients.clear()


class TestVerifyKeyEndpoint(TestLLMRoutes):
    """Test cases for the /api/llm/verify-key endpoint."""
    
    def test_verify_key_success(self, client, valid_request, clear_llm_clients):
        """Test successful API key verification with per-user storage."""
        user_id = valid_request["user_id"]
        
        with patch('api.llm_routes.ConsentValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_external_services_consent.return_value = True
            mock_validator_class.return_value = mock_validator
            
            with patch('api.llm_routes.LLMClient') as mock_llm_class:
                mock_llm = Mock(spec=LLMClient)
                mock_llm.verify_api_key.return_value = True
                mock_llm_class.return_value = mock_llm
                
                response = client.post("/api/llm/verify-key", json=valid_request)
                
                assert response.status_code == 200
                data = response.json()
                assert data["valid"] is True
                assert "successfully" in data["message"]
                
                # Verify client was stored for this user
                stored_client = routes.get_user_client(user_id)
                assert stored_client is not None
    
    def test_verify_key_no_consent(self, client, valid_request, clear_llm_clients):
        """Test API key verification without external services consent."""
        with patch('api.llm_routes.ConsentValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_external_services_consent.side_effect = ExternalServiceError(
                "User has not consented"
            )
            mock_validator_class.return_value = mock_validator
            
            response = client.post("/api/llm/verify-key", json=valid_request)
            
            assert response.status_code == 403
            assert "consent" in response.json()["detail"].lower()
    
    def test_verify_key_consent_returns_false(self, client, valid_request, clear_llm_clients):
        """Test when consent validation returns False."""
        with patch('api.llm_routes.ConsentValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_external_services_consent.return_value = False
            mock_validator_class.return_value = mock_validator
            
            response = client.post("/api/llm/verify-key", json=valid_request)
            
            assert response.status_code == 403
            assert "consent" in response.json()["detail"].lower()
    
    def test_verify_key_invalid_key(self, client, valid_request, clear_llm_clients):
        """Test API key verification with invalid key."""
        with patch('api.llm_routes.ConsentValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_external_services_consent.return_value = True
            mock_validator_class.return_value = mock_validator
            
            with patch('api.llm_routes.LLMClient') as mock_llm_class:
                mock_llm = Mock(spec=LLMClient)
                mock_llm.verify_api_key.side_effect = InvalidAPIKeyError("Invalid API key")
                mock_llm_class.return_value = mock_llm
                
                response = client.post("/api/llm/verify-key", json=valid_request)
                
                assert response.status_code == 200
                data = response.json()
                assert data["valid"] is False
                assert "Invalid API key" in data["message"]
    
    def test_verify_key_llm_error(self, client, valid_request, clear_llm_clients):
        """Test API key verification with LLM error."""
        with patch('api.llm_routes.ConsentValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_external_services_consent.return_value = True
            mock_validator_class.return_value = mock_validator
            
            with patch('api.llm_routes.LLMClient') as mock_llm_class:
                mock_llm = Mock(spec=LLMClient)
                mock_llm.verify_api_key.side_effect = LLMError("Service unavailable")
                mock_llm_class.return_value = mock_llm
                
                response = client.post("/api/llm/verify-key", json=valid_request)
                
                assert response.status_code == 500
                assert "LLM service error" in response.json()["detail"]
    
    def test_verify_key_unexpected_error(self, client, valid_request, clear_llm_clients):
        """Test API key verification with unexpected error."""
        with patch('api.llm_routes.ConsentValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_external_services_consent.return_value = True
            mock_validator_class.return_value = mock_validator
            
            with patch('api.llm_routes.LLMClient') as mock_llm_class:
                mock_llm_class.side_effect = Exception("Unexpected error")
                
                response = client.post("/api/llm/verify-key", json=valid_request)
                
                assert response.status_code == 500
                assert "unexpected error" in response.json()["detail"].lower()


class TestClearKeyEndpoint(TestLLMRoutes):
    """Test cases for the /api/llm/clear-key endpoint."""
    
    def test_clear_key(self, client, clear_llm_clients):
        """Test clearing the API key for a specific user."""
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Store a mock client for this user
        routes.set_user_client(user_id, Mock(spec=LLMClient))
        assert routes.get_user_client(user_id) is not None
        
        response = client.post("/api/llm/clear-key", json={"user_id": user_id})
        
        assert response.status_code == 200
        data = response.json()
        assert "cleared successfully" in data["message"]
        
        # Verify client was removed for this user
        assert routes.get_user_client(user_id) is None
    
    def test_clear_key_when_none(self, client, clear_llm_clients):
        """Test clearing the API key when none is set for user."""
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        
        response = client.post("/api/llm/clear-key", json={"user_id": user_id})
        
        assert response.status_code == 200
        data = response.json()
        assert "cleared successfully" in data["message"]
    
    def test_clear_key_does_not_affect_other_users(self, client, clear_llm_clients):
        """Test that clearing one user's key doesn't affect others."""
        user1_id = "550e8400-e29b-41d4-a716-446655440000"
        user2_id = "550e8400-e29b-41d4-a716-446655440001"
        
        # Store clients for both users
        routes.set_user_client(user1_id, Mock(spec=LLMClient))
        routes.set_user_client(user2_id, Mock(spec=LLMClient))
        
        # Clear user1's client
        response = client.post("/api/llm/clear-key", json={"user_id": user1_id})
        assert response.status_code == 200
        
        # Verify user1's client is gone but user2's remains
        assert routes.get_user_client(user1_id) is None
        assert routes.get_user_client(user2_id) is not None


class TestClientStatusEndpoint(TestLLMRoutes):
    """Test cases for the /api/llm/client-status endpoint."""
    
    def test_client_status_with_client(self, client, clear_llm_clients):
        """Test checking status when client exists."""
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Store a mock client
        routes.set_user_client(user_id, Mock(spec=LLMClient))
        
        response = client.post("/api/llm/client-status", json={"user_id": user_id})
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_client"] is True
        assert "found" in data["message"].lower()
    
    def test_client_status_without_client(self, client, clear_llm_clients):
        """Test checking status when no client exists."""
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        
        response = client.post("/api/llm/client-status", json={"user_id": user_id})
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_client"] is False
        assert "no client" in data["message"].lower()


class TestIntegrationScenarios(TestLLMRoutes):
    """Integration test scenarios for LLM API routes."""
    
    def test_complete_workflow(self, client, clear_llm_clients):
        """Test complete workflow: verify -> status check -> clear."""
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        
        with patch('api.llm_routes.ConsentValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_external_services_consent.return_value = True
            mock_validator_class.return_value = mock_validator
            
            with patch('api.llm_routes.LLMClient') as mock_llm_class:
                mock_llm = Mock(spec=LLMClient)
                mock_llm.verify_api_key.return_value = True
                mock_llm_class.return_value = mock_llm
                
                # Verify key
                response = client.post("/api/llm/verify-key", json={
                    "api_key": "sk-test123",
                    "user_id": user_id
                })
                assert response.status_code == 200
                assert response.json()["valid"] is True
        
        # Check status
        response = client.post("/api/llm/client-status", json={"user_id": user_id})
        assert response.status_code == 200
        assert response.json()["has_client"] is True
        
        # Clear key
        response = client.post("/api/llm/clear-key", json={"user_id": user_id})
        assert response.status_code == 200
        
        # Verify cleared
        response = client.post("/api/llm/client-status", json={"user_id": user_id})
        assert response.status_code == 200
        assert response.json()["has_client"] is False
    
    def test_multiple_users_isolation(self, client, clear_llm_clients):
        """Test that multiple users can have separate API keys."""
        user1_id = "550e8400-e29b-41d4-a716-446655440000"
        user2_id = "550e8400-e29b-41d4-a716-446655440001"
        
        with patch('api.llm_routes.ConsentValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_external_services_consent.return_value = True
            mock_validator_class.return_value = mock_validator
            
            with patch('api.llm_routes.LLMClient') as mock_llm_class:
                mock_llm = Mock(spec=LLMClient)
                mock_llm.verify_api_key.return_value = True
                mock_llm_class.return_value = mock_llm
                
                # Verify keys for both users
                response1 = client.post("/api/llm/verify-key", json={
                    "api_key": "sk-user1-key",
                    "user_id": user1_id
                })
                assert response1.status_code == 200
                
                response2 = client.post("/api/llm/verify-key", json={
                    "api_key": "sk-user2-key",
                    "user_id": user2_id
                })
                assert response2.status_code == 200
        
        # Both users should have clients
        status1 = client.post("/api/llm/client-status", json={"user_id": user1_id})
        status2 = client.post("/api/llm/client-status", json={"user_id": user2_id})
        
        assert status1.json()["has_client"] is True
        assert status2.json()["has_client"] is True
        
        # Verify they have different client instances
        client1 = routes.get_user_client(user1_id)
        client2 = routes.get_user_client(user2_id)
        assert client1 is not client2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
