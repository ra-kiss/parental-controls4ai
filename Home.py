from openai import OpenAI
import streamlit as st
from content_filter import filter_content  # Import the filter_content function

# --- OpenAI Client Setup ---
# Ensure API key is available
if "OPENAI_API_KEY" not in st.secrets:
    st.error("OpenAI API key not found. Please add it to your Streamlit secrets.")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

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

# --- Sidebar for Settings ---
with st.sidebar:
    st.markdown("# Parental Controls")

    # --- Parent Password Management ---
    st.markdown("### Parent Password")
    if not st.session_state["parent_password"]:
        new_password = st.text_input("Set initial parent password:", type="password", key="init_pwd")
        if new_password:
            if st.button("Set Password"):
                st.session_state["parent_password"] = new_password
                st.success("Password set successfully!")
                st.rerun() # Rerun to update UI
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
                        # Optionally just reset verification, stay in change mode
                        # st.session_state["password_verified"] = False
                        # Or exit change mode completely
                        st.session_state["password_change_mode"] = False
                        st.session_state["password_verified"] = False
                        st.rerun()

    # --- Content Filtering Settings ---
    st.markdown("### Content Filtering")
    # Use a key for text_area to preserve its value across reruns reliably
    banned_keywords_input = st.text_area(
        "Banned Keywords (comma-separated)",
        value=st.session_state.get("banned_keywords_input", ""), # Load previous value
        key="banned_keywords_input",
        help="Enter words like: game, bad, secret"
    )
    # Update session state only if it changes (optional optimization)
    if banned_keywords_input != st.session_state.get("banned_keywords", ""):
         st.session_state["banned_keywords"] = banned_keywords_input
         # No rerun needed here unless you want immediate effect on history (not typical)

# --- Display Chat History ---
# This loop now handles displaying regular, filtered, and revealed messages
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if message.get("is_filtered"):
            if message.get("is_revealed"):
                st.markdown("**Original Content (Revealed):**")
                st.markdown(message["original_content"])
            else:
                # Show the filtered placeholder
                st.markdown(message["content"]) # This holds "[CONTENT FILTERED...]"

                # --- Reveal Mechanism - ONLY for the *last* filtered message ---
                # Check if password is set and if this is the latest message
                if st.session_state.get("parent_password") and i == len(st.session_state.messages) - 1:
                    st.markdown("---") # Separator
                    # Use a unique key for the password input to avoid conflicts
                    pwd = st.text_input("Enter Parent Password to Reveal:", type="password", key=f"pwd_reveal_{i}")
                    if st.button("Reveal Original Content", key=f"btn_reveal_{i}"):
                        if pwd == st.session_state["parent_password"]:
                            # --- SUCCESS: Update state and rerun ---
                            st.session_state.messages[i]["is_revealed"] = True
                            st.success("Password correct! Revealing content.")
                            # Use st.rerun() to force the script to run again from the top.
                            # The chat history loop will then see is_revealed=True and display original_content.
                            st.rerun()
                        else:
                            st.error("Incorrect password.")
                elif not st.session_state.get("parent_password"):
                     st.warning("Set a parent password in the sidebar to enable revealing content.", icon="⚠️")

        else: # Regular message
            st.markdown(message["content"])


# --- Handle New User Input ---
if prompt := st.chat_input("What is up?"):
    # Add user message to state
    st.session_state.messages.append({
        "role": "user",
        "content": prompt,
        "is_filtered": False, # User messages aren't filtered
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
            stream = client.chat.completions.create(
                model=st.session_state["openai_model"],
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    # Filter out internal keys before sending to OpenAI
                    for m in st.session_state.messages if m["role"] == "user" or not m.get("is_filtered") or m.get("is_revealed")
                    # More robust: only send non-internal keys
                    # for m_dict in st.session_state.messages:
                    #    api_message = {"role": m_dict["role"], "content": m_dict["content"]}
                    #    # Decide if we need to use original content for history? If revealed, yes.
                    #    if m_dict["role"] == "assistant" and m_dict.get("is_revealed"):
                    #       api_message["content"] = m_dict["original_content"]
                    #    elif m_dict["role"] == "assistant" and m_dict.get("is_filtered") and not m_dict.get("is_revealed"):
                    #       continue # Maybe skip sending filtered message history? Or send placeholder? Sending placeholder is safer.
                    #       # api_message["content"] = m_dict["content"] # Send "[CONTENT FILTERED...]"
                    #    # Make sure it's a dict OpenAI expects {role, content}
                    #    if "role" in api_message and "content" in api_message:
                    #        st.session_state.api_messages_temp.append(api_message)

                ],
                stream=True,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌") # Show typing indicator

            # Get banned keywords from sidebar state
            banned_keywords = st.session_state.get("banned_keywords", "")

            # Filter the complete response
            filtered_response, was_filtered = filter_content(full_response, banned_keywords)

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
                # We don't need to manually add the password input here anymore.
                # The history display loop will handle it on the next run.
                st.rerun() # Rerun to make the reveal controls appear via the history loop

        except Exception as e:
            st.error(f"An error occurred: {e}")
            # Add error message to chat history
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Error generating response: {e}",
                "is_filtered": False,
                "original_content": None,
                "is_revealed": False
            })
            message_placeholder.error(f"Error generating response: {e}")