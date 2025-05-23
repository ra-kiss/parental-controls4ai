import streamlit as st
from openai import OpenAI
import settings_helper
import password_manager as pm
import content_filter as cf
import time_manager as tm
from streamlit_local_storage import LocalStorage
import uuid

localS = LocalStorage()
myUuid = localS.getItem('uuid')

if not myUuid:
    myUuid = str(uuid.uuid4())
    localS.setItem('uuid', myUuid)

# st.write(myUuid)

# --- Load Initial Settings & OpenAI Client ---
initial_settings = settings_helper.load_settings(myUuid)
if "OPENAI_API_KEY" not in st.secrets:
    st.error("OPENAI_API_KEY not found. Please add one to streamlit secrets at `.streamlit/secrets.toml`")
    st.stop()
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception as e:
    st.error(f"Failed to initialize OpenAI client: {e}")
    st.stop()

# --- Session State Initialization ---
for key, value in initial_settings.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Transient UI state variables
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "password_change_mode" not in st.session_state:
    st.session_state.password_change_mode = False
if "password_verified" not in st.session_state:
    st.session_state.password_verified = False
if "in_time_management_mode" not in st.session_state:
    st.session_state.in_time_management_mode = False
if "time_management_pwd_prompt" not in st.session_state:
    st.session_state.time_management_pwd_prompt = False

# --- Time Management Logic (called on each rerun) ---
time_state_updates = tm.manage_daily_reset_and_state(
    st.session_state.time_limit_active,
    st.session_state.time_used_today_seconds,
    st.session_state.date_for_time_used,
    st.session_state.active_session_start_time_iso
)
needs_save_after_reset_check = time_state_updates.pop("settings_were_updated_by_reset", False)
for key, value in time_state_updates.items():
    st.session_state[key] = value
if needs_save_after_reset_check:
    settings_helper.save_settings(st.session_state, myUuid)

total_usage_seconds_today, current_limit_seconds, is_exceeded_now = \
    tm.calculate_current_usage_and_limit_status(
        st.session_state.time_limit_active,
        st.session_state.time_used_today_seconds,
        st.session_state.active_session_start_time_iso,
        st.session_state.time_limit_minutes
    )

if is_exceeded_now != st.session_state.get("time_exceeded_flag", False):
    st.session_state.time_exceeded_flag = is_exceeded_now
    if st.session_state.get("time_limit_active") and st.session_state.get("active_session_start_time_iso"):
        c_t, n_as = tm.commit_session_time(
            st.session_state.time_used_today_seconds,
            st.session_state.active_session_start_time_iso
        )
        st.session_state.time_used_today_seconds = c_t
        st.session_state.active_session_start_time_iso = n_as
    settings_helper.save_settings(st.session_state, myUuid)

# --- Sidebar UI ---
with st.sidebar:
    st.title("🔒 Parental Controls")
    has_parent_password = bool(st.session_state.get("parent_password_hash"))

    # --- Parent Password Management ---
    st.header("🔑 Parent Password")
    if not has_parent_password:
        new_password = st.text_input("Set initial parent password:", type="password", key="init_pwd_sidebar")
        if st.button("Set Password", key="set_pwd_btn_sidebar"):
            if pm.set_initial_password(st.session_state, new_password):
                if st.session_state.get("time_limit_active") and st.session_state.get("active_session_start_time_iso"):
                    c_t, n_as = tm.commit_session_time(
                        st.session_state.time_used_today_seconds,
                        st.session_state.active_session_start_time_iso
                    )
                    st.session_state.time_used_today_seconds = c_t
                    st.session_state.active_session_start_time_iso = n_as
                settings_helper.save_settings(st.session_state, myUuid)
                st.success("Password set!")
                st.rerun()
            else:
                st.warning("Password cannot be empty.")
    else:
        if not st.session_state.password_change_mode:
            if st.button("Change Password", key="change_pwd_btn_sidebar"):
                st.session_state.password_change_mode = True
                st.session_state.password_verified = False
                st.rerun()
        else:
            st.subheader("Change Password")
            if not st.session_state.password_verified:
                current_pwd = st.text_input("Current password:", type="password", key="verify_curr_pwd_sidebar")
                vb, cb = st.columns(2)
                if vb.button("Verify", key="verify_btn_sidebar", use_container_width=True):
                    if pm.verify_password(st.session_state, current_pwd):
                        st.session_state.password_verified = True
                        st.session_state.stored_current_pwd = current_pwd  # Store the verified password
                        st.success("Verified!")
                        st.rerun()
                    else:
                        st.error("Incorrect password.")
                if cb.button("Cancel", key="cancel_verify_sidebar", use_container_width=True):
                    st.session_state.password_change_mode = False
                    st.rerun()
            else:
                new_pwd = st.text_input("New password:", type="password", key="new_pwd_sidebar")
                conf_pwd = st.text_input("Confirm new password:", type="password", key="conf_pwd_sidebar")
                ub, ucb = st.columns(2)
                if ub.button("Update", key="update_pwd_btn_sidebar", use_container_width=True):
                    if not new_pwd:
                        st.warning("New password empty.")
                    elif new_pwd == conf_pwd:
                        if st.session_state.get("time_limit_active") and st.session_state.get("active_session_start_time_iso"):
                            c_t, n_as = tm.commit_session_time(
                                st.session_state.time_used_today_seconds,
                                st.session_state.active_session_start_time_iso
                            )
                            st.session_state.time_used_today_seconds = c_t
                            st.session_state.active_session_start_time_iso = n_as
                        # Use stored password from session_state
                        if pm.change_password(st.session_state, st.session_state.get("stored_current_pwd", ""), new_pwd):
                            st.session_state.password_change_mode = False
                            st.session_state.password_verified = False
                            st.session_state.stored_current_pwd = None  # Clear stored password
                            settings_helper.save_settings(st.session_state, myUuid)
                            st.success("Password updated!")
                            st.rerun()
                        else:
                            st.error("Password change failed. Please verify again.")
                    else:
                        st.error("Passwords don't match.")
                if ucb.button("Cancel", key="cancel_update_sidebar", use_container_width=True):
                    st.session_state.password_change_mode = False
                    st.session_state.password_verified = False
                    st.session_state.stored_current_pwd = None  # Clear stored password
                    st.rerun()
    st.markdown("---")

    # --- Content Filtering Keywords ---
    st.header("🚫 Content Filtering")
    is_keywords_area_disabled = pm.is_keywords_locked(st.session_state) and has_parent_password
    if not has_parent_password:
        st.info("Set parent password for keyword locking.")
    kw_display = cf.get_banned_keywords(st.session_state) if not is_keywords_area_disabled else "[Keywords hidden when locked]"
    edited_kw = st.text_area("Banned Keywords (comma-separated):", value=kw_display, key="kw_ta_sidebar", disabled=is_keywords_area_disabled, help="Unlock to edit.")
    if not is_keywords_area_disabled and edited_kw != cf.get_banned_keywords(st.session_state):
        cf.set_banned_keywords(st.session_state, edited_kw)
    if has_parent_password:
        if pm.is_keywords_locked(st.session_state):
            pwd_kw_unlock = st.text_input("Password to edit keywords:", type="password", key="kw_unlock_pwd_sidebar")
            if st.button("Unlock Keywords", key="kw_unlock_btn_sidebar"):
                if pm.unlock_keywords(st.session_state, pwd_kw_unlock):
                    settings_helper.save_settings(st.session_state, myUuid)
                    st.success("Keywords unlocked.")
                    st.rerun()
                else:
                    st.error("Incorrect password.")
        else:
            st.write("Keyword list is unlocked.")
            if st.button("Save and Lock Keywords", key="kw_lock_btn_sidebar"):
                if st.session_state.get("time_limit_active") and st.session_state.get("active_session_start_time_iso"):
                    c_t, n_as = tm.commit_session_time(
                        st.session_state.time_used_today_seconds,
                        st.session_state.active_session_start_time_iso
                    )
                    st.session_state.time_used_today_seconds = c_t
                    st.session_state.active_session_start_time_iso = n_as
                pm.lock_keywords(st.session_state)
                settings_helper.save_settings(st.session_state, myUuid)
                st.success("Keywords saved and locked.")
                st.rerun()
    st.markdown("---")

    # --- Time Limiter Controls UI ---
    st.header("⏱️ Time Limiter")
    if not st.session_state.in_time_management_mode and not st.session_state.time_management_pwd_prompt:
        if st.button("Manage Time Limit", key="enter_time_mgmt_btn", disabled=not has_parent_password):
            if has_parent_password:
                st.session_state.time_management_pwd_prompt = True
                st.rerun()
        if st.session_state.time_limit_active:
            if st.session_state.time_exceeded_flag:
                st.caption("Status: Time limit reached!")
            else:
                st.caption("Status: Active")
        elif not has_parent_password:
            st.caption("Status: Inactive (Set parent password to enable)")
        else:
            st.caption("Status: Inactive")

    if st.session_state.time_management_pwd_prompt:
        st.subheader("Enter Password to Manage Time")
        time_mgmt_pwd = st.text_input("Parent Password:", type="password", key="time_mgmt_pwd_input")
        tmpb, tmpcb = st.columns(2)
        if tmpb.button("Access", key="access_time_settings_btn", use_container_width=True):
            if pm.verify_password(st.session_state, time_mgmt_pwd):
                st.session_state.in_time_management_mode = True
                st.session_state.time_management_pwd_prompt = False
                st.success("Access granted to time settings.")
                st.rerun()
            else:
                st.error("Incorrect password.")
        if tmpcb.button("Cancel", key="cancel_time_mgmt_pwd_prompt", use_container_width=True):
            st.session_state.time_management_pwd_prompt = False
            st.rerun()

    if st.session_state.in_time_management_mode:
        st.subheader("Time Limit Settings")
        prev_time_limit_active = st.session_state.time_limit_active
        new_time_limit_active_ui = st.checkbox("Enable Time Limit", value=st.session_state.time_limit_active, key="edit_timer_active_cb")
        new_time_limit_minutes_ui = st.number_input(
            "Set daily limit (minutes):",
            min_value=5,
            value=st.session_state.time_limit_minutes,
            step=5,
            key="edit_timer_limit_min_input"
        )
        if st.button("Reset Daily Timer Usage", key="edit_reset_timer_btn"):
            st.session_state.time_limit_active = new_time_limit_active_ui
            st.session_state.time_limit_minutes = new_time_limit_minutes_ui
            if st.session_state.get("time_limit_active") and st.session_state.get("active_session_start_time_iso"):
                c_t, n_as = tm.commit_session_time(
                    st.session_state.time_used_today_seconds,
                    st.session_state.active_session_start_time_iso
                )
                st.session_state.time_used_today_seconds = c_t
                st.session_state.active_session_start_time_iso = n_as
            reset_vals = tm.reset_timer_logic(st.session_state.time_limit_active)
            for k, v in reset_vals.items():
                st.session_state[k] = v
            settings_helper.save_settings(st.session_state, myUuid)
            st.info("Timer usage reset. Click 'Save and Exit' to apply all changes.")
            st.rerun()

        st.markdown("---")
        if st.button("Save and Exit Time Management", key="save_exit_time_mgmt_btn"):
            st.session_state.time_limit_active = new_time_limit_active_ui
            st.session_state.time_limit_minutes = new_time_limit_minutes_ui
            if prev_time_limit_active and not st.session_state.time_limit_active:
                c_t, _ = tm.commit_session_time(
                    st.session_state.time_used_today_seconds,
                    st.session_state.active_session_start_time_iso
                )
                st.session_state.time_used_today_seconds = c_t
            settings_helper.save_settings(st.session_state, myUuid)
            st.session_state.in_time_management_mode = False
            st.success("Time settings updated.")
            st.rerun()
        if st.button("Cancel Changes", key="cancel_time_mgmt_changes_btn"):
            st.session_state.in_time_management_mode = False
            st.info("Changes discarded.")
            st.rerun()

# --- Display Chat History ---
num_messages = len(st.session_state.messages)
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if message.get("is_filtered"):
            if message.get("is_revealed"):
                st.markdown(f"**Original Content (Revealed):**\n{message.get('original_content', '')}")
            else:
                st.markdown(message["content"])
                if has_parent_password and i == num_messages - 1:
                    st.markdown("---")
                    pwd_rev = st.text_input("Parent Password to Reveal:", type="password", key=f"main_pwd_rev_{i}")
                    if st.button("Reveal Original", key=f"main_btn_rev_{i}"):
                        if pm.verify_password(st.session_state, pwd_rev):
                            st.session_state.messages[i]["is_revealed"] = True
                            st.success("Revealed.")
                            st.rerun()
                        else:
                            st.error("Incorrect password.")
        else:
            st.markdown(message["content"])

        if message["role"] == "assistant" and i == num_messages - 1 and \
           st.session_state.time_limit_active and \
           not st.session_state.get("time_exceeded_flag", False) and \
           not message["content"].startswith("Time limit reached"):
            live_total_usage, _, _ = tm.calculate_current_usage_and_limit_status(
                st.session_state.time_limit_active,
                st.session_state.time_used_today_seconds,
                st.session_state.active_session_start_time_iso,
                st.session_state.time_limit_minutes
            )
            used_m, used_s = divmod(int(live_total_usage), 60)
            limit_m = st.session_state.time_limit_minutes
            st.caption(f"⏱️ Time used: {used_m}m {used_s}s / {limit_m}m")

# --- Handle New User Input & Assistant Response ---
chat_input_disabled = st.session_state.get("time_exceeded_flag", False)
if chat_input_disabled:
    if not st.session_state.messages or not st.session_state.messages[-1]["content"].startswith("Time limit reached"):
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Time limit reached. Chat disabled.",
            "is_filtered": False,
            "original_content": None,
            "is_revealed": False
        })
        st.rerun()

if prompt := st.chat_input("Ask the assistant...", disabled=chat_input_disabled, key="main_chat_input_area"):
    st.session_state.messages.append({"role": "user", "content": prompt, "is_filtered": False, "original_content": None, "is_revealed": False})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        msg_placeholder = st.empty()
        full_res = ""
        try:
            api_msgs = []
            for m_val in st.session_state.messages:
                if m_val["role"] == "assistant" and m_val["content"].startswith("Time limit reached"):
                    continue
                role, content = m_val["role"], m_val.get("content", "")
                if role == "assistant" and m_val.get("is_filtered") and m_val.get("is_revealed"):
                    content = m_val.get("original_content") or content
                elif role == "assistant" and m_val.get("is_filtered") and not m_val.get("is_revealed"):
                    continue
                if role and isinstance(content, str) and content:
                    api_msgs.append({"role": role, "content": content})
            if not api_msgs:
                msg_placeholder.markdown("No messages to send.")
            else:
                stream = client.chat.completions.create(model=st.session_state.openai_model, messages=api_msgs, stream=True)
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        full_res += chunk.choices[0].delta.content
                        msg_placeholder.markdown(full_res + "▌")
                f_res, was_f = cf.filter_content(full_res, cf.get_banned_keywords(st.session_state))
                msg_placeholder.markdown(f_res)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f_res,
                    "is_filtered": was_f,
                    "original_content": full_res if was_f else None,
                    "is_revealed": False
                })
                if was_f or (st.session_state.time_limit_active and not st.session_state.get("time_exceeded_flag", False)):
                    st.rerun()
        except Exception as e:
            st.error(f"API error: {e}")
            err_m = f"Error: {e}"
            st.session_state.messages.append({
                "role": "assistant",
                "content": err_m,
                "is_filtered": False,
                "original_content": None,
                "is_revealed": False
            })
            msg_placeholder.error(err_m)
            if st.session_state.time_limit_active and not st.session_state.get("time_exceeded_flag", False):
                st.rerun()