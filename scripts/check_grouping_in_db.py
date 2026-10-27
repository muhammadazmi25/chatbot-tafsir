import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('Chatbot/.env')
engine = create_engine(os.getenv('DATABASE_URL'))

missing = {
    11: [12, 14, 37, 41, 43, 47, 51, 56, 67, 68, 78, 79, 89, 90, 96, 97, 98, 102, 112, 114],
    12: [47, 54, 57, 59, 61, 62, 65, 69, 76, 77, 79, 96]
}

with engine.connect() as conn:
    for ch, vnums in missing.items():
        print(f"\n==========================================")
        print(f"CHECKING SURAH {ch}")
        print(f"==========================================")
        for vn in vnums:
            # Ambil potongan teks arab & terjemahan dari verse yang hilang
            vinfo = conn.execute(text('''
                SELECT v.id, v.text_uthmani, t.text
                FROM verses v
                JOIN chapters c ON v.id_chapter = c.id
                LEFT JOIN verse_translations t ON t.id_verse = v.id AND t.id_translation = 1
                WHERE c.number_chapter = :ch AND v.number = :vn
            '''), {'ch': ch, 'vn': vn}).fetchone()
            
            vid, uthmani, indo = vinfo[0], vinfo[1], vinfo[2]
            # Ambil beberapa kata kunci bahasa indonesia
            indo_words = [w for w in indo.split() if len(w) > 4][:3] if indo else []
            
            # Cek tetangga: vn-1, vn-2, vn+1, vn+2
            neighbors = [vn-2, vn-1, vn+1, vn+2]
            found_in = []
            for n in neighbors:
                if n < 1: continue
                n_row = conn.execute(text('''
                    SELECT v.number, vt.id, vt.text
                    FROM verses v
                    JOIN chapters c ON v.id_chapter = c.id
                    JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = 7
                    WHERE c.number_chapter = :ch AND v.number = :n
                '''), {'ch': ch, 'n': n}).fetchone()
                
                if n_row and n_row[2]:
                    ntxt = n_row[2]
                    # Cek apakah nomor ayat atau kata kunci terjemahan ada di teks tetangga
                    matches_kw = [w for w in indo_words if w.lower() in ntxt.lower()]
                    if len(matches_kw) >= 2 or f"[{ch}]: {vn}" in ntxt or f"[{ch}]:{vn}" in ntxt or f"{vn}-" in ntxt or f"-{vn}" in ntxt:
                        found_in.append((n_row[0], n_row[1], matches_kw))
            
            print(f"Ayat {vn} (id={vid}): matches in neighbors -> {found_in}")
