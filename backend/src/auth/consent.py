# auth/consent.py

# Module Purpose:
#   - Manage user consent for external services (e.g., LLMs, APIs).
#   - Show a privacy notice to inform users about risks & data handling.
#   - Save consent decisions persistently in Supabase database.
#   - Enforce blocking of external calls unless consent is granted.

import datetime
import os
from typing import Optional, Dict, Any

try:
    from supabase.client import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Initialize Supabase client for consent persistence
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
)

_supabase_client = None
_authenticated_client: Optional[Client] = None
_authenticated_client_token: Optional[str] = None
if SUPABASE_AVAILABLE and SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase.client import create_client as _create_client
        _supabase_client = _create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        pass

# In-memory fallback store for consent records (used when Supabase unavailable)
# Keys   → (user_id, service_name)
# Values → dict with consent info (decision, timestamp, privacy notice, etc.)
_consent_store = {}

# Active session context for authenticated requests
_active_access_token: Optional[str] = None


def set_session_token(access_token: Optional[str]) -> None:
    """
    Set the active user's access token for authenticated database requests.
    Should be called after login.
    
    Args:
        access_token: The user's JWT access token from Supabase auth
    """
    global _active_access_token
    _active_access_token = access_token


def clear_session_token() -> None:
    """
    Clear the active session token.
    Should be called on logout.
    """
    global _active_access_token
    _active_access_token = None


def _get_authenticated_client(access_token: Optional[str] = None):
    """
    Get a Supabase client with optional authentication.
    
    Uses the documented supabase-py pattern for setting user authentication:
    client.auth.set_session(access_token, refresh_token)
    
    Args:
        access_token: User's JWT access token for authenticated requests.
                     If None, uses the globally set _active_access_token.
        
    Returns:
        Authenticated Supabase client or None
    """
    if not _supabase_client or not SUPABASE_URL or not SUPABASE_KEY:
        return None
    
    token = access_token or _active_access_token
    global _authenticated_client, _authenticated_client_token
    if token and _authenticated_client and _authenticated_client_token == token:
        return _authenticated_client

    client = _supabase_client
    if token:
        try:
            from supabase.client import create_client as _create_client
            client = _create_client(SUPABASE_URL, SUPABASE_KEY)
            client.auth.set_session(token, token)
            _authenticated_client = client
            _authenticated_client_token = token
            return client
        except Exception:
            pass

    return client


def stop_authenticated_client_auto_refresh() -> None:
    """Cancel any pending auto-refresh timers to avoid dangling threads."""

    if not _authenticated_client:
        return

    auth_client = getattr(_authenticated_client, "auth", None)
    timer = getattr(auth_client, "_refresh_token_timer", None)
    if timer:
        try:
            timer.cancel()
        except Exception:
            pass
        setattr(auth_client, "_refresh_token_timer", None)

# Versioned Privacy Notice (single source of truth)
# - This is what users see when deciding on consent.
# - Stored alongside their decision for audit purposes.

PRIVACY_NOTICE = """
When you use features that rely on external services (e.g., Large Language Models, APIs, or cloud providers),
please be aware of the following:

1. Data Transmission
   - Your input (text, files, or other data) may be sent to an external service for processing.
   - This service may be operated by a third party outside of our direct control.

2. Data Handling & Storage
   - Data transmitted may be temporarily or permanently stored by the external provider.
   - The provider may process your data in accordance with its own terms of service and privacy policy.
   - We cannot guarantee that your data will be deleted or anonymized once sent.

3. Personal Information
   - Do NOT include personally identifiable information (PII) such as name, email, phone number,
     address, or financial details in your input.
   - If you provide PII, it may be visible to the external provider and potentially logged.

4. Risks
   - Your data may be transferred across international borders.
   - The external provider may update its terms and practices without our direct oversight.

5. Consent
   - By proceeding, you acknowledge and accept that your data will be processed by an external service.
   - You may withdraw consent at any time, after which no further data will be sent.
"""

# Request consent (to show the notice to the user)

def request_consent(user_id: str, service_name: str):
    """
    Generate the privacy notice and available options for the user.

    Args:
        user_id (str): The ID of the user being asked for consent.
        service_name (str): The external service (e.g., "LLM").

    Returns:
        dict: Contains the service name, privacy notice text, and available options.
    """
    return {
        "service": service_name,
        "privacy_notice": PRIVACY_NOTICE.strip(),
        "options": ["agree", "decline"]
    }

# Save consent decision

def save_consent(user_id: str, service_name: str, consent_given: bool, access_token: Optional[str] = None):
    """
    Save or update the user's consent decision to Supabase database.

    Args:
        user_id (str): The user making the decision.
        service_name (str): The service requiring consent.
        consent_given (bool): True if the user agreed, False if declined.
        access_token (str, optional): User's access token for authenticated requests.

    Returns:
        dict: Confirmation with stored data.
    """
    timestamp = datetime.datetime.now(datetime.UTC).isoformat()
    data = {
        "user_id": user_id,
        "service_name": service_name,
        "consent_given": consent_given,
        "consent_timestamp": timestamp,
        "privacy_notice_version": "v1.0",
        "privacy_notice": PRIVACY_NOTICE.strip()
    }
    
    # Store in memory (fallback/cache)
    _consent_store[(user_id, service_name)] = data
    
    # Persist to Supabase if available
    client = _get_authenticated_client(access_token)
    if client:
        try:
            # Store in consents_v1 table with metadata
            metadata = {
                "service_name": service_name,
                "consent_given": consent_given,
                "consent_timestamp": timestamp,
                "privacy_notice_version": "v1.0"
            }
            
            # Check if record exists
            existing = client.table("consents_v1").select("*").eq("user_id", user_id).execute()
            
            if existing.data:
                # Update existing record
                current_metadata = existing.data[0].get("metadata", {})
                # Merge service-specific consent into metadata
                current_metadata[service_name] = {
                    "consent_given": consent_given,
                    "timestamp": timestamp
                }
                
                client.table("consents_v1").update({
                    "metadata": current_metadata,
                    "accepted": consent_given,  # Update accepted if any consent given
                    "accepted_at": timestamp if consent_given else existing.data[0].get("accepted_at")
                }).eq("user_id", user_id).execute()
            else:
                # Insert new record
                client.table("consents_v1").insert({
                    "user_id": user_id,
                    "accepted": consent_given,
                    "accepted_at": timestamp if consent_given else None,
                    "version": "v1.0",
                    "metadata": {service_name: {"consent_given": consent_given, "timestamp": timestamp}}
                }).execute()
        except Exception as e:
            # Silently fall back to memory store on database error
            pass
    
    return {"status": "success", "data": data}

# Retrieve consent

def get_consent(user_id: str, service_name: str, access_token: Optional[str] = None):
    """
    Retrieve the consent record for a given user and service from database.

    Args:
        user_id (str): User ID to look up.
        service_name (str): Service name to check.
        access_token (str, optional): User's access token for authenticated requests.

    Returns:
        dict | None: The stored consent record, or None if not found.
    """
    # Try to fetch from Supabase first
    client = _get_authenticated_client(access_token)
    if client:
        try:
            result = client.table("consents_v1").select("*").eq("user_id", user_id).execute()
            
            if result.data:
                record = result.data[0]
                metadata = record.get("metadata", {})
                service_data = metadata.get(service_name)
                
                if service_data:
                    return {
                        "user_id": user_id,
                        "service_name": service_name,
                        "consent_given": service_data.get("consent_given", False),
                        "consent_timestamp": service_data.get("timestamp", record.get("accepted_at")),
                        "privacy_notice_version": record.get("version", "v1.0"),
                        "privacy_notice": PRIVACY_NOTICE.strip()
                    }
        except Exception as e:
            # Silently fall back to memory store on database error
            pass
    
    # Fallback to memory store
    return _consent_store.get((user_id, service_name))

# Check if consent is granted

def has_consent(user_id: str, service_name: str) -> bool:
    """
    Check if the user has granted consent for a given service.

    Args:
        user_id (str): The user to check.
        service_name (str): The service to check for consent.

    Returns:
        bool: True if consent exists and is True, otherwise False.
    """
    consent = get_consent(user_id, service_name)
    return bool(consent and consent["consent_given"])

# Withdraw consent

def withdraw_consent(user_id: str, service_name: str, access_token: Optional[str] = None):
    """
    Remove a user's consent record (as if they withdrew consent).
    Persists withdrawal to database.

    Args:
        user_id (str): The user ID to clear.
        service_name (str): The service name to clear.
        access_token (str, optional): User's access token for authenticated requests.

    Returns:
        None
    """
    # Remove from memory store
    _consent_store.pop((user_id, service_name), None)
    
    # Persist withdrawal to Supabase if available
    client = _get_authenticated_client(access_token)
    if client:
        try:
            # Get existing record
            result = client.table("consents_v1").select("*").eq("user_id", user_id).execute()
            
            if result.data:
                record = result.data[0]
                metadata = record.get("metadata", {})
                
                # Remove the specific service from metadata
                if service_name in metadata:
                    del metadata[service_name]
                
                # Update the record
                client.table("consents_v1").update({
                    "metadata": metadata,
                    "accepted": False,  # Mark as not accepted when withdrawing
                    "accepted_at": None
                }).eq("user_id", user_id).execute()
        except Exception as e:
            # Silently fall back to memory store on database error
            pass


def get_all_consents(user_id: str, access_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve all consent records for a user from database.
    
    Args:
        user_id (str): User ID to look up.
        access_token (str, optional): User's access token for authenticated requests.
    
    Returns:
        dict: All consent records for the user, or empty dict if none found.
    """
    client = _get_authenticated_client(access_token)
    if client:
        try:
            result = client.table("consents_v1").select("*").eq("user_id", user_id).execute()
            
            if result.data:
                record = result.data[0]
                return {
                    "user_id": user_id,
                    "accepted": record.get("accepted", False),
                    "accepted_at": record.get("accepted_at"),
                    "version": record.get("version", "v1.0"),
                    "metadata": record.get("metadata", {})
                }
        except Exception as e:
            # Silently fall back to memory store on database error
            pass
    
    # Fallback: gather from memory store
    user_consents = {}
    for (uid, service), data in _consent_store.items():
        if uid == user_id:
            user_consents[service] = data
    
    return user_consents if user_consents else {}


def load_user_consents(user_id: str, access_token: Optional[str] = None) -> None:
    """
    Load all consents for a user from database into memory cache.
    Should be called when a user logs in.
    
    Args:
        user_id (str): The user ID to load consents for.
        access_token (str, optional): User's access token for authenticated requests.
    """
    all_consents = get_all_consents(user_id, access_token)
    
    if all_consents and "metadata" in all_consents:
        # Load each service consent into memory cache
        for service_name, service_data in all_consents["metadata"].items():
            if isinstance(service_data, dict):
                _consent_store[(user_id, service_name)] = {
                    "user_id": user_id,
                    "service_name": service_name,
                    "consent_given": service_data.get("consent_given", False),
                    "consent_timestamp": service_data.get("timestamp", all_consents.get("accepted_at")),
                    "privacy_notice_version": all_consents.get("version", "v1.0"),
                    "privacy_notice": PRIVACY_NOTICE.strip()
                }


def clear_user_consents_cache(user_id: str) -> None:
    """
    Clear all cached consents for a user from memory.
    Should be called when a user logs out.
    
    Args:
        user_id (str): The user ID to clear consents for.
    """
    keys_to_remove = [key for key in _consent_store.keys() if key[0] == user_id]
    for key in keys_to_remove:
        _consent_store.pop(key, None)
