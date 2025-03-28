import streamlit as st
from settings_helper import load_settings, save_settings
from werkzeug.security import generate_password_hash, check_password_hash

def ParentPasswordManagement():
  # --- Parent Password Management ---
  st.markdown("### Parent Password")
  if not st.session_state.get("parent_password_hash"):
      new_password = st.text_input("Set initial parent password:", type="password", key="init_pwd")
      if st.button("Set Password"):
          if new_password:
              hashed_pwd = generate_password_hash(new_password)
              st.session_state["parent_password_hash"] = hashed_pwd
              st.session_state.settings_locked = True
              save_settings(hashed_pwd, st.session_state.banned_keywords, st.session_state.settings_locked)
              st.success("Password set successfully!")
              st.rerun()
          else:
              st.warning("Password cannot be empty.")
  else:
      # Password Change Section
      if not st.session_state.get("password_change_mode", False):
            if st.button("Change Password"):
              st.session_state["password_change_mode"] = True
              st.session_state["password_verified"] = False
              st.rerun()
      else:
          st.markdown("#### Change Password")
          if not st.session_state.get("password_verified", False):
              current_pwd_input = st.text_input("Current password:", type="password", key="current_pwd_verify")
              col1, col2 = st.columns(2)
              with col1:
                  if st.button("Verify"):
                      if check_password_hash(st.session_state.parent_password_hash, current_pwd_input):
                          st.session_state["password_verified"] = True
                          st.success("Password verified!")
                          st.rerun()
                      else:
                          st.error("Incorrect current password!")
              with col2:
                    if st.button("Cancel", key="cancel_change_pwd_verify"):
                      st.session_state["password_change_mode"] = False
                      st.session_state["password_verified"] = False
                      st.rerun()

          if st.session_state.get("password_verified", False):
              new_pwd_input = st.text_input("New password:", type="password", key="new_pwd_input")
              confirm_pwd_input = st.text_input("Confirm new password:", type="password", key="confirm_pwd_input")
              col1, col2 = st.columns(2)
              with col1:
                  if st.button("Update Password"):
                      if not new_pwd_input:
                          st.warning("New password cannot be empty.")
                      elif new_pwd_input == confirm_pwd_input:
                          new_hashed_pwd = generate_password_hash(new_pwd_input)
                          st.session_state["parent_password_hash"] = new_hashed_pwd
                          st.session_state["password_change_mode"] = False
                          st.session_state["password_verified"] = False
                          save_settings(new_hashed_pwd, st.session_state.banned_keywords, st.session_state.settings_locked)
                          st.success("Password updated successfully!")
                          st.rerun()
                      else:
                          st.error("New passwords don't match!")
              with col2:
                  if st.button("Cancel", key="cancel_change_pwd_update"):
                      st.session_state["password_change_mode"] = False
                      st.session_state["password_verified"] = False
                      st.rerun()