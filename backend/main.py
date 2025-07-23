import os
import json
from extractor import extract_outline

input_dir = './input'
output_dir = './output'

os.makedirs(output_dir, exist_ok=True)

for filename in os.listdir(input_dir):
    if filename.endswith('.pdf'):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename.replace('.pdf', '.json'))

        title, outline = extract_outline(input_path)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                "title": title,
                "outline": outline
            }, f, indent=2, ensure_ascii=False)

        print(f"✅ Processed {filename} -> {output_path}")
