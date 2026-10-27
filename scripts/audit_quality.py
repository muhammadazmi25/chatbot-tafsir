import os
import sys
import re
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('Chatbot/.env')
engine = create_engine(os.getenv('DATABASE_URL'))

# Test samples from restored verses:
# Hud 12, 41, 114
# Yusuf 47, 76, 96
# Nahl 12, 90
# Nur 11, 35, 61
sample_verses = [
    (11, 12), (11, 41), (11, 114),
    (12, 47), (12, 76), (12, 96),
    (16, 12), (16, 90),
    (24, 11), (24, 35), (24, 61)
]

with engine.connect() as conn:
    print("=" * 80)
    print("AUDIT KUALITAS HASIL RESTORASI TAFSIR ATH-THABARI")
    print("=" * 80)
    for ch, vn in sample_verses:
        q = text('''
            SELECT v.id, vt.id, LENGTH(vt.text), vt.text, c.name
            FROM verses v
            JOIN chapters c ON v.id_chapter = c.id
            JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = 7
            WHERE c.number_chapter = :ch AND v.number = :vn
        ''')
        r = conn.execute(q, {'ch': ch, 'vn': vn}).fetchone()
        vid, vtid, length, full_txt, sname = r[0], r[1], r[2], r[3], r[4]
        
        # Check for Arabic text
        has_arabic = bool(re.search(r'[\u0600-\u06FF]', full_txt))
        # Check for bad OCR symbols like # &, $, etc.
        bad_symbols = len(re.findall(r'[\#\$\*\{\}\^\~]{2,}', full_txt))
        # Check truncated words
        trunc_words = re.findall(r'\b(?:ters|mer|berk|adlh)\b', full_txt)
        
        print(f"\n[SURAH {ch}:{vn} ({sname})] - Length: {length} chars | vt_id: {vtid}")
        print(f"  Teks Arab ada: {has_arabic} | Bad Symbols: {bad_symbols} | Truncated words: {trunc_words}")
        print("  --- Cuplikan Teks Awal (300 chars) ---")
        print(full_txt[:300].strip())
        print("  --- Cuplikan Teks Akhir (200 chars) ---")
        print(full_txt[-200:].strip())
