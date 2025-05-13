import streamlit as st

def get_banned_keywords(session_state):
    return session_state.banned_keywords

def set_banned_keywords(session_state, keywords):
    if not session_state.keywords_locked:
        session_state.banned_keywords = keywords
        return True
    return False

def filter_content(content, banned_keywords):
    banned_list = [kw.strip() for kw in banned_keywords.split(',') if kw.strip()]
    for kw in banned_list:
        if kw.lower() in content.lower():
            return "Content filtered due to banned keywords.", True
    return content, False