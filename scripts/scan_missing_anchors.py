import fitz
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

def find_anchors_in_doc(pdf_path, surah_keywords, max_ayat=200):
    doc = fitz.open(pdf_path)
    pattern = re.compile(
        r'\(Qs\.\s*[^)]*(?:' + surah_keywords + r')[^)]*?[:z\.\s\|]\s*([0-9l\,\.\-\'\"]+)\)',
        re.IGNORECASE
    )
    anchors = []
    for pno in range(len(doc)):
        text = doc[pno].get_text('text')
        for m in pattern.finditer(text):
            raw_match = m.group(0)
            num_str = m.group(1).lower().replace('l', '1')
            # Parse numbers
            parts = re.split(r'[\'\"\,\.\-\/\s]', num_str)
            nums = []
            for p in parts:
                p = p.strip()
                if p.isdigit():
                    n = int(p)
                    if n <= max_ayat:
                        nums.append(n)
            anchors.append({
                'slide': pno + 1,
                'raw': raw_match.replace('\n', ' '),
                'nums': nums,
                'num_str': num_str
            })
    return anchors

print("Scanning Tafsir 13 for Hud...")
hud13 = find_anchors_in_doc('DATA/pdf/Tafsir 13.pdf', 'Huud|fluud|Hwd', 123)
print(f"Total anchors found in Tafsir 13: {len(hud13)}")
for a in hud13:
    if any(n in [12, 13, 14, 35, 36, 37] for n in a['nums']):
        print(f"  Slide {a['slide']}: {a['raw']} -> {a['nums']}")

print("\nScanning Tafsir 14 for Hud & Yusuf...")
hud14 = find_anchors_in_doc('DATA/pdf/Tafsir 14.pdf', 'Huud|fluud|Hwd', 123)
print(f"Total Hud anchors in Tafsir 14: {len(hud14)}")
for a in hud14:
    if any(n in [37, 38, 41, 42, 43, 44, 47, 51, 56, 67, 68, 78, 79, 89, 90, 96, 97, 98, 102, 112, 114] for n in a['nums']):
        print(f"  Slide {a['slide']}: {a['raw']} -> {a['nums']}")

yusuf14 = find_anchors_in_doc('DATA/pdf/Tafsir 14.pdf', 'Y[uU]+suf', 111)
print(f"Total Yusuf anchors in Tafsir 14: {len(yusuf14)}")
for a in yusuf14:
    if any(n in [47, 54, 57, 59, 61, 62, 65, 69, 76, 77, 79, 96] for n in a['nums']):
        print(f"  Slide {a['slide']}: {a['raw']} -> {a['nums']}")
