"""
Simple ConfigManager Tests
===========================
Run with: pytest test_config.py -v
"""

import pytest
import time
import random
import string
from dotenv import load_dotenv
import os
from supabase import create_client
import sys
from pathlib import Path

# Import your ConfigManager
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src" / "config"))

from config_manager import ConfigManager

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


@pytest.fixture(scope="module")
def test_user():
    """Create a test user for all tests"""
    print("\n🔧 Creating test user...")
    
    # Generate unique email
    timestamp = int(time.time())
    random_str = ''.join(random.choices(string.ascii_lowercase, k=6))
    test_email = "alexG38@outlook.com"
    test_password = "TestPassword123!"
    
    # Sign up
    user_response = supabase.auth.sign_up({
        "email": test_email,
        "password": test_password,
        "options": {"data": {"full_name": "Test User"}}
    })
    
    user_id = user_response.user.id
    
    # Sign in
    supabase.auth.sign_in_with_password({
        "email": test_email,
        "password": test_password
    })
    
    # Create profile
    supabase.table("profiles").insert({
        "id": user_id,
        "email": test_email,
        "full_name": "Test User"
    }).execute()
    
    # Create config
    supabase.table("user_configs").insert({
        "owner": user_id
    }).execute()
    
    print(f"✅ Test user created: {test_email}")
    
    yield user_id
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    supabase.table("user_configs").delete().eq("owner", user_id).execute()
    supabase.table("profiles").delete().eq("id", user_id).execute()


def test_config_loads_successfully(test_user):
    """Test 1: Config manager initializes and loads config"""
    config = ConfigManager(test_user)
    
    assert config is not None
    assert config.user_id == test_user
    assert config.config is not None
    assert "scan_profiles" in config.config


# def test_switch_profile(test_user):
#     """Test 2: Can switch between profiles"""
#     config = ConfigManager(test_user)
    
#     # Switch to python_only
#     result = config.set_current_profile("python_only")
#     assert result is True
#     assert config.get_current_profile() == "python_only"
    
#     # Get extensions for python profile
#     extensions = config.get_allowed_extensions()
#     assert extensions == [".py"]


# def test_create_custom_profile(test_user):
#     """Test 3: Can create a custom profile"""
#     config = ConfigManager(test_user)
    
#     # Create rust profile
#     result = config.create_custom_profile(
#         name="rust_only",
#         extensions=[".rs", ".toml"],
#         exclude_dirs=["target"],
#         description="Rust files only"
#     )
    
#     assert result is True
    
#     # Verify it exists
#     extensions = config.get_allowed_extensions("rust_only")
#     assert ".rs" in extensions
#     assert ".toml" in extensions


# def test_update_profile(test_user):
#     """Test 4: Can update an existing profile"""
#     config = ConfigManager(test_user)
    
#     # Create a profile
#     config.create_custom_profile("test_profile", [".txt"])
    
#     # Update it
#     result = config.update_profile(
#         "test_profile",
#         extensions=[".txt", ".md"],
#         description="Updated description"
#     )
    
#     assert result is True
    
#     # Verify update
#     extensions = config.get_allowed_extensions("test_profile")
#     assert ".md" in extensions


# def test_update_settings(test_user):
#     """Test 5: Can update general settings"""
#     config = ConfigManager(test_user)
    
#     # Update settings
#     result = config.update_settings(
#         max_file_size_mb=50,
#         follow_symlinks=True
#     )
    
#     assert result is True
    
#     # Verify
#     summary = config.get_config_summary()
#     assert summary["max_file_size_mb"] == 50
#     assert summary["follow_symlinks"] is True


# def test_delete_profile(test_user):
#     """Test 6: Can delete a custom profile"""
#     config = ConfigManager(test_user)
    
#     # Create profile
#     config.create_custom_profile("to_delete", [".tmp"])
    
#     # Delete it
#     result = config.delete_profile("to_delete")
#     assert result is True
    
#     # Verify it's gone
#     assert "to_delete" not in config.config["scan_profiles"]








