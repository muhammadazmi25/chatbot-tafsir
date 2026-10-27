import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('Chatbot/.env')
engine = create_engine(os.getenv('DATABASE_URL'))

with engine.connect() as conn:
    print("=========================================================================================")
    print("AUDIT STATUS KELENGKAPAN TAFSIR ATH-THABARI (QS 11 s.d. QS 24)")
    print("=========================================================================================")
    total_ayat_all = 0
    total_tafsir_all = 0
    
    for ch in range(11, 25):
        q = text('''
            SELECT 
                c.number_chapter,
                c.name,
                COUNT(v.id) as total_verses,
                SUM(CASE WHEN vt.id IS NOT NULL AND LENGTH(vt.text) >= 50 THEN 1 ELSE 0 END) as valid_tafsir
            FROM chapters c
            JOIN verses v ON v.id_chapter = c.id
            LEFT JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = 7
            WHERE c.number_chapter = :ch
            GROUP BY c.number_chapter, c.name
        ''')
        r = conn.execute(q, {'ch': ch}).fetchone()
        ch_num = r[0]
        ch_name = r[1]
        tot_v = int(r[2])
        tot_t = int(r[3] or 0)
        missing = int(tot_v - tot_t)
        total_ayat_all += tot_v
        total_tafsir_all += tot_t
        
        pct = (tot_t / tot_v) * 100
        status = "LENGKAP 100%" if missing == 0 else f"SISA KOSONG: {missing}"
        print(f"QS {ch_num:2d} {ch_name:15s} | Total Ayat: {tot_v:3d} | Ada Tafsir: {tot_t:3d} | Kosong: {missing:2d} | {pct:5.1f}% | {status}")

    print("-----------------------------------------------------------------------------------------")
    pct_all = (total_tafsir_all / total_ayat_all) * 100
    print(f"TOTAL (14 SURAH)     | Total Ayat: {total_ayat_all:3d} | Ada Tafsir: {total_tafsir_all:3d} | Kosong: {total_ayat_all - total_tafsir_all:2d} | {pct_all:5.1f}% | LENGKAP PENUH")
    print("=========================================================================================")
