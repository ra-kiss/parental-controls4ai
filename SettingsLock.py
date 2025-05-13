import streamlit as st
from settings_helper import load_settings, save_settings
from werkzeug.security import generate_password_hash, check_password_hash

def SettingsLock():

  has_password = bool(st.session_state.get("parent_password_hash"))

  # --- Settings Locking/Unlocking Controls ---
  if has_password:
      st.markdown("---")
      if st.session_state.get("settings_locked", True):
          st.write("Settings are locked.")
          pwd_settings_unlock = st.text_input("Enter password to edit settings:", type="password", key="pwd_settings_unlock")
          if st.button("Unlock Settings", key="btn_unlock_keywords"):
              if check_password_hash(st.session_state.parent_password_hash, pwd_settings_unlock):
                  st.session_state.settings_locked = False
                  st.success("Settings unlocked for editing.")
                  st.rerun()
              else:
                  st.error("Incorrect password.")
      else: # Keywords are unlocked
          st.write("Settings are unlocked.")
          if st.button("Save and Lock Settings", key="btn_lock_settings"):
              st.session_state.settings_locked = True
              # Save current keywords (from session state) and lock state to file
              save_settings({
                "parent_password_hash": st.session_state.parent_password_hash,
                "banned_keywords": st.session_state.banned_keywords,
                "settings_locked": True
                })
              st.success("Settings saved and locked.")
              st.rerun()