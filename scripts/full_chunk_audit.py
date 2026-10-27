# -*- coding: utf-8 -*-
"""
=============================================================================
FULL CHUNK AUDIT  Tafsir Ath-Thabari
=============================================================================
Memeriksa kondisi aktual:
  1. MySQL: verse_tafsirs & tafsir_takwil_units (kelengkapan, kekosongan, struktur)
  2. Qdrant: collection, jumlah vectors, payload integrity
  3. Cross-check MySQL <-> Qdrant (orphan / missing)
  4. Kualitas konten chunk (teks pendek, rusak, tanpa atribusi)
=============================================================================
"""
import os, sys, re
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
load_dotenv(ROOT / ".env")

from sqlalchemy import create_engine, text

DATABASE_URL   = os.getenv("DATABASE_URL")
QDRANT_URL     = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION     = os.getenv("QDRANT_COLLECTION", "tafsir_ath_thabari_hud_annur_v14")
SURAH_START    = int(os.getenv("SURAH_START", "11"))
SURAH_END      = int(os.getenv("SURAH_END",   "24"))
TAFSIR_ID      = 7

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
sys.stdout.reconfigure(encoding="utf-8")

SEP = "=" * 80
WARN = "[WARN]"; OK = "[ OK ]"; ERR = "[ERR ]"; INFO = "[INFO]"
issues = []

def flag(level, msg):
    prefix = {"WARN": WARN, "OK": OK, "ERR": ERR, "INFO": INFO}.get(level, "?")
    print(f"   {prefix} {msg}")
    if level in ("WARN", "ERR"):
        issues.append(f"{prefix} {msg}")

# -------------------------------------------------------------
# BAGIAN 1: MySQL verse_tafsirs
# -------------------------------------------------------------
def audit_verse_tafsirs(conn):
    print(f"\n{SEP}")
    print("BAGIAN 1: MySQL -> verse_tafsirs (teks tafsir mentah per ayat)")
    print(SEP)

    r = conn.execute(text("""
        SELECT c.number_chapter, c.name,
               COUNT(v.id) total_ayat, COUNT(vt.id) ada_tafsir,
               COUNT(v.id) - COUNT(vt.id) kosong
        FROM verses v
        JOIN chapters c ON v.id_chapter = c.id
        LEFT JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = :tid
        WHERE c.number_chapter BETWEEN :s AND :e
        GROUP BY c.number_chapter, c.name ORDER BY c.number_chapter
    """), {"tid": TAFSIR_ID, "s": SURAH_START, "e": SURAH_END}).fetchall()

    print(f"\n  {'QS':>4} {'Nama':<20} {'Total':>6} {'Ada':>6} {'Kosong':>7}")
    print(f"  {'-'*4} {'-'*20} {'-'*6} {'-'*6} {'-'*7}")
    total_ayat = total_ada = total_kosong = 0
    for row in r:
        surah, nama, tot, ada, kos = row
        total_ayat += tot; total_ada += ada; total_kosong += kos
        status = OK if kos == 0 else (ERR if kos > 20 else WARN)
        print(f"  {surah:>4} {nama:<20} {tot:>6} {ada:>6} {kos:>7}  {status}")
        if kos > 0:
            flag("ERR" if kos > 20 else "WARN", f"QS {surah} ({nama}): {kos} ayat belum ada teks tafsir")
    print(f"  {'-'*4} {'-'*20} {'-'*6} {'-'*6} {'-'*7}")
    print(f"  {'TOT':>4} {'':20} {total_ayat:>6} {total_ada:>6} {total_kosong:>7}")
    print(f"\n  Kelengkapan: {total_ada}/{total_ayat} ({total_ada/total_ayat*100:.1f}%)")

    # Duplikat
    dups = conn.execute(text("""
        SELECT v.id, c.number_chapter, v.number, COUNT(vt.id) c
        FROM verses v JOIN chapters c ON v.id_chapter = c.id
        JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = :tid
        WHERE c.number_chapter BETWEEN :s AND :e
        GROUP BY v.id HAVING c > 1
    """), {"tid": TAFSIR_ID, "s": SURAH_START, "e": SURAH_END}).fetchall()
    print(f"\n  Duplikat verse_tafsirs: {len(dups)}")
    for d in dups:
        flag("ERR", f"Duplikat: verse_id={d[0]} QS {d[1]}:{d[2]} => {d[3]} baris")
    if not dups:
        flag("OK", "Tidak ada duplikat")

    # Teks pendek
    short = conn.execute(text("""
        SELECT c.number_chapter, v.number, LENGTH(vt.text) len
        FROM verses v JOIN chapters c ON v.id_chapter = c.id
        JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = :tid
        WHERE c.number_chapter BETWEEN :s AND :e
          AND (vt.text IS NULL OR LENGTH(TRIM(vt.text)) < 100)
        ORDER BY c.number_chapter, v.number
    """), {"tid": TAFSIR_ID, "s": SURAH_START, "e": SURAH_END}).fetchall()
    print(f"\n  Teks NULL / < 100 char: {len(short)}")
    for s in short:
        flag("ERR", f"Teks sangat pendek ({s[2]} char): QS {s[0]}:{s[1]}")

    # Teks tanpa huruf Arab
    all_rows = conn.execute(text("""
        SELECT c.number_chapter, v.number, vt.text
        FROM verses v JOIN chapters c ON v.id_chapter = c.id
        JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = :tid
        WHERE c.number_chapter BETWEEN :s AND :e
    """), {"tid": TAFSIR_ID, "s": SURAH_START, "e": SURAH_END}).fetchall()

    no_ar = bad_sym = 0
    bad_sym_pat = re.compile(r'[\#\$\*\{\}\^\~]{2,}')
    for row in all_rows:
        txt = row[2] or ""
        if not re.search(r'[\u0600-\u06FF]', txt):
            no_ar += 1
            flag("WARN", f"Tidak ada huruf Arab: QS {row[0]}:{row[1]}")
        if bad_sym_pat.search(txt):
            bad_sym += 1
            flag("WARN", f"Simbol rusak OCR: QS {row[0]}:{row[1]}")
    print(f"\n  Teks tanpa huruf Arab  : {no_ar}")
    print(f"  Teks simbol rusak OCR  : {bad_sym}")

    return total_ada

# -------------------------------------------------------------
# BAGIAN 2: MySQL tafsir_takwil_units
# -------------------------------------------------------------
def audit_takwil_units(conn):
    print(f"\n{SEP}")
    print("BAGIAN 2: MySQL -> tafsir_takwil_units (chunk terstruktur)")
    print(SEP)

    r = conn.execute(text("""
        SELECT c.number_chapter, c.name,
               COUNT(DISTINCT v.id) ayat,
               COUNT(u.id) units,
               COUNT(CASE WHEN u.ringkasan_takwil IS NULL OR TRIM(u.ringkasan_takwil)='' THEN 1 END) kosong,
               COUNT(CASE WHEN u.lafaz_frasa IS NULL OR TRIM(u.lafaz_frasa)='' THEN 1 END) tanpa_lafaz,
               COUNT(CASE WHEN u.has_ikhtilaf=1 THEN 1 END) ikhtilaf,
               ROUND(AVG(LENGTH(u.ringkasan_takwil))) avg_len
        FROM verses v JOIN chapters c ON v.id_chapter = c.id
        JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = :tid
        LEFT JOIN tafsir_takwil_units u ON u.id_verse_tafsir = vt.id
        WHERE c.number_chapter BETWEEN :s AND :e
        GROUP BY c.number_chapter, c.name ORDER BY c.number_chapter
    """), {"tid": TAFSIR_ID, "s": SURAH_START, "e": SURAH_END}).fetchall()

    print(f"\n  {'QS':>4} {'Nama':<20} {'Ayat':>5} {'Units':>6} {'Kos':>5} {'TnpLafaz':>9} {'Ikh':>5} {'Avg':>6}")
    print(f"  {'-'*4} {'-'*20} {'-'*5} {'-'*6} {'-'*5} {'-'*9} {'-'*5} {'-'*6}")
    total_u = total_k = 0
    for row in r:
        surah, nama, ayat, units, kos, tl, ikh, avg = row
        total_u += (units or 0); total_k += (kos or 0)
        avg = int(avg) if avg else 0
        print(f"  {surah:>4} {nama:<20} {ayat:>5} {units or 0:>6} {kos or 0:>5} {tl or 0:>9} {ikh or 0:>5} {avg:>6}")
        if not units:
            flag("ERR", f"QS {surah} ({nama}) punya verse_tafsir tapi 0 takwil units!")
        if kos and kos > 0:
            flag("WARN", f"QS {surah}: {kos} units dengan ringkasan_takwil kosong")
    print(f"  {'-'*4} {'-'*20} {'-'*5} {'-'*6} {'-'*5}")
    print(f"  {'TOT':>4} {'':20} {'':>5} {total_u:>6} {total_k:>5}")

    # Ayat ber-teks tapi belum di-chunk
    no_units = conn.execute(text("""
        SELECT c.number_chapter, c.name, v.number, vt.id
        FROM verses v JOIN chapters c ON v.id_chapter = c.id
        JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = :tid
        LEFT JOIN tafsir_takwil_units u ON u.id_verse_tafsir = vt.id
        WHERE c.number_chapter BETWEEN :s AND :e
          AND u.id IS NULL AND vt.text IS NOT NULL AND TRIM(vt.text) != ''
        ORDER BY c.number_chapter, v.number
    """), {"tid": TAFSIR_ID, "s": SURAH_START, "e": SURAH_END}).fetchall()
    print(f"\n  Ayat ber-teks tapi 0 units (pakai fallback mentah): {len(no_units)}")
    if no_units:
        flag("WARN", f"{len(no_units)} ayat memakai fallback teks mentah (belum di-parse)")
        by_surah = {}
        for row in no_units:
            key = f"QS {row[0]} ({row[1]})"
            by_surah.setdefault(key, []).append(row[2])
        for k, vlist in by_surah.items():
            print(f"     {k}: ayat {vlist}")
    else:
        flag("OK", "Semua ayat ber-teks sudah memiliki minimal 1 takwil unit")

    # tafsir_aqwal
    try:
        aq = conn.execute(text("""
            SELECT COUNT(*) total,
                   COUNT(CASE WHEN speaker_name IS NULL OR TRIM(speaker_name)='' THEN 1 END) tanpa_nama,
                   COUNT(CASE WHEN statement IS NULL OR TRIM(statement)='' THEN 1 END) tanpa_stmt,
                   COUNT(DISTINCT id_unit) unit_ada
            FROM tafsir_aqwal
        """)).fetchone()
        print(f"\n  tafsir_aqwal: total={aq[0]}, tanpa_nama={aq[1]}, tanpa_stmt={aq[2]}, unit_ada={aq[3]}")
        if aq[1] > 0:
            flag("ERR", f"{aq[1]} aqwal tanpa speaker_name (perawi hilang  Al-Hasan/Qatadah/Mujahid dst)")
        else:
            flag("OK", "Semua aqwal punya speaker_name")
        if aq[3] == 0:
            flag("ERR", "tafsir_aqwal kosong  tidak ada data pendapat ulama sama sekali!")

        # Distribusi tipe
        types = conn.execute(text("""
            SELECT speaker_type, COUNT(*) c FROM tafsir_aqwal GROUP BY speaker_type ORDER BY c DESC
        """)).fetchall()
        print(f"  Distribusi speaker_type:")
        for t in types:
            print(f"     {str(t[0] or '(NULL)'):<25}: {t[1]}")
    except Exception as ex:
        flag("WARN", f"tafsir_aqwal error: {ex}")

    # tafsir_tarjih
    try:
        tj = conn.execute(text("""
            SELECT COUNT(*),
                   COUNT(CASE WHEN status IS NULL OR TRIM(status)='' THEN 1 END),
                   COUNT(CASE WHEN reasoning IS NULL OR TRIM(reasoning)='' THEN 1 END)
            FROM tafsir_tarjih
        """)).fetchone()
        print(f"\n  tafsir_tarjih: total={tj[0]}, tanpa_status={tj[1]}, tanpa_reasoning={tj[2]}")
        if tj[0] == 0:
            flag("ERR", "tafsir_tarjih KOSONG  kesimpulan/tarjih Ath-Thabari tidak tersimpan!")
        else:
            flag("OK", f"{tj[0]} tarjih tersimpan")
    except Exception as ex:
        flag("WARN", f"tafsir_tarjih tidak ada / error: {ex}")

    return total_u, no_units

# -------------------------------------------------------------
# BAGIAN 3: Qdrant
# -------------------------------------------------------------
def audit_qdrant():
    print(f"\n{SEP}")
    print(f"BAGIAN 3: Qdrant -> '{COLLECTION}'")
    print(SEP)
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        flag("ERR", "qdrant-client tidak terinstall"); return 0, []

    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
    try:
        info = client.get_collection(COLLECTION)
        count = info.points_count
        print(f"\n  Jumlah vectors: {count}")
        if count == 0:
            flag("ERR", "Collection KOSONG!"); return 0, []
        flag("OK", f"{count} vectors tersedia")
    except Exception as ex:
        flag("ERR", f"Gagal akses Qdrant: {ex}"); return 0, []

    # Scroll sample
    print(f"\n  Mengambil sample payload (200 points)...")
    sample = []
    offset = None
    while len(sample) < 200:
        batch, next_offset = client.scroll(
            collection_name=COLLECTION, limit=100, offset=offset,
            with_payload=True, with_vectors=False)
        sample.extend(batch)
        if next_offset is None or not batch: break
        offset = next_offset

    # Inspect payload
    miss_surah = miss_ayat = miss_teks = miss_uid = 0
    has_aqwal = has_seg = has_perawi = 0
    short_ids = []
    lengths = []
    surah_cnt = {}

    for pt in sample:
        pl = pt.payload or {}
        if not (pl.get("no_surah") or pl.get("nama_surah")): miss_surah += 1
        if not pl.get("no_ayat"): miss_ayat += 1
        teks = pl.get("teks_tafsir", pl.get("text", ""))
        if not teks or len(str(teks).strip()) < 50:
            miss_teks += 1; short_ids.append(pt.id)
        else:
            lengths.append(len(str(teks)))
        if not pl.get("id_unit"): miss_uid += 1
        if "aqwal" in pl or "speaker" in pl: has_aqwal += 1
        if "segment_type" in pl: has_seg += 1
        if "perawi" in pl or "speaker_name" in pl: has_perawi += 1
        s = pl.get("no_surah", "?")
        surah_cnt[s] = surah_cnt.get(s, 0) + 1

    avg_l = int(sum(lengths)/len(lengths)) if lengths else 0
    n = len(sample)
    print(f"\n  Sample {n} points:")
    print(f"     Tanpa surah        : {miss_surah}")
    print(f"     Tanpa no_ayat      : {miss_ayat}")
    print(f"     Teks < 50 char     : {miss_teks}  ids={short_ids[:5]}")
    print(f"     Tanpa id_unit      : {miss_uid}")
    print(f"     Len teks min/avg/mx: {min(lengths) if lengths else 0}/{avg_l}/{max(lengths) if lengths else 0}")
    print(f"\n  Field kritis untuk kualitas RAG:")
    print(f"     'aqwal'            : {has_aqwal}/{n}  <- pendapat ulama")
    print(f"     'segment_type'     : {has_seg}/{n}   <- riwayat/tarjih/penjelasan")
    print(f"     'perawi'           : {has_perawi}/{n}  <- nama perawi Al-Hasan/Qatadah")

    if miss_surah > 0:   flag("ERR",  f"{miss_surah} points tanpa identitas surah")
    if miss_ayat  > 0:   flag("ERR",  f"{miss_ayat} points tanpa no_ayat")
    if miss_teks  > 0:   flag("ERR",  f"{miss_teks} points teks rusak/kosong")
    if miss_uid   > 0:   flag("WARN", f"{miss_uid} points tanpa id_unit")
    if has_aqwal  == 0:  flag("ERR",  "Tidak ada field 'aqwal' -> atribusi perawi tidak masuk Qdrant")
    if has_seg    == 0:  flag("ERR",  "Tidak ada field 'segment_type' -> LLM tidak bisa bedakan riwayat vs tarjih")
    if has_perawi == 0:  flag("ERR",  "Tidak ada field 'perawi' -> LLM tidak bisa sebut nama perawi")

    print(f"\n  Distribusi surah (sample):")
    for s in sorted(surah_cnt.keys()):
        print(f"     QS {s}: {surah_cnt[s]}")

    return count, sample

# -------------------------------------------------------------
# BAGIAN 4: Cross-check
# -------------------------------------------------------------
def audit_cross_check(conn, qdrant_count, sample):
    print(f"\n{SEP}")
    print("BAGIAN 4: Cross-check MySQL <-> Qdrant")
    print(SEP)

    mysql_units = conn.execute(text("""
        SELECT COUNT(u.id) FROM tafsir_takwil_units u
        JOIN verse_tafsirs vt ON u.id_verse_tafsir = vt.id
        JOIN verses v ON vt.id_verse = v.id
        JOIN chapters c ON v.id_chapter = c.id
        WHERE c.number_chapter BETWEEN :s AND :e
          AND u.ringkasan_takwil IS NOT NULL AND TRIM(u.ringkasan_takwil) != ''
    """), {"s": SURAH_START, "e": SURAH_END}).scalar()

    print(f"\n  MySQL units (valid)   : {mysql_units}")
    print(f"  Qdrant count          : {qdrant_count}")
    diff = (qdrant_count or 0) - (mysql_units or 0)
    if diff == 0:
        flag("OK", "MySQL units == Qdrant count  sinkron sempurna")
    elif diff > 0:
        flag("WARN", f"Qdrant memiliki {diff} points LEBIH dari MySQL units (mungkin embed lama/orphan)")
    else:
        flag("ERR",  f"Qdrant memiliki {abs(diff)} points KURANG  belum di-embed semua!")

    # Validate sample IDs
    if sample:
        qdrant_ids = {int(pt.payload.get("id_unit")) for pt in sample if pt.payload and pt.payload.get("id_unit")}
        if qdrant_ids:
            pl = ",".join(str(i) for i in list(qdrant_ids)[:50])
            mysql_ids = set(conn.execute(text(f"SELECT id FROM tafsir_takwil_units WHERE id IN ({pl})")).scalars().fetchall())
            orphan = qdrant_ids - mysql_ids
            print(f"\n  Qdrant sample id_unit check ({len(qdrant_ids)} IDs):")
            print(f"     Ada di MySQL  : {len(mysql_ids)}")
            if orphan:
                flag("WARN", f"{len(orphan)} id_unit di Qdrant tidak ada di MySQL: {list(orphan)[:10]}")
            else:
                flag("OK", "Semua sample id_unit ada di MySQL")

# -------------------------------------------------------------
# BAGIAN 5: Kualitas chunk konten
# -------------------------------------------------------------
def audit_chunk_quality(conn):
    print(f"\n{SEP}")
    print("BAGIAN 5: Kualitas Konten Chunk")
    print(SEP)

    rows = conn.execute(text("""
        SELECT u.id, u.ringkasan_takwil, c.number_chapter, v.number
        FROM tafsir_takwil_units u
        JOIN verse_tafsirs vt ON u.id_verse_tafsir = vt.id
        JOIN verses v ON vt.id_verse = v.id
        JOIN chapters c ON v.id_chapter = c.id
        WHERE c.number_chapter BETWEEN :s AND :e
          AND u.ringkasan_takwil IS NOT NULL
    """), {"s": SURAH_START, "e": SURAH_END}).fetchall()

    if not rows:
        flag("ERR", "Tidak ada takwil_units  tidak bisa audit kualitas"); return

    llm_pat  = re.compile(r"(ayat ini menegaskan|petunjuk hidup|tidak hanya berisi informasi|hendaknya kita|pelajaran yang bisa|hikmah dari)", re.I)
    perawi_p = re.compile(r"(al-hasan|qatadah|mujahid|ibnu abbas|ibnu mas'ud|diriwayatkan|berkata)", re.I)
    tarjih_p = re.compile(r"(abu ja'far berkata|pendapat yang benar|menurut ath-thabari|menurut kami|yang paling tepat)", re.I)

    too_short = []; llm_added = []; no_perawi = []; has_tarjih = 0
    lengths = []

    for row in rows:
        uid, teks, surah, ayat = row
        if not teks: continue
        lengths.append(len(teks))
        if len(teks) < 100: too_short.append((surah, ayat, uid, len(teks)))
        if llm_pat.search(teks): llm_added.append((surah, ayat, uid, teks[:120]))
        if not perawi_p.search(teks): no_perawi.append((surah, ayat, uid))
        if tarjih_p.search(teks): has_tarjih += 1

    n = len(rows)
    avg_l = int(sum(lengths)/len(lengths)) if lengths else 0
    print(f"\n  Total chunks       : {n}")
    print(f"  Panjang min/avg/max: {min(lengths) if lengths else 0}/{avg_l}/{max(lengths) if lengths else 0} char")
    print(f"\n  Chunk < 100 char   : {len(too_short)}")
    for c in too_short[:10]: flag("ERR", f"Chunk pendek ({c[3]} char): QS {c[0]}:{c[1]} unit_id={c[2]}")
    print(f"\n  Kemungkinan tambahan LLM bukan dari Ath-Thabari: {len(llm_added)}")
    for c in llm_added[:10]: flag("ERR", f"Tambahan LLM: QS {c[0]}:{c[1]} -> '{c[3]}...'")
    pct_no_perawi = len(no_perawi)/n*100 if n else 0
    print(f"\n  Chunk tanpa nama perawi: {len(no_perawi)}/{n} ({pct_no_perawi:.1f}%)")
    if pct_no_perawi > 50: flag("ERR",  f">{pct_no_perawi:.0f}% chunk tanpa perawi  atribusi sangat lemah")
    elif pct_no_perawi > 20: flag("WARN", f">{pct_no_perawi:.0f}% chunk tanpa perawi")
    else: flag("OK", "Mayoritas chunk menyebut nama perawi")
    print(f"\n  Chunk mengandung tarjih: {has_tarjih}/{n}")
    if has_tarjih == 0: flag("ERR", "Tidak ada tarjih Ath-Thabari dalam chunks  kesimpulan mufasir hilang!")
    else: flag("OK", f"{has_tarjih} chunk mengandung teks tarjih")

# -------------------------------------------------------------
# MAIN
# -------------------------------------------------------------
def main():
    print(SEP)
    print("FULL CHUNK AUDIT  Tafsir Ath-Thabari")
    print(f"DB    : {(DATABASE_URL or '')[:55]}...")
    print(f"Qdrant: {QDRANT_URL} / {COLLECTION}")
    print(f"Range : QS {SURAH_START} - {SURAH_END}")
    print(SEP)

    with engine.connect() as conn:
        audit_verse_tafsirs(conn)
        audit_takwil_units(conn)
        audit_chunk_quality(conn)

    qdrant_count, sample = audit_qdrant()

    with engine.connect() as conn:
        audit_cross_check(conn, qdrant_count, sample)

    print(f"\n{SEP}")
    print("RINGKASAN TEMUAN")
    print(SEP)
    errs  = [i for i in issues if i.startswith(ERR)]
    warns = [i for i in issues if i.startswith(WARN)]
    print(f"  Total isu : {len(issues)}  |  ERR: {len(errs)}  |  WARN: {len(warns)}")
    if errs:
        print(f"\n  === ERROR (Harus Diperbaiki) ===")
        for e in errs: print(f"  {e}")
    if warns:
        print(f"\n  === WARNING (Perlu Diperhatikan) ===")
        for w in warns: print(f"  {w}")
    if not issues:
        print(f"  {OK} Tidak ada isu ditemukan!")
    print(SEP)

if __name__ == "__main__":
    main()
