import fitz
import re
import sys
from test_scanner_enhanced import clean_ocr_digits

sys.stdout.reconfigure(encoding='utf-8')

doc = fitz.open('DATA/pdf/Tafsir 19.pdf')

# Let's find every anchor of An-Nur in first 320 pages
anchors = []
for pno in range(320):
    t = doc[pno].get_text('text').replace('\n', ' ')
    # Match Qs. An-Nuur or similar
    for m in re.finditer(r'\(Qs\.\s*[^)]*(?:Nuu?r|Nutrr)[^)]*?\)', t, re.IGNORECASE):
        raw = m.group(0)
        digits = [int(x) for x in clean_ocr_digits(raw).split() if x.isdigit()]
        # Filter for verse numbers <= 64
        verses = [d for d in digits if 1 <= d <= 64 and d != 24]
        if verses:
            anchors.append({
                'slide': pno + 1,
                'raw': raw[:45],
                'verses': verses
            })

print(f"Total raw An-Nur anchors: {len(anchors)}")
# Print sorted
for a in sorted(anchors, key=lambda x: x['slide']):
    print(f"Slide {a['slide']:3d}: verses {a['verses']}  |  {a['raw']}")
