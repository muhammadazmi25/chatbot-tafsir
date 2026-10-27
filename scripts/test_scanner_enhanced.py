import fitz
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

SURAH_NAMES = {
    11: r'(?:Huud|fluud|Hwd|Httd|Hund|Iluud)',
    12: r'(?:Yuusuf|Yusuf|Ytrusuf)',
    16: r'(?:An[,\-\'\s]*Nahl|An[,\-\'\s]*Nattl|An[,\-\'\s]*Nchl|An[,\-\'\s]*Ncttl)',
    17: r'(?:Al[,\-\'\s]*Israa?\'?|Al[,\-\'\s]*lsraa?\'?)',
    21: r'(?:Al[,\-\'\s]*Anbiyaa?\'?|Al[,\-\'\s]*Anblyaa?\'?)',
    23: r'(?:Al[,\-\'\s]*Mu\'?minuu?n|Al[,\-\'\s]*Muminuu?n)',
    24: r'(?:An[,\-\'\s]*Nuu?r|An[,\-\'\s]*Nutrr)',
}

def clean_ocr_digits(raw_str):
    """Mengubah karakter OCR yang mirip angka menjadi angka."""
    # Karakter translasi angka
    char_map = {
        'l': '1', 'i': '1', 'I': '1', 'L': '1', '|': '1', '!': '1', ']': '1', ')': '',
        'o': '0', 'O': '0', 'Q': '0',
        'z': '2', 'Z': '2',
        's': '5', 'S': '5',
    }
    cleaned = ''
    for c in raw_str:
        if c.isdigit():
            cleaned += c
        elif c in char_map:
            cleaned += char_map[c]
        elif c in [',', '.', '-', ' ', ';', ':', '/', '\'']:
            cleaned += ' '
    return cleaned

def parse_citation(raw_citation, target_chapter, max_verses):
    """
    Mengurai sitasi (Qs. Surah [chap]: verse)
    Mengembalikan daftar nomor ayat (list of int)
    """
    # Pisahkan setelah nama surah
    # Cari posisi chapter / separator
    digits_raw = clean_ocr_digits(raw_citation)
    tokens = [t for t in digits_raw.split() if t.isdigit()]
    
    # Biasanya token pertama adalah chapter (atau chapter termakan)
    # Jika token pertama == target_chapter, ayat adalah token berikutnya
    verse_nums = []
    if len(tokens) >= 2 and int(tokens[0]) == target_chapter:
        for t in tokens[1:]:
            n = int(t)
            if 1 <= n <= max_verses:
                verse_nums.append(n)
    else:
        # Mungkin token pertama langsung nomor ayat jika chapter tidak ter-OCR
        for t in tokens:
            n = int(t)
            if n != target_chapter and 1 <= n <= max_verses:
                verse_nums.append(n)
                
    # Tangani rentang misal '36 38' -> jika beda <= 3
    if len(verse_nums) == 2 and verse_nums[0] < verse_nums[1] and (verse_nums[1] - verse_nums[0] <= 4):
        verse_nums = list(range(verse_nums[0], verse_nums[1] + 1))
        
    return verse_nums

def scan_pdf_anchors(pdf_path, target_chapter, max_verses, max_pages=None):
    doc = fitz.open(pdf_path)
    total_pages = len(doc) if not max_pages else min(max_pages, len(doc))
    name_regex = SURAH_NAMES[target_chapter]
    pattern = re.compile(rf'\(Qs\.\s*[^)]*{name_regex}[^)]*?\)', re.IGNORECASE)
    
    found_anchors = []
    for pno in range(total_pages):
        txt = doc[pno].get_text('text')
        # ganti newline dalam kurung agar regex bisa match multi-line citation
        txt_single = txt.replace('\n', ' ')
        for m in pattern.finditer(txt_single):
            raw_cit = m.group(0)
            v_list = parse_citation(raw_cit, target_chapter, max_verses)
            if v_list:
                found_anchors.append({
                    'slide': pno + 1,
                    'raw': raw_cit,
                    'verses': v_list
                })
    return found_anchors

print("=== TESTING AN-NUR (24) IN TAFSIR 19 ===")
nur_anchors = scan_pdf_anchors('DATA/pdf/Tafsir 19.pdf', 24, 64, max_pages=320)
print(f"Total An-Nur anchors found: {len(nur_anchors)}")
for a in nur_anchors:
    print(f"Slide {a['slide']:3d}: verses {a['verses']}  <- {a['raw']}")
