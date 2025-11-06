import json
import os
from pathlib import Path
from typing import List, Dict, Optional

from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class ConfigManager:
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
            return result.data  # FIXED: was result.datar
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
                    "extensions": [".py", ".js", ".html", ".css", ".txt", ".md", ".json", ".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".xml", ".yaml", ".yml", ".csv", ".xlsx", ".xls"],
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
        
   