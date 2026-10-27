import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('Chatbot/.env')
engine = create_engine(os.getenv('DATABASE_URL'))

RESTORED_TARGETS = {
    11: [12, 14, 37, 41, 43, 47, 51, 56, 67, 68, 78, 79, 89, 90, 96, 97, 98, 102, 112, 114],
    12: [47, 54, 57, 59, 61, 62, 65, 69, 76, 77, 79, 96],
    16: [12, 18, 29, 90],
    17: [38],
    21: [69],
    23: [75],
    24: list(range(11, 65))
}

with engine.connect() as conn:
    print("=== DAFTAR 93 AYAT YANG BERHASIL DIRESTORASI ===")
    total_found = 0
    for ch, v_list in RESTORED_TARGETS.items():
        q = text('''
            SELECT v.number, v.id, vt.id, LENGTH(vt.text), c.name
            FROM verses v
            JOIN chapters c ON v.id_chapter = c.id
            JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = 7
            WHERE c.number_chapter = :ch AND v.number IN :v_list
            ORDER BY v.number
        ''')
        rows = conn.execute(q, {'ch': ch, 'v_list': tuple(v_list)}).fetchall()
        print(f"\n[Surah {ch} - {rows[0][4] if rows else ''}] ({len(rows)} Ayat):")
        for r in rows:
            print(f"  Ayat {r[0]:2d} | id_verse: {r[1]:4d} | vt_id: {r[2]:5d} | Panjang Teks: {r[3]:5d} chars")
            total_found += 1

    print(f"\nTotal Ayat Terverifikasi: {total_found}/93 ayat!")
