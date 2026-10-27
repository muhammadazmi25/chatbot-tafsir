import fitz
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

pdfs = {
    '13': 'DATA/pdf/Tafsir 13.pdf',
    '14': 'DATA/pdf/Tafsir 14.pdf',
    '16': 'DATA/pdf/Tafsir ath-Thabari_Jilid 16.pdf',
    '17': 'DATA/pdf/Tafsir ath-Thabari_Jilid 17.pdf',
    '18': 'DATA/pdf/Tafsir ath-Thabari_Jilid 18.pdf',
    '19': 'DATA/pdf/Tafsir 19.pdf',
}

# 1. Check where Surah 17 (Al-Isra') ayat 38 is
print("=== Search for Al-Isra' [17]: 38 ===")
for pkey in ['16', '17']:
    doc = fitz.open(pdfs[pkey])
    for pno in range(len(doc)):
        txt = doc[pno].get_text('text')
        if ('isra' in txt.lower() or 'lsra' in txt.lower() or '17' in txt) and '38' in txt:
            # Check if there is a match for (Qs. ... 38)
            m = re.findall(r'\(Qs\.[^)]*?(?:Isra|lsra)[^)]*?\)', txt, re.IGNORECASE)
            if m:
                print(f"Found in {pkey} slide {pno+1}: {m}")
            elif '38' in txt and ('isra' in txt.lower() or 'lsra' in txt.lower()):
                # check surrounding lines
                for line in txt.split('\n'):
                    if '38' in line and any(w in line.lower() for w in ['qs', 'ayat', 'surah']):
                        print(f"Possible in {pkey} slide {pno+1}: {line}")

# 2. Check where An-Nahl (16) ayat 12, 18, 29, 90 are
print("\n=== Search for An-Nahl [16]: 12, 18, 29, 90 ===")
for pkey in ['16']:
    doc = fitz.open(pdfs[pkey])
    for pno in range(len(doc)):
        txt = doc[pno].get_text('text')
        m = re.findall(r'\(Qs\.[^)]*?(?:Nahl|Nattl|Nchl|Ncttl)[^)]*?\)', txt, re.IGNORECASE)
        for match in m:
            if any(num in match for num in ['12', '18', '29', '90']):
                print(f"Found in {pkey} slide {pno+1}: {match}")

# 3. Check where Al-Anbiya' 69 and Al-Mu'minun 75 are
print("\n=== Search for Al-Anbiya 69 & Al-Mu'minun 75 ===")
for pkey in ['18']:
    doc = fitz.open(pdfs[pkey])
    for pno in range(len(doc)):
        txt = doc[pno].get_text('text')
        m = re.findall(r'\(Qs\.[^)]*?(?:Anbiya|Anblya|Mu\'min|Mumin)[^)]*?\)', txt, re.IGNORECASE)
        for match in m:
            if '69' in match or '75' in match:
                print(f"Found in {pkey} slide {pno+1}: {match}")

# 4. Check where An-Nur (24) starts and ends in Jilid 18 and 19
print("\n=== Search for An-Nur [24] in Jilid 18 and 19 ===")
for pkey in ['18', '19']:
    doc = fitz.open(pdfs[pkey])
    found_nur = []
    for pno in range(len(doc)):
        txt = doc[pno].get_text('text')
        m = re.findall(r'\(Qs\.[^)]*?(?:Nuur|Nur)[^)]*?\)', txt, re.IGNORECASE)
        if m:
            found_nur.append((pno+1, m[0]))
    print(f"In {pkey}, found {len(found_nur)} An-Nur anchors. First 3: {found_nur[:3]}, Last 3: {found_nur[-3:]}")
