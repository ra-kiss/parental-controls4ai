import json
import os

# --- Constants ---
SETTINGS_FILE = "app_settings.json"

# --- Helper Functions for Settings ---
def load_settings():
    """Loads settings from the JSON file."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                # Ensure default keys exist
                settings.setdefault("parent_password_hash", None)
                settings.setdefault("banned_keywords", "")
                settings.setdefault("settings_locked", bool(settings.get("parent_password_hash")))
                return settings
        except (json.JSONDecodeError, IOError) as e:
            st.error(f"Error loading settings file ({SETTINGS_FILE}): {e}. Using defaults.")
    # Return defaults if file doesn't exist or loading failed
    return {
        "parent_password_hash": None,
        "banned_keywords": "",
        "settings_locked": False
    }

def save_settings(password_hash, keywords, locked_state):
    """Saves settings to the JSON file."""
    settings = {
        "parent_password_hash": password_hash,
        "banned_keywords": keywords,
        "settings_locked": locked_state
    }
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
    except IOError as e:
        st.error(f"Error saving settings file ({SETTINGS_FILE}): {e}")