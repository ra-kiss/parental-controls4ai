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
                settings.setdefault("time_limit", 0)
                settings.setdefault("timer_start", None)
                return settings
        except (json.JSONDecodeError, IOError) as e:
            st.error(f"Error loading settings file ({SETTINGS_FILE}): {e}. Using defaults.")
    # Return defaults if file doesn't exist or loading failed
    return {
        "parent_password_hash": None,
        "banned_keywords": "",
        "settings_locked": False,
        "time_limit": 0,
        "timer_start": None
    }

def save_settings(new_settings):
    """Saves settings to the JSON file."""
    current_settings = load_settings();
    settings = {**current_settings, **new_settings}
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
    except IOError as e:
        st.error(f"Error saving settings file ({SETTINGS_FILE}): {e}")