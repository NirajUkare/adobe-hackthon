from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar
from heuristics import detect_heading_level
from collections import defaultdict

def extract_outline(pdf_path):
    candidates = []
    font_stats = defaultdict(list)

    for page_num, layout in enumerate(extract_pages(pdf_path), start=1):
        for element in layout:
            if isinstance(element, LTTextContainer):
                for text_line in element:
                    text = text_line.get_text().strip()
                    if not text or len(text) > 200:
                        continue

                    font_sizes = []
                    for char in text_line:
                        if isinstance(char, LTChar):
                            font_sizes.append(char.size)

                    if font_sizes:
                        avg_font_size = sum(font_sizes) / len(font_sizes)
                        candidates.append({
                            "text": text,
                            "font_size": avg_font_size,
                            "page": page_num
                        })

    # Title: largest font on first page
    page1_texts = [c for c in candidates if c["page"] == 1]
    title_text = max(page1_texts, key=lambda x: x["font_size"]) if page1_texts else max(candidates, key=lambda x: x["font_size"])
    title_font_size = title_text["font_size"]
    title = title_text["text"]

    # Detect outline
    outline = []
    for c in candidates:
        level = detect_heading_level(c["font_size"], title_font_size)
        if level:
            outline.append({
                "level": level,
                "text": c["text"],
                "page": c["page"]
            })

    return title, outline
