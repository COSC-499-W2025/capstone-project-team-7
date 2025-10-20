# Unit tests for the LLM Client module

import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

backend_src = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

from analyzer.llm.client import (
    LLMClient,
    LLMError,
    InvalidAPIKeyError,
    create_llm_client
)


class TestLLMClient:
    """Test cases for the LLMClient class."""
    
    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        mock = Mock()
        mock.chat.completions.create = Mock()
        return mock
    
    def test_client_initialization_without_key(self):
        """Test LLM client initialization without API key (mock mode)."""
        client = LLMClient()
        
        assert client.api_key is None
        assert client.client is None
        assert not client.is_configured()
    
    def test_client_initialization_with_key(self):
        """Test LLM client initialization with API key."""
        with patch('analyzer.llm.client.OpenAI') as mock_openai:
            client = LLMClient(api_key="test-key-123")
            
            assert client.api_key == "test-key-123"
            assert client.client is not None
            assert client.is_configured()
            mock_openai.assert_called_once_with(api_key="test-key-123")
    
    def test_client_initialization_failure(self):
        """Test LLM client initialization failure."""
        with patch('analyzer.llm.client.OpenAI', side_effect=Exception("API Error")):
            with pytest.raises(LLMError) as exc_info:
                LLMClient(api_key="test-key-123")
            
            assert "Failed to initialize LLM client" in str(exc_info.value)
    
    def test_create_llm_client_factory(self):
        """Test the factory function for creating LLM clients."""
        client = create_llm_client()
        assert isinstance(client, LLMClient)
        assert not client.is_configured()
        
        with patch('analyzer.llm.client.OpenAI'):
            client_with_key = create_llm_client(api_key="test-key")
            assert isinstance(client_with_key, LLMClient)
            assert client_with_key.is_configured()


class TestVerifyAPIKey:
    """Test cases for API key verification."""
    
    @pytest.fixture
    def client_with_key(self):
        """Create a client with a test API key."""
        with patch('analyzer.llm.client.OpenAI'):
            return LLMClient(api_key="test-key-123")
    
    def test_verify_without_api_key(self):
        """Test verification fails when no API key is provided."""
        client = LLMClient()
        
        with pytest.raises(InvalidAPIKeyError) as exc_info:
            client.verify_api_key()
        
        assert "No API key provided" in str(exc_info.value)
    
    def test_verify_without_client(self):
        """Test verification fails when client is not initialized."""
        client = LLMClient()
        client.api_key = "test-key"  # Set key but no client
        
        with pytest.raises(InvalidAPIKeyError) as exc_info:
            client.verify_api_key()
        
        assert "LLM client not initialized" in str(exc_info.value)
    
    def test_verify_success(self, client_with_key):
        """Test successful API key verification."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        result = client_with_key.verify_api_key()
        
        assert result is True
        client_with_key.client.chat.completions.create.assert_called_once()
    
    def test_verify_authentication_error(self, client_with_key):
        """Test verification with authentication error."""
        import openai
        
        with patch.object(
            client_with_key.client.chat.completions,
            'create',
            side_effect=openai.AuthenticationError(
                message="Invalid API key",
                response=Mock(status_code=401),
                body=None
            )
        ):
            with pytest.raises(InvalidAPIKeyError) as exc_info:
                client_with_key.verify_api_key()
            
            assert "Invalid API key" in str(exc_info.value)
    
    def test_verify_api_error(self, client_with_key):
        """Test verification with API error."""
        import openai
        
        with patch.object(
            client_with_key.client.chat.completions,
            'create',
            side_effect=openai.APIError(
                message="Service unavailable",
                request=Mock(),
                body=None
            )
        ):
            with pytest.raises(LLMError) as exc_info:
                client_with_key.verify_api_key()
            
            assert "API error" in str(exc_info.value)
    
    def test_verify_unexpected_error(self, client_with_key):
        """Test verification with unexpected error."""
        with patch.object(
            client_with_key.client.chat.completions,
            'create',
            side_effect=Exception("Unexpected error")
        ):
            with pytest.raises(LLMError) as exc_info:
                client_with_key.verify_api_key()
            
            assert "Verification failed" in str(exc_info.value)
    
    def test_verify_empty_response(self, client_with_key):
        """Test verification with empty response."""
        mock_response = Mock()
        mock_response.choices = []
        
        client_with_key.client.chat.completions.create = Mock(return_value=mock_response)
        
        with pytest.raises(LLMError) as exc_info:
            client_with_key.verify_api_key()
        
        assert "Unexpected response" in str(exc_info.value)


class TestClientMethods:
    """Test cases for LLM client utility methods."""
    
    def test_is_configured_false(self):
        """Test is_configured returns False when not configured."""
        client = LLMClient()
        assert not client.is_configured()
    
    def test_is_configured_true(self):
        """Test is_configured returns True when configured."""
        with patch('analyzer.llm.client.OpenAI'):
            client = LLMClient(api_key="test-key")
            assert client.is_configured()
    
    def test_get_model_info_unconfigured(self):
        """Test get_model_info for unconfigured client."""
        client = LLMClient()
        info = client.get_model_info()
        
        assert info["provider"] == "openai"
        assert info["default_model"] == "gpt-3.5-turbo"
        assert info["configured"] is False
    
    def test_get_model_info_configured(self):
        """Test get_model_info for configured client."""
        with patch('analyzer.llm.client.OpenAI'):
            client = LLMClient(api_key="test-key")
            info = client.get_model_info()
            
            assert info["provider"] == "openai"
            assert info["default_model"] == "gpt-3.5-turbo"
            assert info["configured"] is True


class TestIntegrationScenarios:
    """Integration test scenarios for common use cases."""
    
    def test_complete_setup_workflow(self):
        """Test complete workflow of setting up and verifying LLM client."""
        with patch('analyzer.llm.client.OpenAI') as mock_openai:
            client = create_llm_client(api_key="sk-test123")
            assert client.is_configured()
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            client.client.chat.completions.create = Mock(return_value=mock_response)
            
            is_valid = client.verify_api_key()
            assert is_valid is True
            
            info = client.get_model_info()
            assert info["configured"] is True
    
    def test_workflow_without_api_key(self):
        """Test workflow when API key is not provided."""
        client = create_llm_client()
        
        assert not client.is_configured()
        
        with pytest.raises(InvalidAPIKeyError):
            client.verify_api_key()
        
        info = client.get_model_info()
        assert info["configured"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
