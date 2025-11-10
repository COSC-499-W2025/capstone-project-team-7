"""
Demo script to test consent persistence functionality.

NOTE: This demo tests in-memory consent storage with a test UUID.
To test full database persistence with RLS, you need:
1. A real authenticated user ID from Supabase auth.users
2. A valid access_token from that user's session
3. Pass the access_token to all consent functions

For production usage, see backend/src/cli/app.py for proper integration.
"""

import os
import sys
import uuid
from pathlib import Path

# Add backend/src to path
backend_src = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

from auth import consent
from auth.consent_validator import ConsentValidator


def demo_consent_persistence(access_token: str = None):
    """Demonstrate consent persistence functionality."""
    
    print("=" * 70)
    print("CONSENT PERSISTENCE DEMO")
    print("=" * 70)
    print()
    
    # Check if we have an access token for database persistence
    if access_token:
        print("✓ Access token provided - testing with database persistence")
        consent.set_session_token(access_token)
    else:
        print("⚠ No access token - testing in-memory storage only")
        print("  (To test database persistence, pass a real user's access_token)")
    print()
    
    # Check if Supabase is configured
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    if consent._supabase_client and access_token:
        print("✓ Supabase client is configured and authenticated")
    elif consent._supabase_client:
        print("⚠ Supabase client configured but not authenticated")
    else:
        print("⚠ Supabase client not available - using in-memory fallback")
        if not supabase_url or not supabase_key:
            print("  (Set SUPABASE_URL and SUPABASE_KEY environment variables)")
    print()
    
    # Test user ID (use a valid UUID format)
    test_user_id = str(uuid.uuid4())
    print(f"Test User ID: {test_user_id}")
    print()
    
    print("1. Saving consent for external services...")
    result = consent.save_consent(test_user_id, "external_services", True, access_token)
    print(f"   Status: {result['status']}")
    print(f"   Consent saved: {result['data']['consent_given']}")
    print()
    
    print("2. Saving consent for file analysis...")
    result = consent.save_consent(test_user_id, "file_analysis", True, access_token)
    print(f"   Status: {result['status']}")
    print()
    
    print("3. Retrieving consent for external services...")
    stored_consent = consent.get_consent(test_user_id, "external_services", access_token)
    if stored_consent:
        print(f"   ✓ Consent found!")
        print(f"   Consent given: {stored_consent['consent_given']}")
        print(f"   Timestamp: {stored_consent['consent_timestamp']}")
    else:
        print("   ✗ Consent not found")
    print()
    
    print("4. Getting all consents for user...")
    all_consents = consent.get_all_consents(test_user_id, access_token)
    if all_consents:
        print(f"   ✓ Found consents!")
        if "metadata" in all_consents:
            print(f"   Services: {list(all_consents['metadata'].keys())}")
        print(f"   Accepted: {all_consents.get('accepted', False)}")
    else:
        print("   No consents found")
    print()
    
    print("5. Testing ConsentValidator with persistence...")
    validator = ConsentValidator(use_consent_storage=True)
    
    consent_data = {
        "analyze_uploaded_only": True,
        "process_store_metadata": True,
        "privacy_ack": True,
        "allow_external_services": True
    }
    
    try:
        # Note: ConsentValidator doesn't pass access_token yet, so this will use in-memory only
        record = validator.validate_upload_consent(test_user_id, consent_data)
        print(f"   ✓ Consent validated and stored!")
        print(f"   User ID: {record.user_id}")
        print(f"   External services allowed: {record.allow_external_services}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    print()
    
    print("6. Simulating user logout (clearing cache)...")
    consent.clear_user_consents_cache(test_user_id)
    consent.clear_session_token()
    print("   ✓ Cache cleared")
    print()
    
    print("7. Simulating user login (loading consents)...")
    if access_token:
        consent.set_session_token(access_token)
        consent.load_user_consents(test_user_id, access_token)
        print("   ✓ Consents loaded from database")
    else:
        print("   ⚠ Skipped - no access token for database operations")
    print()
    
    print("8. Verifying consents persisted across 'sessions'...")
    file_consent = consent.get_consent(test_user_id, "file_analysis", access_token)
    external_consent = consent.get_consent(test_user_id, "external_services", access_token)
    
    if file_consent and external_consent:
        print("   ✓ Consents successfully persisted!")
        print(f"   File analysis: {file_consent['consent_given']}")
        print(f"   External services: {external_consent['consent_given']}")
    else:
        if access_token:
            print("   ⚠ Some consents not found after reload")
        else:
            print("   ⚠ Consents not persisted (no database access without token)")
    print()
    
    print("9. Testing consent withdrawal...")
    consent.withdraw_consent(test_user_id, "external_services", access_token)
    print("   ✓ External services consent withdrawn")
    
    withdrawn_consent = consent.get_consent(test_user_id, "external_services", access_token)
    if withdrawn_consent:
        print(f"   Consent still exists (should be False): {withdrawn_consent.get('consent_given', False)}")
    else:
        print("   Consent removed from storage")
    print()
    
    print("=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print()
    
    if consent._supabase_client and access_token:
        print("✓ All operations completed with database persistence")
    elif consent._supabase_client:
        print("⚠ Operations completed with in-memory storage only")
        print("  (Database persistence requires a valid access_token)")
    else:
        print("⚠ Operations completed with in-memory fallback only")
        print("  Configure Supabase to test full persistence")


if __name__ == "__main__":
    # To test with database persistence, pass a real user's access token:
    # demo_consent_persistence(access_token="your_real_access_token_here")
    
    # Run without token for in-memory demo:
    demo_consent_persistence()
