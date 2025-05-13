from werkzeug.security import generate_password_hash, check_password_hash
import streamlit as st

def set_initial_password(session_state, password):
    if password:
        session_state.parent_password_hash = generate_password_hash(password)
        session_state.keywords_locked = True
        return True
    return False

def change_password(session_state, current_password, new_password):
    if check_password_hash(session_state.parent_password_hash, current_password):
        session_state.parent_password_hash = generate_password_hash(new_password)
        return True
    return False

def verify_password(session_state, password):
    return check_password_hash(session_state.parent_password_hash, password)

def is_keywords_locked(session_state):
    return session_state.keywords_locked

def unlock_keywords(session_state, password):
    if verify_password(session_state, password):
        session_state.keywords_locked = False
        return True
    return False

def lock_keywords(session_state):
    session_state.keywords_locked = True