import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('Chatbot/.env')
engine = create_engine(os.getenv('DATABASE_URL'))

# 4 verses that are already present in the grouped text of the database:
# 1. Surah 17:38 (id_verse=2067) from 17:37 (vt_id=38049)
# 2. Surah 21:69 (id_verse=2552) from 21:68 (vt_id=38540)
# 3. Surah 23:75 (id_verse=2748) from 23:74 (vt_id=38747)
# 4. Surah 16:18 (id_verse=1919) from 16:17 (vt_id=37900)

GROUPED_TARGETS = [
    (17, 38, 2067, 38049),
    (21, 69, 2552, 38540),
    (23, 75, 2748, 38747),
    (16, 18, 1919, 37900),
]

with engine.begin() as conn:
    for ch, vnum, target_vid, source_vtid in GROUPED_TARGETS:
        # Get source text
        src = conn.execute(text('SELECT text FROM verse_tafsirs WHERE id = :id'), {'id': source_vtid}).fetchone()
        if not src:
            print(f"[ERROR] Source vt_id {source_vtid} not found!")
            continue
        src_text = src[0]
        
        # Check if target already exists
        tgt = conn.execute(text('SELECT id FROM verse_tafsirs WHERE id_verse = :vid AND id_tafsir = 7'), {'vid': target_vid}).fetchone()
        if tgt:
            conn.execute(text('UPDATE verse_tafsirs SET text = :text WHERE id = :id'), {'text': src_text, 'id': tgt[0]})
            print(f"[UPDATE] Surah {ch}:{vnum} (id_verse={target_vid}) updated using source vt_id {source_vtid}")
        else:
            conn.execute(text('INSERT INTO verse_tafsirs (id_verse, id_tafsir, text) VALUES (:vid, 7, :text)'), {'vid': target_vid, 'text': src_text})
            print(f"[INSERT] Surah {ch}:{vnum} (id_verse={target_vid}) inserted using source vt_id {source_vtid}")

print("Selesai restorasi 4 ayat gabungan!")
