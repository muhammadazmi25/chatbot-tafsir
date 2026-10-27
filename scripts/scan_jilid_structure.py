import fitz
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

def scan_surah_headers_and_anchors(pdf_path, name):
    print(f"\n==========================================")
    print(f"Scanning {name} ({pdf_path})")
    print(f"==========================================")
    doc = fitz.open(pdf_path)
    print(f"Total pages: {len(doc)}")
    
    # Check headers / surah titles across the book
    surah_mentions = []
    for pno in range(0, len(doc), 10):
        t = doc[pno].get_text('text')
        m = re.findall(r'(SURAH\s+[A-Z\-\'\s]+)', t, re.IGNORECASE)
        if m:
            surah_mentions.append((pno+1, m[0].strip()))
    
    print(f"Sample Surah Mentions every 10 pages: {surah_mentions[:10]}")
    
    # Search specific surahs
    # Qs. An-Nahl / An-Nahl
    # Qs. Al-Israa' / Al-Isra'
    # Qs. Al-Anbiyaa'
    # Qs. Al-Mu'minuun
    # Qs. An-Nuur / An-Nur

scan_surah_headers_and_anchors('DATA/pdf/Tafsir ath-Thabari_Jilid 16.pdf', 'Jilid 16')
scan_surah_headers_and_anchors('DATA/pdf/Tafsir ath-Thabari_Jilid 17.pdf', 'Jilid 17')
scan_surah_headers_and_anchors('DATA/pdf/Tafsir ath-Thabari_Jilid 18.pdf', 'Jilid 18')
scan_surah_headers_and_anchors('DATA/pdf/Tafsir 19.pdf', 'Tafsir 19')
