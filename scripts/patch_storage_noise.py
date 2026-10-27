"""
patch_storage_noise.py
======================
Script untuk membersihkan sisa noise OCR langsung di storage:
1. MySQL: tabel `verse_tafsirs`, `tafsir_takwil_units`, `tafsir_aqwal`
2. Qdrant: collection `tafsir_ath_thabari_hud_annur_v17` (in-place payload patch)

Fitur:
- Mode --dry-run (default): hanya menampilkan data yang akan diubah tanpa mengubah database.
- Mode --execute: menerapkan perubahan langsung ke MySQL dan Qdrant.
"""

import os, sys, re, argparse
from pathlib import Path
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

from sqlalchemy import create_engine, text
from qdrant_client import QdrantClient
from qdrant_client.http import models

DB_URL = os.getenv("DATABASE_URL")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLL = os.getenv("QDRANT_COLLECTION")

REPLACEMENTS = [
    ("Nebathardya", "Nabthi"),
    ("Nebasardya", "Nabthi"),
    ("Abdullatr", "Abdullah"),
    ("Abdul Latr", "Abdullah"),
    ("$# 4W $l", ""),
]

def clean_text(s: str) -> str:
    if not s:
        return s
    for old, new in REPLACEMENTS:
        s = s.replace(old, new)
    return s

def patch_mysql(engine, dry_run=True):
    print("\n" + "="*60)
    print("1. MEMERIKSA & MEMBERSIHKAN DATABASE MYSQL")
    print("="*60)
    
    with engine.connect() as conn:
        # 1. verse_tafsirs
        print("\n--- Tabel verse_tafsirs ---")
        for old, new in REPLACEMENTS:
            rows = conn.execute(
                text("SELECT id, id_verse FROM verse_tafsirs WHERE text LIKE :pattern"),
                {"pattern": f"%{old}%"}
            ).fetchall()
            print(f"Pola '{old}' -> '{new}': ditemukan pada {len(rows)} baris")
            if not dry_run and rows:
                with engine.begin() as tx:
                    tx.execute(
                        text("UPDATE verse_tafsirs SET text = REPLACE(text, :old, :new) WHERE text LIKE :pattern"),
                        {"old": old, "new": new, "pattern": f"%{old}%"}
                    )
                print(f"  [OK] Diperbarui {len(rows)} baris di verse_tafsirs")

        # 2. tafsir_takwil_units
        print("\n--- Tabel tafsir_takwil_units ---")
        for old, new in REPLACEMENTS:
            rows = conn.execute(
                text("SELECT id FROM tafsir_takwil_units WHERE ringkasan_takwil LIKE :pattern"),
                {"pattern": f"%{old}%"}
            ).fetchall()
            print(f"Pola '{old}' -> '{new}': ditemukan pada {len(rows)} baris")
            if not dry_run and rows:
                with engine.begin() as tx:
                    tx.execute(
                        text("UPDATE tafsir_takwil_units SET ringkasan_takwil = REPLACE(ringkasan_takwil, :old, :new) WHERE ringkasan_takwil LIKE :pattern"),
                        {"old": old, "new": new, "pattern": f"%{old}%"}
                    )
                print(f"  [OK] Diperbarui {len(rows)} baris di tafsir_takwil_units")

        # 3. tafsir_aqwal
        print("\n--- Tabel tafsir_aqwal ---")
        for old, new in REPLACEMENTS:
            r_spk = conn.execute(
                text("SELECT id FROM tafsir_aqwal WHERE speaker_name LIKE :pattern"),
                {"pattern": f"%{old}%"}
            ).fetchall()
            r_stmt = conn.execute(
                text("SELECT id FROM tafsir_aqwal WHERE statement LIKE :pattern"),
                {"pattern": f"%{old}%"}
            ).fetchall()
            print(f"Pola '{old}': speaker_name={len(r_spk)} baris, statement={len(r_stmt)} baris")
            if not dry_run:
                with engine.begin() as tx:
                    if r_spk:
                        tx.execute(
                            text("UPDATE tafsir_aqwal SET speaker_name = REPLACE(speaker_name, :old, :new) WHERE speaker_name LIKE :pattern"),
                            {"old": old, "new": new, "pattern": f"%{old}%"}
                        )
                    if r_stmt:
                        tx.execute(
                            text("UPDATE tafsir_aqwal SET statement = REPLACE(statement, :old, :new) WHERE statement LIKE :pattern"),
                            {"old": old, "new": new, "pattern": f"%{old}%"}
                        )
                if r_spk or r_stmt:
                    print(f"  [OK] Diperbarui baris di tafsir_aqwal")

def patch_qdrant(client, coll, dry_run=True):
    print("\n" + "="*60)
    print("2. MEMERIKSA & MEMBERSIHKAN CHUNK DI QDRANT")
    print("="*60)

    offset = None
    scanned = 0
    updated = 0

    while True:
        records, next_offset = client.scroll(
            collection_name=coll,
            limit=300,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        if not records:
            break

        for r in records:
            scanned += 1
            payload = r.payload or {}
            teks = payload.get("teks_tafsir", "")
            perawi = payload.get("perawi", "")
            aqwal = payload.get("aqwal", [])

            needs_update = False
            new_payload = {}

            # Cek teks_tafsir
            if any(old in teks for old, _ in REPLACEMENTS):
                new_teks = clean_text(teks)
                new_payload["teks_tafsir"] = new_teks
                needs_update = True

            # Cek perawi string
            if any(old in perawi for old, _ in REPLACEMENTS):
                new_payload["perawi"] = clean_text(perawi)
                needs_update = True

            # Cek aqwal list
            if aqwal and isinstance(aqwal, list):
                aqwal_changed = False
                new_aqwal = []
                for item in aqwal:
                    if isinstance(item, dict):
                        item_copy = dict(item)
                        stmt = item_copy.get("statement") or ""
                        if stmt and any(old in stmt for old, _ in REPLACEMENTS):
                            item_copy["statement"] = clean_text(stmt)
                            aqwal_changed = True
                        spk = item_copy.get("speaker_name") or ""
                        if spk and any(old in spk for old, _ in REPLACEMENTS):
                            item_copy["speaker_name"] = clean_text(spk)
                            aqwal_changed = True
                        new_aqwal.append(item_copy)
                    else:
                        new_aqwal.append(item)
                if aqwal_changed:
                    new_payload["aqwal"] = new_aqwal
                    needs_update = True

            if needs_update:
                updated += 1
                s = payload.get("no_surah")
                a = payload.get("no_ayat")
                uid = payload.get("id_unit")
                print(f"Point ID {r.id} (QS {s}:{a}, unit {uid}) perlu diupdate")
                if not dry_run:
                    client.set_payload(
                        collection_name=coll,
                        payload=new_payload,
                        points=[r.id]
                    )

        offset = next_offset
        if offset is None:
            break

    print(f"\nTotal chunk diperiksa : {scanned}")
    print(f"Total chunk dibersihkan: {updated} {'(simulasi, belum diupdate)' if dry_run else '(BERHASIL diupdate)'}")

def main():
    parser = argparse.ArgumentParser(description="Pembersih Noise Storage MySQL & Qdrant")
    parser.add_argument("--execute", action="store_true", help="Terapkan pembersihan nyata ke storage")
    args = parser.parse_args()

    dry_run = not args.execute
    mode_str = "DRY-RUN (Simulasi)" if dry_run else "EXECUTE (Pembersihan Nyata)"

    print("=" * 60)
    print(f"PEMBERSIH NOISE STORAGE TAFSIR ATH-THABARI - Mode: {mode_str}")
    print("=" * 60)

    engine = create_engine(DB_URL, pool_pre_ping=True)
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=30)

    patch_mysql(engine, dry_run=dry_run)
    patch_qdrant(client, QDRANT_COLL, dry_run=dry_run)

    print("\n" + "="*60)
    if dry_run:
        print("SIMULASI SELESAI. Tidak ada data yang diubah.")
        print("Untuk menerapkan secara nyata ke MySQL dan Qdrant, jalankan:")
        print("  python Chatbot/scripts/patch_storage_noise.py --execute")
    else:
        print("PEMBERSIHAN BERHASIL DITERAPKAN KE MYSQL DAN QDRANT!")
    print("="*60)

if __name__ == "__main__":
    main()
