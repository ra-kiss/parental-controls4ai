# time_manager.py
import datetime

def get_default_time_settings():
    """Returns a dictionary of default time-related settings."""
    return {
        "time_limit_active": False,
        "time_limit_minutes": 30,
        "time_used_today_seconds": 0,
        "date_for_time_used": datetime.date.today().isoformat(),
        "active_session_start_time_iso": None, # Store as ISO string for JSON
        "time_exceeded_flag": False
    }

def ensure_time_settings_keys(settings):
    """Ensures all necessary time keys are present in the settings dict, adding defaults if not."""
    defaults = get_default_time_settings()
    updated = False
    for key, default_value in defaults.items():
        if key not in settings:
            settings[key] = default_value
            updated = True
    
    if "date_for_time_used" not in settings or not isinstance(settings.get("date_for_time_used"), str):
        settings["date_for_time_used"] = datetime.date.today().isoformat()
        updated = True
    else:
        try:
            datetime.date.fromisoformat(settings["date_for_time_used"])
        except (TypeError, ValueError):
            settings["date_for_time_used"] = datetime.date.today().isoformat()
            updated = True
            
    if "active_session_start_time_iso" in settings and settings["active_session_start_time_iso"] is not None:
        if not isinstance(settings["active_session_start_time_iso"], str):
            settings["active_session_start_time_iso"] = None 
            updated = True
        else:
            try:
                datetime.datetime.fromisoformat(settings["active_session_start_time_iso"])
            except (TypeError, ValueError):
                 settings["active_session_start_time_iso"] = None 
                 updated = True
    return updated

def commit_session_time(time_used_today_seconds, active_session_start_time_iso):
    """
    Calculates duration of the current active session and adds it to today's used time.
    Returns updated time_used_today_seconds and a new active_session_start_time_iso (now).
    """
    new_active_session_start_time_iso = datetime.datetime.now().isoformat()
    if active_session_start_time_iso:
        try:
            start_time_dt = datetime.datetime.fromisoformat(active_session_start_time_iso)
            session_duration = (datetime.datetime.now() - start_time_dt).total_seconds()
            time_used_today_seconds += session_duration
        except (TypeError, ValueError):
            pass 
    return time_used_today_seconds, new_active_session_start_time_iso


def manage_daily_reset_and_state(
    time_limit_active,
    time_used_today_seconds,
    date_for_time_used,
    active_session_start_time_iso
):
    now_dt = datetime.datetime.now()
    today_str = now_dt.date().isoformat()
    
    updated_values = {
        "time_used_today_seconds": time_used_today_seconds,
        "date_for_time_used": date_for_time_used,
        "active_session_start_time_iso": active_session_start_time_iso,
        "time_exceeded_flag": False 
    }
    settings_changed_by_reset = False

    if date_for_time_used != today_str:
        if active_session_start_time_iso: 
            committed_time, _ = commit_session_time(time_used_today_seconds, active_session_start_time_iso)
            updated_values["time_used_today_seconds"] = committed_time
        
        updated_values["time_used_today_seconds"] = 0 
        updated_values["date_for_time_used"] = today_str
        updated_values["active_session_start_time_iso"] = now_dt.isoformat() if time_limit_active else None
        settings_changed_by_reset = True
    
    if time_limit_active and updated_values["active_session_start_time_iso"] is None:
        updated_values["active_session_start_time_iso"] = now_dt.isoformat()
        settings_changed_by_reset = True 
    elif not time_limit_active and updated_values["active_session_start_time_iso"] is not None:
        committed_time, _ = commit_session_time(updated_values["time_used_today_seconds"], updated_values["active_session_start_time_iso"])
        updated_values["time_used_today_seconds"] = committed_time
        updated_values["active_session_start_time_iso"] = None
        settings_changed_by_reset = True

    updated_values["settings_were_updated_by_reset"] = settings_changed_by_reset
    return updated_values


def calculate_current_usage_and_limit_status(
    time_limit_active,
    time_used_today_seconds, 
    active_session_start_time_iso, 
    time_limit_minutes
):
    current_session_duration = 0
    if time_limit_active and active_session_start_time_iso:
        try:
            start_time_dt = datetime.datetime.fromisoformat(active_session_start_time_iso)
            current_session_duration = (datetime.datetime.now() - start_time_dt).total_seconds()
        except (TypeError, ValueError):
            pass

    total_live_seconds_today = time_used_today_seconds + current_session_duration
    limit_seconds = time_limit_minutes * 60
    is_exceeded = time_limit_active and (total_live_seconds_today >= limit_seconds)
    
    return total_live_seconds_today, limit_seconds, is_exceeded

def reset_timer_logic(time_limit_active_state):
    return {
        "time_used_today_seconds": 0,
        "active_session_start_time_iso": datetime.datetime.now().isoformat() if time_limit_active_state else None,
        "time_exceeded_flag": False
    }