# LLM API Routes
# Handles API endpoints for LLM operations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from analyzer.llm.client import LLMClient, LLMError, InvalidAPIKeyError, create_llm_client
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
    configured: bool = False


class ModelInfoResponse(BaseModel):
    """Response model for LLM model information."""
    provider: str
    default_model: str
    configured: bool


# Global client instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    Dependency to get the current LLM client instance.
    
    Returns:
        LLMClient: Current LLM client
        
    Raises:
        HTTPException: If LLM client is not configured
    """
    if _llm_client is None or not _llm_client.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service not configured. Please provide an API key."
        )
    return _llm_client


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
        
        client = create_llm_client(api_key=request.api_key)
        is_valid = client.verify_api_key()
        
        if is_valid:
            _llm_client = client  
            logger.info(f"API key verified for user {request.user_id}")
            return APIKeyResponse(
                valid=True,
                message="API key verified successfully",
                configured=True
            )
        
        return APIKeyResponse(
            valid=False,
            message="API key verification failed",
            configured=False
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
            message=str(e),
            configured=False
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


@router.get("/model-info", response_model=ModelInfoResponse, status_code=status.HTTP_200_OK)
async def get_model_info():
    """
    Get information about the configured LLM model.
    
    Returns:
        ModelInfoResponse: Model configuration information
    """
    if _llm_client is None:
        return ModelInfoResponse(
            provider="openai",
            default_model="gpt-3.5-turbo",
            configured=False
        )
    
    info = _llm_client.get_model_info()
    return ModelInfoResponse(**info)


@router.get("/status", status_code=status.HTTP_200_OK)
async def get_llm_status():
    """
    Check the status of the LLM service.
    
    Returns:
        Dict: Status information
    """
    configured = _llm_client is not None and _llm_client.is_configured()
    
    return {
        "service": "llm",
        "status": "configured" if configured else "not_configured",
        "ready": configured
    }


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
        "message": "API key cleared successfully",
        "configured": False
    }
