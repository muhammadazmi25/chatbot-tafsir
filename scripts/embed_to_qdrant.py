"""
Script to embed Tafsir Ath-Thabari from MySQL to Qdrant using BGE-M3.
"""

import os
import sys
import logging
from sqlalchemy.orm import Session
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.append(str(backend_dir))

from app.core.config import settings
from app.db.database import SessionLocal
from app.services.tafsir_service import get_surah_list, get_ayat_list, get_unit_detail
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from FlagEmbedding import BGEM3FlagModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def embed_data():
    logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
    model = BGEM3FlagModel(settings.EMBEDDING_MODEL, use_fp16=True)
    
    client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
    collection = settings.QDRANT_COLLECTION
    
    # Check if collection exists
    try:
        client.get_collection(collection)
        logger.info(f"Collection {collection} exists.")
    except:
        logger.info(f"Creating collection {collection}...")
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=settings.EMBEDDING_DIM, distance=Distance.COSINE)
        )
        
    db = SessionLocal()
    try:
        surahs = get_surah_list(db)
        point_id = 1
        
        for surah in surahs:
            logger.info(f"Processing Surah: {surah['nama_surah']} ({surah['no_surah']})")
            ayats = get_ayat_list(db, surah['no_surah'])
            
            for ayat in ayats:
                # get_tafsir_units (raw query approach to save memory)
                from sqlalchemy import text
                unit_rows = db.execute(
                    text("SELECT id FROM tafsir_takwil_units WHERE id_verse_tafsir = :id"),
                    {"id": ayat["id_verse_tafsir"]}
                ).fetchall()
                
                points = []
                for (unit_id,) in unit_rows:
                    detail = get_unit_detail(db, unit_id)
                    if not detail or not detail.get("ringkasan_takwil"):
                        continue
                        
                    # Format text to embed
                    embed_text = f"Tafsir {detail['nama_surah']} ayat {detail['no_ayat']}: "
                    if detail['lafaz_frasa']:
                        embed_text += f"{detail['lafaz_frasa']} - "
                    embed_text += f"{detail['ringkasan_takwil']}"
                    
                    if detail.get('aqwal') and len(detail['aqwal']) > 0:
                        embed_text += " Pendapat ulama: " + " ".join([a['statement'] for a in detail['aqwal']])
                        
                    # Encode
                    vec = model.encode([embed_text], batch_size=1, max_length=512, return_dense=True)['dense_vecs'][0].tolist()
                    
                    payload = {
                        "id_unit": detail['id_unit'],
                        "no_surah": detail['no_surah'],
                        "nama_surah": detail['nama_surah'],
                        "no_ayat": detail['no_ayat'],
                        "teks_tafsir": embed_text,
                        "lafaz_frasa": detail['lafaz_frasa'],
                        "urutan": detail['urutan']
                    }
                    
                    points.append(PointStruct(id=point_id, vector=vec, payload=payload))
                    point_id += 1
                
                # Batch upload per ayat
                if points:
                    client.upsert(collection_name=collection, points=points)
                    logger.info(f"  Upserted {len(points)} units for Ayat {ayat['no_ayat']}")
                    
    except Exception as e:
        logger.error(f"Error embedding data: {e}")
    finally:
        db.close()
        logger.info("Done.")

if __name__ == "__main__":
    embed_data()
