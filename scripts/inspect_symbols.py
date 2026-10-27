import os, sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv('Chatbot/.env')
from sqlalchemy import create_engine, text

engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    for s, a in [(12, 48), (24, 38)]:
        row = conn.execute(text("""
            SELECT vt.text 
            FROM verses v
            JOIN chapters c ON c.id = v.id_chapter
            JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = 7
            WHERE c.number_chapter = :s AND v.number = :a
        """), {"s": s, "a": a}).fetchone()
        txt = row[0]
        import re
        matches = re.findall(r'[\#\$\*\{\}\^\~]{2,}', txt)
        print(f"QS {s}:{a} matched patterns: {set(matches)}")
        for m in set(matches):
            idx = txt.find(m)
            print(f"  Snippet: {repr(txt[max(0, idx-20):min(len(txt), idx+30)])}")
