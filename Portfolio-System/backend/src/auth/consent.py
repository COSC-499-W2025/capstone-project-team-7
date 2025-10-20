# auth/consent.py

# Module Purpose:
#   - Manage user consent for external services (e.g., LLMs, APIs).
#   - Show a privacy notice to inform users about risks & data handling.
#   - Save consent decisions in an in-memory store (mock database).
#   - Enforce blocking of external calls unless consent is granted.

# Future Extension:
#   - Replace in-memory store with a real database (e.g., Supabase).
#   - Add API endpoints for request/submit/withdraw consent
import datetime

# In-memory store for consent records
# Keys   → (user_id, service_name)
# Values → dict with consent info (decision, timestamp, privacy notice, etc.)
_consent_store = {}

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

def save_consent(user_id: str, service_name: str, consent_given: bool):
    """
    Save or update the user's consent decision.

    Args:
        user_id (str): The user making the decision.
        service_name (str): The service requiring consent.
        consent_given (bool): True if the user agreed, False if declined.

    Returns:
        dict: Confirmation with stored data.
    """
    data = {
        "user_id": user_id,
        "service_name": service_name,
        "consent_given": consent_given,
        "consent_timestamp": datetime.datetime.utcnow().isoformat(),
        "privacy_notice_version": "v1.0",
        "privacy_notice": PRIVACY_NOTICE.strip()
    }
    _consent_store[(user_id, service_name)] = data
    return {"status": "success", "data": data}

# Retrieve consent

def get_consent(user_id: str, service_name: str):
    """
    Retrieve the consent record for a given user and service.

    Args:
        user_id (str): User ID to look up.
        service_name (str): Service name to check.

    Returns:
        dict | None: The stored consent record, or None if not found.
    """
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

def withdraw_consent(user_id: str, service_name: str):
    """
    Remove a user's consent record (as if they withdrew consent).

    Args:
        user_id (str): The user ID to clear.
        service_name (str): The service name to clear.

    Returns:
        None
    """
    _consent_store.pop((user_id, service_name), None)
