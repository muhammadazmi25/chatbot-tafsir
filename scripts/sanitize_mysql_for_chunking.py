"""
Skrip Sanitasi dan Pembersihan Total Database MySQL untuk Tafsir Ath-Thabari (QS 11 - QS 24).
Menyiapkan database agar 100% bersih, valid, dan siap diproses oleh DATA/generate_tafsir.ipynb.

Langkah-langkah:
1. Reset tabel-tabel chunk turunan (tafsir_takwil_units dan semua relasinya).
2. Deduplikasi verse_tafsirs (hapus 118 baris berlebih, sisakan 1 baris terlengkap per ayat -> tepat 1382 baris).
3. Injeksi teks Arab Al-Qur'an resmi pada 11 ayat di Surah Yusuf yang teks Arab awalnya terlewat.
4. Perbaikan kata terpotong (mereka, tersebut, karena, sebelum, mengenai, memberi).
5. Audit akhir untuk memverifikasi 100% kesiapan database.
"""

import os
import sys
import re
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('Chatbot/.env')

DB_URL = os.getenv('DATABASE_URL')
if not DB_URL:
    raise ValueError("DATABASE_URL tidak ditemukan di Chatbot/.env")

engine = create_engine(DB_URL)

TAFSIR_ID = 7
SURAH_START = 11
SURAH_END = 24

def fix_indonesian_tokens(content: str) -> str:
    """Memperbaiki kata-kata yang terpotong akibat artefak skrip pembersih lama."""
    # 1. Mereka
    content = re.sub(r'\bMer\b', 'Mereka', content)
    content = re.sub(r'\bmer\b', 'mereka', content)
    
    # 2. Tersebut
    content = re.sub(r'\bTers\b', 'Tersebut', content)
    content = re.sub(r'\bters\b', 'tersebut', content)
    
    # 3. Karena
    content = re.sub(r'\bKar\b', 'Karena', content)
    content = re.sub(r'\bkar\b', 'karena', content)
    
    # 4. Mengenai
    content = re.sub(r'\bMeng\b', 'Mengenai', content)
    content = re.sub(r'\bmeng\b', 'mengenai', content)
    
    # 5. Memberi
    content = re.sub(r'\bMemb\b', 'Memberi', content)
    content = re.sub(r'\bmemb\b', 'memberi', content)
    
    # 6. Sebelum & Sebenar-benarnya
    content = re.sub(r'seb-benarnya', 'sebenar-benarnya', content, flags=re.IGNORECASE)
    content = re.sub(r'\bSeb\b', 'Sebelum', content)
    content = re.sub(r'\bseb\b', 'sebelum', content)
    
    # 7. Typo umum OCR cetakan
    content = content.replace('adatah', 'adalah')
    content = content.replace('bafuwa', 'bahwa')
    content = content.replace('slahih', 'shahih')
    content = content.replace('Atlatr', 'Allah')
    
    return content

def run_sanitization():
    print("=" * 80)
    print("MEMULAI PROSES SANITASI DAN PEMBESIHAN TOTAL DATABASE MYSQL (QS 11 - QS 24)")
    print("=" * 80)

    with engine.begin() as conn:
        # ---------------------------------------------------------------------
        # LANGKAH 1: KOSONGKAN TABEL CHUNK TURUNAN
        # ---------------------------------------------------------------------
        print("\n[LANGKAH 1] Mengosongkan tabel-tabel chunk turunan lama...")
        
        # Ambil semua id_verse_tafsir untuk QS 11 - 24
        q_vt_ids = text("""
            SELECT vt.id
            FROM verse_tafsirs vt
            JOIN verses v ON vt.id_verse = v.id
            JOIN chapters c ON v.id_chapter = c.id
            WHERE vt.id_tafsir = :id_tafsir AND c.number_chapter BETWEEN :s_start AND :s_end
        """)
        vt_rows = conn.execute(q_vt_ids, {
            "id_tafsir": TAFSIR_ID,
            "s_start": SURAH_START,
            "s_end": SURAH_END
        }).fetchall()
        
        all_vt_ids = [r[0] for r in vt_rows]
        print(f"  Terdeteksi {len(all_vt_ids)} baris verse_tafsirs untuk QS 11-24.")

        if all_vt_ids:
            vt_ids_str = ",".join(str(i) for i in all_vt_ids)
            
            # Hapus bertingkat sesuai Foreign Key:
            # 1. Cucu: tafsir_riwayat
            del_riwayat = conn.execute(text(f"""
                DELETE r FROM tafsir_riwayat r
                JOIN tafsir_aqwal a ON r.id_qaul = a.id
                JOIN tafsir_takwil_units u ON a.id_unit = u.id
                WHERE u.id_verse_tafsir IN ({vt_ids_str})
            """)).rowcount
            print(f"  -> Terhapus {del_riwayat} baris dari `tafsir_riwayat`.")

            # 2. Anak-anak: aqwal, evidence, naqd, tarjih, qiraat
            del_ev = conn.execute(text(f"""
                DELETE e FROM tafsir_evidence e
                JOIN tafsir_takwil_units u ON e.id_unit = u.id
                WHERE u.id_verse_tafsir IN ({vt_ids_str})
            """)).rowcount
            print(f"  -> Terhapus {del_ev} baris dari `tafsir_evidence`.")

            del_naqd = conn.execute(text(f"""
                DELETE n FROM tafsir_naqd n
                JOIN tafsir_takwil_units u ON n.id_unit = u.id
                WHERE u.id_verse_tafsir IN ({vt_ids_str})
            """)).rowcount
            print(f"  -> Terhapus {del_naqd} baris dari `tafsir_naqd`.")

            del_tarjih = conn.execute(text(f"""
                DELETE t FROM tafsir_tarjih t
                JOIN tafsir_takwil_units u ON t.id_unit = u.id
                WHERE u.id_verse_tafsir IN ({vt_ids_str})
            """)).rowcount
            print(f"  -> Terhapus {del_tarjih} baris dari `tafsir_tarjih`.")

            del_qiraat = conn.execute(text(f"""
                DELETE q FROM tafsir_qiraat q
                JOIN tafsir_takwil_units u ON q.id_unit = u.id
                WHERE u.id_verse_tafsir IN ({vt_ids_str})
            """)).rowcount
            print(f"  -> Terhapus {del_qiraat} baris dari `tafsir_qiraat`.")

            del_aqwal = conn.execute(text(f"""
                DELETE a FROM tafsir_aqwal a
                JOIN tafsir_takwil_units u ON a.id_unit = u.id
                WHERE u.id_verse_tafsir IN ({vt_ids_str})
            """)).rowcount
            print(f"  -> Terhapus {del_aqwal} baris dari `tafsir_aqwal`.")

            # 3. Induk unit: tafsir_takwil_units
            del_units = conn.execute(text(f"""
                DELETE FROM tafsir_takwil_units
                WHERE id_verse_tafsir IN ({vt_ids_str})
            """)).rowcount
            print(f"  -> Terhapus {del_units} baris dari `tafsir_takwil_units`.")

        print("  [OK] Seluruh tabel chunk turunan telah dikosongkan dengan aman.")

        # ---------------------------------------------------------------------
        # LANGKAH 2: DEDUPLIKASI VERSE_TAFSIRS
        # ---------------------------------------------------------------------
        print("\n[LANGKAH 2] Memproses deduplikasi record di `verse_tafsirs`...")
        
        q_all_vt = text("""
            SELECT vt.id, vt.id_verse, LENGTH(vt.text) as len, c.number_chapter, v.number
            FROM verse_tafsirs vt
            JOIN verses v ON vt.id_verse = v.id
            JOIN chapters c ON v.id_chapter = c.id
            WHERE vt.id_tafsir = :id_tafsir AND c.number_chapter BETWEEN :s_start AND :s_end
            ORDER BY vt.id_verse, LENGTH(vt.text) DESC, vt.id ASC
        """)
        all_rows = conn.execute(q_all_vt, {
            "id_tafsir": TAFSIR_ID,
            "s_start": SURAH_START,
            "s_end": SURAH_END
        }).fetchall()

        seen_verses = set()
        keep_vt_ids = []
        dup_delete_ids = []

        for r in all_rows:
            vid = r[1]
            if vid not in seen_verses:
                seen_verses.add(vid)
                keep_vt_ids.append(r[0])
            else:
                dup_delete_ids.append(r[0])

        print(f"  Total baris diperiksa : {len(all_rows)}")
        print(f"  Ayat unik dipertahankan: {len(keep_vt_ids)} (target: 1382)")
        print(f"  Duplikat akan dihapus : {len(dup_delete_ids)} (target: 118)")

        if dup_delete_ids:
            dup_str = ",".join(str(i) for i in dup_delete_ids)
            del_dup_count = conn.execute(text(f"DELETE FROM verse_tafsirs WHERE id IN ({dup_str})")).rowcount
            print(f"  -> Sukses menghapus {del_dup_count} baris duplikat dari `verse_tafsirs`.")
        else:
            print("  -> Tidak ada duplikat yang perlu dihapus.")

        # ---------------------------------------------------------------------
        # LANGKAH 3: INJEKSI TEKS ARAB PADA 11 AYAT YUSUF
        # ---------------------------------------------------------------------
        print("\n[LANGKAH 3] Menginjeksi teks Arab Utsmani pada ayat Surah Yusuf yang terlewat...")
        yusuf_targets = [43, 44, 45, 71, 72, 80, 81, 82, 83, 84, 85]
        
        q_yusuf = text("""
            SELECT vt.id, v.number, v.text_uthmani, vt.text
            FROM verse_tafsirs vt
            JOIN verses v ON vt.id_verse = v.id
            JOIN chapters c ON v.id_chapter = c.id
            WHERE vt.id_tafsir = :id_tafsir AND c.number_chapter = 12 AND v.number IN :nums
        """)
        yusuf_rows = conn.execute(q_yusuf, {
            "id_tafsir": TAFSIR_ID,
            "nums": tuple(yusuf_targets)
        }).fetchall()

        yusuf_fixed_cnt = 0
        for yr in yusuf_rows:
            vt_id, v_num, ar_text, cur_text = yr[0], yr[1], yr[2], yr[3]
            # Cek jika belum ada huruf Arab di baris pembuka
            if not re.search(r'[\u0600-\u06FF]', cur_text[:100]):
                fixed_text = f"\r\n{ar_text} \r\n" + cur_text.lstrip('\r\n ')
                conn.execute(
                    text("UPDATE verse_tafsirs SET text = :text WHERE id = :id"),
                    {"text": fixed_text, "id": vt_id}
                )
                yusuf_fixed_cnt += 1
                print(f"  -> Sukses menambahkan teks Arab pada QS 12:{v_num} (ID: {vt_id})")

        print(f"  Total ayat Surah Yusuf diperbaiki: {yusuf_fixed_cnt} ayat.")

        # ---------------------------------------------------------------------
        # LANGKAH 4: RESTORASI KATA TERPOTONG & TYPO OCR
        # ---------------------------------------------------------------------
        print("\n[LANGKAH 4] Memulihkan kata terpotong (mereka, tersebut, karena, sebelum, dll)...")
        
        q_get_all_clean = text("""
            SELECT vt.id, c.number_chapter, v.number, vt.text
            FROM verse_tafsirs vt
            JOIN verses v ON vt.id_verse = v.id
            JOIN chapters c ON v.id_chapter = c.id
            WHERE vt.id_tafsir = :id_tafsir AND c.number_chapter BETWEEN :s_start AND :s_end
        """)
        active_rows = conn.execute(q_get_all_clean, {
            "id_tafsir": TAFSIR_ID,
            "s_start": SURAH_START,
            "s_end": SURAH_END
        }).fetchall()

        token_fixed_cnt = 0
        for row in active_rows:
            vt_id, s_num, v_num, original_txt = row[0], row[1], row[2], row[3]
            cleaned_txt = fix_indonesian_tokens(original_txt)
            if cleaned_txt != original_txt:
                conn.execute(
                    text("UPDATE verse_tafsirs SET text = :text WHERE id = :id"),
                    {"text": cleaned_txt, "id": vt_id}
                )
                token_fixed_cnt += 1

        print(f"  -> Sukses mereparasi teks pada {token_fixed_cnt} record ayat.")

    # -------------------------------------------------------------------------
    # LANGKAH 5: AUDIT & VERIFIKASI AKHIR
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("VERIFIKASI AKHIR STATUS KEBERSIHAN DATABASE")
    print("=" * 80)

    with engine.connect() as conn:
        # Cek jumlah ayat unik & baris verse_tafsirs
        q_check = text("""
            SELECT 
                COUNT(v.id) as total_verses,
                COUNT(vt.id) as total_tafsir,
                COUNT(DISTINCT v.id) as unique_verses,
                COUNT(DISTINCT vt.id) as unique_tafsir
            FROM verses v
            JOIN chapters c ON v.id_chapter = c.id
            LEFT JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = 7
            WHERE c.number_chapter BETWEEN 11 AND 24
        """)
        c_res = conn.execute(q_check).fetchone()

        # Cek duplikasi
        q_check_dup = text("""
            SELECT v.number, c.number_chapter, COUNT(vt.id) as c
            FROM verses v
            JOIN chapters c ON v.id_chapter = c.id
            JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = 7
            WHERE c.number_chapter BETWEEN 11 AND 24
            GROUP BY v.id, v.number, c.number_chapter
            HAVING c > 1
        """)
        remaining_dups = conn.execute(q_check_dup).fetchall()

        # Cek kualitas teks
        q_scan = text("""
            SELECT v.number, c.number_chapter, vt.text
            FROM verses v
            JOIN chapters c ON v.id_chapter = c.id
            JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = 7
            WHERE c.number_chapter BETWEEN 11 AND 24
        """)
        scan_rows = conn.execute(q_scan).fetchall()

        no_arab = 0
        rem_trunc = 0
        trunc_patt = re.compile(r'\b(?:ters|mer|adlh)\b', re.IGNORECASE)

        for r in scan_rows:
            if not re.search(r'[\u0600-\u06FF]', r[2]):
                no_arab += 1
            if trunc_patt.search(r[2]):
                rem_trunc += 1

        # Cek tabel chunk
        q_units = text("SELECT count(*) FROM tafsir_takwil_units")
        rem_units = conn.execute(q_units).fetchone()[0]

        print(f"1. Total Ayat Al-Qur'an (QS 11-24) : {c_res[0]} ayat")
        print(f"2. Total Record Tafsir di DB       : {c_res[1]} record (harus persis 1382)")
        print(f"3. Duplikasi Record                : {len(remaining_dups)} (harus 0)")
        print(f"4. Ayat tanpa Teks Arab            : {no_arab} (harus 0)")
        print(f"5. Record Kata Terpotong           : {rem_trunc} (harus 0)")
        print(f"6. Sisa Baris di tafsir_takwil_units: {rem_units} (siap 0 untuk re-generate)")
        print("=" * 80)

        is_perfect = (c_res[0] == c_res[1] == 1382) and (len(remaining_dups) == 0) and (no_arab == 0) and (rem_trunc == 0) and (rem_units == 0)

        if is_perfect:
            print("STATUS: 100% BERSIH, LENGKAP, DAN SEMPURNA!")
            print("Database MySQL sudah SEPENUHNYA SIAP untuk di-generate ulang dengan generate_tafsir.ipynb.")
        else:
            print("STATUS: Masih ada anomali yang perlu diperiksa.")
        print("=" * 80)

if __name__ == '__main__':
    run_sanitization()
