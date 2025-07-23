def detect_heading_level(font_size, title_font_size):
    ratio = font_size / title_font_size

    if ratio >= 0.8:
        return "H1"
    elif ratio >= 0.6:
        return "H2"
    elif ratio >= 0.5:
        return "H3"
    else:
        return None
