from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Dict, Optional, Tuple

from scanner.models import ScanPreferences
from scanner.preferences import normalize_extensions
from .config_api_service import ConfigAPIService, ConfigAPIServiceError


ConfigManagerFactory = Callable[[str], object]


class PreferencesService:
    """Encapsulates Supabase-backed preferences loading and mutation."""

    def __init__(
        self,
        *,
        media_extensions: Tuple[str, ...],
        manager_factory: Optional[ConfigManagerFactory] = None,
        api_service: Optional[ConfigAPIService] = None,
    ) -> None:
        self._media_extensions = media_extensions
        self._manager_factory = manager_factory
        self._api_service = api_service
        self._fallback_structure = {
            "scan_profiles": {
                "sample": {
                    "description": "Scan common code and doc file types.",
                    "extensions": [".py", ".md", ".json", ".txt", ".pdf", ".doc", ".docx"],
                    "exclude_dirs": ["__pycache__", "node_modules", ".git"],
                }
            },
            "max_file_size_mb": 10,
            "follow_symlinks": False,
        }

    def default_structure(self) -> Dict[str, Any]:
        return deepcopy(self._fallback_structure)

    def load_preferences(
        self,
        user_id: str,
        *,
        access_token: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]], Dict[str, Any], Optional[str]]:
        """Return (summary, profiles, raw_config, error)."""
        if not user_id:
            fallback = self.default_structure()
            summary = self._fallback_summary(fallback)
            return summary, fallback["scan_profiles"], fallback, None

        if self._api_service:
            try:
                config = self._api_service.get_config(user_id, access_token=access_token)
            except Exception as exc:
                fallback = self.default_structure()
                summary = self._fallback_summary(fallback)
                return summary, fallback["scan_profiles"], fallback, str(exc)
            summary = self._summary_from_config(config)
            profiles = config.get("scan_profiles") or {}
            return summary, profiles, config, None

        try:
            manager = self._get_manager(user_id)
        except Exception as exc:  # pragma: no cover - import or init failure
            fallback = self.default_structure()
            summary = self._fallback_summary(fallback)
            return summary, fallback["scan_profiles"], fallback, str(exc)

        config = getattr(manager, "config", {}) or {}
        summary = getattr(manager, "get_config_summary", lambda: None)() or self._summary_from_config(config)
        profiles = config.get("scan_profiles") or {}
        return summary, profiles, config, None

    def execute_action(
        self,
        user_id: str,
        action: str,
        payload: Dict[str, Any],
        *,
        access_token: Optional[str] = None,
    ) -> Tuple[bool, str]:
        if not user_id:
            return False, "No active session."
        if self._api_service:
            return self._execute_action_api(user_id, action, payload, access_token)
        try:
            manager = self._get_manager(user_id)
        except Exception as exc:  # pragma: no cover - import or init failure
            return False, f"Unable to load preferences: {exc}"

        try:
            if action == "set_active":
                name = payload.get("name")
                if not name:
                    return False, "Profile name missing."
                if not manager.set_current_profile(name):
                    return False, f"Failed to activate profile '{name}'."
                return True, f"Active profile set to {name}."

            if action == "delete_profile":
                name = payload.get("name")
                if not name:
                    return False, "Profile name missing."
                if not manager.delete_profile(name):
                    return False, f"Unable to delete profile '{name}'."
                return True, f"Profile {name} deleted."

            if action == "create_profile":
                name = payload.get("name")
                extensions = payload.get("extensions", [])
                exclude_dirs = payload.get("exclude_dirs", [])
                description = payload.get("description", "Custom profile")
                if not manager.create_custom_profile(name, extensions, exclude_dirs, description):
                    return False, f"Unable to create profile '{name}'."
                return True, f"Profile {name} created."

            if action == "update_profile":
                name = payload.get("name")
                extensions = payload.get("extensions", [])
                exclude_dirs = payload.get("exclude_dirs", [])
                description = payload.get("description")
                if not manager.update_profile(
                    name,
                    extensions=extensions,
                    exclude_dirs=exclude_dirs,
                    description=description,
                ):
                    return False, f"Unable to update profile '{name}'."
                return True, f"Profile {name} updated."

            if action == "update_settings":
                max_size = payload.get("max_file_size_mb")
                follow_symlinks = payload.get("follow_symlinks")
                updates: Dict[str, Any] = {}
                if max_size is not None:
                    updates["max_file_size_mb"] = max_size
                if follow_symlinks is not None:
                    updates["follow_symlinks"] = bool(follow_symlinks)
                if not updates:
                    return False, "No settings to update."
                if not manager.update_settings(
                    max_file_size_mb=updates.get("max_file_size_mb"),
                    follow_symlinks=updates.get("follow_symlinks"),
                ):
                    return False, "Unable to update settings."
                return True, "Settings updated."
        except Exception as exc:  # pragma: no cover - defensive fallback
            return False, str(exc)

        return False, "Unknown preferences action."

    def _execute_action_api(
        self,
        user_id: str,
        action: str,
        payload: Dict[str, Any],
        access_token: Optional[str],
    ) -> Tuple[bool, str]:
        try:
            if action == "set_active":
                name = payload.get("name")
                if not name:
                    return False, "Profile name missing."
                self._api_service.update_config(
                    user_id,
                    access_token=access_token,
                    current_profile=name,
                )
                return True, f"Active profile set to {name}."

            if action == "delete_profile":
                name = payload.get("name")
                if not name:
                    return False, "Profile name missing."
                self._api_service.delete_profile(
                    user_id,
                    name,
                    access_token=access_token,
                )
                return True, f"Profile {name} deleted."

            if action in {"create_profile", "update_profile"}:
                name = payload.get("name")
                if not name:
                    return False, "Profile name missing."
                self._api_service.save_profile(
                    user_id,
                    name,
                    access_token=access_token,
                    extensions=payload.get("extensions", []),
                    exclude_dirs=payload.get("exclude_dirs", []),
                    description=payload.get("description") or "Custom profile",
                )
                message = "Profile created." if action == "create_profile" else "Profile updated."
                return True, message

            if action == "update_settings":
                max_size = payload.get("max_file_size_mb")
                follow_symlinks = payload.get("follow_symlinks")
                if max_size is None and follow_symlinks is None:
                    return False, "No settings to update."
                self._api_service.update_config(
                    user_id,
                    access_token=access_token,
                    max_file_size_mb=max_size,
                    follow_symlinks=follow_symlinks,
                )
                return True, "Settings updated."
        except ConfigAPIServiceError as exc:
            return False, str(exc)
        except Exception as exc:  # pragma: no cover - defensive fallback
            return False, str(exc)

        return False, "Unknown preferences action."

    def preferences_from_config(
        self,
        config: Dict[str, Any],
        profile_name: Optional[str],
    ) -> ScanPreferences:
        if not config:
            return ScanPreferences()

        scan_profiles = config.get("scan_profiles", {}) or {}
        profile_key = profile_name or config.get("current_profile")
        profile = scan_profiles.get(profile_key, {}) if isinstance(scan_profiles, dict) else {}

        extensions = profile.get("extensions") or None
        if extensions:
            normalized = normalize_extensions(extensions)
            if normalized:
                seen = set(normalized)
                if profile_key == "all":
                    for media_ext in self._media_extensions:
                        if media_ext not in seen:
                            seen.add(media_ext)
                            normalized.append(media_ext)
                extensions = normalized
            else:
                extensions = None

        excluded_dirs = profile.get("exclude_dirs") or None
        max_file_size_mb = config.get("max_file_size_mb")
        max_file_size_bytes = (
            int(max_file_size_mb * 1024 * 1024)
            if isinstance(max_file_size_mb, (int, float))
            else None
        )
        follow_symlinks = config.get("follow_symlinks")

        return ScanPreferences(
            allowed_extensions=extensions,
            excluded_dirs=excluded_dirs,
            max_file_size_bytes=max_file_size_bytes,
            follow_symlinks=follow_symlinks,
        )

    def _get_manager(self, user_id: str):
        if self._manager_factory:
            return self._manager_factory(user_id)
        from ...config.config_manager import ConfigManager  # pragma: no cover - imported lazily

        return ConfigManager(user_id)

    def _fallback_summary(self, config: Dict[str, Any]) -> Dict[str, Any]:
        sample = config["scan_profiles"]["sample"]
        return {
            "current_profile": "sample",
            "description": sample["description"],
            "extensions": sample["extensions"],
            "exclude_dirs": sample["exclude_dirs"],
            "max_file_size_mb": config["max_file_size_mb"],
            "follow_symlinks": config["follow_symlinks"],
        }

    def _summary_from_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        profiles = config.get("scan_profiles") or {}
        active = config.get("current_profile") or next(iter(profiles), "sample")
        active_profile = profiles.get(active) or {}
        return {
            "current_profile": active,
            "description": active_profile.get("description", ""),
            "extensions": active_profile.get("extensions", []),
            "exclude_dirs": active_profile.get("exclude_dirs", []),
            "max_file_size_mb": config.get("max_file_size_mb"),
            "follow_symlinks": config.get("follow_symlinks"),
        }
