import os
import sys
import re
import time
import asyncio
import fitz
from openai import OpenAI
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('Chatbot/.env')

DB_URL = os.getenv('DATABASE_URL')
engine = create_engine(DB_URL, pool_size=10, max_overflow=20)

client = OpenAI(
    base_url='https://openrouter.ai/api/v1',
    api_key=os.getenv('OPENROUTER_API_KEY')
)

FOOTNOTE_KEYWORDS = [
    'ibnu abi hatim dalam tafsir', 'zad al masir', 'an-nukat wa al',
    'ma\'alim at-tanzil', 'abdurrazzaq dalam tafsir', 'lihat tafsir',
    'ad-durr al-mantsur', 'ibnu katsir', 'fath al-bari', 'ibid.'
]

HEADER_PATTERNS = re.compile(
    r'^(?:TddwAt/l\.Thabmi|Tatsir\s+Ath:Ihahdri|TafurAthflhabai|TCstultt/l\.:Ihafuri|Tds,fAth:Ilutui|Tq6tuAh:Ihatui|SURAH\s+HUUD|SurrchHuud|SunclrHrlud|SurohHuud|SurahHtmd|SurahHllnrd|SurahHwd|SURAH\s+Y[Uu]+SUF|Surah\s+Y[Uu]+suf|TafshNi:Ihabari|Tafsir\s+Ath:fhabari|TafsbAthllwbdri|Surah\s*An[,\-\'\s]*Nahl|SurahAn,Nahl|SurahAn-Nchl|Surah\s*An[,\-\'\s]*Nuur|SurahAn,Nuur|SurahAn-Nuur|SurchAn\.Nuur|SurchAn\s*Nuur|SURAH\s+AN\s*NUUR|SurahAn\s*Nrsr|SurchAn\s*Nrsr)',
    re.IGNORECASE | re.MULTILINE
)

# Cache PDF docs in memory
DOC_CACHE = {}

def get_pdf_doc(path):
    if path not in DOC_CACHE:
        DOC_CACHE[path] = fitz.open(path)
    return DOC_CACHE[path]

def extract_raw_pages(pdf_path, start_slide, end_slide):
    doc = get_pdf_doc(pdf_path)
    paragraphs = []
    for pno in range(start_slide - 1, end_slide):
        page = doc[pno]
        blocks = page.get_text('blocks')
        for b in blocks:
            x0, y0, x1, y1, btext = b[0], b[1], b[2], b[3], b[4].strip()
            # Lewati header atas
            if y0 < 55 or HEADER_PATTERNS.search(btext):
                continue
            # Lewati footer bawah / nomor halaman
            if y0 > 530 and (len(btext) < 10 or any(k in btext.lower() for k in FOOTNOTE_KEYWORDS)):
                continue
            # Sambungkan kata terpotong di ujung baris
            clean_b = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', btext)
            # Typos umum OCR cetakan lama
            clean_b = clean_b.replace('Atlatr', 'Allah').replace('slahih', 'shahih').replace('bafuwa', 'bahwa').replace('adatah', 'adalah')
            if clean_b.strip():
                paragraphs.append(clean_b.strip())
    return '\n\n'.join(paragraphs)

def restore_with_llm_sync(surah_name, verse_num, raw_text, arabic_ayah, indo_translation):
    prompt = f"""Kamu adalah pakar filologi dan digitalisasi naskah Tafsir Ath-Thabari (edisi terjemahan Pustaka Azzam).
Teks berikut diekstrak dari OCR buku cetak untuk:
SURAH {surah_name.upper()} AYAT {verse_num}:
Teks Arab Utsmani: {arabic_ayah}
Terjemahan: {indo_translation}

MASALAH OCR DI TEKS INI:
1. Potongan lafazh/frasa Arab di tengah kalimat rusak menjadi karakter simbol acak (contoh: teks simbol hasil OCR Latin di depan kalimat terjemahan/takwil).
2. Typo OCR cetakan lama pada bahasa Indonesia.

INSTRUKSI WAJIB:
1. Ganti semua simbol Arab yang rusak dengan huruf Arab asli yang benar, berharakat, dan jelas sesuai konteks ayat {surah_name}: {verse_num} dan potongan frasa yang sedang dibahas oleh Ath-Thabari.
2. Perbaiki typo OCR bahasa Indonesia menjadi bahasa Indonesia yang baku, rapi, dan nyaman dibaca.
3. JANGAN PERNAH meringkas isi! Pertahankan 100% seluruh riwayat hadits, nomor hadits/atsar, seluruh nama perawi sanad, dan matannya secara lengkap.
4. Outputkan HANYA teks hasil restorasi tanpa basa-basi atau catatan pembuka/penutup.

TEKS SUMBER OCR:
{raw_text}"""

    for attempt in range(4):
        try:
            resp = client.chat.completions.create(
                model='openai/gpt-4o-mini',
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.1
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            if attempt < 3:
                time.sleep(3 * (attempt + 1))
            else:
                raise e

# Daftar 86 Target Ayat Kosong
HUD_TARGETS = [
    (11, 12, 'DATA/pdf/Tafsir 13.pdf', 844, 845),
    (11, 14, 'DATA/pdf/Tafsir 13.pdf', 850, 852),
    (11, 37, 'DATA/pdf/Tafsir 13.pdf', 941, 944),
    (11, 41, 'DATA/pdf/Tafsir 14.pdf', 40, 45),
    (11, 43, 'DATA/pdf/Tafsir 14.pdf', 47, 50),
    (11, 47, 'DATA/pdf/Tafsir 14.pdf', 83, 84),
    (11, 51, 'DATA/pdf/Tafsir 14.pdf', 95, 95),
    (11, 56, 'DATA/pdf/Tafsir 14.pdf', 108, 108),
    (11, 67, 'DATA/pdf/Tafsir 14.pdf', 139, 140),
    (11, 68, 'DATA/pdf/Tafsir 14.pdf', 139, 140),
    (11, 78, 'DATA/pdf/Tafsir 14.pdf', 193, 204),
    (11, 79, 'DATA/pdf/Tafsir 14.pdf', 205, 207),
    (11, 89, 'DATA/pdf/Tafsir 14.pdf', 275, 280),
    (11, 90, 'DATA/pdf/Tafsir 14.pdf', 275, 280),
    (11, 96, 'DATA/pdf/Tafsir 14.pdf', 296, 297),
    (11, 97, 'DATA/pdf/Tafsir 14.pdf', 296, 297),
    (11, 98, 'DATA/pdf/Tafsir 14.pdf', 298, 300),
    (11, 102, 'DATA/pdf/Tafsir 14.pdf', 314, 316),
    (11, 112, 'DATA/pdf/Tafsir 14.pdf', 357, 358),
    (11, 114, 'DATA/pdf/Tafsir 14.pdf', 363, 404),
]

YUSUF_TARGETS = [
    (12, 47, 'DATA/pdf/Tafsir 14.pdf', 732, 733),
    (12, 54, 'DATA/pdf/Tafsir 14.pdf', 773, 775),
    (12, 57, 'DATA/pdf/Tafsir 14.pdf', 783, 783),
    (12, 59, 'DATA/pdf/Tafsir 14.pdf', 787, 788),
    (12, 61, 'DATA/pdf/Tafsir 14.pdf', 790, 790),
    (12, 62, 'DATA/pdf/Tafsir 14.pdf', 791, 793),
    (12, 65, 'DATA/pdf/Tafsir 14.pdf', 798, 801),
    (12, 69, 'DATA/pdf/Tafsir 14.pdf', 815, 817),
    (12, 76, 'DATA/pdf/Tafsir 14.pdf', 850, 859),
    (12, 77, 'DATA/pdf/Tafsir 14.pdf', 860, 871),
    (12, 79, 'DATA/pdf/Tafsir 14.pdf', 875, 875),
    (12, 96, 'DATA/pdf/Tafsir 14.pdf', 965, 975),
]

NUR_TARGETS = [
    (24, 11, 'DATA/pdf/Tafsir 19.pdf', 9, 27),
    (24, 12, 'DATA/pdf/Tafsir 19.pdf', 39, 41),
    (24, 13, 'DATA/pdf/Tafsir 19.pdf', 42, 43),
    (24, 14, 'DATA/pdf/Tafsir 19.pdf', 44, 44),
    (24, 15, 'DATA/pdf/Tafsir 19.pdf', 45, 47),
    (24, 16, 'DATA/pdf/Tafsir 19.pdf', 48, 50),
    (24, 17, 'DATA/pdf/Tafsir 19.pdf', 48, 50),
    (24, 18, 'DATA/pdf/Tafsir 19.pdf', 48, 50),
    (24, 19, 'DATA/pdf/Tafsir 19.pdf', 51, 52),
    (24, 20, 'DATA/pdf/Tafsir 19.pdf', 53, 53),
    (24, 21, 'DATA/pdf/Tafsir 19.pdf', 54, 57),
    (24, 22, 'DATA/pdf/Tafsir 19.pdf', 28, 38),
    (24, 23, 'DATA/pdf/Tafsir 19.pdf', 28, 38),
    (24, 24, 'DATA/pdf/Tafsir 19.pdf', 69, 70),
    (24, 25, 'DATA/pdf/Tafsir 19.pdf', 71, 76),
    (24, 26, 'DATA/pdf/Tafsir 19.pdf', 77, 80),
    (24, 27, 'DATA/pdf/Tafsir 19.pdf', 81, 86),
    (24, 28, 'DATA/pdf/Tafsir 19.pdf', 81, 86),
    (24, 29, 'DATA/pdf/Tafsir 19.pdf', 87, 104),
    (24, 30, 'DATA/pdf/Tafsir 19.pdf', 105, 107),
    (24, 31, 'DATA/pdf/Tafsir 19.pdf', 108, 132),
    (24, 32, 'DATA/pdf/Tafsir 19.pdf', 133, 164),
    (24, 33, 'DATA/pdf/Tafsir 19.pdf', 133, 164),
    (24, 34, 'DATA/pdf/Tafsir 19.pdf', 165, 166),
    (24, 35, 'DATA/pdf/Tafsir 19.pdf', 167, 193),
    (24, 36, 'DATA/pdf/Tafsir 19.pdf', 194, 207),
    (24, 37, 'DATA/pdf/Tafsir 19.pdf', 194, 207),
    (24, 38, 'DATA/pdf/Tafsir 19.pdf', 194, 207),
    (24, 39, 'DATA/pdf/Tafsir 19.pdf', 208, 213),
    (24, 40, 'DATA/pdf/Tafsir 19.pdf', 214, 218),
    (24, 41, 'DATA/pdf/Tafsir 19.pdf', 219, 222),
    (24, 42, 'DATA/pdf/Tafsir 19.pdf', 219, 222),
    (24, 43, 'DATA/pdf/Tafsir 19.pdf', 223, 228),
    (24, 44, 'DATA/pdf/Tafsir 19.pdf', 223, 228),
    (24, 45, 'DATA/pdf/Tafsir 19.pdf', 229, 230),
    (24, 46, 'DATA/pdf/Tafsir 19.pdf', 231, 231),
    (24, 47, 'DATA/pdf/Tafsir 19.pdf', 232, 232),
    (24, 48, 'DATA/pdf/Tafsir 19.pdf', 232, 232),
    (24, 49, 'DATA/pdf/Tafsir 19.pdf', 233, 234),
    (24, 50, 'DATA/pdf/Tafsir 19.pdf', 233, 234),
    (24, 51, 'DATA/pdf/Tafsir 19.pdf', 235, 235),
    (24, 52, 'DATA/pdf/Tafsir 19.pdf', 236, 236),
    (24, 53, 'DATA/pdf/Tafsir 19.pdf', 237, 238),
    (24, 54, 'DATA/pdf/Tafsir 19.pdf', 239, 240),
    (24, 55, 'DATA/pdf/Tafsir 19.pdf', 241, 247),
    (24, 56, 'DATA/pdf/Tafsir 19.pdf', 248, 251),
    (24, 57, 'DATA/pdf/Tafsir 19.pdf', 248, 251),
    (24, 58, 'DATA/pdf/Tafsir 19.pdf', 252, 258),
    (24, 59, 'DATA/pdf/Tafsir 19.pdf', 259, 261),
    (24, 60, 'DATA/pdf/Tafsir 19.pdf', 262, 266),
    (24, 61, 'DATA/pdf/Tafsir 19.pdf', 267, 295),
    (24, 62, 'DATA/pdf/Tafsir 19.pdf', 296, 299),
    (24, 63, 'DATA/pdf/Tafsir 19.pdf', 300, 304),
    (24, 64, 'DATA/pdf/Tafsir 19.pdf', 305, 306),
]

ALL_TARGETS = HUD_TARGETS + YUSUF_TARGETS + NUR_TARGETS

sem = asyncio.Semaphore(5)

async def process_item(idx, total, item, metadata_dict):
    ch, vnum, pdf_path, s_start, s_end = item
    meta = metadata_dict[(ch, vnum)]
    vid = meta['id']
    ar_verse = meta['text_uthmani']
    indo_tr = meta['indo']
    surah_name = meta['name']

    async with sem:
        try:
            print(f"[{idx}/{total}] Mulai Surah {ch}:{vnum} (Slides {s_start}-{s_end})...", flush=True)
            # 1. Ekstrak
            raw = extract_raw_pages(pdf_path, s_start, s_end)
            if not raw or len(raw) < 50:
                print(f"  [WARN] {ch}:{vnum} teks terlalu pendek ({len(raw)} chars)", flush=True)
            
            # 2. LLM restore (in thread)
            restored = await asyncio.to_thread(
                restore_with_llm_sync, 
                surah_name, vnum, raw, ar_verse, indo_tr
            )
            
            full_payload = f"\r\n{ar_verse}\r\n{restored}\r\n"
            
            # 3. Simpan ke database
            def save_to_db():
                with engine.begin() as conn:
                    conn.execute(text('''
                        INSERT INTO verse_tafsirs (id_verse, id_tafsir, text)
                        VALUES (:vid, 7, :text)
                        ON DUPLICATE KEY UPDATE text = :text
                    '''), {'vid': vid, 'text': full_payload})

            await asyncio.to_thread(save_to_db)
            print(f"[{idx}/{total}] [SUKSES] Surah {ch}:{vnum} selesai ({len(full_payload)} chars, id_verse={vid})", flush=True)
            return True
        except Exception as e:
            print(f"[{idx}/{total}] [ERROR] Surah {ch}:{vnum} gagal: {e}", flush=True)
            return False

async def main():
    print("=" * 80, flush=True)
    print(f"MEMULAI BATCH RESTORASI TAFSIR ATH-THABARI (TOTAL {len(ALL_TARGETS)} AYAT)", flush=True)
    print("=" * 80, flush=True)

    # Load metadata for all targets
    metadata_dict = {}
    with engine.connect() as conn:
        for ch, vn, _, _, _ in ALL_TARGETS:
            q = text('''
                SELECT v.id, v.text_uthmani, t.text, c.name
                FROM verses v
                JOIN chapters c ON v.id_chapter = c.id
                LEFT JOIN verse_translations t ON t.id_verse = v.id AND t.id_translation = 1
                WHERE c.number_chapter = :ch AND v.number = :vn
            ''')
            r = conn.execute(q, {'ch': ch, 'vn': vn}).fetchone()
            metadata_dict[(ch, vn)] = {
                'id': r[0],
                'text_uthmani': r[1],
                'indo': r[2] or '',
                'name': r[3]
            }

    tasks = [
        process_item(i + 1, len(ALL_TARGETS), target, metadata_dict)
        for i, target in enumerate(ALL_TARGETS)
    ]

    results = await asyncio.gather(*tasks)
    success_count = sum(1 for r in results if r)
    print("=" * 80, flush=True)
    print(f"SELESAI! Berhasil direstorasi: {success_count}/{len(ALL_TARGETS)} ayat.", flush=True)
    print("=" * 80, flush=True)

if __name__ == '__main__':
    asyncio.run(main())
