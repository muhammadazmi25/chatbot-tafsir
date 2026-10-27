import sys, os
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv('Chatbot/.env')
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sqlalchemy import create_engine, text

db_url = os.getenv('DATABASE_URL')
q_url = os.getenv('QDRANT_URL')
q_key = os.getenv('QDRANT_API_KEY')
coll = os.getenv('QDRANT_COLLECTION')

engine = create_engine(db_url)
client = QdrantClient(url=q_url, api_key=q_key, timeout=20)

sample_verses = [(11, 1), (12, 23), (17, 85), (24, 35)]

for s, a in sample_verses:
    print(f"\n==========================================")
    print(f"=== SURAH {s} AYAT {a} ===")
    print(f"==========================================")
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT vt.text 
            FROM verses v
            JOIN chapters c ON c.id = v.id_chapter
            JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = 7
            WHERE c.number_chapter = :s AND v.number = :a
        """), {"s": s, "a": a}).fetchone()
    mysql_text = row[0] if row else "NOT FOUND IN MYSQL"
    print(f"[MySQL] Length: {len(mysql_text)}")
    print(f"[MySQL] First 250 chars:\n{mysql_text[:250]}")

    res, _ = client.scroll(
        collection_name=coll,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(key="no_surah", match=models.MatchValue(value=s)),
                models.FieldCondition(key="no_ayat", match=models.MatchValue(value=a)),
            ]
        ),
        limit=10,
        with_payload=True,
        with_vectors=False
    )
    print(f"\n[Qdrant] Found {len(res)} chunks")
    for idx, r in enumerate(res):
        q_text = r.payload.get("teks_tafsir", "")
        uid = r.payload.get("id_unit")
        urutan = r.payload.get("urutan")
        print(f"  --- Chunk {idx+1} [id_unit={uid}, urutan={urutan}, len={len(q_text)}] ---")
        print(f"  {repr(q_text[:250])}")
