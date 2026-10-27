import fitz
import sys

sys.stdout.reconfigure(encoding='utf-8')
doc = fitz.open('DATA/pdf/Tafsir ath-Thabari_Jilid 16.pdf')

print('--- Searching for Ayat 12 ---')
for pno in range(len(doc)):
    txt = doc[pno].get_text('text')
    if any(k in txt.lower() for k in ['menundukkan malam', 'malam dan siang', 'bintang-bintang']):
        clean = txt[:150].strip().replace('\n', ' ')
        print(f"Slide {pno+1}: {clean}")

print('\n--- Searching for Ayat 90 ---')
for pno in range(len(doc)):
    txt = doc[pno].get_text('text')
    if any(k in txt.lower() for k in ['berlaku adil', 'kebajikan, memberi', 'perbuatan keji', 'kemungkaran dan permusuhan']):
        clean = txt[:150].strip().replace('\n', ' ')
        print(f"Slide {pno+1}: {clean}")
