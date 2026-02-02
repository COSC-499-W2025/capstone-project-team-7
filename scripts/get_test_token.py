#!/usr/bin/env python3
"""
Script to get a test access token for frontend development.
This creates a test user in Supabase and returns their access token.
"""
import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from supabase import create_client, Client

def get_test_token():
    """Get or create a test user and return their access token."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        sys.exit(1)
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    # Test credentials
    test_email = "FILL_IN_TEST_EMAIL_HERE"
    test_password = "FILL_IN_TEST_PASSWORD_HERE"
    
    print("🔐 Attempting to authenticate test user...")
    print(f"   Email: {test_email}")
    
    try:
        # Try to sign in with existing user
        response = supabase.auth.sign_in_with_password({
            "email": test_email,
            "password": test_password
        })
        
        access_token = response.session.access_token
        user_id = response.user.id
        
        print(f"✅ Successfully authenticated!")
        print(f"   User ID: {user_id}")
        print(f"\n📋 Your Access Token:\n")
        print(f"{access_token}\n")
        print("📌 Copy this token and paste it into the Login dialog in the Settings page.")
        print("   The token will be stored in localStorage and used for all API calls.\n")
        
        return access_token
        
    except Exception as e:
        error_msg = str(e)
        
        # If user doesn't exist, try to create one
        if "Invalid login credentials" in error_msg or "User not found" in error_msg:
            print("⚠️  Test user doesn't exist. Creating new test user...")
            
            try:
                response = supabase.auth.sign_up({
                    "email": test_email,
                    "password": test_password
                })
                
                if response.session:
                    access_token = response.session.access_token
                    user_id = response.user.id
                    
                    print(f"✅ Successfully created and authenticated test user!")
                    print(f"   User ID: {user_id}")
                    print(f"\n📋 Your Access Token:\n")
                    print(f"{access_token}\n")
                    print("📌 Copy this token and paste it into the Login dialog in the Settings page.")
                    print("   The token will be stored in localStorage and used for all API calls.\n")
                    
                    return access_token
                else:
                    print("⚠️  User created but email confirmation may be required.")
                    print("   Check your Supabase dashboard to confirm the user or disable email confirmation.")
                    sys.exit(1)
                    
            except Exception as create_error:
                print(f"❌ Error creating test user: {create_error}")
                sys.exit(1)
        else:
            print(f"❌ Authentication error: {error_msg}")
            sys.exit(1)

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  TEST TOKEN GENERATOR FOR SETTINGS PAGE")
    print("="*70 + "\n")
    
    get_test_token()
    
    print("="*70)
    print("  NEXT STEPS:")
    print("="*70)
    print("1. Make sure the FastAPI backend is running:")
    print("   cd backend")
    print("   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000")
    print()
    print("2. Make sure the Next.js frontend is running:")
    print("   cd frontend")
    print("   npm run dev")
    print()
    print("3. Open http://localhost:3000/settings in your browser")
    print("4. Click the 'Login' button")
    print("5. Paste the access token above into the dialog")
    print("6. You should now be able to test consent and config management!")
    print("="*70 + "\n")
