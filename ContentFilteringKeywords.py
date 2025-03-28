import streamlit as st
from settings_helper import load_settings, save_settings
from werkzeug.security import generate_password_hash, check_password_hash

def ContentFilteringKeywords():
  # --- Content Filtering Keywords ---
  st.markdown("### Content Filtering")

  has_password = bool(st.session_state.get("parent_password_hash"))
  is_keywords_disabled = (st.session_state.get("settings_locked", True) and has_password) if has_password else True

  if not has_password:
      st.info("Set a parent password above to enable keyword locking.")

  current_keywords_value = st.session_state.get("banned_keywords", "")
  new_keywords_value = st.text_area(
      "Banned Keywords (comma-separated)",
      value=current_keywords_value,
      key="banned_keywords_input_area",
      disabled=is_keywords_disabled,
      help="Unlock below to edit."
  )

  # If unlocked, update session state with current text area value on each rerun
  if not is_keywords_disabled:
      if new_keywords_value != st.session_state.banned_keywords:
            st.session_state.banned_keywords = new_keywords_value