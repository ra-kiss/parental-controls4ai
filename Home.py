from openai import OpenAI
import streamlit as st
from content_filter import filter_content  # Import the filter_content function

# --- OpenAI Client Setup ---
# Ensure API key is available
if "OPENAI_API_KEY" not in st.secrets:
    st.error("OpenAI API key not found. Please add it to your Streamlit secrets.")
    st.stop()

try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception as e:
    st.error(f"Failed to initialize OpenAI client: {e}")
    st.stop()

# --- Session State Initialization ---
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo"

if "messages" not in st.session_state:
    # Store message dicts: {"role": str, "content": str, "is_filtered": bool, "original_content": str|None, "is_revealed": bool}
    st.session_state.messages = []

if "parent_password" not in st.session_state:
    st.session_state["parent_password"] = "" # Default: no password set initially

if "password_change_mode" not in st.session_state:
    st.session_state["password_change_mode"] = False

if "password_verified" not in st.session_state:
    st.session_state["password_verified"] = False

# --- State for keyword locking ---
if "keywords_locked" not in st.session_state:
    # Start locked by default if a password exists, otherwise unlocked
    st.session_state.keywords_locked = bool(st.session_state.get("parent_password"))

if "banned_keywords" not in st.session_state:
     st.session_state.banned_keywords = "" # Initialize if not present


# --- Sidebar for Settings ---
with st.sidebar:
    st.markdown("# Parental Controls")

    # --- Parent Password Management ---
    st.markdown("### Parent Password")
    if not st.session_state.get("parent_password"): # Use .get for safety
        new_password = st.text_input("Set initial parent password:", type="password", key="init_pwd")
        if st.button("Set Password"):
            if new_password:
                st.session_state["parent_password"] = new_password
                st.session_state.keywords_locked = True # Lock keywords now that pwd exists
                st.success("Password set successfully!")
                st.rerun() # Rerun to update UI
            else:
                st.warning("Password cannot be empty.")
    else:
        # Password Change Section
        if not st.session_state.get("password_change_mode", False):
             if st.button("Change Password"):
                st.session_state["password_change_mode"] = True
                st.session_state["password_verified"] = False # Reset verification state
                st.rerun()
        else:
            st.markdown("#### Change Password")
            if not st.session_state.get("password_verified", False):
                current_pwd = st.text_input("Current password:", type="password", key="current_pwd_verify")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Verify"):
                        if current_pwd == st.session_state["parent_password"]:
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
                new_pwd = st.text_input("New password:", type="password", key="new_pwd_input")
                confirm_pwd = st.text_input("Confirm new password:", type="password", key="confirm_pwd_input")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Update Password"):
                        if not new_pwd:
                            st.warning("New password cannot be empty.")
                        elif new_pwd == confirm_pwd:
                            st.session_state["parent_password"] = new_pwd
                            st.session_state["password_change_mode"] = False
                            st.session_state["password_verified"] = False
                            st.success("Password updated successfully!")
                            st.rerun() # Rerun to hide change fields
                        else:
                            st.error("New passwords don't match!")
                with col2:
                    if st.button("Cancel##UpdatePwd", key="cancel_change_pwd_update"):
                        st.session_state["password_change_mode"] = False
                        st.session_state["password_verified"] = False
                        st.rerun()


    # --- Content Filtering Settings with Lock ---
    st.markdown("### Content Filtering")

    # Determine if the text area should be disabled
    is_keywords_disabled = st.session_state.get("keywords_locked", True) and bool(st.session_state.get("parent_password"))

    if not st.session_state.get("parent_password"):
        st.info("Set a parent password above to lock keyword editing.")

    # Display the text area
    current_keywords_value = st.session_state.get("banned_keywords", "")
    new_keywords_value = st.text_area(
        "Banned Keywords (comma-separated)",
        value=current_keywords_value,
        key="banned_keywords_input_area",
        disabled=is_keywords_disabled,
        help="Enter words like: game, bad, secret. Unlock below to edit."
    )

    # If the text area is *not* disabled, update the session state
    if not is_keywords_disabled:
        # Only update if the value actually changed to prevent unnecessary state changes
        if new_keywords_value != st.session_state.banned_keywords:
             st.session_state.banned_keywords = new_keywords_value
             # No rerun needed here, just capture the value

    # --- Keyword Locking/Unlocking Controls ---
    if st.session_state.get("parent_password"):
        st.markdown("---")
        if st.session_state.get("keywords_locked", True):
            # --- Section to UNLOCK ---
            st.write("Keyword list is locked.")
            pwd_keyword_unlock = st.text_input("Enter password to edit keywords:", type="password", key="pwd_keyword_unlock")
            if st.button("Unlock Keywords", key="btn_unlock_keywords"):
                if pwd_keyword_unlock == st.session_state.parent_password:
                    st.session_state.keywords_locked = False
                    st.success("Keywords unlocked for editing.")
                    st.rerun()
                else:
                    st.error("Incorrect password.")
        else:
            # --- Section to LOCK ---
            st.write("Keyword list is unlocked.")
            if st.button("Save and Lock Keywords", key="btn_lock_keywords"):
                # The latest value should already be in st.session_state.banned_keywords
                st.session_state.keywords_locked = True
                st.success("Keywords saved and locked.")
                st.rerun()


# --- Display Chat History ---
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if message.get("is_filtered"):
            if message.get("is_revealed"):
                st.markdown("**Original Content (Revealed):**")
                st.markdown(message.get("original_content", "*Error: Original content not found.*")) # Display original
            else:
                st.markdown(message["content"]) # Display placeholder "[CONTENT FILTERED...]"

                # Reveal Mechanism - ONLY for the *last* filtered message that isn't revealed yet
                if st.session_state.get("parent_password") and i == len(st.session_state.messages) - 1:
                    st.markdown("---") # Separator
                    pwd = st.text_input("Enter Parent Password to Reveal:", type="password", key=f"pwd_reveal_{i}")
                    if st.button("Reveal Original Content", key=f"btn_reveal_{i}"):
                        if pwd == st.session_state["parent_password"]:
                            st.session_state.messages[i]["is_revealed"] = True
                            st.success("Password correct! Revealing content.")
                            st.rerun()
                        else:
                            st.error("Incorrect password.")
                # Show warning if password not set for the last message if it's filtered
                elif not st.session_state.get("parent_password") and i == len(st.session_state.messages) - 1:
                     st.warning("Set a parent password in the sidebar to enable revealing content.", icon="⚠️")

        else: # Regular (non-filtered) message
            st.markdown(message["content"])


# --- Handle New User Input ---
if prompt := st.chat_input("What is up?"):
    # Add user message to state
    st.session_state.messages.append({
        "role": "user",
        "content": prompt,
        "is_filtered": False,
        "original_content": None,
        "is_revealed": False
    })

    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)

    # --- Generate and Process Assistant Response ---
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        try:
            # --- Construct messages for API (CORRECTED LOGIC) ---
            api_messages = []
            for m in st.session_state.messages:
                role = m["role"]
                content = m.get("content", "") # Default to empty string

                # If it's an assistant message that was filtered BUT IS revealed, use original content
                if role == "assistant" and m.get("is_filtered") and m.get("is_revealed"):
                    original_content = m.get("original_content")
                    # Use original content if available, otherwise the conversation might be broken.
                    # Alternatively, could fall back to the filtered placeholder if original is missing.
                    if original_content:
                        content = original_content
                    else:
                        # Decide: skip? or send placeholder? Sending placeholder might confuse AI less than skipping.
                        # content = m.get("content", "") # Send "[CONTENT FILTERED...]" if original missing
                        st.warning(f"Revealed message {m.get('content', '')[:20]}... missing original content for API history.")
                        continue # Skip message if original content is missing after reveal

                # Skip assistant messages that are still filtered (never revealed)
                elif role == "assistant" and m.get("is_filtered") and not m.get("is_revealed"):
                    continue # Skip sending "[CONTENT FILTERED...]" to the API history

                # Basic validation before appending
                if role and isinstance(content, str) and content: # Ensure content is a non-empty string
                    api_messages.append({"role": role, "content": content})
                elif role == "user": # Always include user messages even if empty? Maybe not.
                    # If user message is empty, maybe skip?
                    pass
                # Potentially log skipped messages for debugging if needed
                # else:
                #     print(f"Skipping message in API call prep: Role='{role}', Content Type='{type(content)}'")


            # --- Make the API call with the prepared messages ---
            # Check if there are any messages to send
            if not api_messages:
                 st.warning("No valid messages to send to the API.")
                 # Handle this case - maybe display a message?
                 message_placeholder.markdown("I need some conversation history first!")

            else:
                stream = client.chat.completions.create(
                    model=st.session_state["openai_model"],
                    messages=api_messages, # Use the correctly constructed list
                    stream=True,
                )

                # Stream and display response
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response + "▌") # Show typing indicator

                # --- Filter and Store Response ---
                # Get banned keywords from sidebar state (uses the value potentially updated while unlocked)
                banned_keywords_from_state = st.session_state.get("banned_keywords", "")

                # Filter the complete response
                filtered_response, was_filtered = filter_content(full_response, banned_keywords_from_state)

                # Display the final response (filtered or not)
                message_placeholder.markdown(filtered_response)

                # Add assistant message to state with filtering info
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": filtered_response, # Store the potentially filtered content
                    "is_filtered": was_filtered,
                    "original_content": full_response if was_filtered else None, # Store original ONLY if filtered
                    "is_revealed": False # Initially not revealed
                })

                # If it WAS filtered, we need to rerun so the history loop adds the reveal controls
                if was_filtered:
                    st.rerun() # Rerun to make the reveal controls appear via the history loop

        except Exception as e:
            st.error(f"An error occurred: {e}")
            # Add error message to chat history for context
            error_message = f"Sorry, an error occurred while generating the response: {e}"
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_message,
                "is_filtered": False,
                "original_content": None,
                "is_revealed": False
            })
            message_placeholder.error(error_message) # Also display in placeholder