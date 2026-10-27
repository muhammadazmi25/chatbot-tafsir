import fitz
import re
import sys
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from test_scanner_enhanced import clean_ocr_digits

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('Chatbot/.env')
engine = create_engine(os.getenv('DATABASE_URL'))

def get_surah_verses(ch_num):
    with engine.connect() as conn:
        q = text('''
            SELECT v.number, v.id, v.text_uthmani, t.text
            FROM verses v
            JOIN chapters c ON v.id_chapter = c.id
            LEFT JOIN verse_translations t ON t.id_verse = v.id AND t.id_translation = 1
            WHERE c.number_chapter = :ch
            ORDER BY v.number
        ''')
        return conn.execute(q, {'ch': ch_num}).fetchall()

def find_boundaries_for_surah(pdf_path, ch_num, surah_name_patt, target_verses, search_range=None):
    doc = fitz.open(pdf_path)
    verses_data = get_surah_verses(ch_num)
    v_dict = {r[0]: {'id': r[1], 'uthmani': r[2], 'indo': r[3]} for r in verses_data}
    
    start_p, end_p = (0, len(doc)) if not search_range else search_range
    print(f"\n=======================================================")
    print(f"Scanning {pdf_path} for Surah {ch_num} (Slides {start_p+1} to {end_p})")
    print(f"=======================================================")
    
    # 1. Scan all citations on each page
    patt = re.compile(rf'\(Qs\.\s*[^)]*{surah_name_patt}[^)]*?\)', re.IGNORECASE)
    page_citations = {}
    for pno in range(start_p, end_p):
        txt = doc[pno].get_text('text').replace('\n', ' ')
        for m in patt.finditer(txt):
            raw = m.group(0)
            digits = [int(x) for x in clean_ocr_digits(raw).split() if x.isdigit()]
            if pno not in page_citations:
                page_citations[pno] = []
            page_citations[pno].append((raw, digits))

    # 2. For each target verse, find candidate slides
    found_map = {}
    for vn in target_verses:
        v_indo = v_dict[vn]['indo'] or ''
        # keywords from translation (first 4 words)
        clean_words = re.sub(r'[^a-zA-Z\s]', '', v_indo).lower().split()
        first_phrase = ' '.join(clean_words[:4]) if len(clean_words) >= 4 else ' '.join(clean_words)
        
        candidates = []
        for pno in range(start_p, end_p):
            # Check citations on this page
            if pno in page_citations:
                for raw, digits in page_citations[pno]:
                    if vn in digits:
                        candidates.append((pno + 1, 'citation', raw[:40]))
                    elif len(digits) >= 2 and min(digits) <= vn <= max(digits) and max(digits) - min(digits) <= 5:
                        candidates.append((pno + 1, 'group_citation', raw[:40]))
                        
            # Check translation text
            if first_phrase and len(first_phrase) > 10:
                txt_p = doc[pno].get_text('text').lower()
                if first_phrase in txt_p:
                    candidates.append((pno + 1, 'indo_phrase', first_phrase))
                    
        found_map[vn] = candidates
        print(f"Verse {vn:3d} -> {candidates[:3]}")
        
    return found_map

# Test on Hud
find_boundaries_for_surah(
    'DATA/pdf/Tafsir 13.pdf', 11, r'(?:Huud|fluud|Hwd)', 
    [12, 14, 37], (780, 944)
)
find_boundaries_for_surah(
    'DATA/pdf/Tafsir 14.pdf', 11, r'(?:Huud|fluud|Hwd)', 
    [37, 41, 43, 47, 51, 56, 67, 68, 78, 79, 89, 90, 96, 97, 98, 102, 112, 114], (0, 450)
)
