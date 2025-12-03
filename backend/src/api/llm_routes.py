# LLM API Routes
# Handles API endpoints for LLM operations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, NamedTuple
from datetime import datetime, timedelta
import logging
import sys
from pathlib import Path
from threading import Lock

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


class ClearKeyRequest(BaseModel):
    """Request model for clearing API key."""
    user_id: str


class ClientStatusRequest(BaseModel):
    """Request model for checking client status."""
    user_id: str


class ClientStatusResponse(BaseModel):
    """Response model for client status."""
    has_client: bool
    message: str


# TTL Configuration
CLIENT_TTL_MINUTES = 30  # Clients expire after 30 minutes of inactivity
MAX_CLIENTS = 100  # Maximum number of clients to store (LRU eviction)


class ClientEntry(NamedTuple):
    """Entry storing an LLM client with its last access timestamp."""
    client: LLMClient
    last_accessed: datetime


# Per-user client storage with TTL support
# Key: user_id, Value: ClientEntry (client + timestamp)
_user_clients: Dict[str, ClientEntry] = {}
_clients_lock = Lock()


def get_user_client(user_id: str) -> Optional[LLMClient]:
    """
    Thread-safely retrieve a user's LLM client.
    
    Args:
        user_id: User identifier
        
    Returns:
        LLMClient instance or None if not found
    """
    with _clients_lock:
        return _user_clients.get(user_id)


def set_user_client(user_id: str, client: LLMClient) -> None:
    """
    Thread-safely store a user's LLM client.
    
    Args:
        user_id: User identifier
        client: LLMClient instance
    """
    with _clients_lock:
        _user_clients[user_id] = client


def remove_user_client(user_id: str) -> bool:
    """
    Thread-safely remove a user's LLM client.
    
    Args:
        user_id: User identifier
        
    Returns:
        True if client was removed, False if not found
    """
    with _clients_lock:
        if user_id in _user_clients:
            del _user_clients[user_id]
            return True
        return False


@router.post("/verify-key", response_model=APIKeyResponse, status_code=status.HTTP_200_OK)
async def verify_api_key(request: APIKeyRequest):
    """
    Verify an OpenAI API key and check user consent for external services.
    Stores client per-user to prevent race conditions and data leakage.
    
    Args:
        request: APIKeyRequest containing api_key and user_id
        
    Returns:
        APIKeyResponse: Validation result
        
    Raises:
        HTTPException: If consent is not granted or verification fails
    """
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
            set_user_client(request.user_id, client)
            logger.info(f"API key verified and stored for user {request.user_id}")
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


@router.post("/clear-key", status_code=status.HTTP_200_OK)
async def clear_api_key(request: ClearKeyRequest):
    """
    Clear the stored API key from memory for a specific user.
    
    Args:
        request: ClearKeyRequest containing user_id
        
    Returns:
        Dict: Success message
    """
    remove_user_client(request.user_id)
    logger.info(f"API key cleared for user {request.user_id}")
    return {"message": "API key cleared successfully"}


@router.post("/client-status", response_model=ClientStatusResponse, status_code=status.HTTP_200_OK)
async def check_client_status(request: ClientStatusRequest):
    """
    Check if a user has a stored LLM client (verified API key).
    
    Args:
        request: ClientStatusRequest containing user_id
        
    Returns:
        ClientStatusResponse: Whether client exists and status message
    """
    client = get_user_client(request.user_id)
    has_client = client is not None
    
    logger.info(f"Client status checked for user {request.user_id}: {has_client}")
    
    return ClientStatusResponse(
        has_client=has_client,
        message="Client found" if has_client else "No client stored for this user"
    )
