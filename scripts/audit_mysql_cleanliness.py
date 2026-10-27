import os
import sys
import re
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('Chatbot/.env')
engine = create_engine(os.getenv('DATABASE_URL'))

def run_deep_audit():
    print("=" * 80)
    print("AUDIT MENDALAM KESIAPAN DATABASE MYSQL UNTUK CHUNKING (QS 11 - QS 24)")
    print("=" * 80)

    with engine.connect() as conn:
        # 1. Total verses & check duplicates
        q_count = text('''
            SELECT 
                COUNT(v.id) as total_verses,
                COUNT(vt.id) as total_tafsir,
                COUNT(DISTINCT v.id) as unique_verses,
                COUNT(DISTINCT vt.id) as unique_tafsir
            FROM verses v
            JOIN chapters c ON v.id_chapter = c.id
            LEFT JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = 7
            WHERE c.number_chapter BETWEEN 11 AND 24
        ''')
        r_cnt = conn.execute(q_count).fetchone()
        print(f"1. VERIFIKASI KUANTITAS:")
        print(f"   - Total Ayat Al-Qur'an (QS 11-24) : {r_cnt[0]}")
        print(f"   - Total Record Tafsir di Database : {r_cnt[1]}")
        print(f"   - Ayat Unik                      : {r_cnt[2]}")
        print(f"   - Tafsir Unik                    : {r_cnt[3]}")
        
        # Check duplicates
        q_dup = text('''
            SELECT v.number, c.number_chapter, COUNT(vt.id) as c
            FROM verses v
            JOIN chapters c ON v.id_chapter = c.id
            JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = 7
            WHERE c.number_chapter BETWEEN 11 AND 24
            GROUP BY v.id, v.number, c.number_chapter
            HAVING c > 1
        ''')
        dups = conn.execute(q_dup).fetchall()
        print(f"   - Duplikasi Record               : {len(dups)} (Harus 0)")
        if dups:
            print(f"     [WARN] Duplikat ditemukan pada: {dups}")

        # 2. Text Length Statistics & Empty/Short text
        q_stats = text('''
            SELECT 
                MIN(LENGTH(vt.text)) as min_len,
                MAX(LENGTH(vt.text)) as max_len,
                AVG(LENGTH(vt.text)) as avg_len,
                SUM(CASE WHEN vt.text IS NULL OR LENGTH(TRIM(vt.text)) = 0 THEN 1 ELSE 0 END) as empty_cnt,
                SUM(CASE WHEN LENGTH(vt.text) < 100 THEN 1 ELSE 0 END) as short_cnt
            FROM verses v
            JOIN chapters c ON v.id_chapter = c.id
            JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = 7
            WHERE c.number_chapter BETWEEN 11 AND 24
        ''')
        r_stats = conn.execute(q_stats).fetchone()
        print(f"\n2. STATISTIK PANJANG TEKS:")
        print(f"   - Minimal Karakter               : {r_stats[0]} chars")
        print(f"   - Maksimal Karakter              : {r_stats[1]} chars")
        print(f"   - Rata-rata Karakter             : {int(r_stats[2])} chars")
        print(f"   - Record Kosong / NULL           : {int(r_stats[3])} (Harus 0)")
        print(f"   - Record Terlalu Pendek (<100c)  : {int(r_stats[4])} (Harus 0)")

        # 3. Scan all 1500 records for bad artifacts
        q_all = text('''
            SELECT v.number, c.number_chapter, c.name, vt.id, vt.text
            FROM verses v
            JOIN chapters c ON v.id_chapter = c.id
            JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = 7
            WHERE c.number_chapter BETWEEN 11 AND 24
            ORDER BY c.number_chapter, v.number
        ''')
        rows = conn.execute(q_all).fetchall()

        no_arabic_cnt = 0
        bad_symbols_cnt = 0
        truncated_words_cnt = 0
        markers_takwil_cnt = 0
        markers_firman_cnt = 0
        hadits_num_cnt = 0

        bad_symbol_pattern = re.compile(r'[\#\$\*\{\}\^\~]{2,}')
        trunc_pattern = re.compile(r'\b(?:ters|mer|adlh)\b', re.IGNORECASE)
        hadits_num_pattern = re.compile(r'\b[12]\d{4}\.')

        for r in rows:
            txt = r[4]
            # Check Arabic
            if not re.search(r'[\u0600-\u06FF]', txt):
                no_arabic_cnt += 1
            # Check bad symbols
            if bad_symbol_pattern.search(txt):
                bad_symbols_cnt += 1
            # Check truncated words
            if trunc_pattern.search(txt):
                truncated_words_cnt += 1
            # Check structural markers for chunking
            if 'takwil firman' in txt.lower():
                markers_takwil_cnt += 1
            if 'firman-nya' in txt.lower() or 'firman allah' in txt.lower():
                markers_firman_cnt += 1
            if hadits_num_pattern.search(txt):
                hadits_num_cnt += 1

        print(f"\n3. PEMERIKSAAN KUALITAS & KEBERSIHAN:")
        print(f"   - Ayat tanpa Huruf Arab          : {no_arabic_cnt} (Harus 0)")
        print(f"   - Record dengan Simbol Rusak     : {bad_symbols_cnt}")
        print(f"   - Record dengan Kata Terpotong   : {truncated_words_cnt}")

        print(f"\n4. KESIAPAN PENANDA STRUKTURAL CHUNK:")
        print(f"   - Ayat dengan penanda 'Takwil'   : {markers_takwil_cnt} / {len(rows)} ({(markers_takwil_cnt/len(rows))*100:.1f}%)")
        print(f"   - Ayat dengan penanda 'Firman'   : {markers_firman_cnt} / {len(rows)} ({(markers_firman_cnt/len(rows))*100:.1f}%)")
        print(f"   - Ayat dengan nomor hadits/atsar : {hadits_num_cnt} / {len(rows)} ({(hadits_num_cnt/len(rows))*100:.1f}%)")

        print("=" * 80)
        is_ready = (r_cnt[0] == r_cnt[1] == 1382) and (r_stats[3] == 0) and (no_arabic_cnt == 0) and (len(dups) == 0) and (truncated_words_cnt == 0)
        if is_ready:
            print("KESIMPULAN: DATABASE 100% BERSIH, LENGKAP, DAN SIAP DI-GENERATE MENJADI CHUNK!")
        else:
            print("KESIMPULAN: PERLU PERBAIKAN LEBIH LANJUT SEBELUM CHUNKING.")
        print("=" * 80)

if __name__ == '__main__':
    run_deep_audit()
