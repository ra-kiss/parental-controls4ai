import streamlit as st
from openai import OpenAI
from content_filter import filter_content
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash

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
                settings.setdefault("keywords_locked", bool(settings.get("parent_password_hash")))
                return settings
        except (json.JSONDecodeError, IOError) as e:
            st.error(f"Error loading settings file ({SETTINGS_FILE}): {e}. Using defaults.")
    # Return defaults if file doesn't exist or loading failed
    return {
        "parent_password_hash": None,
        "banned_keywords": "",
        "keywords_locked": False
    }

def save_settings(password_hash, keywords, locked_state):
    """Saves settings to the JSON file."""
    settings = {
        "parent_password_hash": password_hash,
        "banned_keywords": keywords,
        "keywords_locked": locked_state
    }
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
    except IOError as e:
        st.error(f"Error saving settings file ({SETTINGS_FILE}): {e}")

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
if "keywords_locked" not in st.session_state:
    st.session_state.keywords_locked = initial_settings["keywords_locked"]
# --- Other transient state variables ---
if "password_change_mode" not in st.session_state:
    st.session_state["password_change_mode"] = False
if "password_verified" not in st.session_state:
    st.session_state["password_verified"] = False

# --- Sidebar ---
with st.sidebar:
    st.markdown("# Parental Controls")
    st.warning(
        """**Note:** Settings persistence depends on the server environment.
        On temporary filesystems (like Streamlit Community Cloud), settings
        may be lost on restarts."""
    )
    st.markdown("---")

    # --- Parent Password Management ---
    st.markdown("### Parent Password")
    if not st.session_state.get("parent_password_hash"):
        new_password = st.text_input("Set initial parent password:", type="password", key="init_pwd")
        if st.button("Set Password"):
            if new_password:
                hashed_pwd = generate_password_hash(new_password)
                st.session_state["parent_password_hash"] = hashed_pwd
                st.session_state.keywords_locked = True
                save_settings(hashed_pwd, st.session_state.banned_keywords, st.session_state.keywords_locked)
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
                     if st.button("Cancel##ChangePwd", key="cancel_change_pwd_verify"):
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
                            save_settings(new_hashed_pwd, st.session_state.banned_keywords, st.session_state.keywords_locked)
                            st.success("Password updated successfully!")
                            st.rerun()
                        else:
                            st.error("New passwords don't match!")
                with col2:
                    if st.button("Cancel##UpdatePwd", key="cancel_change_pwd_update"):
                        st.session_state["password_change_mode"] = False
                        st.session_state["password_verified"] = False
                        st.rerun()


    # --- Content Filtering Keywords ---
    st.markdown("### Content Filtering")

    has_password = bool(st.session_state.get("parent_password_hash"))
    is_keywords_disabled = st.session_state.get("keywords_locked", True) and has_password

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

    # --- Keyword Locking/Unlocking Controls ---
    if has_password:
        st.markdown("---")
        if st.session_state.get("keywords_locked", True):
            st.write("Keyword list is locked.")
            pwd_keyword_unlock = st.text_input("Enter password to edit keywords:", type="password", key="pwd_keyword_unlock")
            if st.button("Unlock Keywords", key="btn_unlock_keywords"):
                if check_password_hash(st.session_state.parent_password_hash, pwd_keyword_unlock):
                    st.session_state.keywords_locked = False
                    st.success("Keywords unlocked for editing.")
                    st.rerun()
                else:
                    st.error("Incorrect password.")
        else: # Keywords are unlocked
            st.write("Keyword list is unlocked.")
            if st.button("Save and Lock Keywords", key="btn_lock_keywords"):
                st.session_state.keywords_locked = True
                # Save current keywords (from session state) and lock state to file
                save_settings(st.session_state.parent_password_hash, st.session_state.banned_keywords, True)
                st.success("Keywords saved and locked.")
                st.rerun()


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
if prompt := st.chat_input("Ask the assistant..."):
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