"""Tafsir Data API — surah list, ayat list, unit detail from MySQL."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.tafsir_service import (
    get_surah_list, get_ayat_list, get_tafsir_units, get_unit_detail, get_full_verse_tafsir
)

router = APIRouter()


@router.get("/surahs")
def list_surahs(db: Session = Depends(get_db)):
    """GET /api/v1/tafsir/surahs — List all 14 surahs (Hud–An-Nur)."""
    return get_surah_list(db)


@router.get("/surahs/{no_surah}/ayat")
def list_ayat(no_surah: int, db: Session = Depends(get_db)):
    """GET /api/v1/tafsir/surahs/{no_surah}/ayat — Ayat list per surah."""
    if not (1 <= no_surah <= 114):
        raise HTTPException(400, "Surah number must be between 1 and 114")
    return get_ayat_list(db, no_surah)


@router.get("/verse/{id_verse_tafsir}/units")
def list_units(id_verse_tafsir: int, db: Session = Depends(get_db)):
    """GET /api/v1/tafsir/verse/{id}/units — Tafsir units per ayat."""
    return get_tafsir_units(db, id_verse_tafsir)


@router.get("/verse/{id_verse_tafsir}/full")
def full_verse_tafsir(id_verse_tafsir: int, db: Session = Depends(get_db)):
    """GET /api/v1/tafsir/verse/{id}/full — Full original raw tafsir text of Ath-Thabari."""
    data = get_full_verse_tafsir(db, id_verse_tafsir)
    if not data:
        raise HTTPException(404, "Tafsir naskah lengkap tidak ditemukan")
    return data


@router.get("/units/{id_unit}")
def unit_detail(id_unit: int, db: Session = Depends(get_db)):
    """GET /api/v1/tafsir/units/{id} — Full detail of one tafsir unit."""
    unit = get_unit_detail(db, id_unit)
    if not unit:
        raise HTTPException(404, "Unit not found")
    return unit
