import os
import sys
import re
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

pattern = re.compile(r',\s*(\d+)\s*,\s*[\'\"`]?7[\'\"`]?\s*\)\s*[,;]?\s*$')

def scan_sql(filepath):
    print(f"=== SCANNING {filepath} ===")
    if not os.path.exists(filepath):
        print("File not found!")
        return {}
        
    count = 0
    verses_found = defaultdict(list)
    in_vt = False
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            if 'INSERT INTO `verse_tafsirs`' in line or 'INSERT INTO verse_tafsirs' in line:
                in_vt = True
            elif in_vt and (line.startswith('INSERT INTO') or line.startswith('CREATE TABLE') or line.startswith('-- Table structure')):
                in_vt = False
            
            if in_vt:
                m = pattern.search(line)
                if m:
                    id_verse = int(m.group(1))
                    count += 1
                    verses_found[id_verse].append(line_num)
                    
    print(f"Total Ath-Thabari (id_tafsir=7) tuples found: {count}")
    print(f"Total distinct id_verse found: {len(verses_found)}")
    if verses_found:
        min_v = min(verses_found.keys())
        max_v = max(verses_found.keys())
        print(f"Min id_verse: {min_v}, Max id_verse: {max_v}")
    return verses_found

if __name__ == '__main__':
    for path in ['../DATA/alquran.sql', '../DATA/alquran .sql']:
        scan_sql(path)
