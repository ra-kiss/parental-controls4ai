import json
import os
import streamlit as st
import time_manager
import uuid

def get_default_settings():
    defaults = {
        "parent_password_hash": None,
        "banned_keywords": "",
        "keywords_locked": False,
    }
    time_defaults = time_manager.get_default_time_settings()
    defaults.update(time_defaults)
    return defaults

def load_settings():
    # Initialize or retrieve device UUID
    if 'device_uuid' not in st.session_state:
        # Check existing settings files for a UUID
        settings_dir = "."
        found_uuid = None
        for fname in os.listdir(settings_dir):
            if fname.startswith("app_settings_") and fname.endswith(".json"):
                try:
                    with open(os.path.join(settings_dir, fname), 'r') as f:
                        data = json.load(f)
                        if "device_uuid" in data:
                            found_uuid = data["device_uuid"]
                            break
                except (json.JSONDecodeError, IOError):
                    continue
        st.session_state.device_uuid = found_uuid or str(uuid.uuid4())

    settings_file = f"app_settings_{st.session_state.device_uuid}.json"
    defaults = get_default_settings()
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r') as f:
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
            st.error(f"Error loading settings file ({settings_file}): {e}. Using defaults.")
    return defaults

def save_settings(settings):
    persisted_keys = [
        "parent_password_hash", "banned_keywords", "keywords_locked",
        "time_limit_active", "time_limit_minutes", "time_used_today_seconds",
        "date_for_time_used", "active_session_start_time_iso", "time_exceeded_flag",
        "device_uuid"
    ]
    settings_to_save = {key: settings.get(key, st.session_state.get('device_uuid')) for key in persisted_keys}
    settings_file = f"app_settings_{st.session_state.device_uuid}.json"
    try:
        with open(settings_file, 'w') as f:
            json.dump(settings_to_save, f, indent=4)
    except IOError as e:
        st.error(f"Error saving settings file ({settings_file}): {e}")