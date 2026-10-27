import fitz
import re
import sys
from test_scanner_enhanced import clean_ocr_digits, SURAH_NAMES

sys.stdout.reconfigure(encoding='utf-8')

def scan_hud_yusuf():
    print("=== SCANNING HUD (11) IN TAFSIR 13 & 14 ===")
    missing_hud = [12, 14, 37, 41, 43, 47, 51, 56, 67, 68, 78, 79, 89, 90, 96, 97, 98, 102, 112, 114]
    
    # Tafsir 13 has Hud 1 to ~37
    doc13 = fitz.open('DATA/pdf/Tafsir 13.pdf')
    for pno in range(780, len(doc13)):
        t = doc13[pno].get_text('text').replace('\n', ' ')
        m = re.findall(r'\(Qs\.\s*[^)]*(?:Huud|fluud|Hwd)[^)]*?\)', t, re.IGNORECASE)
        for cit in m:
            digits = [int(x) for x in clean_ocr_digits(cit).split() if x.isdigit()]
            print(f"Tafsir 13 Slide {pno+1}: {cit[:50]} -> digits: {digits}")
            
    doc14 = fitz.open('DATA/pdf/Tafsir 14.pdf')
    # Check Hud in Tafsir 14 (Slide 1 to 450)
    for pno in range(450):
        t = doc14[pno].get_text('text').replace('\n', ' ')
        m = re.findall(r'\(Qs\.\s*[^)]*(?:Huud|fluud|Hwd)[^)]*?\)', t, re.IGNORECASE)
        for cit in m:
            digits = [int(x) for x in clean_ocr_digits(cit).split() if x.isdigit()]
            # check if any missing verse in digits
            if any(h in digits for h in missing_hud) or pno < 20:
                print(f"Tafsir 14 Slide {pno+1}: {cit[:50]} -> digits: {digits}")

scan_hud_yusuf()
