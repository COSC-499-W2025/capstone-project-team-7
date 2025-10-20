# LLM Client Module
# Handles integration with OpenAI API for analysis tasks

import logging
from typing import Optional, Dict, Any
import openai
from openai import OpenAI


logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when LLM operations fail."""
    pass


class InvalidAPIKeyError(Exception):
    """Raised when API key is invalid or missing."""
    pass


class LLMClient:
    """
    Client for interacting with OpenAI's API.
    
    This class provides a foundation for LLM-based analysis operations.
    # TODO: Add specific analysis functions in future depending on requirements
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the LLM client.
        
        Args:
            api_key: OpenAI API key. If None, client operates in mock mode.
        """
        self.api_key = api_key
        self.client = None
        self.logger = logging.getLogger(__name__)
        
        if api_key:
            try:
                self.client = OpenAI(api_key=api_key)
                self.logger.info("LLM client initialized with API key")
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI client: {e}")
                raise LLMError(f"Failed to initialize LLM client: {str(e)}")
        else:
            self.logger.warning("LLM client initialized without API key (mock mode)")
    
    def verify_api_key(self) -> bool:
        """
        Verify that the API key is valid by making a test request.
        
        Returns:
            bool: True if API key is valid, False otherwise
            
        Raises:
            InvalidAPIKeyError: If API key is missing or invalid
            LLMError: If verification fails due to other reasons
        """
        if not self.api_key:
            raise InvalidAPIKeyError("No API key provided")
        
        if not self.client:
            raise InvalidAPIKeyError("LLM client not initialized")
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            
            if response and response.choices:
                self.logger.info("API key verified successfully")
                return True
            
            raise LLMError("Unexpected response from API")
            
        except openai.AuthenticationError as e:
            self.logger.error(f"Authentication failed: {e}")
            raise InvalidAPIKeyError("Invalid API key")
        except openai.APIError as e:
            self.logger.error(f"API error during verification: {e}")
            raise LLMError(f"API error: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error during verification: {e}")
            raise LLMError(f"Verification failed: {str(e)}")
    
    def is_configured(self) -> bool:
        """
        Check if the client is properly configured with an API key.
        
        Returns:
            bool: True if API key is set, False otherwise
        """
        return self.api_key is not None and self.client is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the configured LLM model.
        
        Returns:
            Dict containing model configuration information
        """
        return {
            "provider": "openai",
            "default_model": "gpt-3.5-turbo",
            "configured": self.is_configured()
        }


def create_llm_client(api_key: Optional[str] = None) -> LLMClient:
    """
    Function to create an LLM client instance.
    
    Args:
        api_key: OpenAI API key
        
    Returns:
        LLMClient: Configured LLM client instance
    """
    return LLMClient(api_key=api_key)
