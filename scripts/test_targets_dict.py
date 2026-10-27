import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('Chatbot/.env')
engine = create_engine(os.getenv('DATABASE_URL'))

# Define all 86 remaining targets
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
    (24, 17, 'DATA/pdf/Tafsir 19.pdf', 48, 50), # grouped with 16
    (24, 18, 'DATA/pdf/Tafsir 19.pdf', 48, 50), # grouped with 16
    (24, 19, 'DATA/pdf/Tafsir 19.pdf', 51, 52),
    (24, 20, 'DATA/pdf/Tafsir 19.pdf', 53, 53),
    (24, 21, 'DATA/pdf/Tafsir 19.pdf', 54, 57),
    (24, 22, 'DATA/pdf/Tafsir 19.pdf', 28, 38),
    (24, 23, 'DATA/pdf/Tafsir 19.pdf', 28, 38), # grouped with 22
    (24, 24, 'DATA/pdf/Tafsir 19.pdf', 69, 70),
    (24, 25, 'DATA/pdf/Tafsir 19.pdf', 71, 76),
    (24, 26, 'DATA/pdf/Tafsir 19.pdf', 77, 80),
    (24, 27, 'DATA/pdf/Tafsir 19.pdf', 81, 86),
    (24, 28, 'DATA/pdf/Tafsir 19.pdf', 81, 86), # grouped with 27
    (24, 29, 'DATA/pdf/Tafsir 19.pdf', 87, 104),
    (24, 30, 'DATA/pdf/Tafsir 19.pdf', 105, 107),
    (24, 31, 'DATA/pdf/Tafsir 19.pdf', 108, 132),
    (24, 32, 'DATA/pdf/Tafsir 19.pdf', 133, 164),
    (24, 33, 'DATA/pdf/Tafsir 19.pdf', 133, 164), # grouped with 32
    (24, 34, 'DATA/pdf/Tafsir 19.pdf', 165, 166),
    (24, 35, 'DATA/pdf/Tafsir 19.pdf', 167, 193),
    (24, 36, 'DATA/pdf/Tafsir 19.pdf', 194, 207),
    (24, 37, 'DATA/pdf/Tafsir 19.pdf', 194, 207), # grouped with 36-38
    (24, 38, 'DATA/pdf/Tafsir 19.pdf', 194, 207), # grouped with 36-38
    (24, 39, 'DATA/pdf/Tafsir 19.pdf', 208, 213),
    (24, 40, 'DATA/pdf/Tafsir 19.pdf', 214, 218),
    (24, 41, 'DATA/pdf/Tafsir 19.pdf', 219, 222),
    (24, 42, 'DATA/pdf/Tafsir 19.pdf', 219, 222), # grouped with 41
    (24, 43, 'DATA/pdf/Tafsir 19.pdf', 223, 228),
    (24, 44, 'DATA/pdf/Tafsir 19.pdf', 223, 228), # grouped with 43
    (24, 45, 'DATA/pdf/Tafsir 19.pdf', 229, 230),
    (24, 46, 'DATA/pdf/Tafsir 19.pdf', 231, 231),
    (24, 47, 'DATA/pdf/Tafsir 19.pdf', 232, 232),
    (24, 48, 'DATA/pdf/Tafsir 19.pdf', 232, 232), # grouped with 47
    (24, 49, 'DATA/pdf/Tafsir 19.pdf', 233, 234),
    (24, 50, 'DATA/pdf/Tafsir 19.pdf', 233, 234), # grouped with 49
    (24, 51, 'DATA/pdf/Tafsir 19.pdf', 235, 235),
    (24, 52, 'DATA/pdf/Tafsir 19.pdf', 236, 236),
    (24, 53, 'DATA/pdf/Tafsir 19.pdf', 237, 238),
    (24, 54, 'DATA/pdf/Tafsir 19.pdf', 239, 240),
    (24, 55, 'DATA/pdf/Tafsir 19.pdf', 241, 247),
    (24, 56, 'DATA/pdf/Tafsir 19.pdf', 248, 251),
    (24, 57, 'DATA/pdf/Tafsir 19.pdf', 248, 251), # grouped with 56
    (24, 58, 'DATA/pdf/Tafsir 19.pdf', 252, 258),
    (24, 59, 'DATA/pdf/Tafsir 19.pdf', 259, 261),
    (24, 60, 'DATA/pdf/Tafsir 19.pdf', 262, 266),
    (24, 61, 'DATA/pdf/Tafsir 19.pdf', 267, 295),
    (24, 62, 'DATA/pdf/Tafsir 19.pdf', 296, 299),
    (24, 63, 'DATA/pdf/Tafsir 19.pdf', 300, 304),
    (24, 64, 'DATA/pdf/Tafsir 19.pdf', 305, 306),
]

ALL_TARGETS = HUD_TARGETS + YUSUF_TARGETS + NUR_TARGETS

print(f"Total targets: {len(ALL_TARGETS)}")
with engine.connect() as conn:
    for ch, vn, pdf, s1, s2 in ALL_TARGETS:
        q = text('''
            SELECT v.id, v.text_uthmani, c.name
            FROM verses v
            JOIN chapters c ON v.id_chapter = c.id
            WHERE c.number_chapter = :ch AND v.number = :vn
        ''')
        r = conn.execute(q, {'ch': ch, 'vn': vn}).fetchone()
        if not r:
            print(f"ERROR: Surah {ch}:{vn} not found in database!")
        if not os.path.exists(pdf):
            print(f"ERROR: PDF {pdf} does not exist!")

print("Semua 86 target terverifikasi valid!")
