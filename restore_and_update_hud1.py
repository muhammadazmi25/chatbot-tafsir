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
    'ibid.'
]

HEADER_PATTERNS = re.compile(
    r'^(?:TddwAt/l\.Thabmi|Tatsir\s+Ath:Ihahdri|TafurAthflhabai|SURAH\s+HUUD|SurrchHuud|SunclrHrlud|SurohHuud)',
    re.IGNORECASE | re.MULTILINE
)

def extract_raw_hud1():
    doc = fitz.open('DATA/pdf/Tafsir 13.pdf')
    paragraphs = []
    # Slide 785 (index 784) sampai Slide 791 (index 790).
    # Slide 792 adalah awal Ayat 2, jadi TIDAK boleh diikutkan!
    for pno in range(784, 791):
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
            # Sambungkan kata yang terpenggal di ujung baris
            clean_b = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', btext)
            paragraphs.append(clean_b.strip())

    return '\n\n'.join(paragraphs)

def restore_with_llm(raw_text, arabic_ayah):
    prompt = """Kamu adalah asisten pakar filologi dan digitalisasi naskah Tafsir Ath-Thabari (edisi terjemahan Pustaka Azzam).
Teks berikut diekstrak dari OCR buku cetak untuk:
SURAH HUD AYAT 1:
""" + arabic_ayah + """

MASALAH OCR DI TEKS INI:
1. Potongan lafazh/frasa Arab di tengah kalimat rusak menjadi karakter simbol acak (contoh: teks simbol di depan kalimat terjemahan).
2. Typo OCR cetakan lama (seperti 'bafuwa' -> 'bahwa', 'adatah' -> 'adalah', 'perintatr' -> 'perintah', 'patrala' -> 'pahala', 'slahih' -> 'shahih', 'Atlatr' -> 'Allah', 'lTgSL' -> '17981.').

INSTRUKSI WAJIB:
1. Ganti semua simbol Arab yang rusak dengan huruf Arab asli yang benar dan jelas sesuai konteks ayat Hud: 1 (misalnya: الٓر, كِتَابٌ أُحْكِمَتْ آيَاتُهُ, ثُمَّ فُصِّلَتْ, مِنْ لَدُنْ حَكِيمٍ خَبِيرٍ, هذا كتاب, dll).
2. Perbaiki typo OCR bahasa Indonesia menjadi bahasa Indonesia yang baku, rapi, dan nyaman dibaca.
3. JANGAN PERNAH meringkas isi! Pertahankan 100% seluruh riwayat hadits (nomor 17977 s.d. 17989), seluruh nama perawi sanad, dan matannya secara lengkap.
4. Outputkan HANYA teks hasil restorasi tanpa basa-basi atau catatan pembuka/penutup.

TEKS SUMBER OCR:
""" + raw_text
    resp = client.chat.completions.create(
        model='openai/gpt-4o-mini',
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.1
    )
    return resp.choices[0].message.content.strip()

if __name__ == '__main__':
    print("1. Mengekstrak naskah mentah Hud Ayat 1 dari Slide 785 s.d. 791...")
    raw = extract_raw_hud1()
    print(f"   Raw text length: {len(raw)} chars, {len(raw.split())} words")

    with engine.connect() as conn:
        r = conn.execute(text("SELECT id, text_uthmani FROM verses WHERE id_chapter = 11 AND number = 1")).fetchone()
        id_verse, arabic_verse = r[0], r[1]

    print("2. Merestorasi teks dengan LLM (memperbaiki Arab rusak & typo)...")
    restored = restore_with_llm(raw, arabic_verse)
    print(f"   Restored text length: {len(restored)} chars")

    # Format akhir standar database
    full_payload = f"\r\n{arabic_verse}\r\n{restored}\r\n"

    print("3. Memperbarui record di database MySQL (verse_tafsirs)...")
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE verse_tafsirs 
            SET text = :text 
            WHERE id_verse = :id_verse AND id_tafsir = 7
        """), {'id_verse': id_verse, 'text': full_payload})

    print("4. SELESAI! Record Surah Hud Ayat 1 berhasil diperbarui.")
    print("\n--- PREVIEW 1000 KARAKTER PERTAMA ---")
    print(full_payload[:1000])
    print("\n--- PREVIEW 500 KARAKTER TERAKHIR ---")
    print(full_payload[-500:])
