import streamlit as st
import time

def TimeLimit():
  # --- Time Limit Settings ---
    st.markdown("### Time Limit")
    has_password = bool(st.session_state.get("parent_password_hash"))
    is_buttons_disabled = (st.session_state.get("settings_locked", True) and has_password) if has_password else True

    hours, minutes = st.columns((1,1))
    with hours:
        hours_input = st.number_input("Hours", min_value=0, value=1, disabled=is_buttons_disabled)
    with minutes:
        minutes_input = st.number_input("Minutes", min_value=0, value=0, disabled=is_buttons_disabled)
    start, reset = st.columns((3,1))
    with start:
        start_timer = st.button("Start", use_container_width=True, disabled=is_buttons_disabled)
        if start_timer:
            st.session_state.time_limit = hours_input*60*60 + minutes_input*60
            st.session_state.timer_start = time.time()
    with reset:
        reset_timer = st.button("Reset", use_container_width=True, disabled=is_buttons_disabled)
        if reset_timer:
            st.session_state.timer_start = None