import fitz
import re
import sys
from test_scanner_enhanced import clean_ocr_digits

sys.stdout.reconfigure(encoding='utf-8')

# Check Hud missing verses
# 12, 14, 37, 41, 43, 47, 51, 56, 67, 68, 78, 79, 89, 90, 96, 97, 98, 102, 112, 114
missing_hud = [12, 14, 37, 41, 43, 47, 51, 56, 67, 68, 78, 79, 89, 90, 96, 97, 98, 102, 112, 114]

def find_hud_verse_slides():
    doc13 = fitz.open('DATA/pdf/Tafsir 13.pdf')
    doc14 = fitz.open('DATA/pdf/Tafsir 14.pdf')
    
    print("=== HUD SCAN IN DOC 13 & 14 ===")
    all_anchors = []
    
    # Doc 13 (verses 1-37)
    for pno in range(784, len(doc13)):
        txt = doc13[pno].get_text('text')
        for m in re.finditer(r'\(Qs\.\s*[^)]*(?:Huud|fluud|Hwd)[^)]*?\)', txt, re.IGNORECASE):
            raw = m.group(0).replace('\n', ' ')
            digits = [int(x) for x in clean_ocr_digits(raw).split() if x.isdigit()]
            all_anchors.append(('doc13', pno + 1, raw, digits))
            
    # Doc 14 (verses 37-123)
    for pno in range(450):
        txt = doc14[pno].get_text('text')
        for m in re.finditer(r'\(Qs\.\s*[^)]*(?:Huud|fluud|Hwd)[^)]*?\)', txt, re.IGNORECASE):
            raw = m.group(0).replace('\n', ' ')
            digits = [int(x) for x in clean_ocr_digits(raw).split() if x.isdigit()]
            all_anchors.append(('doc14', pno + 1, raw, digits))
            
    for v in missing_hud:
        matches = []
        for d, s, raw, digits in all_anchors:
            if v in digits or (len(digits) > 1 and min(digits) <= v <= max(digits)):
                matches.append((d, s, digits, raw[:40]))
        print(f"Hud Verse {v:3d}: {matches}")

find_hud_verse_slides()
