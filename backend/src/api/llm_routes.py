# LLM API Routes
# Handles API endpoints for LLM operations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from analyzer.llm.client import LLMClient, LLMError, InvalidAPIKeyError
from auth.consent_validator import ConsentValidator, ExternalServiceError


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/llm", tags=["LLM"])


class APIKeyRequest(BaseModel):
    """Request model for API key verification."""
    api_key: str = Field(..., description="OpenAI API key")
    user_id: str = Field(..., description="User ID for consent validation")


class APIKeyResponse(BaseModel):
    """Response model for API key operations."""
    valid: bool
    message: str


# Global client instance
_llm_client: Optional[LLMClient] = None


@router.post("/verify-key", response_model=APIKeyResponse, status_code=status.HTTP_200_OK)
async def verify_api_key(request: APIKeyRequest):
    """
    Verify an OpenAI API key and check user consent for external services.
    
    Args:
        request: APIKeyRequest containing api_key and user_id
        
    Returns:
        APIKeyResponse: Validation result
        
    Raises:
        HTTPException: If consent is not granted or verification fails
    """
    global _llm_client
    
    try:
        consent_validator = ConsentValidator()
        has_consent = consent_validator.validate_external_services_consent(request.user_id)
        
        if not has_consent:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has not consented to external services. Please grant consent first."
            )
        
        client = LLMClient(api_key=request.api_key)
        is_valid = client.verify_api_key()
        
        if is_valid:
            _llm_client = client  
            logger.info(f"API key verified for user {request.user_id}")
            return APIKeyResponse(
                valid=True,
                message="API key verified successfully"
            )
        
        return APIKeyResponse(
            valid=False,
            message="API key verification failed"
        )
        
    except HTTPException:
        raise
    except ExternalServiceError as e:
        logger.warning(f"External service consent not granted for user {request.user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except InvalidAPIKeyError as e:
        logger.error(f"Invalid API key for user {request.user_id}: {e}")
        return APIKeyResponse(
            valid=False,
            message=str(e)
        )
    except LLMError as e:
        logger.error(f"LLM error during verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM service error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during API key verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.delete("/clear-key", status_code=status.HTTP_200_OK)
async def clear_api_key():
    """
    Clear the stored API key from the service.
    
    Returns:
        Dict: Confirmation message
    """
    global _llm_client
    _llm_client = None
    logger.info("API key cleared from LLM service")
    
    return {
        "message": "API key cleared successfully"
    }
