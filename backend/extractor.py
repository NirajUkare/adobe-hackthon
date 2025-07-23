from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LAParams
from collections import Counter, defaultdict
import re
import json
from pathlib import Path

class PDFOutlineExtractor:
    def __init__(self):
        # Optimized layout parameters
        self.laparams = LAParams(
            char_margin=2.0,
            word_margin=0.1,
            line_margin=0.5,
            boxes_flow=0.5,
            all_texts=False
        )
        
        # Common noise patterns
        self.noise_patterns = [
            r'^\d+$',  # Just page numbers
            r'^©.*', r'^copyright.*', r'^www\.', r'^http',
            r'^page\s+\d+', r'^\s*overview\s*$',
            r'^version\s+\d+', r'^v\d+\.\d+',
            r'^international software testing qualifications board$',
            r'^foundation level extensions$',
            r'^istqb.*foundation.*level.*$'
        ]
        
        # Strong heading indicators
        self.strong_heading_patterns = [
            r'^\d+\.\s+[A-Z].*',  # "1. Title"
            r'^\d+\.\d+\s+[A-Z].*',  # "2.1 Title"
            r'^\d+\.\d+\.\d+\s+[A-Z].*',  # "2.1.1 Title"
            r'^(Chapter|Section|Part)\s+\d+',
            r'^(Table of Contents|Acknowledgements?|References?|Bibliography)$',
            r'^(Introduction|Overview|Conclusion|Summary)\s*(to.*)?$',
            r'^Revision\s+History$'
        ]

    def extract_outline(self, pdf_path):
        """Main extraction function"""
        print(f"📄 Processing: {pdf_path.name}")
        
        # Step 1: Extract raw text blocks
        raw_blocks = self._extract_text_blocks(pdf_path)
        if not raw_blocks:
            return {"title": "", "outline": []}
        
        # Step 2: Clean and filter blocks
        clean_blocks = self._clean_blocks(raw_blocks)
        print(f"  📊 Found {len(clean_blocks)} clean text blocks")
        
        # Step 3: Analyze document structure
        doc_analysis = self._analyze_document_structure(clean_blocks)
        
        # Step 4: Extract title
        title = self._extract_title(clean_blocks, doc_analysis)
        print(f"  📑 Title: '{title}'")
        
        # Step 5: Extract headings
        headings = self._extract_headings(clean_blocks, doc_analysis)
        print(f"  🎯 Found {len(headings)} headings")
        
        return {"title": title, "outline": headings}

    def _extract_text_blocks(self, pdf_path):
        """Extract text blocks with metadata"""
        blocks = []
        
        try:
            for page_num, page in enumerate(extract_pages(str(pdf_path), laparams=self.laparams), 1):
                if page_num > 50:  # Limit pages
                    break
                
                page_height = page.height
                page_width = page.width
                
                for element in page:
                    if isinstance(element, LTTextContainer):
                        text = element.get_text().strip()
                        if not text:
                            continue
                        
                        font_info = self._get_detailed_font_info(element)
                        if not font_info:
                            continue
                        
                        # Calculate relative position
                        y_relative = element.bbox[1] / page_height  # 0 = bottom, 1 = top
                        x_relative = element.bbox[0] / page_width   # 0 = left, 1 = right
                        
                        blocks.append({
                            'text': text,
                            'page': page_num,
                            'font_size': font_info['size'],
                            'font_name': font_info['name'],
                            'is_bold': font_info['is_bold'],
                            'bbox': element.bbox,
                            'y_relative': y_relative,
                            'x_relative': x_relative,
                            'line_count': text.count('\n') + 1,
                            'word_count': len(text.split())
                        })
        
        except Exception as e:
            print(f"  ⚠️ Error parsing PDF: {e}")
            return []
        
        return blocks

    def _get_detailed_font_info(self, element):
        """Extract detailed font information"""
        font_data = []
        
        for text_line in element:
            if hasattr(text_line, '_objs'):
                for char in text_line._objs:
                    if isinstance(char, LTChar) and char.get_text().strip():
                        font_data.append({
                            'size': round(char.height, 1),
                            'name': char.fontname or '',
                            'char': char.get_text()
                        })
        
        if not font_data:
            return None
        
        # Get most common font size and name
        sizes = [f['size'] for f in font_data]
        names = [f['name'] for f in font_data if f['name']]
        
        avg_size = sum(sizes) / len(sizes) if sizes else 0
        most_common_name = Counter(names).most_common(1)[0][0] if names else ''
        is_bold = any('bold' in name.lower() for name in names)
        
        return {
            'size': round(avg_size, 1),
            'name': most_common_name,
            'is_bold': is_bold
        }

    def _clean_blocks(self, raw_blocks):
        """Clean and filter text blocks"""
        clean_blocks = []
        
        for block in raw_blocks:
            text = block['text']
            
            # Skip noise
            if self._is_noise_text(text):
                continue
            
            # Skip if too long (likely body text)
            if block['word_count'] > 20:
                continue
            
            # Skip if too small font
            if block['font_size'] < 8:
                continue
            
            # Clean text
            cleaned_text = self._clean_text(text)
            if not cleaned_text:
                continue
            
            block['text'] = cleaned_text
            clean_blocks.append(block)
        
        return clean_blocks

    def _is_noise_text(self, text):
        """Check if text is noise/unwanted"""
        text_lower = text.lower().strip()
        
        # Check against noise patterns
        for pattern in self.noise_patterns:
            if re.match(pattern, text_lower):
                return True
        
        # Skip very short or very long text
        if len(text.strip()) <= 1 or len(text) > 200:
            return True
        
        # Skip if mostly numbers or special characters
        if len(re.sub(r'[^a-zA-Z]', '', text)) < len(text) * 0.3:
            return True
        
        return False

    def _clean_text(self, text):
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\-,;:()&]', ' ', text)
        # Clean up spaces
        text = ' '.join(text.split())
        return text.strip()

    def _analyze_document_structure(self, blocks):
        """Analyze document structure to identify patterns"""
        if not blocks:
            return {}
        
        # Font size analysis
        font_sizes = [b['font_size'] for b in blocks]
        size_counts = Counter(font_sizes)
        
        # Find body text size (most common, medium-sized)
        body_candidates = [size for size, count in size_counts.most_common(5) 
                          if 9 <= size <= 14]  # Typical body text range
        body_size = body_candidates[0] if body_candidates else 12
        
        # Identify heading sizes (larger than body)
        heading_sizes = sorted([size for size in set(font_sizes) 
                               if size > body_size * 1.15], reverse=True)
        
        # Page structure analysis
        pages_with_blocks = defaultdict(list)
        for block in blocks:
            pages_with_blocks[block['page']].append(block)
        
        return {
            'body_size': body_size,
            'heading_sizes': heading_sizes[:4],  # Top 4 heading sizes
            'size_distribution': dict(size_counts),
            'total_pages': max(pages_with_blocks.keys()) if pages_with_blocks else 1,
            'blocks_per_page': dict(pages_with_blocks)
        }

    def _extract_title(self, blocks, doc_analysis):
        """Extract document title"""
        # Focus on first 2 pages for title
        title_candidates = [b for b in blocks if b['page'] <= 2]
        
        if not title_candidates:
            return ""
        
        # Find largest font size in first 2 pages
        max_size = max(b['font_size'] for b in title_candidates)
        
        # Get blocks with largest fonts, prioritizing page 1
        title_blocks = []
        for block in title_candidates:
            if (block['font_size'] >= max_size * 0.95 and 
                block['word_count'] <= 15 and
                block['y_relative'] > 0.3):  # Upper part of page
                
                # Prioritize page 1
                priority = 2 if block['page'] == 1 else 1
                title_blocks.append((priority, block))
        
        # Sort by priority and position
        title_blocks.sort(key=lambda x: (x[0], -x[1]['y_relative']), reverse=True)
        
        # Combine top title blocks
        title_parts = []
        for _, block in title_blocks[:3]:  # Max 3 parts
            text = block['text']
            if not self._is_noise_text(text) and text not in title_parts:
                title_parts.append(text)
        
        return ' '.join(title_parts) if title_parts else ""

    def _extract_headings(self, blocks, doc_analysis):
        """Extract and classify headings"""
        headings = []
        heading_sizes = doc_analysis['heading_sizes']
        body_size = doc_analysis['body_size']
        
        if not heading_sizes:
            return headings
        
        # Define size thresholds
        thresholds = self._calculate_heading_thresholds(heading_sizes, body_size)
        
        for block in blocks:
            level = self._classify_heading(block, thresholds, doc_analysis)
            if level:
                headings.append({
                    'level': level,
                    'text': block['text'],
                    'page': block['page']
                })
        
        # Post-process headings
        headings = self._refine_headings(headings)
        
        # Sort by page and position
        return sorted(headings, key=lambda x: (x['page'], x['text']))

    def _calculate_heading_thresholds(self, heading_sizes, body_size):
        """Calculate font size thresholds for heading levels"""
        thresholds = {}
        
        # Ensure minimum gap from body text
        min_heading_size = body_size * 1.2
        valid_sizes = [size for size in heading_sizes if size >= min_heading_size]
        
        if len(valid_sizes) >= 3:
            thresholds['H1'] = valid_sizes[0]
            thresholds['H2'] = valid_sizes[1] 
            thresholds['H3'] = valid_sizes[2]
        elif len(valid_sizes) >= 2:
            thresholds['H1'] = valid_sizes[0]
            thresholds['H2'] = valid_sizes[1]
        elif len(valid_sizes) >= 1:
            thresholds['H1'] = valid_sizes[0]
        
        return thresholds

    def _classify_heading(self, block, thresholds, doc_analysis):
        """Classify a block as a heading level"""
        text = block['text']
        font_size = block['font_size']
        
        # Must be larger than body text
        if font_size < doc_analysis['body_size'] * 1.15:
            return None
        
        # Calculate heading score
        score = 0
        
        # Font size scoring
        if font_size >= thresholds.get('H1', 999):
            base_level = 'H1'
            score += 10
        elif font_size >= thresholds.get('H2', 999):
            base_level = 'H2'
            score += 8
        elif font_size >= thresholds.get('H3', 999):
            base_level = 'H3'
            score += 6
        else:
            return None
        
        # Pattern-based scoring
        for pattern in self.strong_heading_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                score += 8
                break
        
        # Style-based scoring
        if block['is_bold']:
            score += 3
        
        # Position scoring (top of page)
        if block['y_relative'] > 0.8:
            score += 2
        
        # Length scoring (headings are typically short)
        if block['word_count'] <= 8:
            score += 3
        elif block['word_count'] <= 4:
            score += 5
        
        # Special case: numbered sections should be higher level
        if re.match(r'^\d+\.\s+', text):
            if base_level == 'H2':
                base_level = 'H1'
        elif re.match(r'^\d+\.\d+\s+', text):
            if base_level == 'H3':
                base_level = 'H2'
        
        # Minimum score threshold
        return base_level if score >= 12 else None

    def _refine_headings(self, headings):
        """Post-process and refine headings"""
        if not headings:
            return headings
        
        # Remove duplicates
        seen = set()
        unique_headings = []
        for heading in headings:
            key = (heading['text'].lower().strip(), heading['page'])
            if key not in seen:
                seen.add(key)
                unique_headings.append(heading)
        
        # Adjust levels based on context
        refined_headings = []
        for i, heading in enumerate(unique_headings):
            # Look for numbered patterns to adjust hierarchy
            text = heading['text']
            
            # Main sections (1., 2., 3., etc.) should be H1
            if re.match(r'^\d+\.\s+[A-Z]', text):
                heading['level'] = 'H1'
            # Subsections (1.1, 2.1, etc.) should be H2  
            elif re.match(r'^\d+\.\d+\s+[A-Z]', text):
                heading['level'] = 'H2'
            # Sub-subsections (1.1.1, etc.) should be H3
            elif re.match(r'^\d+\.\d+\.\d+\s+[A-Z]', text):
                heading['level'] = 'H3'
            
            refined_headings.append(heading)
        
        return refined_headings

    def save_json(self, result, output_path):
        """Save result to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)


# Main function for compatibility
def extract_outline(pdf_path):
    extractor = PDFOutlineExtractor()
    result = extractor.extract_outline(Path(pdf_path))
    return result['title'], result['outline']
