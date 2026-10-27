import os
import sys
import re
import fitz
from openai import OpenAI
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('Chatbot/.env')

DB_URL = os.getenv('DATABASE_URL')
engine = create_engine(DB_URL)

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
    r'^(?:TddwAt/l\.Thabmi|Tatsir\s+Ath:Ihahdri|TafurAthflhabai|TCstultt/l\.:Ihafuri|Tds,fAth:Ilutui|Tq6tuAh:Ihatui|SURAH\s+HUUD|SurrchHuud|SunclrHrlud|SurohHuud|SurahHtmd|SurahHllnrd|SurahHwd|SURAH\s+Y[Uu]+SUF|Surah\s+Y[Uu]+suf|TafshNi:Ihabari|Tafsir\s+Ath:fhabari|TafsbAthllwbdri|Surah\s*An[,\-\'\s]*Nahl|SurahAn,Nahl|SurahAn-Nchl)',
    re.IGNORECASE | re.MULTILINE
)

def extract_raw_pages(pdf_path, start_slide, end_slide):
    doc = fitz.open(pdf_path)
    paragraphs = []
    for pno in range(start_slide - 1, end_slide):
        page = doc[pno]
        blocks = page.get_text('blocks')
        for b in blocks:
            x0, y0, x1, y1, btext = b[0], b[1], b[2], b[3], b[4].strip()
            # Lewati header
            if y0 < 55 or HEADER_PATTERNS.search(btext):
                continue
            # Lewati footer / nomor halaman buku
            if y0 > 530 and (len(btext) < 10 or any(k in btext.lower() for k in FOOTNOTE_KEYWORDS)):
                continue
            # De-hyphenation sederhana
            clean_b = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', btext)
            # Typos cetakan umum
            clean_b = clean_b.replace('Atlatr', 'Allah').replace('slahih', 'shahih').replace('bafuwa', 'bahwa').replace('adatah', 'adalah')
            if clean_b.strip():
                paragraphs.append(clean_b.strip())
    return '\n\n'.join(paragraphs)

def restore_with_llm(surah_name, verse_num, raw_text, arabic_ayah, indo_translation):
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

    resp = client.chat.completions.create(
        model='openai/gpt-4o-mini',
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.1
    )
    return resp.choices[0].message.content.strip()

def process_target(ch, vnum, pdf_path, s_start, s_end):
    print(f"\n[MEMPROSES SURAH {ch}:{vnum} (Slides {s_start}-{s_end})]")
    with engine.connect() as conn:
        q = text('''
            SELECT v.id, v.text_uthmani, t.text, c.name
            FROM verses v
            JOIN chapters c ON v.id_chapter = c.id
            LEFT JOIN verse_translations t ON t.id_verse = v.id AND t.id_translation = 1
            WHERE c.number_chapter = :ch AND v.number = :vnum
        ''')
        r = conn.execute(q, {'ch': ch, 'vnum': vnum}).fetchone()
        vid, ar_verse, indo_tr, surah_name = r[0], r[1], r[2], r[3]
        
    print(f"  1. Ekstraksi mentah dari PDF...")
    raw = extract_raw_pages(pdf_path, s_start, s_end)
    print(f"     Raw length: {len(raw)} chars, {len(raw.split())} words")
    
    print(f"  2. Restorasi filologi dengan LLM (Arabic & Clean Indonesian)...")
    restored = restore_with_llm(surah_name, vnum, raw, ar_verse, indo_tr)
    print(f"     Restored length: {len(restored)} chars")
    
    full_payload = f"\r\n{ar_verse}\r\n{restored}\r\n"
    
    print(f"  3. Menyimpan ke database MySQL (id_verse={vid})...")
    with engine.begin() as conn:
        conn.execute(text('''
            INSERT INTO verse_tafsirs (id_verse, id_tafsir, text)
            VALUES (:vid, 7, :text)
            ON DUPLICATE KEY UPDATE text = :text
        '''), {'vid': vid, 'text': full_payload})
        
    print(f"  [SUKSES] Surah {ch}:{vnum} berhasil diperbarui!")

if __name__ == '__main__':
    # An-Nahl 12, 29, 90
    pdf_16 = 'DATA/pdf/Tafsir ath-Thabari_Jilid 16.pdf'
    process_target(16, 12, pdf_16, 52, 64)
    process_target(16, 29, pdf_16, 94, 99)
    process_target(16, 90, pdf_16, 289, 297)
