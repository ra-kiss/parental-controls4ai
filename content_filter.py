import re

def filter_content(text, banned_words):
    """
    Filter content based on banned words
    
    Args:
        text (str): The text to filter
        banned_words (str): Comma-separated list of banned words
        
    Returns:
        tuple: (filtered_text, was_filtered) where filtered_text is the 
               filtered version and was_filtered is a boolean indicating 
               if filtering occurred
    """
    if not text or not banned_words:
        return text, False
    
    # Create a list of banned words from comma-separated input
    banned_list = [word.strip().lower() for word in banned_words.replace("\n", "").split(",") if word.strip()]
    
    # Check if any banned word is in the text
    for word in banned_list:
        if word and word.lower() in text.lower():
            # Return complete message filtered notice
            return "[CONTENT FILTERED: This response contained prohibited content]", True
    
    # If no banned words found, return original text
    return text, False 