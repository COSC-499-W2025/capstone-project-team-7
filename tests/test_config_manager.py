"""
Simple tests for ConfigManager class
Run with: pytest tests/test_config_manager.py -v
"""

import pytest
import sys
import tempfile
import shutil
import json
from pathlib import Path

# Add backend/src to path so we can import from it
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))

from config.config_manager import ConfigManager


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for test config files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def config_manager(temp_config_dir):
    """Create a ConfigManager instance with temporary config path."""
    config_path = Path(temp_config_dir) / "test_config.json"
    return ConfigManager(config_path=str(config_path))


def test_init_creates_config(temp_config_dir):
    """Test that ConfigManager creates a config file on initialization."""
    config_path = Path(temp_config_dir) / "test_config.json"
    config = ConfigManager(config_path=str(config_path))
    
    assert config_path.exists()
    assert config.config is not None


def test_get_current_profile(config_manager):
    """Test getting current profile returns 'all' by default."""
    profile = config_manager.get_current_profile()
    assert profile == "all"


def test_set_current_profile_success(config_manager):
    """Test switching to a valid profile."""
    result = config_manager.set_current_profile("python_only")
    
    assert result is True
    assert config_manager.get_current_profile() == "python_only"


def test_set_current_profile_invalid(config_manager):
    """Test switching to invalid profile fails."""
    result = config_manager.set_current_profile("nonexistent")
    
    assert result is False


def test_get_allowed_extensions(config_manager):
    """Test getting allowed extensions for current profile."""
    extensions = config_manager.get_allowed_extensions()
    
    assert isinstance(extensions, list)
    assert ".py" in extensions


def test_get_excluded_dirs(config_manager):
    """Test getting excluded directories for current profile."""
    excluded = config_manager.get_excluded_dirs()
    
    assert isinstance(excluded, list)
    assert "__pycache__" in excluded


def test_list_profiles(config_manager, capsys):
    """Test that list_profiles runs without error."""
    config_manager.list_profiles()
    captured = capsys.readouterr()
    
    assert "Available Scan Profiles" in captured.out


def test_create_custom_profile_success(config_manager):
    """Test creating a new custom profile."""
    result = config_manager.create_custom_profile(
        name="my_profile",
        extensions=[".ts", ".tsx"],
        description="TypeScript files"
    )
    
    assert result is True
    assert "my_profile" in config_manager.config["scan_profiles"]


def test_create_custom_profile_duplicate(config_manager):
    """Test creating duplicate profile fails."""
    config_manager.create_custom_profile(name="test", extensions=[".txt"])
    result = config_manager.create_custom_profile(name="test", extensions=[".md"])
    
    assert result is False


def test_update_profile(config_manager):
    """Test updating an existing profile."""
    config_manager.create_custom_profile(name="test", extensions=[".txt"])
    result = config_manager.update_profile(name="test", extensions=[".txt", ".md"])
    
    assert result is True
    profile = config_manager.config["scan_profiles"]["test"]
    assert ".md" in profile["extensions"]


def test_delete_profile_success(config_manager):
    """Test deleting a non-active profile."""
    config_manager.create_custom_profile(name="to_delete", extensions=[".tmp"])
    result = config_manager.delete_profile("to_delete")
    
    assert result is True
    assert "to_delete" not in config_manager.config["scan_profiles"]


def test_delete_active_profile_fails(config_manager):
    """Test that deleting active profile fails."""
    config_manager.create_custom_profile(name="active", extensions=[".txt"])
    config_manager.set_current_profile("active")
    result = config_manager.delete_profile("active")
    
    assert result is False


def test_get_config(config_manager):
    """Test getting the complete configuration."""
    config = config_manager.get_config()
    
    assert isinstance(config, dict)
    assert "scan_profiles" in config
    assert "current_profile" in config


def test_get_config_summary(config_manager):
    """Test getting configuration summary."""
    summary = config_manager.get_config_summary()
    
    assert "current_profile" in summary
    assert "extensions" in summary
    assert "exclude_dirs" in summary
    assert summary["current_profile"] == "all"


# JSON File Verification Tests
def test_profile_change_saves_to_json_file(temp_config_dir):
    """Test that profile changes are actually written to the JSON file."""
    config_path = Path(temp_config_dir) / "test_config.json"
    config = ConfigManager(config_path=str(config_path))
    
    # Change profile
    config.set_current_profile("python_only")
    
    # Read the JSON file directly
    with open(config_path, 'r') as f:
        file_contents = json.load(f)
    
    # Verify the file was updated
    assert file_contents["current_profile"] == "python_only"


def test_create_profile_saves_to_json_file(temp_config_dir):
    """Test that creating a profile writes it to the JSON file."""
    config_path = Path(temp_config_dir) / "test_config.json"
    config = ConfigManager(config_path=str(config_path))
    
    # Create custom profile
    config.create_custom_profile(
        name="typescript",
        extensions=[".ts", ".tsx"],
        description="TypeScript files"
    )
    
    # Read the JSON file directly
    with open(config_path, 'r') as f:
        file_contents = json.load(f)
    
    # Verify profile exists in file
    assert "typescript" in file_contents["scan_profiles"]
    assert file_contents["scan_profiles"]["typescript"]["extensions"] == [".ts", ".tsx"]


def test_delete_profile_removes_from_json_file(temp_config_dir):
    """Test that deleting a profile removes it from the JSON file."""
    config_path = Path(temp_config_dir) / "test_config.json"
    config = ConfigManager(config_path=str(config_path))
    
    # Create and delete profile
    config.create_custom_profile(name="temp_profile", extensions=[".tmp"])
    config.delete_profile("temp_profile")
    
    # Read the JSON file directly
    with open(config_path, 'r') as f:
        file_contents = json.load(f)
    
    # Verify profile is gone from file
    assert "temp_profile" not in file_contents["scan_profiles"]


def test_user_preferences_persist_across_sessions(temp_config_dir):
    """Preferences should be saved for reuse in later sessions."""
    config_path = Path(temp_config_dir) / "test_config.json"
    config = ConfigManager(config_path=str(config_path))
    config.set_user_preference("theme", "dark")
    config.set_user_preference("recent_project", "/path/to/project")

    reloaded = ConfigManager(config_path=str(config_path))
    assert reloaded.get_user_preference("theme") == "dark"
    assert reloaded.get_user_preference("recent_project") == "/path/to/project"


def test_delete_user_preference_updates_file(temp_config_dir):
    """Removing a preference should update the persisted config."""
    config_path = Path(temp_config_dir) / "test_config.json"
    config = ConfigManager(config_path=str(config_path))
    config.set_user_preference("experimental_mode", True)

    removed = config.delete_user_preference("experimental_mode")
    assert removed is True

    with open(config_path, 'r') as f:
        file_contents = json.load(f)

    assert "experimental_mode" not in file_contents["user_preferences"]
