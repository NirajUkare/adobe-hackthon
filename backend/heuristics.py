import re

def detect_heading_level(font_size, title_font_size, text):
    """
    Detect heading level based on font size and text patterns
    This is a simplified version - the main logic is now in extractor.py
    """
    # This function is kept for compatibility but main logic moved to extractor
    if font_size >= title_font_size * 0.8:
        return 'H1'
    elif font_size >= title_font_size * 0.7:
        return 'H2' 
    elif font_size >= title_font_size * 0.6:
        return 'H3'
    
    return None
