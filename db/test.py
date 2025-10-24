"""
User Config Database Helper - UPDATED
======================================
Now creates profiles and configs manually (doesn't rely on triggers!)
"""

from supabase import create_client, Client
from dotenv import load_dotenv
import os
import json
import time
import random
import string

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class DatabaseConfigManager:
    """
    Database-backed version of ConfigManager
    Works with the user_configs table in Supabase
    """
    
    def __init__(self, user_id: str):
        """
        Initialize with a user ID
        
        Args:
            user_id: UUID of the user from profiles table
        """
        self.user_id = user_id
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """Load user config from database"""
        try:
            result = supabase.table("user_configs").select("*").eq("owner", self.user_id).single().execute()
            return result.data
        except Exception as e:
            print(f"Error loading config: {e}")
            print("Config should have been auto-created. Trying to create manually...")
            config = self._create_default_config()
            
            if config is None:
                # Return a default structure to prevent crashes
                print("⚠️  Using in-memory default config (not saved to database)")
                return self._get_default_structure()
            
            return config
    
    def _get_default_structure(self) -> dict:
        """Get default config structure without saving to DB"""
        return {
            "scan_profiles": {
                "all": {
                    "description": "Scan all supported file types",
                    "extensions": [".py", ".js", ".html", ".css", ".txt", ".md", ".json"],
                    "exclude_dirs": ["__pycache__", "node_modules", ".git", "venv"]
                },
                "code_only": {
                    "description": "Scan only code files",
                    "extensions": [".py", ".js", ".java", ".cpp", ".c", ".go", ".rs"],
                    "exclude_dirs": ["__pycache__", "node_modules", ".git", "venv"]
                },
                "python_only": {
                    "description": "Scan only Python files",
                    "extensions": [".py"],
                    "exclude_dirs": ["__pycache__", "venv", ".git"]
                },
                "web_only": {
                    "description": "Scan only web files",
                    "extensions": [".html", ".css", ".js", ".jsx", ".tsx", ".vue"],
                    "exclude_dirs": ["node_modules", ".git"]
                },
                "documents_only": {
                    "description": "Scan only document files",
                    "extensions": [".txt", ".md", ".doc", ".docx", ".pdf"],
                    "exclude_dirs": [".git"]
                }
            },
            "current_profile": "all",
            "max_file_size_mb": 10,
            "follow_symlinks": False
        }
    
    def _create_default_config(self) -> dict:
        """Create default config for user"""
        try:
            result = supabase.table("user_configs").insert({
                "owner": self.user_id
            }).execute()
            
            if result.data:
                print("✅ Config created successfully!")
                return result.data[0]
            else:
                print("❌ Config creation returned no data")
                return None
                
        except Exception as e:
            print(f"Error creating config: {e}")
            
            if "policy" in str(e).lower() or "42501" in str(e):
                print("\n💡 RLS Policy Error!")
                print("   This means you're not signed in as the user.")
                print("   The user needs to sign in first before accessing their config.")
            
            return None
    
    def get_current_profile(self) -> str:
        """Get the name of the active profile"""
        return self.config.get("current_profile", "all")
    
    def set_current_profile(self, profile_name: str) -> bool:
        """
        Set the active scanning profile
        
        Args:
            profile_name: Name of the profile to set as active
            
        Returns:
            True if successful, False if profile doesn't exist
        """
        scan_profiles = self.config.get("scan_profiles", {})
        
        if profile_name not in scan_profiles:
            print(f"Profile '{profile_name}' not found")
            return False
        
        try:
            result = supabase.table("user_configs").update({
                "current_profile": profile_name
            }).eq("owner", self.user_id).execute()
            
            self.config["current_profile"] = profile_name
            print(f"Active profile set to '{profile_name}'")
            return True
        except Exception as e:
            print(f"Error updating profile: {e}")
            return False
    
    def get_allowed_extensions(self, profile_name: str = None) -> list:
        """
        Get list of allowed file extensions for a profile
        
        Args:
            profile_name: Name of profile (uses current if None)
            
        Returns:
            List of file extensions
        """
        profile = profile_name or self.get_current_profile()
        scan_profiles = self.config.get("scan_profiles", {})
        return scan_profiles.get(profile, {}).get("extensions", [])
    
    def get_excluded_dirs(self, profile_name: str = None) -> list:
        """
        Get list of excluded directories for a profile
        
        Args:
            profile_name: Name of profile (uses current if None)
            
        Returns:
            List of directory names to exclude
        """
        profile = profile_name or self.get_current_profile()
        scan_profiles = self.config.get("scan_profiles", {})
        return scan_profiles.get(profile, {}).get("exclude_dirs", [])
    
    def list_profiles(self) -> None:
        """Display all available scanning profiles"""
        current = self.get_current_profile()
        scan_profiles = self.config.get("scan_profiles", {})
        
        print("\nAvailable Scan Profiles:")
        print("-" * 50)
        for name, details in scan_profiles.items():
            marker = "* " if name == current else "  "
            print(f"{marker}{name}")
            print(f"  Description: {details['description']}")
            print(f"  Extensions: {', '.join(details['extensions'])}")
            print()
    
    def create_custom_profile(
        self,
        name: str,
        extensions: list,
        exclude_dirs: list = None,
        description: str = "Custom profile"
    ) -> bool:
        """
        Create a new custom scanning profile
        
        Args:
            name: Name for the new profile
            extensions: List of file extensions to include
            exclude_dirs: List of directories to exclude
            description: Description of the profile
            
        Returns:
            True if successful, False if profile already exists
        """
        scan_profiles = self.config.get("scan_profiles", {})
        
        if name in scan_profiles:
            print(f"Profile '{name}' already exists. Use update_profile() to modify.")
            return False
        
        scan_profiles[name] = {
            "description": description,
            "extensions": extensions,
            "exclude_dirs": exclude_dirs or [".git", "__pycache__"]
        }
        
        try:
            result = supabase.table("user_configs").update({
                "scan_profiles": scan_profiles
            }).eq("owner", self.user_id).execute()
            
            self.config["scan_profiles"] = scan_profiles
            print(f"Profile '{name}' created successfully!")
            return True
        except Exception as e:
            print(f"Error creating profile: {e}")
            return False
    
    def update_profile(
        self,
        name: str,
        extensions: list = None,
        exclude_dirs: list = None,
        description: str = None
    ) -> bool:
        """
        Update an existing profile
        
        Args:
            name: Name of profile to update
            extensions: New list of extensions (optional)
            exclude_dirs: New list of excluded directories (optional)
            description: New description (optional)
            
        Returns:
            True if successful, False if profile doesn't exist
        """
        scan_profiles = self.config.get("scan_profiles", {})
        
        if name not in scan_profiles:
            print(f"Profile '{name}' not found.")
            return False
        
        if extensions is not None:
            scan_profiles[name]["extensions"] = extensions
        if exclude_dirs is not None:
            scan_profiles[name]["exclude_dirs"] = exclude_dirs
        if description is not None:
            scan_profiles[name]["description"] = description
        
        try:
            result = supabase.table("user_configs").update({
                "scan_profiles": scan_profiles
            }).eq("owner", self.user_id).execute()
            
            self.config["scan_profiles"] = scan_profiles
            print(f"Profile '{name}' updated successfully!")
            return True
        except Exception as e:
            print(f"Error updating profile: {e}")
            return False
    
    def delete_profile(self, name: str) -> bool:
        """
        Delete a scanning profile
        
        Args:
            name: Name of profile to delete
            
        Returns:
            True if successful, False if profile doesn't exist or is active
        """
        scan_profiles = self.config.get("scan_profiles", {})
        
        if name not in scan_profiles:
            print(f"Profile '{name}' not found.")
            return False
        
        if name == self.config.get("current_profile"):
            print(f"Cannot delete active profile. Switch to another profile first.")
            return False
        
        del scan_profiles[name]
        
        try:
            result = supabase.table("user_configs").update({
                "scan_profiles": scan_profiles
            }).eq("owner", self.user_id).execute()
            
            self.config["scan_profiles"] = scan_profiles
            print(f"Profile '{name}' deleted successfully!")
            return True
        except Exception as e:
            print(f"Error deleting profile: {e}")
            return False
    
    def get_config_summary(self) -> dict:
        """Get a summary of current configuration settings"""
        current_profile = self.get_current_profile()
        scan_profiles = self.config.get("scan_profiles", {})
        profile_details = scan_profiles.get(current_profile, {})
        
        return {
            "current_profile": current_profile,
            "description": profile_details.get("description", ""),
            "extensions": profile_details.get("extensions", []),
            "exclude_dirs": profile_details.get("exclude_dirs", []),
            "max_file_size_mb": self.config.get("max_file_size_mb", 10),
            "follow_symlinks": self.config.get("follow_symlinks", False)
        }
    
    def update_settings(
        self,
        max_file_size_mb: int = None,
        follow_symlinks: bool = None
    ) -> bool:
        """
        Update general settings
        
        Args:
            max_file_size_mb: Maximum file size in MB
            follow_symlinks: Whether to follow symbolic links
            
        Returns:
            True if successful
        """
        updates = {}
        
        if max_file_size_mb is not None:
            updates["max_file_size_mb"] = max_file_size_mb
        if follow_symlinks is not None:
            updates["follow_symlinks"] = follow_symlinks
        
        if not updates:
            print("No settings to update")
            return False
        
        try:
            result = supabase.table("user_configs").update(updates).eq("owner", self.user_id).execute()
            
            for key, value in updates.items():
                self.config[key] = value
            
            print("Settings updated successfully!")
            return True
        except Exception as e:
            print(f"Error updating settings: {e}")
            return False


# === TESTING FUNCTIONS ===

def test_config_manager(user_id: str):
    """
    Test the DatabaseConfigManager with a user ID
    
    Args:
        user_id: UUID of a user from profiles table
    """
    print("="*70)
    print("🧪 TESTING DATABASE CONFIG MANAGER")
    print("="*70)
    
    print(f"\nTesting with user ID: {user_id}")
    
    # Initialize
    print("\n1️⃣ Initializing config manager...")
    config_mgr = DatabaseConfigManager(user_id)
    
    # Show current config
    print("\n2️⃣ Current configuration:")
    summary = config_mgr.get_config_summary()
    print(f"   Active profile: {summary['current_profile']}")
    print(f"   Extensions: {summary['extensions']}")
    print(f"   Max file size: {summary['max_file_size_mb']} MB")
    
    # List profiles
    print("\n3️⃣ Available profiles:")
    config_mgr.list_profiles()
    
    # Switch profile
    print("\n4️⃣ Switching to 'python_only' profile...")
    config_mgr.set_current_profile("python_only")
    summary = config_mgr.get_config_summary()
    print(f"   New extensions: {summary['extensions']}")
    
    # Create custom profile
    print("\n5️⃣ Creating custom 'typescript_only' profile...")
    config_mgr.create_custom_profile(
        name="typescript_only",
        extensions=[".ts", ".tsx"],
        exclude_dirs=["node_modules", ".git", "dist"],
        description="Scan only TypeScript files"
    )
    
    # Switch to custom profile
    print("\n6️⃣ Switching to custom profile...")
    config_mgr.set_current_profile("typescript_only")
    
    # Update settings
    print("\n7️⃣ Updating general settings...")
    config_mgr.update_settings(max_file_size_mb=20, follow_symlinks=True)
    
    # Final summary
    print("\n8️⃣ Final configuration:")
    summary = config_mgr.get_config_summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    
    print("\n" + "="*70)
    print("✅ All tests completed!")
    print("="*70)


def get_or_create_test_user():
    """Get existing user or create a test user"""
    try:
        # Try to find existing user
        result = supabase.table("profiles").select("id, email").limit(1).execute()
        if result.data:
            user_id = result.data[0]['id']
            email = result.data[0].get('email', 'Unknown')
            print(f"\n✅ Found existing user: {email}")
            print(f"   User ID: {user_id}")
            return user_id
        else:
            # No users found, create one
            print("\n📝 No users found. Creating test user...")
            return create_test_user()
    except Exception as e:
        print(f"❌ Error fetching user: {e}")
        print("\n📝 Attempting to create test user...")
        return create_test_user()


def create_test_user():
    """Create a test user for testing configs"""
    
    print("\n" + "="*70)
    print("🔧 CREATING TEST USER")
    print("="*70)
    
    # Generate unique email
    timestamp = int(time.time())
    random_str = ''.join(random.choices(string.ascii_lowercase, k=6))
    test_email = "oms@gmail.com"
    test_password = "TestPassword123!"
    
    print(f"\nGenerating test user:")
    print(f"   Email: {test_email}")
    print(f"   Password: {test_password}")
    
    try:
        # Create user via Supabase Auth
        print("\n1️⃣ Creating auth user...")
        user_response = supabase.auth.sign_up({
            "email": test_email,
            "password": test_password,
            "options": {
                "data": {
                    "full_name": "Config Test User"
                }
            }
        })
        
        if user_response.user:
            user_id = user_response.user.id
            print(f"✅ User created!")
            print(f"   User ID: {user_id}")
            
            # IMPORTANT: Sign in as the user to set auth.uid() for RLS policies
            print("\n2️⃣ Signing in as the new user...")
            time.sleep(2)  # Wait a moment for auth to process
            
            try:
                sign_in_response = supabase.auth.sign_in_with_password({
                    "email": test_email,
                    "password": test_password
                })
                
                if sign_in_response.user:
                    print(f"✅ Signed in successfully!")
                else:
                    print(f"⚠️  Sign-in returned no user (email confirmation may be required)")
                    
            except Exception as e:
                if "email not confirmed" in str(e).lower() or "confirm" in str(e).lower():
                    print(f"⚠️  Email confirmation required")
                    print(f"   To fix: Supabase Dashboard > Authentication > Providers > Email")
                    print(f"   Disable 'Confirm email' for testing")
                    print(f"   For now, continuing without sign-in...")
                else:
                    print(f"⚠️  Sign-in error: {e}")
            
            # ===================================================================
            # MANUALLY CREATE PROFILE (Don't rely on trigger!)
            # ===================================================================
            print("\n3️⃣ Creating profile manually...")
            
            try:
                profile_result = supabase.table("profiles").insert({
                    "id": user_id,
                    "email": user_response.user.email,
                    "full_name": user_response.user.user_metadata.get("full_name", "Config Test User")
                }).execute()
                
                if profile_result.data:
                    print(f"✅ Profile created!")
                    print(f"   Email: {profile_result.data[0].get('email')}")
                    print(f"   Name: {profile_result.data[0].get('full_name')}")
                else:
                    print(f"⚠️  Profile creation returned no data")
                    # Check if it exists anyway (trigger may have created it)
                    existing = supabase.table("profiles").select("*").eq("id", user_id).execute()
                    if existing.data:
                        print(f"✅ Profile already exists (created by trigger)")
                    else:
                        print(f"❌ Profile doesn't exist! This will cause config creation to fail!")
                        return None
                    
            except Exception as profile_error:
                if "duplicate" in str(profile_error).lower() or "unique" in str(profile_error).lower():
                    print(f"✅ Profile already exists (created by trigger)")
                else:
                    print(f"❌ Error creating profile: {profile_error}")
                    print(f"   This will cause config creation to fail!")
                    return None
            
            # ===================================================================
            # MANUALLY CREATE CONFIG (Don't rely on trigger!)
            # ===================================================================
            print("\n4️⃣ Creating config manually...")
            time.sleep(1)  # Brief pause to ensure profile is committed
            
            try:
                config_result = supabase.table("user_configs").insert({
                    "owner": user_id
                }).execute()
                
                if config_result.data:
                    print(f"✅ Config created!")
                    print(f"   Current profile: {config_result.data[0].get('current_profile')}")
                    print(f"   Profiles available: {len(config_result.data[0].get('scan_profiles', {}))}")
                else:
                    print(f"⚠️  Config creation returned no data")
                    # Check if it exists anyway (trigger may have created it)
                    existing = supabase.table("user_configs").select("*").eq("owner", user_id).execute()
                    if existing.data:
                        print(f"✅ Config already exists (created by trigger)")
                    else:
                        print(f"⚠️  Config doesn't exist, will be created on first access")
                    
            except Exception as config_error:
                if "duplicate" in str(config_error).lower() or "unique" in str(config_error).lower():
                    print(f"✅ Config already exists (created by trigger)")
                elif "foreign key" in str(config_error).lower() or "23503" in str(config_error):
                    print(f"❌ Config creation failed: Profile doesn't exist!")
                    print(f"   Error: {config_error}")
                    print(f"   This means the profile creation above failed.")
                    return None
                else:
                    print(f"⚠️  Error creating config: {config_error}")
                    print(f"   Config will be created on first access if needed")
            
            print("\n" + "="*70)
            print("✅ Test user ready!")
            print("="*70)
            print(f"\n💡 User credentials:")
            print(f"   Email: {test_email}")
            print(f"   Password: {test_password}")
            print(f"   User ID: {user_id}")
            
            return user_id
        else:
            print("❌ User creation failed")
            return None
            
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        
        if "email" in str(e).lower() and "confirm" in str(e).lower():
            print("\n💡 Email confirmation is required!")
            print("   To fix: Supabase Dashboard > Authentication > Providers > Email")
            print("   Disable 'Confirm email' for testing")
        
        return None


if __name__ == "__main__":
    print("\n" + "="*70)
    print("USER CONFIG DATABASE HELPER & TESTER")
    print("="*70)
    
    # Get or create a user ID to test with
    user_id = get_or_create_test_user()
    
    if user_id:
        print("\n🚀 Starting config tests...")
        test_config_manager(user_id)
    else:
        print("\n❌ Cannot test without a user ID")
        print("\n💡 Troubleshooting:")
        print("   1. Make sure migrations ran successfully")
        print("   2. Check email confirmation settings in Supabase")
        print("   3. Check the error messages above for details")