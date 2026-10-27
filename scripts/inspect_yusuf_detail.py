import fitz
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')
doc = fitz.open('DATA/pdf/Tafsir 14.pdf')

def inspect_yusuf(p_start, p_end, label):
    print(f"\n==========================================")
    print(f"{label} (Slides {p_start} to {p_end})")
    print(f"==========================================")
    for p in range(p_start - 1, p_end):
        t = doc[p].get_text('text')
        lines = [l.strip() for l in t.split('\n') if l.strip()]
        for l in lines:
            if any(k in l.lower() for k in ['(qs.', 'takwil firman', 'talrwil', 'firman allah', 'firman-nya']):
                if any(w in l.lower() for w in ['yuusuf', 'yusuf', 'firman']):
                    print(f"  Slide {p+1}: {l[:80]}")

# 47
inspect_yusuf(730, 735, "Yusuf 47")

# 54, 57, 59, 61, 62, 65, 69
inspect_yusuf(755, 830, "Yusuf 54 - 69")

# 76, 77, 79
inspect_yusuf(850, 885, "Yusuf 76 - 79")

# 96
inspect_yusuf(960, 975, "Yusuf 96")
