import streamlit as st
from openai import OpenAI
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import time

from content_filter import filter_content
from settings_helper import load_settings, save_settings
from ParentPasswordManagement import ParentPasswordManagement
from ContentFilteringKeywords import ContentFilteringKeywords
from SettingsLock import SettingsLock
from TimeLimit import TimeLimit

# --- Load Initial Settings ---
initial_settings = load_settings()

# --- OpenAI Client Setup ---
if "OPENAI_API_KEY" not in st.secrets:
    st.error("OpenAI API key not found. Please add it to your Streamlit secrets.")
    st.stop()
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception as e:
    st.error(f"Failed to initialize OpenAI client: {e}")
    st.stop()


# --- Session State Initialization (Using Loaded Settings) ---
# Initialize only if keys are not already present in the current session
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo"
if "messages" not in st.session_state:
    st.session_state.messages = [] # Chat history is session-specific, don't load from file
if "parent_password_hash" not in st.session_state:
    st.session_state["parent_password_hash"] = initial_settings["parent_password_hash"]
if "banned_keywords" not in st.session_state:
     st.session_state.banned_keywords = initial_settings["banned_keywords"]
if "settings_locked" not in st.session_state:
    st.session_state.settings_locked = initial_settings["settings_locked"]
# --- Other transient state variables ---
if "password_change_mode" not in st.session_state:
    st.session_state["password_change_mode"] = False
if "password_verified" not in st.session_state:
    st.session_state["password_verified"] = False
if "timer_start" not in st.session_state:
    st.session_state.timer_start = initial_settings["timer_start"]
if "time_limit" not in st.session_state:
    st.session_state.time_limit = initial_settings["time_limit"]

# --- Sidebar ---
with st.sidebar:
    st.markdown("# Parental Controls")
    st.warning(
        """**Note:** Settings persistence depends on the server environment.
        On temporary filesystems (like Streamlit Community Cloud), settings
        may be lost on restarts."""
    )
    st.markdown("---")

    # --- Parent Password Management Component ---
    ParentPasswordManagement()

    # --- Content Filtering Keywords ---
    ContentFilteringKeywords()

    # --- Time Limit Settings ---
    TimeLimit()
    
    # --- Settings Lock ---
    SettingsLock()

    

# --- Timer Check in Main App Area ---
chat_disabled = False  # Flag to control chat input
if st.session_state.timer_start is not None:
    elapsed = time.time() - st.session_state.timer_start
    remaining = st.session_state.time_limit - elapsed
    if remaining <= 0:
        st.warning("⏰ Time to take a break!")
        chat_disabled = True
    else:
        hours, remainder = divmod(int(remaining), 3600)
        minutes, seconds = divmod(remainder, 60)
        st.info(f"Time remaining: {hours:02d}:{minutes:02d}:{seconds:02d}")


# --- Display Chat History ---
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if message.get("is_filtered"):
            if message.get("is_revealed"):
                st.markdown("**Original Content (Revealed):**")
                st.markdown(message.get("original_content", "*Error: Original content not found.*"))
            else:
                st.markdown(message["content"]) # Placeholder "[CONTENT FILTERED...]"
                # Reveal Mechanism (only for last message, if password exists)
                if st.session_state.get("parent_password_hash") and i == len(st.session_state.messages) - 1:
                    st.markdown("---")
                    pwd_reveal_input = st.text_input("Enter Parent Password to Reveal:", type="password", key=f"pwd_reveal_{i}")
                    if st.button("Reveal Original Content", key=f"btn_reveal_{i}"):
                        if check_password_hash(st.session_state.parent_password_hash, pwd_reveal_input):
                            st.session_state.messages[i]["is_revealed"] = True
                            st.success("Password correct! Revealing content.")
                            st.rerun()
                        else:
                            st.error("Incorrect password.")
                elif not st.session_state.get("parent_password_hash") and i == len(st.session_state.messages) - 1:
                     st.warning("Set a parent password in the sidebar to enable revealing content.", icon="⚠️")
        else: # Regular (non-filtered) message
            st.markdown(message["content"])


# --- Handle New User Input ---
if prompt := st.chat_input("Ask the assistant...", disabled=chat_disabled):
    # Add user message to state
    st.session_state.messages.append({
        "role": "user",
        "content": prompt,
        "is_filtered": False,
        "original_content": None,
        "is_revealed": False
    })
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # --- Generate and Process Assistant Response (Correctly Indented) ---
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        try:
            # Prepare messages for API call
            api_messages = []
            for m in st.session_state.messages:
                role = m["role"]
                content = m.get("content", "")
                # Use original content if revealed, skip if filtered and not revealed
                if role == "assistant" and m.get("is_filtered") and m.get("is_revealed"):
                    original_content = m.get("original_content")
                    if original_content: content = original_content
                    else: continue # Skip message if original missing
                elif role == "assistant" and m.get("is_filtered") and not m.get("is_revealed"):
                    continue # Skip sending "[CONTENT FILTERED...]" placeholder
                # Add valid messages
                if role and isinstance(content, str) and content:
                    api_messages.append({"role": role, "content": content})

            # Make API call if messages exist
            if not api_messages:
                 message_placeholder.markdown("Hmm, I need a starting message.")
            else:
                stream = client.chat.completions.create(
                    model=st.session_state["openai_model"],
                    messages=api_messages,
                    stream=True,
                )
                # Stream response
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response + "▌")

                # Filter and store final response
                banned_keywords_from_state = st.session_state.get("banned_keywords", "")
                filtered_response, was_filtered = filter_content(full_response, banned_keywords_from_state)
                message_placeholder.markdown(filtered_response) # Display final

                st.session_state.messages.append({
                    "role": "assistant", "content": filtered_response,
                    "is_filtered": was_filtered,
                    "original_content": full_response if was_filtered else None,
                    "is_revealed": False
                })
                # Rerun if filtered to show reveal controls
                if was_filtered:
                    st.rerun()

        except Exception as e:
            st.error(f"An error occurred during API call: {e}")
            error_message = f"Sorry, I encountered an error: {e}"
            st.session_state.messages.append({
                "role": "assistant", "content": error_message,
                "is_filtered": False, "original_content": None, "is_revealed": False
            })
            message_placeholder.error(error_message)