import fitz
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

doc = fitz.open('DATA/pdf/Tafsir 19.pdf')
print(f"Total pages in Tafsir 19: {len(doc)}")

nur_anchors = []
for pno in range(320): # An-Nur is within first ~320 pages
    txt = doc[pno].get_text('text')
    # Match any Qs. ... Nuur / Nur ... : XX
    matches = re.finditer(r'\(Qs\.\s*[^)]*Nu+r[^)]*?[:z\.\s\|]\s*([0-9l\,\.\-\'\"]+)\)', txt, re.IGNORECASE)
    for m in matches:
        raw = m.group(0).replace('\n', ' ')
        num_str = m.group(1).lower().replace('l', '1')
        parts = re.split(r'[\'\"\,\.\-\/\s]', num_str)
        nums = [int(p) for p in parts if p.isdigit() and int(p) <= 64]
        if nums:
            nur_anchors.append((pno + 1, nums, raw))

print(f"Found {len(nur_anchors)} An-Nur anchors:")
for item in nur_anchors:
    print(f"  Slide {item[0]:3d}: {item[1]}  |  {item[2][:50]}")
