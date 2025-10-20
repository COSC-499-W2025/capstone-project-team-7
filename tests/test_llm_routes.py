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
    def clear_llm_client(self):
        """Clear the global LLM client before each test."""
        import api.llm_routes as routes
        routes._llm_client = None
        yield
        routes._llm_client = None


class TestVerifyKeyEndpoint(TestLLMRoutes):
    """Test cases for the /api/llm/verify-key endpoint."""
    
    def test_verify_key_success(self, client, valid_request, clear_llm_client):
        """Test successful API key verification."""
        with patch('api.llm_routes.ConsentValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_external_services_consent.return_value = True
            mock_validator_class.return_value = mock_validator
            
            with patch('api.llm_routes.create_llm_client') as mock_create:
                mock_llm = Mock(spec=LLMClient)
                mock_llm.verify_api_key.return_value = True
                mock_create.return_value = mock_llm
                
                response = client.post("/api/llm/verify-key", json=valid_request)
                
                assert response.status_code == 200
                data = response.json()
                assert data["valid"] is True
                assert data["configured"] is True
                assert "successfully" in data["message"]
    
    def test_verify_key_no_consent(self, client, valid_request, clear_llm_client):
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
    
    def test_verify_key_consent_returns_false(self, client, valid_request, clear_llm_client):
        """Test when consent validation returns False."""
        with patch('api.llm_routes.ConsentValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_external_services_consent.return_value = False
            mock_validator_class.return_value = mock_validator
            
            response = client.post("/api/llm/verify-key", json=valid_request)
            
            assert response.status_code == 403
            assert "consent" in response.json()["detail"].lower()
    
    def test_verify_key_invalid_key(self, client, valid_request, clear_llm_client):
        """Test API key verification with invalid key."""
        with patch('api.llm_routes.ConsentValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_external_services_consent.return_value = True
            mock_validator_class.return_value = mock_validator
            
            with patch('api.llm_routes.create_llm_client') as mock_create:
                mock_llm = Mock(spec=LLMClient)
                mock_llm.verify_api_key.side_effect = InvalidAPIKeyError("Invalid API key")
                mock_create.return_value = mock_llm
                
                response = client.post("/api/llm/verify-key", json=valid_request)
                
                assert response.status_code == 200
                data = response.json()
                assert data["valid"] is False
                assert data["configured"] is False
    
    def test_verify_key_llm_error(self, client, valid_request, clear_llm_client):
        """Test API key verification with LLM error."""
        with patch('api.llm_routes.ConsentValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_external_services_consent.return_value = True
            mock_validator_class.return_value = mock_validator
            
            with patch('api.llm_routes.create_llm_client') as mock_create:
                mock_llm = Mock(spec=LLMClient)
                mock_llm.verify_api_key.side_effect = LLMError("Service unavailable")
                mock_create.return_value = mock_llm
                
                response = client.post("/api/llm/verify-key", json=valid_request)
                
                assert response.status_code == 500
                assert "LLM service error" in response.json()["detail"]
    
    def test_verify_key_unexpected_error(self, client, valid_request, clear_llm_client):
        """Test API key verification with unexpected error."""
        with patch('api.llm_routes.ConsentValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_external_services_consent.return_value = True
            mock_validator_class.return_value = mock_validator
            
            with patch('api.llm_routes.create_llm_client', side_effect=Exception("Unexpected")):
                response = client.post("/api/llm/verify-key", json=valid_request)
                
                assert response.status_code == 500
                assert "unexpected error" in response.json()["detail"].lower()


class TestModelInfoEndpoint(TestLLMRoutes):
    """Test cases for the /api/llm/model-info endpoint."""
    
    def test_get_model_info_unconfigured(self, client, clear_llm_client):
        """Test getting model info when LLM is not configured."""
        response = client.get("/api/llm/model-info")
        
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "openai"
        assert data["default_model"] == "gpt-3.5-turbo"
        assert data["configured"] is False
    
    def test_get_model_info_configured(self, client, clear_llm_client):
        """Test getting model info when LLM is configured."""
        import api.llm_routes as routes
        
        mock_client = Mock(spec=LLMClient)
        mock_client.get_model_info.return_value = {
            "provider": "openai",
            "default_model": "gpt-3.5-turbo",
            "configured": True
        }
        routes._llm_client = mock_client
        
        response = client.get("/api/llm/model-info")
        
        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is True
        assert data["provider"] == "openai"


class TestStatusEndpoint(TestLLMRoutes):
    """Test cases for the /api/llm/status endpoint."""
    
    def test_status_not_configured(self, client, clear_llm_client):
        """Test status endpoint when LLM is not configured."""
        response = client.get("/api/llm/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "llm"
        assert data["status"] == "not_configured"
        assert data["ready"] is False
    
    def test_status_configured(self, client, clear_llm_client):
        """Test status endpoint when LLM is configured."""
        import api.llm_routes as routes
        
        mock_client = Mock(spec=LLMClient)
        mock_client.is_configured.return_value = True
        routes._llm_client = mock_client
        
        response = client.get("/api/llm/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "llm"
        assert data["status"] == "configured"
        assert data["ready"] is True


class TestClearKeyEndpoint(TestLLMRoutes):
    """Test cases for the /api/llm/clear-key endpoint."""
    
    def test_clear_key(self, client, clear_llm_client):
        """Test clearing the API key."""
        import api.llm_routes as routes
        
        # Set a mock client first
        routes._llm_client = Mock(spec=LLMClient)
        
        response = client.delete("/api/llm/clear-key")
        
        assert response.status_code == 200
        data = response.json()
        assert "cleared successfully" in data["message"]
        assert data["configured"] is False
        assert routes._llm_client is None
    
    def test_clear_key_when_none(self, client, clear_llm_client):
        """Test clearing the API key when none is set."""
        response = client.delete("/api/llm/clear-key")
        
        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is False


class TestGetLLMClientDependency(TestLLMRoutes):
    """Test cases for the get_llm_client dependency."""
    
    def test_dependency_not_configured(self, client, clear_llm_client):
        """Test that endpoints requiring LLM client fail when not configured."""
        from api.llm_routes import get_llm_client
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            get_llm_client()
        
        assert exc_info.value.status_code == 503
        assert "not configured" in exc_info.value.detail
    
    def test_dependency_configured(self, clear_llm_client):
        """Test that dependency returns client when configured."""
        import api.llm_routes as routes
        from api.llm_routes import get_llm_client
        
        mock_client = Mock(spec=LLMClient)
        mock_client.is_configured.return_value = True
        routes._llm_client = mock_client
        
        result = get_llm_client()
        assert result == mock_client


class TestIntegrationScenarios(TestLLMRoutes):
    """Integration test scenarios for LLM API routes."""
    
    def test_complete_workflow(self, client, clear_llm_client):
        """Test complete workflow: status -> verify -> status -> clear."""
        response = client.get("/api/llm/status")
        assert response.json()["ready"] is False
        
        with patch('api.llm_routes.ConsentValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_external_services_consent.return_value = True
            mock_validator_class.return_value = mock_validator
            
            with patch('api.llm_routes.create_llm_client') as mock_create:
                mock_llm = Mock(spec=LLMClient)
                mock_llm.verify_api_key.return_value = True
                mock_llm.is_configured.return_value = True
                mock_llm.get_model_info.return_value = {
                    "provider": "openai",
                    "default_model": "gpt-3.5-turbo",
                    "configured": True
                }
                mock_create.return_value = mock_llm
                
                response = client.post("/api/llm/verify-key", json={
                    "api_key": "sk-test123",
                    "user_id": "550e8400-e29b-41d4-a716-446655440000"
                })
                assert response.json()["valid"] is True
        
        response = client.get("/api/llm/status")
        assert response.json()["ready"] is True
        
        response = client.delete("/api/llm/clear-key")
        assert response.json()["configured"] is False
        
        response = client.get("/api/llm/status")
        assert response.json()["ready"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
