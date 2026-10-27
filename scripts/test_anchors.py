import fitz
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

def test_raw_anchors(pdf_path, name, s_no):
    doc = fitz.open(pdf_path)
    patt = re.compile(
        r'\(Qs\.\s*[^)]*(?:Huud|fluud|Hwd|Httd|Hund|Iluud|Y[uU]+suf|Nahl|Nattl|Nchl|Ncttl|Isra|lsra|Anbiya|Anblya|Mu\'min|Mumin|Nuur|Nur)[^)]*?[:z\.\s\|]\s*([0-9l\,\.\-\'\"\s]+)',
        re.IGNORECASE
    )
    print(f"=== RAW ANCHORS IN {name} ({len(doc)} pages) ===")
    matches = []
    for pno in range(len(doc)):
        txt = doc[pno].get_text('text')
        for m in patt.finditer(txt):
            raw_s = m.group(0).replace('\n', ' ')
            num_part = m.group(1).strip()
            matches.append((pno + 1, raw_s[:70], num_part))
    print(f"Total raw matches: {len(matches)}")
    return matches

m13 = test_raw_anchors('DATA/pdf/Tafsir 13.pdf', 'Tafsir 13', 11)
for s, raw, num in m13:
    if any(n in num for n in ['12', '14', '37', '38']):
        print(f"  Slide {s}: {raw} | num: {num}")

m14 = test_raw_anchors('DATA/pdf/Tafsir 14.pdf', 'Tafsir 14', 11)
print(f"Sample matches in 14: total {len(m14)}")
for s, raw, num in m14:
    if any(n in num for n in ['37', '41', '43', '47', '51', '56', '67', '68', '78', '79', '89', '90', '96', '97', '98', '102', '112', '114']):
        print(f"  Slide {s}: {raw} | num: {num}")
