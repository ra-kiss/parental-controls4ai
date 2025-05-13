import json
import os
import streamlit as st
import time_manager
from streamlit_local_storage import LocalStorage

def get_default_settings():
    defaults = {
        "parent_password_hash": None,
        "banned_keywords": "",
        "keywords_locked": False,
    }
    time_defaults = time_manager.get_default_time_settings()
    defaults.update(time_defaults)
    return defaults

def load_settings(uuid):
    SETTINGS_FILE = f"app_settings_{uuid}.json"
    defaults = get_default_settings()
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
            for key, default_value in defaults.items():
                settings.setdefault(key, default_value)
            time_manager.ensure_time_settings_keys(settings)
            if settings.get("parent_password_hash") and "keywords_locked" not in settings:
                settings["keywords_locked"] = True
            elif not settings.get("parent_password_hash"):
                settings["keywords_locked"] = False
            return settings
        except (json.JSONDecodeError, IOError) as e:
            st.error(f"Error loading settings file ({SETTINGS_FILE}): {e}. Using defaults.")
    return defaults

def save_settings(settings, uuid):
    SETTINGS_FILE = f"app_settings_{uuid}.json"
    persisted_keys = [
        "parent_password_hash", "banned_keywords", "keywords_locked",
        "time_limit_active", "time_limit_minutes", "time_used_today_seconds",
        "date_for_time_used", "active_session_start_time_iso", "time_exceeded_flag"
    ]
    settings_to_save = {key: settings.get(key) for key in persisted_keys}
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings_to_save, f, indent=4)
    except IOError as e:
        st.error(f"Error saving settings file ({SETTINGS_FILE}): {e}")