def detect_heading_level(font_size, title_font_size, text):
    ratio = font_size / title_font_size
    if ratio >= 0.8 and len(text.split()) <= 10:
        return "H1"
    elif ratio >= 0.6 and len(text.split()) <= 10:
        return "H2"
    elif ratio >= 0.5 and len(text.split()) <= 12:
        return "H3"
    elif ratio >= 0.4 and (text.startswith("1.") or ":" in text):
        return "H4"
    else:
        return None