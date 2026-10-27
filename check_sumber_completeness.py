import sys
import os
import re
from collections import Counter, defaultdict
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('Chatbot/.env')

engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    v_rows = conn.execute(text('SELECT v.id, c.number_chapter, c.name, v.number FROM verses v JOIN chapters c ON v.id_chapter = c.id')).fetchall()
verse_map = {r[0]: (r[1], r[2], r[3]) for r in v_rows}

filepath = 'DATA/alquran sumber.sql'
tafsir_counter = Counter()
thabari_verses = defaultdict(list)

pattern = re.compile(r'[,;\t]\s*(\d+)\s*[,;\t]\s*(\d+)\s*\)\s*[,;]?\s*$')

in_vt = False
with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    for i, line in enumerate(f):
        if 'INSERT INTO `verse_tafsirs`' in line or 'INSERT INTO verse_tafsirs' in line:
            in_vt = True
        elif in_vt and (line.startswith('DROP TABLE') or line.startswith('CREATE TABLE') or line.startswith('-- Table structure') or (line.startswith('INSERT INTO') and 'verse_tafsirs' not in line)):
            in_vt = False
            
        if in_vt:
            m = pattern.search(line)
            if m:
                id_verse = int(m.group(1))
                id_tafsir = int(m.group(2))
                tafsir_counter[id_tafsir] += 1
                if id_tafsir == 7:
                    thabari_verses[id_verse].append(i)

print('=== DISTRIBUTION ID_TAFSIR IN DATA/alquran sumber.sql ===')
for t_id, cnt in sorted(tafsir_counter.items()):
    print(f'  id_tafsir = {t_id}: {cnt} rows')

print(f'\nTotal Ath-Thabari (id_tafsir=7) rows: {len(thabari_verses)} distinct verses, {sum(len(v) for v in thabari_verses.values())} total rows')

# Group by Surah
surah_ayat = defaultdict(list)
for vid, lines in thabari_verses.items():
    if vid in verse_map:
        surah_no, surah_name, ayat_no = verse_map[vid]
        surah_ayat[(surah_no, surah_name)].append(ayat_no)

print('\n=== SURAH COVERAGE FOR ATH-THABARI (id_tafsir=7) ===')
for (s_no, s_name), ayats in sorted(surah_ayat.items()):
    ayats_sorted = sorted(ayats)
    print(f'Surah {s_no:02d} ({s_name:<15}): {len(set(ayats_sorted)):3d} ayat (Ayat {min(ayats_sorted)} s.d. {max(ayats_sorted)}) [Total baris: {len(ayats_sorted)}]')
