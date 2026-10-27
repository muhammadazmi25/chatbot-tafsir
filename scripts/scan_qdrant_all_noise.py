import os, sys, re
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv('Chatbot/.env')
from qdrant_client import QdrantClient

q_url = os.getenv('QDRANT_URL')
q_key = os.getenv('QDRANT_API_KEY')
coll = os.getenv('QDRANT_COLLECTION')

client = QdrantClient(url=q_url, api_key=q_key, timeout=30)

noise_patterns = [
    (r'\brakrril\b|\bratrwil\b', 'rakrril/ratrwil typo for Takwil'),
    (r'\bl<firil\b', 'l<firil typo for tidak'),
    (r'Nebathardya', 'Nebathardya typo for Nabath'),
    (r'Abdullatr', 'Abdullatr typo for Abdullah'),
    (r'W:35|UK,\$Y', 'Cryptic OCR symbols W:35/UK,$Y'),
    (r'\]LUK|\$ij|\?rj|4y1;', 'Broken Arabic OCR symbols'),
    (r'Nfuh|Nftuhaffinad', 'Broken names Nfuh/Nftuhaffinad'),
    (r'\b[a-zA-Z]{1,2}\s+[a-zA-Z]{1,2}\s+[a-zA-Z]{1,2}\s+[a-zA-Z]{1,2}\b', 'Spaced letters (e.g. g e mb ir a)'),
    (r'[\$^\*@_~]{2,}', 'Multiple weird punctuation symbols'),
    (r'Takwll|Takwii', 'Takwll/Takwii typos'),
    (r'\bseperu\b', 'seperu typo for seperti'),
    (r'\bdarip ada\b', 'darip ada broken word'),
    (r'\bkep adamu\b', 'kep adamu broken word'),
    (r'\b(Sesunggzhnya|sesunggzhnya)\b', 'sesunggzhnya typo'),
    (r'\b(berkata|berkata:)\s*$', 'Dangling sentence ending with berkata'),
    (r'[\uFFFD]', 'Unicode replacement character U+FFFD (broken byte)'),
]

compiled = [(re.compile(p[0], re.IGNORECASE), p[1]) for p in noise_patterns]

offset = None
total_scanned = 0
noise_stats = {desc: 0 for _, desc in noise_patterns}
noise_samples = {desc: [] for _, desc in noise_patterns}
short_chunks = []
empty_chunks = []

print(f"Scanning collection: {coll}...")

while True:
    records, next_offset = client.scroll(
        collection_name=coll,
        limit=500,
        offset=offset,
        with_payload=True,
        with_vectors=False
    )
    if not records:
        break
    for r in records:
        total_scanned += 1
        txt = r.payload.get('teks_tafsir', '')
        s = r.payload.get('no_surah')
        a = r.payload.get('no_ayat')
        uid = r.payload.get('id_unit')

        if not txt or not txt.strip():
            empty_chunks.append((s, a, uid))
        elif len(txt.strip()) < 100:
            short_chunks.append((s, a, uid, len(txt), txt.strip()))

        for cp, desc in compiled:
            m = cp.search(txt)
            if m:
                noise_stats[desc] += 1
                if len(noise_samples[desc]) < 3:
                    snippet = txt[max(0, m.start()-25):min(len(txt), m.end()+25)].replace('\n', ' ')
                    noise_samples[desc].append((s, a, uid, m.group(0), snippet))

    offset = next_offset
    if offset is None:
        break

print(f"\n================ AUDIT SUMMARY ================")
print(f"Total chunks scanned      : {total_scanned}")
print(f"Empty chunks (0 chars)    : {len(empty_chunks)}")
print(f"Short chunks (< 100 chars): {len(short_chunks)}")

print("\n--- OCR Noise Breakdown in Qdrant Chunks ---")
total_noise_chunks = 0
for _, desc in noise_patterns:
    cnt = noise_stats[desc]
    status = "CLEAN [0]" if cnt == 0 else f"DETECTED [{cnt}]"
    print(f"{desc:<45}: {status}")
    if cnt > 0:
        total_noise_chunks += cnt
        for smp in noise_samples[desc]:
            print(f"   -> QS {smp[0]}:{smp[1]} (id_unit {smp[2]}) | Match: {repr(smp[3])} | Snippet: ...{smp[4]}...")

print(f"\nTotal noise matches found across chunks: {total_noise_chunks}")

print("\n--- Sample Short Chunks (< 100 chars) ---")
for sc in short_chunks[:5]:
    print(f"QS {sc[0]}:{sc[1]} (unit {sc[2]}, len {sc[3]}): {repr(sc[4])}")
