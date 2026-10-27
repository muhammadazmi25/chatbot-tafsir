"""
RAG Service — Chatbot Tafsir Ath-Thabari.

Pipeline:
1. Scope Guard  — tolak query tentang surah di luar 11-24
2. OOD Guard    — tolak query non-tafsir (kode, resep, dsb)
3. Query Expansion (HyDE, domain-constrained)
4. Semantic Search (Qdrant, BAAI/bge-m3 dense vector)
5. Hybrid Search (BM25 + Semantic via RRF)
6. Cross-Encoder Reranker
7. LLM Generation (OpenRouter → Gemini fallback)
"""

import re
import json
import requests
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from qdrant_client import QdrantClient
from FlagEmbedding import BGEM3FlagModel

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger('services.rag')

# ─── Load BGE-M3 once at module level ─────────────────────────────────────
logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
_embed_model = BGEM3FlagModel(settings.EMBEDDING_MODEL, use_fp16=True)
logger.info("BGE-M3 model loaded.")

# ─── System prompt ─────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Kamu adalah asisten akademik Tafsir Ath-Thabari yang HANYA menjawab pertanyaan seputar tafsir Al-Quran dari kitab Jami' al-Bayan karya Ibnu Jarir Ath-Thabari, khususnya Surah 11 (Hud) hingga Surah 24 (An-Nur).

═══════════════════════════════════════════════════════
ATURAN MUTLAK — PELANGGARAN = JAWABAN SALAH/BERBAHAYA
═══════════════════════════════════════════════════════

0. DOMAIN GUARD — CEK PERTAMA SEBELUM APAPUN.
   Jika pertanyaan TIDAK berkaitan dengan tafsir Al-Quran atau Ath-Thabari,
   WAJIB tolak dengan kalimat berikut dan JANGAN lanjutkan menjawab:
   "Maaf, saya hanya dapat menjawab pertanyaan seputar Tafsir Ath-Thabari untuk Surah 11–24 (Hud hingga An-Nur). Pertanyaan Anda di luar cakupan saya."
   ❌ DILARANG menggunakan konteks tafsir untuk menjawab pertanyaan tentang: kode komputer, pemrograman, resep makanan, topik umum, atau hal-hal di luar tafsir.

1. HANYA DARI KONTEKS.
   Setiap kalimat dalam jawabanmu HARUS dapat dilacak ke konteks yang diberikan.
   Jika konteks tidak memuat suatu informasi, jangan tulis informasi itu.
   ⚠ Jika konteks yang tersedia TIDAK RELEVAN dengan pertanyaan (dokumen membahas topik yang berbeda),
   WAJIB tulis: "Maaf, data tafsir untuk pertanyaan ini tidak ditemukan atau tidak cukup dalam database."
   JANGAN mengarang jawaban dari dokumen yang tidak relevan.

2. KATA-KATA TERLARANG — DILARANG KERAS menggunakan kata/frasa berikut kecuali kata itu benar-benar ada di teks konteks:
   ❌  "cenderung", "menggarisbawahi", "menekankan", "tampaknya", "sepertinya"
   ❌  "Secara keseluruhan", "Dengan demikian", "Dapat disimpulkan", "Pada intinya"
   ❌  "Ayat ini mengajarkan", "Hikmah dari ayat ini", "Pelajaran yang dapat diambil"
   ❌  "Pentingnya tauhid", "keesaan Allah" (kecuali ada di teks)
   ❌  "sebagian ulama", "beberapa ulama", "para ulama" (WAJIB ganti dengan nama perawi)

3. ATRIBUSI PERAWI — WAJIB EKSPLISIT.
   - Setiap riwayat dari sahabat atau tabi'in HARUS disebut nama perawinya (Al-Hasan, Qatadah, Mujahid, dll.).
   - Jika konteks menandai segmen sebagai [TIPE: takwil_langsung], artinya kalimat itu adalah penjelasan/takwil Ath-Thabari sendiri — BUKAN riwayat dari perawi lain. Jangan bubuhkan nama perawi palsu.

4. PEMBEDAAN RIWAYAT vs TAKWIL vs TARJIH.
   - Riwayat: diriwayatkan dari sahabat/tabi'in dengan sanad. Sebut nama perawinya.
   - Takwil langsung: Ath-Thabari sendiri menjelaskan makna tanpa menyebut khilaf. Tulis sebagai "Ath-Thabari menjelaskan: ..."
   - Tarjih: muncul ketika ada dua pendapat atau lebih, lalu Abu Ja'far menyimpulkan pendapat yang paling benar.
     Contoh penanda: "Abu Ja'far berkata: Yang paling benar/tepat menurut kami adalah..."

5. HORMATI CONSTRAINT DARI USER — WAJIB IKUTI.
   Jika dalam pertanyaan terdapat [CONSTRAINT USER], WAJIB ikuti semua constraint tersebut secara ketat.
   Contoh: jika ada [CONSTRAINT USER: Jangan sebut nama tokoh], maka seluruh jawaban TIDAK BOLEH menyebut nama apapun.

6. FORMAT JAWABAN — CONDITIONAL (IKUTI SESUAI ISI KONTEKS).
   Jangan paksa mengisi bagian yang tidak ada di konteks.

   Tafsir Ath-Thabari mengenai [Nama Surah] Ayat [Nomor]:

   **Penjelasan Ath-Thabari:**
   [Tulis penjelasan/takwil langsung dari Ath-Thabari jika ada di konteks]

   **Pendapat Ulama / Riwayat Salaf:** ← Tulis bagian ini HANYA jika konteks memuat riwayat bersanad dari perawi
   1. **[Nama Perawi]**: [kutipan pendapatnya]
   2. **[Nama Perawi]**: [kutipan pendapatnya]

   **Tarjih / Kesimpulan Ath-Thabari:** ← Tulis bagian ini HANYA jika konteks memuat sinyal [Ada tarjih] atau [Tarjih Ath-Thabari]
   Abu Ja'far Ath-Thabari menyatakan bahwa pendapat yang paling tepat adalah: ...

   Jika salah satu bagian tidak ada di konteks, tulis:
   → *Tidak ada perbedaan pendapat pada bagian ini.*  (untuk bagian Riwayat)
   → *Tidak ada tarjih pada bagian ini.*  (untuk bagian Tarjih)

   (Sumber: QS [Surah]:[Ayat])"""


# ─── Scope & OOD constants ────────────────────────────────────────────────

# Surah yang tersedia di database (11-24)
VALID_SURAH_NUMBERS = set(range(11, 25))

# Peta nama surah → nomor (digunakan bersama oleh _extract_surah_ayat & _extract_all_surahs)
_SURAH_NAME_MAP: dict = {
    'hud': 11, 'yusuf': 12, 'ar-rad': 13, "ar-ra'd": 13, 'ar rad': 13, 'rad': 13,
    'ibrahim': 14, 'al-hijr': 15, 'hijr': 15, 'an-nahl': 16, 'nahl': 16,
    'al-isra': 17, "al-isra'": 17, 'isra': 17, 'al-kahf': 18, 'kahf': 18, 'kahfi': 18,
    'maryam': 19, 'thaha': 20, 'taha': 20, 'al-anbiya': 21, "al-anbiya'": 21,
    'anbiya': 21, 'al-hajj': 22, 'hajj': 22, "al-mu'minun": 23, 'al-muminun': 23,
    'muminun': 23, "mu'minun": 23, 'an-nur': 24, 'annur': 24, 'nur': 24,
}

# Nama surah yang ADA di database (11-24) — untuk deteksi explicit mention
VALID_SURAH_NAMES = {
    'hud', 'yusuf', 'ar-rad', "ar-ra'd", 'ibrahim', 'al-hijr', 'hijr',
    'an-nahl', 'nahl', 'al-isra', "al-isra'", 'isra', 'al-kahf', 'kahfi',
    'kahf', 'maryam', 'thaha', 'taha', 'al-anbiya', "al-anbiya'", 'anbiya',
    'al-hajj', 'hajj', "al-mu'minun", 'al-muminun', 'muminun',
    'an-nur', 'annur', 'nur',
}

# Nama surah di LUAR scope database — yang sering ditanyakan
OUT_OF_SCOPE_SURAH = {
    'al-fatihah', 'fatihah', 'al-baqarah', 'baqarah',
    'ali imran', "ali 'imran", 'an-nisa', 'nisa', 'al-maidah', 'maidah',
    'al-anam', 'anam', 'al-araf', 'araf', 'al-anfal', 'anfal',
    'at-taubah', 'taubah', 'yunus', 'al-furqan', 'furqan',
    'asy-syuara', 'syuara', 'an-naml', 'naml', 'al-qasas', 'qasas',
    'al-ankabut', 'ankabut', 'ar-rum', 'rum', 'luqman',
    'as-sajdah', 'sajdah', 'al-ahzab', 'ahzab', 'saba', "saba'",
    'fatir', 'yasin', 'as-saffat', 'saffat', 'sad', 'az-zumar', 'zumar',
    'ghafir', 'fussilat', 'asy-syura', 'az-zukhruf', 'zukhruf',
    'ad-dukhan', 'dukhan', 'al-jatsiyah', 'al-ahqaf', 'muhammad',
    'al-fath', 'fath', 'al-hujurat', 'hujurat', 'qaf', 'adz-dzariyat',
    'at-tur', 'an-najm', 'najm', 'al-qamar', 'qamar', 'ar-rahman',
    'rahman', 'al-waqiah', 'waqiah', 'al-hadid', 'hadid',
    'al-mujadilah', 'al-hasyr', 'hasyr', 'al-mumtahanah',
    'as-saf', 'al-jumuah', 'al-munafiqun', 'at-tagabun', 'at-talaq',
    'at-tahrim', 'al-mulk', 'mulk', 'al-qalam', 'al-haqqah', 'al-maarij',
    'nuh', 'al-jin', 'jin', 'al-muzammil', 'al-muddatstsir', 'al-qiyamah',
    'al-insan', 'al-mursalat', 'an-naba', 'naba', 'an-naziat',
    'abasa', "'abasa", 'at-takwir', 'al-infitar', 'al-mutaffifin',
    'al-insyiqaq', 'al-buruj', 'at-tariq', 'al-ala', 'al-ghasyiyah',
    'al-fajr', 'al-balad', 'asy-syams', 'al-lail', 'ad-duha',
    'al-insyirah', 'at-tin', 'al-alaq', 'alaq', 'al-qadr', 'qadr',
    'al-bayyinah', 'az-zalzalah', 'al-adiyat', 'al-qariah',
    'at-takatsur', 'al-asr', 'al-humazah', 'al-fil', 'quraisy',
    'al-maun', 'al-kautsar', 'al-kafirun', 'an-nasr', 'al-lahab',
    'al-ikhlas', 'al-falaq', 'an-nas', 'nas',
    'al-kursi', 'ayat kursi',  # shortcut umum
}

# Pattern untuk deteksi pertanyaan di luar domain tafsir
_OOD_PATTERNS = [
    # Pemrograman
    r'\b(python|javascript|java|php|sql|html|css|react|node|django|flask|laravel)\b',
    r'\b(kode|code|program|script|fungsi|function|algoritma|algorithm)\b',
    r'\b(fibonacci|factorial|sorting|array|loop|for\s+loop|while\s+loop)\b',
    r'\b(compile|debug|syntax|error|exception|import|library|framework)\b',
    # Topik umum non-Islam
    r'\b(resep|masak|memasak|kuliner|makanan\s+enak)\b',
    r'\b(olahraga|bola|basket|sepak\s+bola|renang)\b',
    r'\b(film|musik|lagu|artis|selebriti|drama|anime)\b',
    r'\b(ekonomi\s+global|saham|crypto|bitcoin|investasi\s+saham)\b',
    # Permintaan yang jelas bukan tafsir
    r'\b(terjemahkan|translate|translation)\s+(ke\s+)?(bahasa\s+)?(inggris|jepang|korea|prancis|jerman|mandarin)\b',
    r'\bbuatkan?\s+(saya\s+)?(cerita|puisi|lagu|essay|artikel)\b',
    r'\bgambar(kan)?\b',
    r'\bcari(kan)?\s+(harga|produk|toko|hotel|tiket)\b',
]

# Constraint patterns dari user yang perlu diekstrak
_CONSTRAINT_PATTERNS = [
    (r'tanpa\s+menyebut\s+nama\s*(nabinya?|nabi|tokohnya?|tokoh|orangnya?|orang)?', 'Jangan sebut nama tokoh, nabi, atau individu apapun dalam jawaban.'),
    (r'tanpa\s+kutipan?\s+arab', 'Jangan sertakan teks Arab dalam jawaban.'),
    (r'tanpa\s+sanad|tanpa\s+menyebut\s+sanad', 'Jangan cantumkan rantai sanad, cukup nama perawi.'),
    (r'ringkas(kan)?|singkat(kan)?', 'Berikan jawaban yang ringkas dan singkat.'),
    (r'dalam\s+bahasa\s+sederhana|bahasa\s+awam', 'Gunakan bahasa yang mudah dipahami orang awam, hindari istilah teknis Arab.'),
    (r'hanya\s+(poin|poin-poin|poin\s+utama|inti)', 'Hanya sebutkan poin-poin utama, tidak perlu elaborasi panjang.'),
]


def _check_scope(query: str) -> Optional[str]:
    """Periksa apakah query menyebut surah di luar scope database (11-24).

    Returns:
        Pesan error jika di luar scope, None jika aman.
    """
    q = query.lower()

    # Cek nama surah yang eksplisit di luar scope
    for name in OUT_OF_SCOPE_SURAH:
        # Gunakan word-boundary sederhana
        pattern = r'(^|[\s,.\(\[\"\'])' + re.escape(name) + r'($|[\s,.\)\]\"\'\?!])'
        if re.search(pattern, q):
            return (
                f"Maaf, database Tafsir Ath-Thabari yang tersedia hanya mencakup "
                f"**Surah 11 (Hud) hingga Surah 24 (An-Nur)**. "
                f"Surah yang Anda tanyakan tidak tersedia dalam database ini. "
                f"Silakan tanyakan tentang salah satu surah berikut: "
                f"Hud, Yusuf, Ar-Ra'd, Ibrahim, Al-Hijr, An-Nahl, Al-Isra', "
                f"Al-Kahfi, Maryam, Thaha, Al-Anbiya', Al-Hajj, Al-Mu'minun, atau An-Nur."
            )

    # Cek nomor surah eksplisit di luar 11-24
    # Format: "surah/surat X" atau "QS X" atau "QS X:Y"
    num_patterns = [
        r'\bsurah?\s+(\d+)\b',
        r'\bqs\.?\s*(\d+)\b',
        r'\bsurat\s+(\d+)\b',
    ]
    for pat in num_patterns:
        for m in re.finditer(pat, q):
            n = int(m.group(1))
            if n < 1 or n > 114:
                continue
            if n not in VALID_SURAH_NUMBERS:
                return (
                    f"Maaf, database ini hanya mencakup **Surah 11–24**. "
                    f"Surah {n} tidak tersedia. "
                    f"Silakan tanyakan surah antara Surah 11 (Hud) sampai Surah 24 (An-Nur)."
                )

    return None


def _check_ood(query: str) -> Optional[str]:
    """Deteksi pertanyaan di luar domain tafsir (Out-of-Domain).

    Returns:
        Pesan penolakan jika OOD, None jika relevan.
    """
    q = query.lower()
    for pat in _OOD_PATTERNS:
        if re.search(pat, q, re.IGNORECASE):
            return (
                "Maaf, saya adalah asisten khusus **Tafsir Ath-Thabari** dan hanya dapat "
                "menjawab pertanyaan seputar tafsir Al-Quran (Surah 11–24). "
                "Pertanyaan Anda tampaknya di luar bidang tafsir. "
                "Silakan ajukan pertanyaan tentang tafsir, makna ayat, pendapat ulama salaf, "
                "atau kisah dalam Al-Quran."
            )
    return None


def _extract_user_constraints(question: str) -> str:
    """Ekstrak constraint linguistik dari pertanyaan user.

    Returns:
        String constraint yang akan disertakan dalam prompt, atau '' jika tidak ada.
    """
    found = []
    q = question.lower()
    for pattern, constraint_text in _CONSTRAINT_PATTERNS:
        if re.search(pattern, q, re.IGNORECASE):
            found.append(constraint_text)

    if not found:
        return ''
    lines = '\n'.join(f'  - {c}' for c in found)
    return f'\n[CONSTRAINT USER — WAJIB DIPATUHI DALAM SELURUH JAWABAN:\n{lines}\n]'


def _is_context_sufficient(docs: List[Dict[str, Any]], question: str) -> bool:
    """Periksa apakah dokumen yang diambil cukup relevan untuk menjawab pertanyaan.

    Menggunakan heuristik: minimal 1 dokumen dengan reranker_score > -3
    dan source yang mengandung nama surah atau nomor surah yang disebutkan.
    """
    if not docs:
        return False

    # Jika ada dokumen dengan skor reranker yang cukup baik, anggap cukup
    has_good_score = any(
        d.get('reranker_score', d.get('score', 0)) > -5
        for d in docs
    )

    # Pastikan minimal ada 1 dokumen dengan teks yang tidak kosong
    has_content = any(len(d.get('text', '')) > 50 for d in docs)

    return has_good_score and has_content


def _detect_segment_type(meta: dict, aqwal_list: list, tarjih_obj) -> str:
    """Deteksi tipe segmen dari metadata untuk dikirim ke LLM.

    Return:
        'takwil_langsung' — penjelasan Ath-Thabari sendiri, tidak ada khilaf
        'riwayat'        — ada riwayat bersanad dari perawi (sahabat/tabi'in)
        'tarjih'         — ada pernyataan kesimpulan Ath-Thabari
        'campuran'       — gabungan riwayat + tarjih
    """
    has_riwayat = bool(aqwal_list and any(a.get("speaker_name") for a in aqwal_list))
    has_tarjih = bool(
        tarjih_obj
        and isinstance(tarjih_obj, dict)
        and tarjih_obj.get("reasoning", "")
    )
    if has_riwayat and has_tarjih:
        return "campuran"
    if has_tarjih:
        return "tarjih"
    if has_riwayat:
        return "riwayat"
    return "takwil_langsung"


# ─── OCR noise patterns ───────────────────────────────────────────────────
# Pasangan (pattern_salah, koreksi) untuk artefak OCR umum di teks tafsir Arab/Indonesia
_OCR_CORRECTIONS = [
    # Nama tempat/orang yang salah OCR
    (r'\bNebathardya\b', 'Nabthi'),
    (r'\bNebasardya\b', 'Nabthi'),
    (r'\bAth-Tha\'labi\b', "Ath-Tha'labi"),
    (r'\bAbdullatr\b', 'Abdullah'),
    (r'\bAbdul Latr\b', 'Abdullah'),
    (r'\bAs-Sa\'lb\b', "As-Sa'ib"),
    (r'\bIbn\s+Al\s+Atl\b', 'Ibnu Al-Atsir'),
    (r'\bAth-Thabaril\b', 'Ath-Thabari'),
    # Karakter aneh / noise
    (r'[​‌‍\u200b\u200c\u200d\ufeff]', ''),  # zero-width chars
    (r'\s{3,}', '  '),                         # multiple spaces → 2 spaces
    (r'(\w)\1{4,}', r'\1\1'),                  # karakter berulang 5+ → 2
    # Kata-kata terpotong umum
    (r'\bMasyit ah\b', 'Masyithah'),
    (r'\bFir\'aun\b', "Fir'aun"),
    (r'\bHaudz\b', 'Haudz'),
]

_OCR_COMPILED = [(re.compile(pat), rep) for pat, rep in _OCR_CORRECTIONS]


def _clean_ocr_artifacts(text: str) -> str:
    """Bersihkan artefak OCR umum dari teks tafsir.

    Dijalankan pada setiap blok teks sebelum dikirim ke LLM agar
    jawaban tidak mengandung kata-kata yang salah OCR.
    """
    if not text:
        return text
    for pattern, replacement in _OCR_COMPILED:
        text = pattern.sub(replacement, text)
    return text


def build_rag_context(docs: List[Dict[str, Any]]) -> str:
    """Bangun teks konteks terstruktur dari daftar dokumen RAG.

    Setiap dokumen dianotasi dengan [TIPE: ...] agar LLM tahu apakah
    segmen ini memuat riwayat bersanad, tarjih, atau hanya penjelasan
    langsung Ath-Thabari — sehingga model tidak mengarang bagian yang
    tidak ada di teks.
    """
    ctx_parts = []
    surah_set: set = set()  # track surah yang muncul di konteks

    for i, doc in enumerate(docs, 1):
        meta = doc.get("metadata", {})
        reranker_score = doc.get("reranker_score", doc.get("score", 0))

        # Relevance label — disesuaikan untuk BGE normalized score (0-1)
        # BGE reranker-v2-m3 mengembalikan 0-1 setelah normalize=True
        relevance = ""
        if reranker_score > 0.7:
            relevance = " [SANGAT RELEVAN]"
        elif reranker_score > 0.4:
            relevance = " [RELEVAN]"
        elif reranker_score < 0.1 and reranker_score >= 0:
            relevance = " [KURANG RELEVAN — gunakan hati-hati]"
        elif reranker_score > 5:
            # Fallback untuk score non-normalized (CrossEncoder lama)
            relevance = " [SANGAT RELEVAN]"
        elif reranker_score > 2:
            relevance = " [RELEVAN]"

        # Track surah
        no_surah = meta.get("no_surah")
        nama_surah = meta.get("nama_surah", "")
        if no_surah:
            surah_set.add((no_surah, nama_surah))

        aqwal_list = meta.get("aqwal") or []
        tarjih_obj = meta.get("tarjih")

        # ── Deteksi tipe segmen ──────────────────────────────────────────
        seg_type = _detect_segment_type(meta, aqwal_list, tarjih_obj)
        seg_label_map = {
            "takwil_langsung": "takwil_langsung — ini adalah penjelasan/takwil Ath-Thabari sendiri, BUKAN riwayat dari perawi lain, TIDAK ADA perbedaan pendapat ulama",
            "riwayat": "riwayat — memuat pendapat/riwayat dari sahabat atau tabi'in",
            "tarjih": "tarjih — memuat kesimpulan Ath-Thabari atas perbedaan pendapat",
            "campuran": "campuran — memuat riwayat dari perawi DAN tarjih Ath-Thabari",
        }

        lafaz = meta.get("lafaz_frasa", "")
        header_parts = [
            f"[Dokumen {i} — {doc['source']}{relevance}]",
            f"[TIPE: {seg_label_map.get(seg_type, seg_type)}]",
        ]
        if lafaz:
            header_parts.append(f"[Lafaz: {lafaz}]")

        # Daftar nama perawi (hanya jika ada riwayat)
        if seg_type in ("riwayat", "campuran") and aqwal_list:
            perawi_names = [a.get("speaker_name") for a in aqwal_list if a.get("speaker_name")]
            if perawi_names:
                unique_perawi = list(dict.fromkeys(perawi_names))  # preserve order, deduplicate
                header_parts.append(f"[Perawi yang disebut: {', '.join(unique_perawi[:8])}]")

        block = "\n".join(header_parts) + "\n" + _clean_ocr_artifacts(doc["text"])

        # ── Detail riwayat per perawi ────────────────────────────────────
        if aqwal_list:
            aqwal_lines = []
            for aq in aqwal_list[:8]:
                name = aq.get("speaker_name", "") or "(tidak diketahui)"
                stmt = (aq.get("statement") or "").strip()
                stype = aq.get("speaker_type", "")
                if stmt:
                    aqwal_lines.append(f"  • {name} ({stype}): {stmt[:300]}")
            if aqwal_lines:
                block += "\n[Riwayat dari perawi — kutip nama perawi ini secara eksplisit:]\n" + "\n".join(aqwal_lines)

        # ── Detail tarjih ────────────────────────────────────────────────
        if tarjih_obj and isinstance(tarjih_obj, dict):
            reason = tarjih_obj.get("reasoning", "")
            status = tarjih_obj.get("status", "")
            selected_spk = tarjih_obj.get("selected_speaker", "")
            if reason:
                tarjih_line = f"[Ada tarjih — Ath-Thabari menyimpulkan ({status}): {reason[:400]}"
                if selected_spk:
                    tarjih_line += f" — mengikuti pendapat: {selected_spk}"
                tarjih_line += "]"
                block += "\n" + tarjih_line

        ctx_parts.append(block)

    # ── Ringkasan sinyal untuk LLM ───────────────────────────────────────
    seg_types = [_detect_segment_type((d.get("metadata") or {}), (d.get("metadata") or {}).get("aqwal") or [], (d.get("metadata") or {}).get("tarjih")) for d in docs]
    has_any_riwayat = any(t in ("riwayat", "campuran") for t in seg_types)
    has_any_tarjih = any(t in ("tarjih", "campuran") for t in seg_types)

    signals = []
    if not has_any_riwayat:
        signals.append("⚠ SINYAL: Konteks ini TIDAK memuat riwayat bersanad dari perawi. Jangan tulis bagian 'Pendapat Ulama'. Tulis: Tidak ada perbedaan pendapat pada bagian ini.")
    if not has_any_tarjih:
        signals.append("⚠ SINYAL: Konteks ini TIDAK memuat tarjih Ath-Thabari. Jangan tulis bagian 'Tarjih'. Tulis: Tidak ada tarjih pada bagian ini.")
    if has_any_riwayat and not has_any_tarjih:
        signals.append("ℹ SINYAL: Ada riwayat dari perawi, tetapi Ath-Thabari belum menarik tarjih di bagian ini.")
    if has_any_riwayat and has_any_tarjih:
        signals.append("ℹ SINYAL: Ada riwayat dari perawi DAN tarjih Ath-Thabari. Sajikan keduanya secara terpisah.")

    # ── Sinyal cross-surah untuk pertanyaan komparatif ───────────────────
    if len(surah_set) > 1:
        surah_list = ", ".join(f"Surah {s[1]} ({s[0]})" for s in sorted(surah_set))
        signals.append(
            f"ℹ SINYAL MULTI-SURAH: Konteks memuat dokumen dari {len(surah_set)} surah berbeda: {surah_list}. "
            f"Jika pertanyaan bersifat komparatif, sajikan perbandingan per surah secara terpisah."
        )

    prefix = "\n".join(signals) + "\n\n" if signals else ""
    return prefix + "\n\n".join(ctx_parts)


class RAGService:
    """RAG Service using Qdrant + BGE-M3 for Tafsir Ath-Thabari."""

    def __init__(self):
        self.collection = settings.QDRANT_COLLECTION
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
        )
        self._conversation_history: List[Dict] = []
        logger.info(f"RAG Service ready. Collection: {self.collection}")

    # ── Embedding ──────────────────────────────────────────────────────────

    def get_embedding(self, text: str) -> List[float]:
        """Embed text using BGE-M3 (dense vector, dim=1024)."""
        result = _embed_model.encode(
            [text],
            batch_size=1,
            max_length=512,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        return result['dense_vecs'][0].tolist()

    # ── Semantic Search ────────────────────────────────────────────────────

    def _semantic_search(self, query: str, top_k: int = 30) -> List[Dict[str, Any]]:
        vec = self.get_embedding(query)
        results = self.client.query_points(
            collection_name=self.collection,
            query=vec,
            using="dense",
            limit=top_k,
        ).points

        docs = []
        for rank, r in enumerate(results, 1):
            payload = r.payload or {}
            docs.append({
                "text": payload.get("teks_tafsir", payload.get("text", "")),
                "source": self._format_source(payload),
                "score": r.score,
                "semantic_score": r.score,
                "semantic_rank": rank,
                "metadata": payload,
            })
        logger.debug(f"Semantic search: {len(docs)} docs for '{query[:50]}'")
        return docs

    def _format_source(self, payload: dict) -> str:
        surah = payload.get("nama_surah", "")
        ayat = payload.get("no_ayat", "")
        lafaz = payload.get("lafaz_frasa", "")
        if surah and ayat:
            base = f"QS {surah}:{ayat}"
            return f"{base} — {lafaz}" if lafaz else base
        return payload.get("source", "Tafsir Ath-Thabari")

    # ── HyDE Query Expansion ───────────────────────────────────────────────

    def _hyde_expand(self, query: str) -> str:
        """Generate a hypothetical tafsir passage (domain-constrained) to improve retrieval.

        Menggunakan system prompt khusus agar tidak terpicu aturan penolakan konteks.
        """
        try:
            hyde_system = (
                "Kamu adalah asisten akademik Tafsir Ath-Thabari. Tugasmu membuat satu paragraf ringkas "
                "(2-3 kalimat) berisi estimasi narasi takwil tafsir klasik Ath-Thabari yang relevan dengan pertanyaan "
                "untuk memperluas pencarian dokumen. Jangan buat penolakan, salam, atau teks di luar tafsir."
            )
            prompt = f"Pertanyaan user: {query}\n\nEstimasi narasi takwil Ath-Thabari:"
            resp = self._call_llm(prompt, max_tokens=150, system_prompt=hyde_system)
            resp = resp.strip()
            # Jika HyDE mengembalikan sinyal penolakan/gagal, fallback ke query asli
            if len(resp) < 15 or 'di luar domain' in resp.lower() or 'maaf' in resp.lower()[:30]:
                return query
            return resp
        except Exception as e:
            logger.warning(f"HyDE expansion failed: {e}")
            return query

    def _multi_query_search(self, queries: List[str], top_k: int) -> List[Dict[str, Any]]:
        from app.services.hybrid_search import reciprocal_rank_fusion
        if len(queries) == 1:
            return self._semantic_search(queries[0], top_k)
        all_results = [self._semantic_search(q, top_k) for q in queries]
        return reciprocal_rank_fusion(all_results, k=settings.RRF_K)

    def _extract_surah_ayat(self, query: str):
        """Ekstrak SATU surah+ayat dari query untuk exact verse lookup."""
        q_low = query.lower()
        # 1. Format: QS 11:1 atau QS 11 : 1 atau QS. 11:1
        m1 = re.search(r'\bqs\.?\s*(\d+)\s*[:\s]\s*(\d+)\b', q_low)
        if m1:
            return int(m1.group(1)), int(m1.group(2))

        # 2. Format: (surah/surat/qs) <nama> (ayat) <nomor>
        for name, s_num in _SURAH_NAME_MAP.items():
            pat = rf'\b{re.escape(name)}\b.*?(?:ayat\s*|[:\s])\s*(\d+)\b'
            m2 = re.search(pat, q_low)
            if m2:
                return s_num, int(m2.group(1))
        return None, None

    def _extract_all_surahs(self, query: str) -> List[int]:
        """Ekstrak SEMUA nomor surah yang disebut dalam query (untuk pertanyaan komparatif)."""
        q_low = query.lower()
        found: List[int] = []
        seen: set = set()

        # Format QS X:Y atau QS X
        for m in re.finditer(r'\bqs\.?\s*(\d+)\b', q_low):
            n = int(m.group(1))
            if n in VALID_SURAH_NUMBERS and n not in seen:
                found.append(n)
                seen.add(n)

        # Nama surah
        for name, s_num in _SURAH_NAME_MAP.items():
            if s_num in seen:
                continue
            if re.search(rf'\b{re.escape(name)}\b', q_low):
                found.append(s_num)
                seen.add(s_num)

        # Format "surah X" atau "surat X"
        for m in re.finditer(r'\bsurat?\s+(\d+)\b', q_low):
            n = int(m.group(1))
            if n in VALID_SURAH_NUMBERS and n not in seen:
                found.append(n)
                seen.add(n)

        return found

    def _search_surah_topic(
        self,
        query: str,
        no_surah: int,
        limit: int = 8,
        query_vector: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """Cari dokumen relevan pada surah tertentu berdasarkan embedding query (bukan scroll acak)."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        try:
            vec = query_vector if query_vector is not None else self.get_embedding(query)
            res = self.client.query_points(
                collection_name=self.collection,
                query=vec,
                using="dense",
                query_filter=Filter(
                    must=[FieldCondition(key="no_surah", match=MatchValue(value=no_surah))]
                ),
                limit=limit,
                with_payload=True,
            ).points
            docs = []
            for rank, p in enumerate(res, 1):
                payload = p.payload or {}
                docs.append({
                    "text": payload.get("teks_tafsir", payload.get("text", "")),
                    "source": self._format_source(payload),
                    "score": p.score,
                    "semantic_score": p.score,
                    "semantic_rank": rank,
                    "metadata": payload,
                })
            return docs
        except Exception as e:
            logger.warning(f"Surah topic search error (surah={no_surah}): {e}")
            return []

    def _expand_arabic_terms(self, query: str) -> str:
        """Tambahkan sinonim/konteks untuk istilah Arab spesifik dalam query.

        Membantu retrieval ketika user menyebut istilah Arab yang mungkin
        tidak tersimpan persis sama di database (variasi transliterasi, dll).
        """
        expansions = {
            # Istilah tafsir
            r'\bhayta\s*lak\b': 'hayta lak هَيْتَ لَكَ zulaikha goda Yusuf',
            r'\bsalsal\b': 'salsal صَلْصَال tanah liat kering penciptaan manusia',
            r'\bsijjil\b': 'sijjil سِجِّيل batu dari tanah terbakar kaum Luth',
            r'\bruh\b.*\b(makna|arti|tafsir)\b': 'ruh روح makna hakikat perbedaan pendapat khilaf',
            r'\b(asbabun|asbab)\s*nuzul\b': 'asbabun nuzul sebab turun latar belakang konteks',
            r'\bhaditsul?\s*ifk\b': 'haditsul ifk tuduhan palsu berita bohong Aisyah',
            r'\bqadzaf\b': 'qadzaf menuduh zina wanita baik-baik hukuman cambuk',
            r"\bli'an\b": "li'an sumpah suami istri zina tuduhan",
            r'\bkhidir\b|\bkhidhr\b|\bkhizr\b': 'Khidir Khizir hamba saleh nabi wali ilmu laduni',
            r'\btakwil\b': 'takwil penafsiran makna penjelasan Ath-Thabari',
            r'\bikhtilaf\b|\bkhilaf\b': 'ikhtilaf khilaf perbedaan pendapat ulama salaf',
            r'\btarjih\b|\bdirajihkan\b|\bditrjihkan\b': 'tarjih pendapat terkuat paling benar Abu Jafar',
            r'\bnabiyullah\b|\bnabi\s+ullah\b': 'nabi Allah rasul',
            r'\bsalaf\b': 'salaf ulama sahabat tabiin perawi',
            r'\bnahwu\b|\blinguistik\b': 'nahwu bahasa Arab gramatika i\'rab analisis lafaz',
        }
        q = query
        for pattern, expansion in expansions.items():
            if re.search(pattern, q, re.IGNORECASE):
                q = q + ' ' + expansion
                break  # Satu ekspansi saja cukup untuk hindari noise
        return q if q != query else query


    def _get_exact_verse_docs(self, no_surah: int, no_ayat: int) -> List[Dict[str, Any]]:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        try:
            res, _ = self.client.scroll(
                collection_name=self.collection,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="no_surah", match=MatchValue(value=no_surah)),
                        FieldCondition(key="no_ayat", match=MatchValue(value=no_ayat)),
                    ]
                ),
                limit=20,
                with_payload=True,
                with_vectors=False,
            )
            pts = list(res)
            pts.sort(key=lambda p: (p.payload or {}).get("urutan", 0))
            docs = []
            for rank, p in enumerate(pts, 1):
                payload = p.payload or {}
                docs.append({
                    "text": payload.get("teks_tafsir", payload.get("text", "")),
                    "source": self._format_source(payload),
                    "score": 10.0,
                    "reranker_score": 10.0,
                    "semantic_score": 10.0,
                    "semantic_rank": rank,
                    "metadata": payload,
                })
            return docs
        except Exception as e:
            logger.warning(f"Exact verse lookup error: {e}")
            return []

    # ── Full Search Pipeline ───────────────────────────────────────────────

    def search(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        top_k = top_k or settings.RERANKER_TOP_K
        initial_k = settings.INITIAL_RETRIEVAL_K

        logger.info(f"=== RAG Search: '{query[:80]}' ===")

        # ── Step 0: Arabic term query expansion ──────────────────────────────
        expanded_query = self._expand_arabic_terms(query)
        if expanded_query != query:
            logger.info(f"Step 0 — Arabic term expansion applied")

        # ── Step 0b: Multi-surah detection ───────────────────────────────────
        all_surahs = self._extract_all_surahs(query)
        is_multi_surah = len(all_surahs) > 1
        logger.info(f"Step 0b — Surah detected: {all_surahs} (multi={is_multi_surah})")

        # ── Step 1: Exact verse lookup (Hanya untuk query single-verse) ──────
        exact_docs = []
        if not is_multi_surah:
            target_surah, target_ayat = self._extract_surah_ayat(query)
            if target_surah and target_ayat:
                exact_docs = self._get_exact_verse_docs(target_surah, target_ayat)
                logger.info(f"Exact verse QS {target_surah}:{target_ayat} → {len(exact_docs)} units")

        # ── Step 2: Query Expansion (HyDE) ───────────────────────────────────
        search_queries = [expanded_query]
        # Jika ayat spesifik sudah ditemukan (exact_docs), lewati HyDE untuk memangkas latensi 3-5 detik
        if not exact_docs and settings.ENABLE_QUERY_EXPANSION and settings.ENABLE_HYDE:
            hyde_doc = self._hyde_expand(query)  # HyDE dari query asli
            if hyde_doc and hyde_doc != query:
                search_queries = [expanded_query, hyde_doc]
            logger.info(f"Step 2 — Query Expansion: {len(search_queries)} queries")
        elif exact_docs:
            logger.info(f"Step 2 — Exact verse found, skipping HyDE for faster retrieval")

        # ── Step 3: Semantic Search ───────────────────────────────────────────
        semantic_results = self._multi_query_search(search_queries, initial_k)

        # Untuk pertanyaan komparatif (multi-surah), cari dokumen bertopik relevan per surah
        # agar tidak mengumpulkan chunk acak yang tidak sesuai pertanyaan
        if is_multi_surah and all_surahs:
            q_vec = self.get_embedding(expanded_query)
            seen_uids = {
                d.get("metadata", {}).get("id_unit")
                for d in semantic_results
                if d.get("metadata", {}).get("id_unit")
            }
            for s_num in all_surahs:
                s_topic_docs = self._search_surah_topic(expanded_query, s_num, limit=8, query_vector=q_vec)
                for d in s_topic_docs:
                    uid = d.get("metadata", {}).get("id_unit")
                    if uid not in seen_uids:
                        seen_uids.add(uid)
                        semantic_results.append(d)
            logger.info(f"Step 3b — Multi-surah topic candidates: {len(semantic_results)} total")

        # ── Step 4: Hybrid BM25 + RRF ────────────────────────────────────────
        if settings.ENABLE_HYBRID_SEARCH and semantic_results:
            from app.services.hybrid_search import hybrid_search_service
            hybrid_results = hybrid_search_service.hybrid_search(
                query=expanded_query,
                semantic_results=semantic_results,
                top_k=initial_k,
            )
            logger.info(f"Step 4 — Hybrid: {len(hybrid_results)} docs")
        else:
            hybrid_results = semantic_results

        # ── Step 5: Reranker ─────────────────────────────────────────────────
        # Untuk multi-surah, naikkan top_k agar representasi tiap surah terjaga
        reranker_top_k = top_k * len(all_surahs) if is_multi_surah and all_surahs else top_k
        reranker_top_k = min(reranker_top_k, 20)  # batas maksimal
        if settings.ENABLE_RERANKER and hybrid_results:
            from app.services.reranker import rerank_documents
            final = rerank_documents(query, hybrid_results, reranker_top_k)
            logger.info(f"Step 5 — Reranker top_k={reranker_top_k}: {len(final)} docs")
        else:
            final = hybrid_results[:reranker_top_k]

        # ── Merge: prioritize exact verse matches ─────────────────────────────
        if exact_docs:
            seen_keys: set = set()
            combined = []
            for d in exact_docs:
                k = (d.get('metadata', {}).get('id_unit'), d.get('source'))
                seen_keys.add(k)
                combined.append(d)
            for d in final:
                k = (d.get('metadata', {}).get('id_unit'), d.get('source'))
                if k not in seen_keys:
                    seen_keys.add(k)
                    combined.append(d)
            # Untuk multi-surah, ambil lebih banyak dokumen
            limit = top_k * max(1, len(all_surahs)) if is_multi_surah else top_k
            limit = min(limit, 20)
            final = combined[:limit]

        logger.info(f"=== Final: {len(final)} docs ===")
        return final

    # ── LLM Generation ────────────────────────────────────────────────────

    def _call_llm(self, prompt: str, max_tokens: int = 2048, system_prompt: str = None) -> str:
        """Call OpenRouter → Gemini fallback."""
        if settings.OPENROUTER_API_KEY:
            return self._openrouter(prompt, max_tokens, system_prompt)
        return self._gemini(prompt, system_prompt)

    def _openrouter(self, prompt: str, max_tokens: int = 2048, system_prompt: str = None) -> str:
        sys_prompt = system_prompt or SYSTEM_PROMPT
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "Chatbot Tafsir Ath-Thabari",
            },
            json={
                "model": settings.OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _gemini(self, prompt: str, system_prompt: str = None) -> str:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        sys_prompt = system_prompt or SYSTEM_PROMPT
        return model.generate_content(sys_prompt + "\n\n" + prompt).text

    # ── Build Conversation History ─────────────────────────────────────────

    def _build_history_ctx(self) -> str:
        if not self._conversation_history:
            return ""
        lines = [f"{m['role'].capitalize()}: {m['content']}" for m in self._conversation_history[-6:]]
        return "RIWAYAT PERCAKAPAN:\n" + "\n".join(lines) + "\n\n"

    # ── Main Query Entry ───────────────────────────────────────────────────

    def query(
        self,
        question: str,
        top_k: int = None,
        conversation_history: List[Dict] = None,
    ) -> Dict[str, Any]:
        self._conversation_history = conversation_history or []

        # ── Layer 1: Scope Guard — surah di luar 11-24 ──────────────────────
        scope_err = _check_scope(question)
        if scope_err:
            logger.info(f"Scope guard triggered for: '{question[:60]}'")
            return {"answer": scope_err, "sources": [], "documents": []}

        # ── Layer 2: OOD Guard — pertanyaan bukan tentang tafsir ────────────
        ood_err = _check_ood(question)
        if ood_err:
            logger.info(f"OOD guard triggered for: '{question[:60]}'")
            return {"answer": ood_err, "sources": [], "documents": []}

        # ── Layer 3: Ekstrak constraint linguistik dari user ─────────────────
        user_constraints = _extract_user_constraints(question)
        if user_constraints:
            logger.info(f"User constraints extracted: {user_constraints[:80]}")

        # ── Layer 4: Retrieval ───────────────────────────────────────────────
        docs = self.search(question, top_k)
        if not docs:
            return {
                "answer": "Maaf, saya tidak menemukan informasi relevan dalam database tafsir untuk pertanyaan ini.",
                "sources": [],
                "documents": [],
            }

        # ── Layer 5: Context sufficiency check ──────────────────────────────
        if not _is_context_sufficient(docs, question):
            logger.warning(f"Context insufficient for: '{question[:60]}'")

        context = build_rag_context(docs)

        # ── Layer 6: Build prompt dengan constraint ──────────────────────────
        prompt = (
            f"{self._build_history_ctx()}"
            f"Konteks dari Tafsir Ath-Thabari:\n{context}\n"
            f"{user_constraints}\n"
            f"Pertanyaan: {question}\n\n"
            f"Jawaban (gunakan format terstruktur, sebut perawi eksplisit, "
            f"bedakan tarjih Ath-Thabari, patuhi semua constraint user):"
        )

        try:
            answer = self._call_llm(prompt)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            answer = f"Terjadi kesalahan saat menghasilkan jawaban: {e}"

        # ── Collect unique sources ────────────────────────────────────────────
        sources = []
        seen = set()
        for doc in docs:
            src = doc.get("source", "")
            if src not in seen:
                seen.add(src)
                sources.append({
                    "source": src,
                    "chunk_content": doc.get("text", "")[:800],
                    "score": doc.get("reranker_score", doc.get("score", 0)),
                    "metadata": doc.get("metadata", {}),
                })

        return {"answer": answer, "sources": sources, "documents": docs}


# ── Singleton ──────────────────────────────────────────────────────────────
_rag_instance: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGService()
    return _rag_instance
