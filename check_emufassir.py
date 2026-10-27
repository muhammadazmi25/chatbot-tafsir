import os
import sys
import re
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

filepath = '../DATA/db_quran_emufassir_server_27112024.sql'

print(f"=== CHECKING {filepath} ===")
if not os.path.exists(filepath):
    print("File not found!")
    sys.exit(1)

# Step 1: Check what tafsirs are defined in `tafsirs` table
print("\n--- Scanning tafsirs table in SQL ---")
tafsirs = []
with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    in_tafsirs = False
    for line in f:
        if 'INSERT INTO `tafsirs`' in line or 'INSERT INTO tafsirs' in line:
            in_tafsirs = True
        elif in_tafsirs and (line.startswith('INSERT INTO') or line.startswith('CREATE TABLE') or line.startswith('-- Table')):
            in_tafsirs = False
            
        if in_tafsirs:
            # Look for Ath-Thabari or Thabari
            if 'Thabari' in line or 'thabari' in line or 'Tabari' in line or 'tabari' in line:
                print("Found Tafsir Thabari definition line:", line[:200])
            if line.strip().startswith('('):
                tafsirs.append(line.strip()[:100])

print(f"Total tafsirs entries previewed: {len(tafsirs)}")
for t in tafsirs[:10]:
    print(" ", t)

# Step 2: Check verse_tafsirs structure and scan for Thabari (e.g. id_tafsir = 7 or others)
print("\n--- Scanning verse_tafsirs in SQL ---")
# Pattern: (..., ..., id_verse, id_tafsir)
pattern_thabari_7 = re.compile(r',\s*(\d+)\s*,\s*[\'\"`]?7[\'\"`]?\s*\)\s*[,;]?\s*$')

count_7 = 0
verses_7 = defaultdict(list)

# Also let's check what other id_tafsir values exist
tafsir_ids_found = defaultdict(int)
pattern_any_tafsir = re.compile(r',\s*(\d+)\s*,\s*(\d+)\s*\)\s*[,;]?\s*$')

with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    in_vt = False
    for line_num, line in enumerate(f, 1):
        if 'INSERT INTO `verse_tafsirs`' in line or 'INSERT INTO verse_tafsirs' in line:
            in_vt = True
        elif in_vt and (line.startswith('INSERT INTO') or line.startswith('CREATE TABLE') or line.startswith('-- Table')):
            in_vt = False
            
        if in_vt:
            m = pattern_any_tafsir.search(line)
            if m:
                id_verse = int(m.group(1))
                id_tafsir = int(m.group(2))
                tafsir_ids_found[id_tafsir] += 1
                if id_tafsir == 7:
                    count_7 += 1
                    verses_7[id_verse].append(line_num)

print("\n--- Summary of id_tafsir counts in verse_tafsirs ---")
for tid, cnt in sorted(tafsir_ids_found.items()):
    print(f"id_tafsir = {tid}: {cnt} rows")

print(f"\nAth-Thabari (id_tafsir=7): {count_7} rows, {len(verses_7)} distinct id_verse")
if verses_7:
    min_v = min(verses_7.keys())
    max_v = max(verses_7.keys())
    print(f"Min id_verse: {min_v}, Max id_verse: {max_v}")
    
    # Check if Verse 1474 (Hud 1) or 1475 (Hud 2) is in verses_7
    print(f"Is Verse 1474 (Hud 1) present?: {1474 in verses_7}")
    print(f"Is Verse 1475 (Hud 2) present?: {1475 in verses_7}")
    
    hud_present = [v for v in verses_7.keys() if 1474 <= v <= 1596]
    print(f"Hud verses present in id_tafsir=7: {len(hud_present)} verses -> {hud_present}")
