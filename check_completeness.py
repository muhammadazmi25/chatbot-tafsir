import os
import sys
from collections import defaultdict
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('.env')

engine = create_engine(os.getenv('DATABASE_URL'))

with engine.connect() as conn:
    # 1. Get all verses for surahs 11-24
    verses_query = text('''
        SELECT 
            c.number_chapter as no_surah,
            c.name as nama_surah,
            c.verse_count as total_ayat,
            v.id as id_verse,
            v.number as no_ayat
        FROM chapters c
        JOIN verses v ON v.id_chapter = c.id
        WHERE c.number_chapter BETWEEN 11 AND 24
        ORDER BY c.number_chapter, v.number
    ''')
    all_verses = conn.execute(verses_query).fetchall()

    # 2. Get all Ath-Thabari records
    thabari_query = text('''
        SELECT 
            vt.id as vt_id,
            vt.id_verse,
            LENGTH(vt.text) as text_len,
            (SELECT COUNT(*) FROM tafsir_takwil_units u WHERE u.id_verse_tafsir = vt.id) as unit_count
        FROM verse_tafsirs vt
        WHERE vt.id_tafsir = 7
    ''')
    thabari_rows = conn.execute(thabari_query).fetchall()

# Organize data
verse_to_vt = defaultdict(list)
for r in thabari_rows:
    verse_to_vt[r.id_verse].append(r)

surah_data = defaultdict(lambda: {'nama': '', 'total': 0, 'verses': []})
for v in all_verses:
    surah_data[v.no_surah]['nama'] = v.nama_surah
    surah_data[v.no_surah]['total'] = v.total_ayat
    surah_data[v.no_surah]['verses'].append(v)

print("="*80)
print(f"{'No':<4} {'Surah':<15} {'Total Ayat':<11} {'Tersedia':<10} {'Unit':<8} {'Duplikat':<10} {'Status Cakupan':<20}")
print("="*80)

detailed_reports = []

for no_surah in range(11, 25):
    data = surah_data[no_surah]
    nama = data['nama']
    total = data['total']
    verses = data['verses']
    
    present_ayat = []
    missing_ayat = []
    dup_ayat = []
    total_units = 0
    total_vt_rows = 0
    
    for v in verses:
        vts = verse_to_vt[v.id_verse]
        if vts:
            present_ayat.append(v.no_ayat)
            total_vt_rows += len(vts)
            if len(vts) > 1:
                dup_ayat.append((v.no_ayat, len(vts)))
            for vt in vts:
                total_units += vt.unit_count
        else:
            missing_ayat.append(v.no_ayat)
            
    pct = (len(present_ayat) / total) * 100
    status = f"{pct:.1f}% ({len(present_ayat)}/{total})"
    dup_str = f"{len(dup_ayat)} ayat" if dup_ayat else "-"
    
    print(f"{no_surah:<4} {nama:<15} {total:<11} {len(present_ayat):<10} {total_units:<8} {dup_str:<10} {status:<20}")
    
    detailed_reports.append({
        'no_surah': no_surah,
        'nama': nama,
        'total': total,
        'present_ayat': present_ayat,
        'missing_ayat': missing_ayat,
        'dup_ayat': dup_ayat,
        'total_units': total_units,
        'total_vt_rows': total_vt_rows
    })

print("="*80)

# Print detailed breakdowns for partial or duplicate surahs
print("\n" + "="*80)
print("RINCIAN DETAIL SETIAP SURAH (11 s.d. 24):")
print("="*80)

for r in detailed_reports:
    print(f"\n[{r['no_surah']}. Surah {r['nama']}] (Total: {r['total']} ayat)")
    if len(r['present_ayat']) == r['total']:
        print(f"  - Kelengkapan: LENGKAP (100%) - Semua ayat 1 s.d. {r['total']} tersedia.")
    else:
        print(f"  - Kelengkapan: SEBAGIAN ({len(r['present_ayat'])}/{r['total']} ayat)")
        if r['present_ayat']:
            print(f"    - Ayat Tersedia: Ayat {min(r['present_ayat'])} s.d. {max(r['present_ayat'])} (Total: {len(r['present_ayat'])})")
        if r['missing_ayat']:
            if len(r['missing_ayat']) > 10:
                print(f"    - Ayat Tidak Ada: Ayat {min(r['missing_ayat'])} s.d. {max(r['missing_ayat'])} (Total: {len(r['missing_ayat'])})")
            else:
                print(f"    - Ayat Tidak Ada: {r['missing_ayat']}")
                
    print(f"  - Total Baris di verse_tafsirs: {r['total_vt_rows']}")
    print(f"  - Total Unit Takwil di tafsir_takwil_units: {r['total_units']}")
    if r['dup_ayat']:
        print(f"  - Ayat dengan baris ganda di database: {len(r['dup_ayat'])} ayat -> Contoh: {r['dup_ayat'][:5]}...")
