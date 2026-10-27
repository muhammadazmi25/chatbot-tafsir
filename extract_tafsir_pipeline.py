"""
Pipeline Ekstraksi Teks Tafsir Ath-Thabari dari PDF ke Database MySQL.
Mendukung:
1. Surah Hud (11): Ayat 1 - 36 (dari Tafsir 13.pdf) dan Ayat 37 - 115 (dari Tafsir 14.pdf)
2. Surah Yusuf (12): Ayat-ayat yang kosong (46-70, 73-79, 96) (dari Tafsir 14.pdf)
"""

import os
import sys
import re
import argparse
from collections import defaultdict
import fitz  # PyMuPDF
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('Chatbot/.env')

DB_URL = os.getenv('DATABASE_URL')
engine = create_engine(DB_URL) if DB_URL else None

PDF_13 = 'DATA/pdf/Tafsir 13.pdf'
PDF_14 = 'DATA/pdf/Tafsir 14.pdf'

FOOTNOTE_KEYWORDS = [
    'ibnu abi hatim dalam tafsir', 'zad al masir', 'an-nukat wa al',
    'ma\'alim at-tanzil', 'abdurrazzaq dalam tafsir', 'lihat tafsir',
    'ad-durr al-mantsur', 'ibnu katsir', 'fath al-bari', 'ibid.'
]

HEADER_PATTERNS = re.compile(
    r'^(?:TddwAt/l\.Thabmi|Tatsir\s+Ath:Ihahdri|TafurAthflhabai|TCstultt/l\.:Ihafuri|Tds,fAth:Ilutui|Tq6tuAh:Ihatui|SURAH\s+HUUD|SurrchHuud|SunclrHrlud|SurohHuud|SurahHtmd|SurahHllnrd|SurahHwd|SURAH\s+Y[Uu]+SUF|Surah\s+Y[Uu]+suf|TafshNi:Ihabari|Tafsir\s+Ath:fhabari|TafsbAthllwbdri)',
    re.IGNORECASE | re.MULTILINE
)

def get_missing_verses(surah_no):
    """Ambil daftar nomor ayat yang masih NULL/kosong di database untuk Ath-Thabari (id_tafsir=7)."""
    if not engine:
        return []
    with engine.connect() as conn:
        q = text("""
            SELECT v.number
            FROM verses v
            JOIN chapters c ON v.id_chapter = c.id
            LEFT JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = 7
            WHERE c.number_chapter = :surah_no AND vt.id IS NULL
            ORDER BY v.number
        """)
        rows = conn.execute(q, {'surah_no': surah_no}).fetchall()
        return [r[0] for r in rows]

def get_verse_id_and_arabic(surah_no, ayat_no):
    """Ambil id_verse dan teks Arab resmi dari tabel verses."""
    if not engine:
        return None, ""
    with engine.connect() as conn:
        q = text("""
            SELECT v.id, v.text_uthmani
            FROM verses v
            JOIN chapters c ON v.id_chapter = c.id
            WHERE c.number_chapter = :surah_no AND v.number = :ayat_no
        """)
        row = conn.execute(q, {'surah_no': surah_no, 'ayat_no': ayat_no}).fetchone()
        if row:
            return row[0], row[1]
    return None, ""

def sanitize_block_text(text):
    """Pembersihan teks level paragraf."""
    # Sambungkan kata yang terpenggal di ujung baris (de-hyphenation)
    cleaned = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    # Typo OCR umum cetakan lama
    cleaned = cleaned.replace('Atlatr', 'Allah').replace('slahih', 'shahih').replace('bafuwa', 'bahwa').replace('adatah', 'adalah')
    return cleaned.strip()

def parse_verse_numbers(match_str, max_ayat):
    """Mengekstrak nomor ayat dari string OCR dengan penanganan grup dan artefak kurung tutup."""
    match_str = match_str.strip().lower()
    if match_str == 'l':
        return [1]
    
    parts = re.split(r'[\'\"\,\.\-\/\s]', match_str)
    verses = []
    for p in parts:
        p = p.strip()
        if not p.isdigit():
            continue
        num = int(p)
        if num > max_ayat and str(num).endswith('1'):
            num = int(str(num)[:-1])
        if 1 <= num <= max_ayat:
            verses.append(num)
            
    if len(verses) == 2 and verses[0] < verses[1] and verses[1] - verses[0] <= 5:
        return list(range(verses[0], verses[1] + 1))
    return verses

class TafsirExtractor:
    def __init__(self, pdf_path, surah_no, surah_name):
        self.pdf_path = pdf_path
        self.surah_no = surah_no
        self.surah_name = surah_name
        self.doc = fitz.open(pdf_path)
        self.max_ayat = 123 if surah_no == 11 else 111

    def scan_anchors(self, start_slide=1, end_slide=None, min_verse_start=0):
        if end_slide is None:
            end_slide = len(self.doc)

        if self.surah_no == 11:
            patt = re.compile(r'\(Qs\.\s*[^)]*(?:Huud|fluud|Hwd)[^)]*?[:z\.\s]\s*([0-9l\,\.\-\'\"]+)', re.IGNORECASE)
        else: # Yusuf
            patt = re.compile(r'\(Qs\.\s*[^)]*Y[uU]+suf[^)]*?[:z\.\s\|]\s*([0-9l\,\.\-\'\"]+)', re.IGNORECASE)

        raw_anchors = []
        for pno in range(start_slide - 1, end_slide):
            txt = self.doc[pno].get_text('text')
            for m in patt.finditer(txt):
                v_list = parse_verse_numbers(m.group(1), self.max_ayat)
                if v_list:
                    raw_anchors.append({
                        'slide': pno + 1,
                        'verses': v_list,
                        'min_verse': min(v_list)
                    })

        # Filter agar monotonik naik sesuai nomor urut slide
        raw_sorted = sorted(raw_anchors, key=lambda x: x['slide'])
        monotonic_anchors = []
        curr_v = min_verse_start
        for a in raw_sorted:
            # Cegah melompat ke belakang karena kutipan ayat lain
            if a['min_verse'] > curr_v:
                monotonic_anchors.append(a)
                curr_v = max(a['verses'])

        return monotonic_anchors

    def extract_verse_text(self, start_slide, end_slide):
        paragraphs = []

        for pno in range(start_slide - 1, end_slide):
            page = self.doc[pno]
            blocks = page.get_text('blocks')

            for b in blocks:
                x0, y0, x1, y1, btext = b[0], b[1], b[2], b[3], b[4].strip()

                if y0 < 55 or HEADER_PATTERNS.search(btext):
                    continue

                if y0 > 530 and (len(btext) < 10 or any(k in btext.lower() for k in FOOTNOTE_KEYWORDS)):
                    continue

                # Filter simbol acak font Arab rusak di kepala slide awal
                if pno == start_slide - 1 and ('# &' in btext or "g'}t" in btext or "$ij ?rj" in btext):
                    continue

                cleaned_b = sanitize_block_text(btext)
                if cleaned_b:
                    paragraphs.append(cleaned_b)

        return '\n'.join(paragraphs).strip()

def run_pipeline(dry_run=True, target_surah=None, target_ayat=None):
    mode_str = "SIMULASI (DRY-RUN)" if dry_run else "EKSEKUSI NYATA (INSERT KE DATABASE)"
    print("=" * 80)
    print(f"PIPELINE EKSTRAKSI TAFSIR ATH-THABARI DARI DUA PDF")
    print(f"Status: {mode_str}")
    print("=" * 80)

    jobs = []
    if target_surah in [None, 11]:
        jobs.append({
            'surah_no': 11,
            'name': 'Hud',
            'sources': [
                {'pdf': PDF_13, 'start_slide': 785, 'end_slide': 944, 'min_verse': 0},
                {'pdf': PDF_14, 'start_slide': 1, 'end_slide': 443, 'min_verse': 36},
            ]
        })

    if target_surah in [None, 12]:
        jobs.append({
            'surah_no': 12,
            'name': 'Yusuf',
            'sources': [
                {'pdf': PDF_14, 'start_slide': 729, 'end_slide': 979, 'min_verse': 45},
            ]
        })

    total_inserted = 0
    total_skipped = 0

    for job in jobs:
        s_no = job['surah_no']
        s_name = job['name']
        missing_db = set(get_missing_verses(s_no))

        print(f"\n[MEMPROSES SURAH {s_no}: {s_name}]")
        print(f"  Ayat Kosong di Database: {len(missing_db)} ayat")

        for src in job['sources']:
            pdf_path = src['pdf']
            if not os.path.exists(pdf_path):
                print(f"  [ERROR] File PDF tidak ditemukan: {pdf_path}")
                continue

            extractor = TafsirExtractor(pdf_path, s_no, s_name)
            anchors = extractor.scan_anchors(
                src['start_slide'], 
                src['end_slide'], 
                min_verse_start=src.get('min_verse', 0)
            )

            print(f"  Sumber: {pdf_path} (Slide {src['start_slide']} - {src['end_slide']})")
            print(f"  Total Jangkar Ayat Ditemukan: {len(anchors)}")

            for i, anchor in enumerate(anchors):
                verses = anchor['verses']
                start_s = anchor['slide']
                next_anchor_s = anchors[i+1]['slide'] if i+1 < len(anchors) else src['end_slide']
                # Slide berikutnya (next_anchor_s) adalah awal ayat selanjutnya, jadi ayat ini berakhir di slide sebelumnya
                end_s = max(start_s, next_anchor_s - 1) if next_anchor_s > start_s else start_s

                # Cek apakah ada ayat dalam grup ini yang perlu diproses
                for v_num in verses:
                    if target_ayat and v_num != target_ayat:
                        continue

                    # Hanya proses ayat yang KOSONG di database (kecuali user menarget ayat spesifik)
                    if v_num not in missing_db and not target_ayat:
                        total_skipped += 1
                        continue

                    extracted_text = extractor.extract_verse_text(start_s, end_s)
                    id_verse, arabic_text = get_verse_id_and_arabic(s_no, v_num)

                    if not id_verse or len(extracted_text) < 50:
                        continue

                    full_payload = f"\r\n{arabic_text}\r\n{extracted_text}\r\n"

                    print(f"    [+] Surah {s_no}:{v_num:3d} (Slide {start_s:3d}-{end_s:3d}) | "
                          f"Len: {len(full_payload):5d} chars | id_verse: {id_verse}")

                    if not dry_run:
                        with engine.begin() as conn:
                            conn.execute(text("""
                                INSERT INTO verse_tafsirs (id_verse, id_tafsir, text)
                                VALUES (:id_verse, 7, :text)
                                ON DUPLICATE KEY UPDATE text = :text
                            """), {'id_verse': id_verse, 'text': full_payload})

                    total_inserted += 1

    print("\n" + "=" * 80)
    print("HASIL PIPELINE:")
    print(f"  Total Ayat Diproses/Dimasukkan: {total_inserted}")
    print(f"  Total Ayat Sudah Ada (Dilewati): {total_skipped}")
    if dry_run:
        print("\n[INFO] Mode simulasi selesai. Untuk mengeksekusi langsung ke MySQL, tambahkan flag --execute:")
        print("  python Chatbot/extract_tafsir_pipeline.py --execute")
    else:
        print("\n[SUKSES] Seluruh data berhasil dimasukkan ke tabel `verse_tafsirs` di database MySQL!")
    print("=" * 80)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Ekstraktor Tafsir Ath-Thabari dari PDF ke MySQL")
    parser.add_argument('--execute', action='store_true', help="Eksekusi INSERT ke database MySQL (default: dry-run)")
    parser.add_argument('--surah', type=int, choices=[11, 12], help="Filter nomor surah (11 atau 12)")
    parser.add_argument('--ayat', type=int, help="Filter nomor ayat tertentu untuk pengujian")

    args = parser.parse_args()
    run_pipeline(dry_run=not args.execute, target_surah=args.surah, target_ayat=args.ayat)
