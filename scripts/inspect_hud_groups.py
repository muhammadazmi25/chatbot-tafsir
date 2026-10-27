import fitz
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')
doc = fitz.open('DATA/pdf/Tafsir 14.pdf')

def inspect_around(p_start, p_end, label):
    print(f"\n==========================================")
    print(f"{label} (Slides {p_start} to {p_end})")
    print(f"==========================================")
    for p in range(p_start - 1, p_end):
        t = doc[p].get_text('text')
        lines = [l.strip() for l in t.split('\n') if l.strip()]
        for l in lines:
            if any(k in l.lower() for k in ['(qs.', 'takwil firman', 'talrwil', 'firman allah', 'firman-nya']):
                print(f"  Slide {p+1}: {l[:80]}")

# 41, 42, 43, 44
inspect_around(40, 55, "Hud 41 - 44")

# 47
inspect_around(80, 88, "Hud 47")

# 51, 56
inspect_around(93, 115, "Hud 51 - 56")

# 67, 68
inspect_around(135, 145, "Hud 67 - 68")

# 78, 79
inspect_around(185, 205, "Hud 78 - 79")

# 89, 90
inspect_around(260, 275, "Hud 89 - 90")

# 96, 97, 98, 102
inspect_around(290, 320, "Hud 96 - 102")

# 112, 114
inspect_around(350, 370, "Hud 112 - 114")
