import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Any

# TODO: Uncomment when Supabase DB PR is merged
# from supabase import create_client, Client
# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class ConfigManager:
    def __init__(
        self,
        user_id: Optional[str] = None,
        config_path: str = "src/config/user_config.json",
    ):
        self.user_id = (
            user_id  # Currently unused, will get user id once database is integrated
        )
        self.config_path = Path(
            config_path
        )  # For now uses local json file, will switch to database later
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load configuration from json file or database"""
        if not self.config_path.exists():
            default_config = self._get_default_config()
            self._save_config(default_config)
            return default_config

        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
                return self._ensure_config_defaults(config)
        except json.JSONDecodeError:
            print(f"Error reading config file. Creating default config.")
            default_config = self._get_default_config()
            self._save_config(default_config)
            return default_config

    def _save_config(self, config: Dict) -> None:
        """Save configuration to json file or database"""
        self.config_path.parent.mkdir(
            parents=True, exist_ok=True
        )  # Create user config folder if it doesn't exist yet
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=4)

    def _get_default_config(self) -> Dict:
        """Return an object containing all possible default file configurations the user can select from"""
        return {
            "scan_profiles": {
                "all": {
                    "description": "Scan all supported file types",
                    "extensions": [
                        ".py",
                        ".js",
                        ".html",
                        ".css",
                        ".txt",
                        ".md",
                        ".json",
                    ],
                    "exclude_dirs": ["__pycache__", "node_modules", ".git", "venv"],
                },
                "code_only": {
                    "description": "Scan only code files",
                    "extensions": [".py", ".js", ".java", ".cpp", ".c", ".go", ".rs"],
                    "exclude_dirs": ["__pycache__", "node_modules", ".git", "venv"],
                },
                "python_only": {
                    "description": "Scan only Python files",
                    "extensions": [".py"],
                    "exclude_dirs": ["__pycache__", "venv", ".git"],
                },
                "web_only": {
                    "description": "Scan only web files",
                    "extensions": [".html", ".css", ".js", ".jsx", ".tsx", ".vue"],
                    "exclude_dirs": ["node_modules", ".git"],
                },
                "documents_only": {
                    "description": "Scan only document files",
                    "extensions": [".txt", ".md", ".doc", ".docx", ".pdf"],
                    "exclude_dirs": [".git"],
                },
            },
            "current_profile": "all",
            "max_file_size_mb": 10,
            "follow_symlinks": False,
            "user_preferences": {},
        }

    def _ensure_config_defaults(self, config: Dict) -> Dict:
        """Backfill missing config keys when loading legacy files."""
        updated = False
        if "user_preferences" not in config:
            config["user_preferences"] = {}
            updated = True
        if updated:
            self._save_config(config)
        return config

    def get_current_profile(self) -> str:
        """Get the name of the active config the user is using, default is all"""
        return self.config.get("current_profile", "all")

    def set_current_profile(self, profile_name: str) -> bool:
        """
        Set the active scanning profile

        Args:
            profile_name (str): Name of the profile to set as active

        Returns true if succesful, false if profile doesn't exist


        """
        if profile_name not in self.config["scan_profiles"]:
            print(f"Profile '{profile_name}' not found")
            return False
        self.config["current_profile"] = profile_name
        self._save_config(self.config)
        print(f"Active profile set to '{profile_name}'")
        return True

    def get_allowed_extensions(self, profile_name: Optional[str] = None) -> List[str]:
        """
        Get list of allowed file extensions for a profile.

        Args:
            profile_name: Name of profile (uses current if None)

        Returns:
            List of file extensions
        """
        profile = profile_name or self.get_current_profile()
        return self.config["scan_profiles"].get(profile, {}).get("extensions", [])

    def get_excluded_dirs(self, profile_name: Optional[str] = None) -> List[str]:
        """
        Get list of excluded directories for a profile.

        Args:
            profile_name: Name of profile (uses current if None)

        Returns:
            List of directory names to exclude
        """
        profile = profile_name or self.get_current_profile()
        return self.config["scan_profiles"].get(profile, {}).get("exclude_dirs", [])

    def list_profiles(self) -> None:
        """Display all available scanning profiles"""
        current = self.get_current_profile()
        print("\nAvailable Scan Profiles:")
        print("-" * 50)
        for name, details in self.config["scan_profiles"].items():
            marker = "* " if name == current else "  "
            print(f"{marker}{name}")
            print(f"  Description: {details['description']}")
            print(f"  Extensions: {', '.join(details['extensions'])}")
            print()

    def create_custom_profile(
        self,
        name: str,
        extensions: List[str],
        exclude_dirs: Optional[List[str]] = None,
        description: str = "Custom profile",
    ) -> bool:
        """
        Create a new custom scanning profile.

        Args:
            name: Name for the new profile
            extensions: List of file extensions to include
            exclude_dirs: List of directories to exclude
            description: Description of the profile

        Returns:
            True if successful, False if profile already exists
        """
        if name in self.config["scan_profiles"]:
            print(f"Profile '{name}' already exists. Use update_profile() to modify.")
            return False

        self.config["scan_profiles"][name] = {
            "description": description,
            "extensions": extensions,
            "exclude_dirs": exclude_dirs or [".git", "__pycache__"],
        }

        self._save_config(self.config)
        print(f"Profile '{name}' created successfully!")
        return True

    def update_profile(
        self,
        name: str,
        extensions: Optional[List[str]] = None,
        exclude_dirs: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> bool:
        """
        Update an existing profile.

        Args:
            name: Name of profile to update
            extensions: New list of extensions (optional)
            exclude_dirs: New list of excluded directories (optional)
            description: New description (optional)

        Returns:
            True if successful, False if profile doesn't exist
        """
        if name not in self.config["scan_profiles"]:
            print(f"Profile '{name}' not found.")
            return False

        if extensions is not None:
            self.config["scan_profiles"][name]["extensions"] = extensions
        if exclude_dirs is not None:
            self.config["scan_profiles"][name]["exclude_dirs"] = exclude_dirs
        if description is not None:
            self.config["scan_profiles"][name]["description"] = description

        self._save_config(self.config)
        print(f"Profile '{name}' updated successfully!")
        return True

    def delete_profile(self, name: str) -> bool:
        """
        Delete a scanning profile

        Args:
            Name: Name of profile to delete

        Returns:
            True if successful, False if profile doesn't exist or is active
        """
        if name not in self.config["scan_profiles"]:
            print(f"Profile '{name}' not found.")
            return False
        if name == self.config["current_profile"]:
            print(f"Cannot delete active profile, switch to another first")
            return False

        del self.config["scan_profiles"][name]
        self._save_config(self.config)
        print(f"Profile '{name}' deleted successfully!")
        return True

    def get_config(self) -> Dict:
        """
        Get the complete configuration dictionary

        """
        return self.config

    def get_config_summary(self) -> Dict:
        """
        Get a summary of current configuration settings

        """
        current_profile = self.get_current_profile()
        profile_details = self.config["scan_profiles"][current_profile]

        return {
            "current_profile": current_profile,
            "description": profile_details["description"],
            "extensions": profile_details["extensions"],
            "exclude_dirs": profile_details["exclude_dirs"],
            "max_file_size_mb": self.config.get("max_file_size_mb", 10),
        }

    def get_user_preferences(self) -> Dict[str, Any]:
        """Return all persisted user preferences."""
        return self.config.setdefault("user_preferences", {})

    def get_user_preference(self, key: str, default: Any = None) -> Any:
        """
        Fetch an individual preference.

        Args:
            key: Preference key to read
            default: Value returned when key is absent
        """
        preferences = self.get_user_preferences()
        return preferences.get(key, default)

    def set_user_preference(self, key: str, value: Any) -> None:
        """
        Persist a single preference value.

        Args:
            key: Preference identifier
            value: Preference value to store
        """
        preferences = self.get_user_preferences()
        preferences[key] = value
        self._save_config(self.config)

    def update_user_preferences(self, preferences: Dict[str, Any]) -> None:
        """
        Merge a batch of preferences into the stored configuration.

        Args:
            preferences: Mapping of preference keys to values
        """
        current_preferences = self.get_user_preferences()
        current_preferences.update(preferences)
        self._save_config(self.config)

    def delete_user_preference(self, key: str) -> bool:
        """
        Remove a stored preference if present.

        Args:
            key: Preference identifier

        Returns:
            True when a preference is removed, False if it did not exist
        """
        preferences = self.get_user_preferences()
        if key not in preferences:
            return False
        del preferences[key]
        self._save_config(self.config)
        return True
