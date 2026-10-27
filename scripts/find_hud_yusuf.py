import fitz
import re
import sys
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('Chatbot/.env')
engine = create_engine(os.getenv('DATABASE_URL'))

# Missing Hud: [12, 14, 37, 41, 43, 47, 51, 56, 67, 68, 78, 79, 89, 90, 96, 97, 98, 102, 112, 114]
# Missing Yusuf: [47, 54, 57, 59, 61, 62, 65, 69, 76, 77, 79, 96]

def get_verse_info(ch, nums):
    with engine.connect() as conn:
        q = text('''
            SELECT v.number, v.id, v.text_uthmani, t.text as indo
            FROM verses v
            JOIN chapters c ON v.id_chapter = c.id
            LEFT JOIN verse_translations t ON t.id_verse = v.id AND t.id_translation = 1
            WHERE c.number_chapter = :ch AND v.number IN :nums
            ORDER BY v.number
        ''')
        return conn.execute(q, {'ch': ch, 'nums': tuple(nums)}).fetchall()

hud_verses = get_verse_info(11, [12, 14, 37, 41, 43, 47, 51, 56, 67, 68, 78, 79, 89, 90, 96, 97, 98, 102, 112, 114])
yusuf_verses = get_verse_info(12, [47, 54, 57, 59, 61, 62, 65, 69, 76, 77, 79, 96])

doc13 = fitz.open('DATA/pdf/Tafsir 13.pdf')
doc14 = fitz.open('DATA/pdf/Tafsir 14.pdf')

print("=== CHECKING HUD MISSING VERSES ===")
for v in hud_verses:
    vnum, vid, ar, indo = v[0], v[1], v[2], v[3]
    first_words = ' '.join(indo.split()[:4]).lower() if indo else ''
    found_anchors = []
    
    # Search in doc13 (verses 1-36) and doc14 (verses 37-123)
    target_docs = [('Tafsir 13', doc13)] if vnum < 37 else [('Tafsir 14', doc14)]
    if vnum in [35, 36, 37, 38]:
        target_docs = [('Tafsir 13', doc13), ('Tafsir 14', doc14)]
        
    for doc_name, doc in target_docs:
        for pno in range(len(doc)):
            txt = doc[pno].get_text('text')
            # Look for (Qs. Huud ... vnum ...)
            if f': {vnum}' in txt or f':{vnum}' in txt or f' {vnum})' in txt or f'-{vnum}' in txt or f'{vnum}-' in txt:
                m = re.findall(rf'\(Qs\.[^)]*?H[uU]+d[^)]*?\)', txt, re.IGNORECASE)
                if m:
                    for match in m:
                        if str(vnum) in match:
                            found_anchors.append(f"{doc_name} Slide {pno+1}: {match.strip()}")
            elif first_words and first_words in txt.lower():
                found_anchors.append(f"{doc_name} Slide {pno+1} [keyword match: {first_words}]: {txt[:100].strip().replace(chr(10), ' ')}")

    print(f"Hud Ayat {vnum}: {found_anchors[:3]}")

print("\n=== CHECKING YUSUF MISSING VERSES ===")
for v in yusuf_verses:
    vnum, vid, ar, indo = v[0], v[1], v[2], v[3]
    first_words = ' '.join(indo.split()[:4]).lower() if indo else ''
    found_anchors = []
    for pno in range(len(doc14)):
        txt = doc14[pno].get_text('text')
        if f': {vnum}' in txt or f':{vnum}' in txt or f' {vnum})' in txt or f'-{vnum}' in txt or f'{vnum}-' in txt:
            m = re.findall(rf'\(Qs\.[^)]*?Y[uU]+suf[^)]*?\)', txt, re.IGNORECASE)
            if m:
                for match in m:
                    if str(vnum) in match:
                        found_anchors.append(f"Tafsir 14 Slide {pno+1}: {match.strip()}")
        elif first_words and first_words in txt.lower():
            clean_txt = txt[:100].strip().replace('\n', ' ')
            found_anchors.append(f"Tafsir 14 Slide {pno+1} [keyword match: {first_words}]: {clean_txt}")

    print(f"Yusuf Ayat {vnum}: {found_anchors[:3]}")
