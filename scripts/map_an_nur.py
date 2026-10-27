import fitz
import re
import sys
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('Chatbot/.env')
engine = create_engine(os.getenv('DATABASE_URL'))

with engine.connect() as conn:
    rows = conn.execute(text('''
        SELECT v.number, v.id, v.text_uthmani, t.text
        FROM verses v
        JOIN chapters c ON v.id_chapter = c.id
        LEFT JOIN verse_translations t ON t.id_verse = v.id AND t.id_translation = 1
        WHERE c.number_chapter = 24 AND v.number BETWEEN 11 AND 64
        ORDER BY v.number
    ''')).fetchall()

doc = fitz.open('DATA/pdf/Tafsir 19.pdf')

print("Mapping 54 verses of An-Nur (11 to 64)...")
verse_map = {}

# Pre-extract text of first 320 slides
pages_text = [doc[i].get_text('text') for i in range(320)]

for r in rows:
    vnum, vid, ar, indo = r[0], r[1], r[2], r[3]
    # Clean first few words of translation
    clean_indo = re.sub(r'[^a-zA-Z\s]', '', indo or '').lower().split()
    first_phrase = ' '.join(clean_indo[:4]) if len(clean_indo) >= 4 else ' '.join(clean_indo)
    second_phrase = ' '.join(clean_indo[2:6]) if len(clean_indo) >= 6 else first_phrase
    
    matches = []
    for pno, txt in enumerate(pages_text):
        txt_lower = txt.lower()
        # Check Qs citation
        # e.g. An Nuur ... : vnum or :vnum or : vnum-
        patterns = [
            rf'\(qs\.[^)]*nu+r[^)]*?[:z\.\s\|]\s*{vnum}[^0-9]',
            rf'\(qs\.[^)]*nu+r[^)]*?[:z\.\s\|]\s*[0-9l\,\.\-\'\"]*[\,\.\-]{vnum}[^0-9]',
            rf'\(qs\.[^)]*nu+r[^)]*?[:z\.\s\|]\s*{vnum}-',
        ]
        for pat in patterns:
            if re.search(pat, txt_lower):
                matches.append((pno + 1, 'citation'))
                break
        
        # Also check translation opening
        if first_phrase and first_phrase in txt_lower:
            matches.append((pno + 1, 'phrase1'))
        elif second_phrase and second_phrase in txt_lower:
            matches.append((pno + 1, 'phrase2'))

    print(f"Verse {vnum:2d} matches: {matches[:3]}")
