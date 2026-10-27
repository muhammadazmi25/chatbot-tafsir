"""
restore_ocr_bulk.py
====================
Script LLM Restoration untuk 903 ayat Tafsir Ath-Thabari yang mengandung OCR noise.
Menggunakan GPT-4o-mini via OpenRouter dengan prompt berkualitas tinggi.

Fitur:
- Checkpoint system: bisa resume jika proses terhenti
- Log biaya real-time (USD) per ayat dan total
- Retry otomatis jika API error (max 3x)
- Dry-run mode untuk test
- Progress bar sederhana
- UPDATE langsung ke database MySQL (tidak buat baris baru, aman untuk FK)

Cara pakai:
  python Chatbot/restore_ocr_bulk.py              # dry-run (simulasi)
  python Chatbot/restore_ocr_bulk.py --execute    # eksekusi nyata ke DB
  python Chatbot/restore_ocr_bulk.py --surah 12   # hanya surah 12
  python Chatbot/restore_ocr_bulk.py --resume     # lanjut dari checkpoint
  python Chatbot/restore_ocr_bulk.py --reset      # hapus checkpoint, mulai ulang
"""

import os, sys, re, json, time, argparse
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = WORKSPACE_ROOT / "Chatbot" / ".env"
CHECKPOINT_FILE = WORKSPACE_ROOT / "Chatbot" / "restore_checkpoint.json"
LOG_FILE = WORKSPACE_ROOT / "Chatbot" / "restore_ocr_log.txt"

from dotenv import load_dotenv
load_dotenv(ENV_PATH)

DB_URL = os.getenv("DATABASE_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "openai/gpt-4o-mini"

# Harga GPT-4o-mini via OpenRouter (per 1M token)
PRICE_INPUT_PER_M  = 0.15   # $0.15/1M input tokens
PRICE_OUTPUT_PER_M = 0.60   # $0.60/1M output tokens

# ─── Daftar 903 ayat bermasalah (hasil audit scan_ocr_noise.py) ───
CORRUPTED_AYAT = {
    11: [1,2,3,4,5,6,7,8,9,10,11,13,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,
         30,31,32,33,34,35,36,37,38,39,40,42,44,45,46,48,49,50,51,52,53,54,55,57,
         58,59,60,61,62,63,64,65,66,69,70,71,72,73,74,75,76,77,78,80,81,82,83,84,
         85,86,87,88,89,90,91,92,93,94,95,98,99,100,101,103,104,105,106,107,108,
         109,110,111,113,114,115,116,118,119,120],
    12: [1,3,4,6,10,12,15,18,19,20,21,22,23,24,25,26,27,28,31,35,36,37,38,39,42,
         45,46,49,50,51,52,53,55,56,58,60,63,64,66,67,68,70,73,74,75,76,77,78,80,
         83,84,85,86,87,88,89,91,92,95,97,98,99,100,101,102,105,106,107,109,110,111],
    13: [2,3,4,5,6,7,8,10,11,12,13,14,15,17,18,25,28,29,30,31,33,35,36,39,41,43],
    14: [1,4,5,7,9,13,14,15,16,17,18,21,22,23,24,25,26,27,28,29,30,31,34,35,36,
         37,42,43,44,45,46,48,49,50,51],
    15: [1,2,9,12,13,14,15,16,17,18,19,22,23,24,25,26,27,30,31,32,33,34,35,41,42,
         43,44,45,46,47,48,49,50,54,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,
         79,80,81,85,86,87,88,89,90,91,92,93,94,95,96,99],
    16: [1,2,4,5,6,7,8,9,10,12,13,14,15,16,17,18,21,22,23,24,25,26,30,32,33,35,
         38,39,40,41,43,44,45,46,47,48,52,56,57,58,59,60,61,62,66,67,68,69,70,71,
         72,73,74,75,76,77,79,80,81,82,83,84,87,88,90,91,92,97,98,99,100,101,103,
         106,110,112,113,115,116,117,118,120,121,122,123,124,126],
    17: [1,2,3,4,5,6,7,8,11,12,13,14,15,16,18,19,20,21,22,23,24,25,26,27,28,29,
         31,33,34,35,36,37,38,39,40,42,43,44,45,46,47,50,51,52,53,55,56,57,58,59,
         60,63,64,65,66,68,69,71,72,73,75,76,77,78,79,80,81,82,83,84,85,90,92,93,
         97,100,101,102,103,104,105,106,107,108,109,110,111],
    18: [1,2,3,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,
         29,32,33,34,35,36,40,41,42,43,44,46,47,48,49,50,51,52,53,57,58,60,61,63,
         64,65,71,74,77,79,80,81,82,83,84,85,86,89,90,91,92,93,94,95,96,97,98,99,
         100,102,103,104,107,108,109,110],
    19: [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,22,23,24,25,26,27,28,29,
         30,31,32,33,34,37,38,39,46,52,53,55,56,57,59,62,64,65,68,69,71,72,73,74,
         76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,96,97,98],
    20: [1,2,3,6,7,8,9,10,11,12,13,14,15,16,18,19,20,21,22,23,24,25,26,27,28,29,
         30,31,32,33,34,35,39,40,41,42,43,48,49,50,51,52,53,55,57,58,59,60,61,62,
         63,64,65,66,70,71,77,80,81,82,85,86,87,88,89,90,91,92,93,94,95,96,97,98,
         101,102,103,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,
         120,121,122,124,125,126,128,129,130,131,132,133],
    21: [3,5,6,9,13,14,15,17,18,19,20,21,23,24,25,26,27,28,29,30,32,33,37,38,42,
         43,45,47,50,57,58,59,60,61,62,63,68,69,70,71,72,73,78,79,80,81,83,84,85,
         86,87,88,89,90,91,95,96,98,100,101,102,103,104,105,106,107,112],
    22: [1,2,3,4,5,9,10,11,12,13,15,16,19,20,21,22,25,26,27,28,29,30,31,32,33,36,
         39,40,41,45,47,49,50,51,52,53,55,66,67,70,72,78],
    23: [1,2,3,4,5,6,7,8,9,10,11,13,14,20,25,26,27,34,35,36,37,41,44,49,50,53,60,
         61,63,66,67,68,69,70,77,86,87,90,91,92,96,97,98,99,100,101,107,108],
    24: [1,2,3,5,6,7,12,25,32,33,35,36,40,62],
}

SURAH_NAMES = {
    11:"Hud", 12:"Yusuf", 13:"Ar-Ra'd", 14:"Ibrahim", 15:"Al-Hijr",
    16:"An-Nahl", 17:"Al-Isra'", 18:"Al-Kahf", 19:"Maryam", 20:"Thaha",
    21:"Al-Anbiya'", 22:"Al-Hajj", 23:"Al-Mu'minun", 24:"An-Nur"
}


# ─── Database helpers ─────────────────────────────────────────────────────────

def get_engine():
    from sqlalchemy import create_engine
    return create_engine(DB_URL, pool_pre_ping=True, pool_size=5, max_overflow=10,
                         connect_args={"connect_timeout": 30})

def get_verse_data(engine, surah_no, ayat_no):
    """Ambil id_verse, teks Arab, terjemahan, dan teks tafsir saat ini."""
    from sqlalchemy import text
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT v.id, v.text_uthmani, t.text as terjemahan,
                   vt.text as tafsir_saat_ini, c.name as surah_name
            FROM verses v
            JOIN chapters c ON c.id = v.id_chapter
            LEFT JOIN verse_translations t ON t.id_verse = v.id AND t.id_translation = 1
            LEFT JOIN verse_tafsirs vt ON vt.id_verse = v.id AND vt.id_tafsir = 7
            WHERE c.number_chapter = :s AND v.number = :a
        """), {"s": surah_no, "a": ayat_no}).fetchone()
    return row

def update_tafsir(engine, id_verse, new_text):
    """UPDATE teks tafsir di database — langsung UPDATE baris yang sudah ada.
    Tidak buat baris baru untuk menghindari duplikat dan foreign key issues.
    """
    from sqlalchemy import text
    with engine.begin() as conn:
        result = conn.execute(text("""
            UPDATE verse_tafsirs SET text = :txt
            WHERE id_verse = :vid AND id_tafsir = 7
        """), {"vid": id_verse, "txt": new_text})
        # Jika belum ada baris (rare case), baru INSERT
        if result.rowcount == 0:
            conn.execute(text("""
                INSERT INTO verse_tafsirs (id_verse, id_tafsir, text)
                VALUES (:vid, 7, :txt)
            """), {"vid": id_verse, "txt": new_text})


# ─── Checkpoint helpers ───────────────────────────────────────────────────────

def load_checkpoint():
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"done": [], "total_input_tokens": 0, "total_output_tokens": 0, "total_cost_usd": 0.0}

def save_checkpoint(cp):
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(cp, f, ensure_ascii=False, indent=2)


# ─── Logging ─────────────────────────────────────────────────────────────────

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = "[" + ts + "] " + msg
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ─── LLM Prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Kamu adalah pakar filologi dan editor naskah Tafsir Ath-Thabari (Jami' al-Bayan 'an Ta'wil ay al-Qur'an), edisi terjemahan Pustaka Azzam Indonesia.

TUGASMU: Membersihkan dan merestorasi teks tafsir yang rusak akibat OCR (Optical Character Recognition) dari scan buku cetak lama.

STANDAR KUALITAS OUTPUT — Ikuti format ini dengan ketat:

1. BARIS PERTAMA: Teks Arab ayat (harakat lengkap, gunakan teks Arab yang diberikan)
2. BARIS KEDUA: Terjemahan Indonesia dalam tanda kutip (ambil dari terjemahan yang diberikan)
3. BARIS BERIKUTNYA: Penjelasan "Takwil firman Allah:" (bukan "rakrril", "ratrwil", dll)
4. ISI TAFSIR: Paragraf-paragraf tafsir Abu Ja'far dengan nomor hadits, nama perawi, matan lengkap
5. AKHIR: Tutup dengan natural, jangan tambah penutup yang tidak ada di aslinya

ATURAN KETAT:
- Ganti SEMUA simbol OCR rusak (W:35 UK,$Y"x$t, ]LUK, $ij ?rj, 4y1;l$yVrc$, dll) dengan teks Arab yang benar
- Perbaiki kata terpecah (g e mb ir a → gembira, d arip ada → daripadanya, kep adamu → kepadamu)
- Perbaiki kata OCR: rakrril/ratrwil → Takwil, l<firil → tidak, Sesunggzhnya → Sesungguhnya
- Perbaiki nama: Nftuhaffinad → Muhammad, [MuhammadJ → Muhammad
- JANGAN HAPUS atau RINGKAS konten apapun — pertahankan 100% isi: semua nomor hadits, sanad, perawi, matan
- Nomor hadits (misal: 18063, 18151) HARUS dipertahankan persis
- Nama perawi (Ibn Jarir, Qatadah, Mujahid, dll) HARUS lengkap
- Format: Mulai langsung dengan teks Arab, JANGAN tambah basa-basi atau keterangan tambahan
- Output dalam bahasa Indonesia baku yang rapi dan nyaman dibaca"""

def build_prompt(surah_no, ayat_no, surah_name, arabic_text, terjemahan, ocr_text):
    return f"""AYAT YANG PERLU DIRESTORASI:
Surah: {surah_no}. {surah_name}, Ayat: {ayat_no}

TEKS ARAB (gunakan ini sebagai referensi):
{arabic_text}

TERJEMAHAN INDONESIA:
{terjemahan or "(tidak tersedia)"}

TEKS OCR RUSAK (yang perlu dibersihkan):
{ocr_text}

Restorasi teks di atas menjadi teks tafsir yang bersih, lengkap, dan berkualitas tinggi. Mulai langsung dengan teks Arab tanpa pengantar apapun."""


# ─── OpenRouter API call ──────────────────────────────────────────────────────

def call_llm(surah_no, ayat_no, surah_name, arabic_text, terjemahan, ocr_text, retries=3):
    import urllib.request, json as _json

    prompt = build_prompt(surah_no, ayat_no, surah_name, arabic_text, terjemahan, ocr_text)

    payload = _json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt}
        ],
        "temperature": 0.05,        # Sangat deterministik untuk konsistensi
        "max_tokens": 4096,
        "top_p": 0.9,
    }).encode("utf-8")

    headers = {
        "Authorization": "Bearer " + OPENROUTER_API_KEY,
        "Content-Type": "application/json",
        "HTTP-Referer": "https://chatbot-tafsir.ift.my.id",
        "X-Title": "Tafsir Ath-Thabari OCR Restoration"
    }

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=payload, headers=headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = _json.loads(resp.read().decode("utf-8"))

            content   = result["choices"][0]["message"]["content"].strip()
            usage     = result.get("usage", {})
            in_tok    = usage.get("prompt_tokens", 0)
            out_tok   = usage.get("completion_tokens", 0)
            cost_usd  = (in_tok * PRICE_INPUT_PER_M / 1_000_000) + \
                        (out_tok * PRICE_OUTPUT_PER_M / 1_000_000)
            return content, in_tok, out_tok, cost_usd

        except Exception as e:
            if attempt < retries:
                wait = 5 * attempt
                log("  [RETRY " + str(attempt) + "/" + str(retries) + "] Error: " + str(e) + " | tunggu " + str(wait) + "s")
                time.sleep(wait)
            else:
                raise e


# ─── Main Pipeline ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="LLM OCR Restoration — Tafsir Ath-Thabari 903 Ayat",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh:
  python Chatbot/restore_ocr_bulk.py              # dry-run (simulasi, tidak update DB)
  python Chatbot/restore_ocr_bulk.py --execute    # eksekusi nyata, UPDATE ke DB
  python Chatbot/restore_ocr_bulk.py --surah 11   # hanya surah 11 (dry-run)
  python Chatbot/restore_ocr_bulk.py --surah 11 --execute
  python Chatbot/restore_ocr_bulk.py --resume     # lanjut dari checkpoint
  python Chatbot/restore_ocr_bulk.py --reset      # hapus checkpoint, mulai ulang
        """
    )
    parser.add_argument("--execute", action="store_true", help="UPDATE nyata ke database MySQL")
    parser.add_argument("--surah",   type=int, metavar="N", help="Proses hanya satu surah (11-24)")
    parser.add_argument("--resume",  action="store_true", help="Lanjut dari checkpoint terakhir")
    parser.add_argument("--reset",   action="store_true", help="Hapus checkpoint, mulai dari awal")
    parser.add_argument("--delay",   type=float, default=0.5, help="Jeda antar request (detik, default: 0.5)")
    args = parser.parse_args()

    dry_run = not args.execute
    mode_str = "DRY-RUN (simulasi)" if dry_run else "EXECUTE (UPDATE ke MySQL)"

    # Reset checkpoint jika diminta
    if args.reset and CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        log("Checkpoint dihapus, mulai dari awal.")

    # Load checkpoint
    cp = load_checkpoint() if args.resume else load_checkpoint()
    done_set = set(tuple(x) for x in cp.get("done", []))

    log("=" * 70)
    log("RESTORE OCR BULK — Tafsir Ath-Thabari")
    log("Mode   : " + mode_str)
    log("Model  : " + MODEL)
    log("Harga  : $" + str(PRICE_INPUT_PER_M) + "/1M input | $" + str(PRICE_OUTPUT_PER_M) + "/1M output")
    log("Surah  : " + (str(args.surah) if args.surah else "Semua (11-24)"))
    log("Resume : " + str(len(done_set)) + " ayat sudah selesai sebelumnya")
    log("=" * 70)

    engine = get_engine()

    # Buat daftar tugas
    tasks = []
    target = CORRUPTED_AYAT
    if args.surah and args.surah in target:
        target = {args.surah: target[args.surah]}

    for surah_no in sorted(target.keys()):
        for ayat_no in target[surah_no]:
            if (surah_no, ayat_no) not in done_set:
                tasks.append((surah_no, ayat_no))

    total = len(tasks)
    log("Total ayat yang akan diproses: " + str(total))
    log("")

    # Akumulasi biaya
    session_input_tok  = 0
    session_output_tok = 0
    session_cost       = 0.0
    total_cost_all     = cp.get("total_cost_usd", 0.0)

    success_count = 0
    fail_count    = 0

    for idx, (surah_no, ayat_no) in enumerate(tasks, 1):
        sname = SURAH_NAMES.get(surah_no, "?")
        progress = "[" + str(idx) + "/" + str(total) + "]"

        # Ambil data dari DB
        row = get_verse_data(engine, surah_no, ayat_no)
        if not row:
            log(progress + " SKIP S" + str(surah_no) + ":" + str(ayat_no) + " — tidak ditemukan di DB")
            continue

        id_verse       = row[0]
        arabic_text    = row[1] or ""
        terjemahan     = row[2] or ""
        ocr_text       = row[3] or ""
        surah_name_db  = row[4] or sname

        if not ocr_text.strip():
            log(progress + " SKIP S" + str(surah_no) + ":" + str(ayat_no) + " — teks kosong")
            continue

        log(progress + " Memproses S" + str(surah_no) + ":" + str(ayat_no) +
            " (" + sname + ") | " + str(len(ocr_text)) + " chars ...")

        try:
            if dry_run:
                # Mode simulasi: hitung estimasi token saja
                est_in  = len(SYSTEM_PROMPT + ocr_text + arabic_text) // 4 + 200
                est_out = min(len(ocr_text) // 4, 4096)
                cost    = (est_in * PRICE_INPUT_PER_M / 1_000_000) + \
                          (est_out * PRICE_OUTPUT_PER_M / 1_000_000)
                log("  [DRY] ~" + str(est_in) + " in | ~" + str(est_out) + " out | ~$" +
                    "{:.6f}".format(cost) + " | [TIDAK ada update DB]")
                session_cost += cost
            else:
                # Panggil LLM
                restored, in_tok, out_tok, cost = call_llm(
                    surah_no, ayat_no, surah_name_db,
                    arabic_text, terjemahan, ocr_text
                )

                # Format payload: \r\n Arab \r\n teks \r\n
                new_payload = "\r\n" + arabic_text + "\r\n" + restored + "\r\n"

                # UPDATE ke DB
                update_tafsir(engine, id_verse, new_payload)

                session_input_tok  += in_tok
                session_output_tok += out_tok
                session_cost       += cost
                total_cost_all     += cost

                log("  [OK] " + str(in_tok) + " in + " + str(out_tok) +
                    " out | Biaya: $" + "{:.6f}".format(cost) +
                    " | Total sesi: $" + "{:.4f}".format(session_cost) +
                    " | Grand total: $" + "{:.4f}".format(total_cost_all))

                # Simpan ke checkpoint
                cp["done"].append([surah_no, ayat_no])
                cp["total_input_tokens"]  = cp.get("total_input_tokens",0) + in_tok
                cp["total_output_tokens"] = cp.get("total_output_tokens",0) + out_tok
                cp["total_cost_usd"]      = total_cost_all
                save_checkpoint(cp)

                success_count += 1

            # Jeda antar request
            if args.delay > 0 and not dry_run:
                time.sleep(args.delay)

        except Exception as e:
            log("  [ERROR] S" + str(surah_no) + ":" + str(ayat_no) + " GAGAL: " + str(e))
            fail_count += 1
            time.sleep(3)

    # ─── Ringkasan akhir ───────────────────────────────────────────────────────
    log("")
    log("=" * 70)
    log("SELESAI!")
    if dry_run:
        log("  Mode         : DRY-RUN (tidak ada perubahan di DB)")
        log("  Estimasi total biaya: $" + "{:.4f}".format(session_cost) +
            " (~Rp " + "{:,.0f}".format(session_cost * 16000) + ")")
    else:
        log("  Berhasil     : " + str(success_count) + " ayat di-UPDATE")
        log("  Gagal        : " + str(fail_count) + " ayat")
        log("  Input token  : " + str(session_input_tok))
        log("  Output token : " + str(session_output_tok))
        log("  Biaya sesi   : $" + "{:.4f}".format(session_cost) +
            " (~Rp " + "{:,.0f}".format(session_cost * 16000) + ")")
        log("  Grand total  : $" + "{:.4f}".format(total_cost_all) +
            " (~Rp " + "{:,.0f}".format(total_cost_all * 16000) + ")")
    log("  Log tersimpan: " + str(LOG_FILE))
    log("  Checkpoint   : " + str(CHECKPOINT_FILE))
    log("=" * 70)


if __name__ == "__main__":
    main()