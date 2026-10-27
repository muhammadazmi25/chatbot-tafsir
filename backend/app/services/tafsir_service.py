"""
Tafsir data service — reads from MySQL alquran database.
Provides surah list, ayat per surah, and tafsir units per ayat.

Actual column names (from DESCRIBE):
  chapters:  id, name, number_chapter, arabic_name, revelation_order, revelation_place, verse_count
  verses:    id, text_uthmani, text_uthmani_simple, text_imlaei, text_imlaei_simple,
             text_indopak, number, transliteration, ..., id_juz, id_chapter
  verse_tafsirs:        id, text(longtext), id_verse, id_tafsir
  tafsir_takwil_units:  id, id_verse_tafsir, urutan, lafaz_frasa, ringkasan_takwil,
                        has_ikhtilaf, has_qiraat, has_naqd, confidence, needs_review, catatan_kaki
"""

import re
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.logging_config import get_logger

logger = get_logger('services.tafsir')

TAFSIR_ID = 7  # Tafsir Ath-Thabari
SURAH_START = 11  # Hud
SURAH_END = 24    # An-Nur


def clean_tafsir_header(raw_text: str) -> str:
    """Bersihkan duplikasi teks Arab dan kutipan terjemahan AI di awal naskah hasil OCR/LLM
    sehingga naskah langsung mengalir mulai dari takwil Ath-Thabari sesuai kitab aslinya.
    """
    if not raw_text:
        return ""
    text_content = raw_text.strip().replace("\r\n", "\n").replace("\r", "\n")

    # 1. Jika ada 'Takwil firman Allah' atau 'Abu Ja'far berkata', mulai langsung dari situ
    m = re.search(r'(Takwil firman Allah[\s\S]*|Abu Ja[\'’]far berkata[\s\S]*)', text_content, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # 2. Jika tidak ada, buang baris-baris pertama jika berupa teks Arab murni yang berulang
    lines = text_content.split("\n")
    cleaned_lines = []
    for l in lines:
        stripped = l.strip()
        is_pure_arabic = bool(re.match(r"^[\u0600-\u06FF\s\d\.\,\(\)\:\-\[\]]+$", stripped))
        if not cleaned_lines and is_pure_arabic:
            continue
        cleaned_lines.append(l)

    return "\n".join(cleaned_lines).strip() if cleaned_lines else text_content


def get_surah_list(db: Session) -> List[Dict[str, Any]]:
    """Get list of 14 surahs (Hud–An-Nur) with ayat count and Indonesian meaning."""
    sql = text("""
        SELECT
            c.id,
            c.number_chapter AS no_surah,
            c.name           AS nama_surah,
            c.arabic_name    AS nama_surah_arab,
            ct.text          AS arti_surah,
            c.revelation_place,
            COUNT(DISTINCT v.id) AS jumlah_ayat,
            COUNT(DISTINCT u.id) AS jumlah_unit
        FROM chapters c
        JOIN verses v ON v.id_chapter = c.id
        LEFT JOIN chapter_translations ct ON ct.id_chapter = c.id AND ct.id_language = 13
        JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = :tafsir_id
        LEFT JOIN tafsir_takwil_units u ON u.id_verse_tafsir = vt.id
        WHERE c.number_chapter BETWEEN :start AND :end
        GROUP BY c.id, c.number_chapter, c.name, c.arabic_name, ct.text, c.revelation_place
        ORDER BY c.number_chapter ASC
    """)
    rows = db.execute(sql, {
        "tafsir_id": TAFSIR_ID,
        "start": SURAH_START,
        "end": SURAH_END,
    }).fetchall()

    return [dict(row._mapping) for row in rows]


def get_ayat_list(db: Session, no_surah: int) -> List[Dict[str, Any]]:
    """Get all ayat in a surah with unit count per ayat and Indonesian translation (King Fahad/Depag matching PDF)."""
    sql = text("""
        SELECT
            v.id             AS id_verse,
            v.number         AS no_ayat,
            v.text_uthmani   AS teks_arab,
            v.transliteration AS teks_latin,
            COALESCE(vtr134.text, vtr33.text) AS terjemahan,
            vt.id            AS id_verse_tafsir,
            COUNT(DISTINCT u.id) AS jumlah_unit
        FROM verses v
        JOIN chapters c ON v.id_chapter = c.id
        LEFT JOIN verse_translations vtr134 ON vtr134.id_verse = v.id AND vtr134.id_translation = 134
        LEFT JOIN verse_translations vtr33 ON vtr33.id_verse = v.id AND vtr33.id_translation = 33
        JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = :tafsir_id
        LEFT JOIN tafsir_takwil_units u ON u.id_verse_tafsir = vt.id
        WHERE c.number_chapter = :no_surah
        GROUP BY v.id, v.number, v.text_uthmani, v.transliteration, vtr134.text, vtr33.text, vt.id
        ORDER BY v.number ASC
    """)
    rows = db.execute(sql, {"tafsir_id": TAFSIR_ID, "no_surah": no_surah}).fetchall()
    return [dict(row._mapping) for row in rows]


def get_tafsir_units(db: Session, id_verse_tafsir: int) -> List[Dict[str, Any]]:
    """Get all tafsir units for a specific ayat. Fallback to raw text if units not yet split."""
    sql = text("""
        SELECT
            u.id             AS id_unit,
            u.urutan,
            u.lafaz_frasa,
            u.ringkasan_takwil,
            u.has_ikhtilaf,
            u.has_qiraat,
            u.has_naqd,
            u.confidence
        FROM tafsir_takwil_units u
        WHERE u.id_verse_tafsir = :id_verse_tafsir
        ORDER BY u.urutan ASC
    """)
    rows = db.execute(sql, {"id_verse_tafsir": id_verse_tafsir}).fetchall()
    if rows:
        return [dict(row._mapping) for row in rows]

    # Fallback ke teks lengkap Ath-Thabari jika ayat belum diparsing ke takwil units
    raw_sql = text("""
        SELECT vt.id, vt.text, v.text_uthmani 
        FROM verse_tafsirs vt 
        JOIN verses v ON vt.id_verse = v.id 
        WHERE vt.id = :id_verse_tafsir
    """)
    raw = db.execute(raw_sql, {"id_verse_tafsir": id_verse_tafsir}).fetchone()
    if raw and raw[1]:
        cleaned_raw = clean_tafsir_header(raw[1])
        return [{
            "id_unit": 1000000 + raw[0],
            "urutan": 1,
            "lafaz_frasa": raw[2],
            "ringkasan_takwil": cleaned_raw,
            "has_ikhtilaf": 0,
            "has_qiraat": 0,
            "has_naqd": 0,
            "confidence": 1.0,
        }]
    return []


def get_full_verse_tafsir(db: Session, id_verse_tafsir: int) -> Optional[Dict[str, Any]]:
    """Get full original raw tafsir text of Ath-Thabari for a specific ayat without unit split."""
    sql = text("""
        SELECT 
            vt.id            AS id_verse_tafsir,
            vt.text          AS teks_asli,
            v.id             AS id_verse,
            v.number         AS no_ayat,
            v.text_uthmani   AS teks_arab,
            v.transliteration AS teks_latin,
            COALESCE(vtr134.text, vtr33.text) AS terjemahan,
            c.number_chapter AS no_surah,
            c.name           AS nama_surah,
            c.arabic_name    AS nama_surah_arab
        FROM verse_tafsirs vt
        JOIN verses v ON vt.id_verse = v.id
        LEFT JOIN verse_translations vtr134 ON vtr134.id_verse = v.id AND vtr134.id_translation = 134
        LEFT JOIN verse_translations vtr33 ON vtr33.id_verse = v.id AND vtr33.id_translation = 33
        JOIN chapters c ON v.id_chapter = c.id
        WHERE vt.id = :id_verse_tafsir
    """)
    row = db.execute(sql, {"id_verse_tafsir": id_verse_tafsir}).fetchone()
    if not row:
        return None
    res = dict(row._mapping)
    raw_teks = res.get("teks_asli") or ""
    cleaned = clean_tafsir_header(raw_teks)
    res["teks_asli"] = cleaned
    res["karakter_count"] = len(cleaned)
    res["estimasi_baca_menit"] = max(1, round(len(cleaned.split()) / 150))
    return res


def get_unit_detail(db: Session, id_unit: int) -> Optional[Dict[str, Any]]:
    """Get full detail of a single tafsir unit including aqwal."""
    if id_unit >= 1000000:
        raw_vt_id = id_unit - 1000000
        raw_sql = text("""
            SELECT 
                vt.id as id_verse_tafsir,
                vt.text as raw_text,
                v.number as no_ayat,
                v.text_uthmani as teks_arab,
                c.number_chapter as no_surah,
                c.name as nama_surah,
                c.arabic_name as nama_surah_arab
            FROM verse_tafsirs vt
            JOIN verses v ON vt.id_verse = v.id
            JOIN chapters c ON v.id_chapter = c.id
            WHERE vt.id = :id_vt
        """)
        raw = db.execute(raw_sql, {"id_vt": raw_vt_id}).fetchone()
        if raw:
            return {
                "id_unit": id_unit,
                "urutan": 1,
                "lafaz_frasa": raw.teks_arab,
                "ringkasan_takwil": raw.raw_text.strip(),
                "has_ikhtilaf": 0,
                "has_qiraat": 0,
                "has_naqd": 0,
                "confidence": 1.0,
                "no_ayat": raw.no_ayat,
                "teks_arab": raw.teks_arab,
                "no_surah": raw.no_surah,
                "nama_surah": raw.nama_surah,
                "nama_surah_arab": raw.nama_surah_arab,
                "aqwal": [],
                "evidence": [],
                "naqd": [],
                "tarjih": [],
                "qiraat": [],
            }
        return None

    unit_sql = text("""
        SELECT
            u.id             AS id_unit,
            u.urutan,
            u.lafaz_frasa,
            u.ringkasan_takwil,
            u.has_ikhtilaf,
            u.has_qiraat,
            u.has_naqd,
            u.confidence,
            v.number         AS no_ayat,
            v.text_uthmani   AS teks_arab,
            c.number_chapter AS no_surah,
            c.name           AS nama_surah,
            c.arabic_name    AS nama_surah_arab
        FROM tafsir_takwil_units u
        JOIN verse_tafsirs vt ON u.id_verse_tafsir = vt.id
        JOIN verses v ON vt.id_verse = v.id
        JOIN chapters c ON v.id_chapter = c.id
        WHERE u.id = :id_unit
    """)
    row = db.execute(unit_sql, {"id_unit": id_unit}).fetchone()
    if not row:
        return None

    unit = dict(row._mapping)

    # Get aqwal
    aqwal_sql = text("""
        SELECT a.id, a.speaker_type, a.speaker_name, a.statement, a.confidence
        FROM tafsir_aqwal a
        WHERE a.id_unit = :id_unit
        ORDER BY a.id ASC
    """)
    aqwal_rows = db.execute(aqwal_sql, {"id_unit": id_unit}).fetchall()
    unit["aqwal"] = [dict(r._mapping) for r in aqwal_rows]

    # Get tarjih (opsional, tabel mungkin tidak ada)
    try:
        tarjih_sql = text("""
            SELECT t.status, t.basis, t.reasoning
            FROM tafsir_tarjih t
            WHERE t.id_unit = :id_unit
            LIMIT 1
        """)
        tarjih_row = db.execute(tarjih_sql, {"id_unit": id_unit}).fetchone()
        unit["tarjih"] = dict(tarjih_row._mapping) if tarjih_row else None
    except Exception:
        unit["tarjih"] = None

    return unit
