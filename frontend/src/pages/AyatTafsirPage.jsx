import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  ArrowLeft, BookOpen, MessageSquare, 
  Info, Copy, Check, Search
} from 'lucide-react';
import { getAyatList, getTafsirUnits, getFullVerseTafsir } from '../api';
import { getSurahByNumber } from '../data/surahData';

export default function AyatTafsirPage() {
  const { surahNo, ayahNo } = useParams();
  const navigate = useNavigate();

  const currentSurahNo = parseInt(surahNo, 10);
  const currentAyahNo = parseInt(ayahNo, 10);
  const surahMeta = getSurahByNumber(currentSurahNo) || {
    nomor: currentSurahNo,
    namaLatin: `Surah ${currentSurahNo}`,
    nama: '',
  };

  const [currentAyat, setCurrentAyat] = useState(null);
  const [units, setUnits] = useState([]);
  const [fullTafsir, setFullTafsir] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [fullCopied, setFullCopied] = useState(false);
  const [fontSize, setFontSize] = useState('normal'); // 'compact' | 'normal' | 'large'
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    loadTafsirData();
  }, [currentSurahNo, currentAyahNo]);

  const loadTafsirData = async () => {
    try {
      setLoading(true);
      setFullTafsir(null);
      setSearchQuery('');

      // 1. Get ayat list to locate the current verse & id_verse_tafsir
      const allAyat = await getAyatList(currentSurahNo);
      const targetAyat = allAyat.find(a => a.no_ayat === currentAyahNo);
      setCurrentAyat(targetAyat || null);

      if (targetAyat && targetAyat.id_verse_tafsir) {
        // 2. Load tafsir units AND full tafsir in parallel
        const [unitsData, fullData] = await Promise.all([
          getTafsirUnits(targetAyat.id_verse_tafsir).catch(err => {
            console.warn("Gagal memuat units:", err);
            return [];
          }),
          getFullVerseTafsir(targetAyat.id_verse_tafsir).catch(err => {
            console.warn("Gagal memuat naskah asli:", err);
            return null;
          }),
        ]);

        setUnits(unitsData || []);
        setFullTafsir(fullData);
      } else {
        setUnits([]);
        setFullTafsir(null);
      }
    } catch (err) {
      console.error("Gagal memuat tafsir:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAskAI = (phrase = '') => {
    const prompt = phrase
      ? `Jelaskan penafsiran Imam Ath-Thabari pada QS ${surahMeta.namaLatin} [${currentSurahNo}]: ${currentAyahNo} mengenai frasa "${phrase}". Apa pendapat para mufassir salaf yang disebutkan?`
      : `Jelaskan secara komprehensif takwil Imam Ath-Thabari untuk QS ${surahMeta.namaLatin} [${currentSurahNo}]: ${currentAyahNo}.`;

    navigate(`/chat?query=${encodeURIComponent(prompt)}`);
  };

  const handleCopyTafsir = () => {
    if (!currentAyat) return;
    const textToCopy = `TAFSIR ATH-THABARI - QS ${surahMeta.namaLatin} [${currentSurahNo}]: ${currentAyahNo}\n\nAyat:\n${currentAyat.teks_arab}\n\nArtinya:\n${currentAyat.terjemahan ? currentAyat.terjemahan.replace(/<sup[^>]*>.*?<\/sup>/g, '') : ''}`;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCopyFullTafsir = () => {
    const textToCopy = fullTextData?.teks_asli;
    if (!textToCopy) return;
    const fullContent = `TAFSIR ATH-THABARI (NASKAH LENGKAP) - QS ${surahMeta.namaLatin} [${currentSurahNo}]: ${currentAyahNo}\n\nAyat:\n${currentAyat?.teks_arab || ''}\n\nArtinya:\n${currentAyat?.terjemahan || ''}\n\nNaskah Lengkap:\n${textToCopy}`;
    navigator.clipboard.writeText(fullContent);
    setFullCopied(true);
    setTimeout(() => setFullCopied(false), 2000);
  };

  // Data naskah lengkap (menggunakan fullTafsir dari backend API, atau fallback gabungan units)
  const fullTextData = useMemo(() => {
    if (fullTafsir?.teks_asli) return fullTafsir;
    if (units && units.length > 0) {
      const combined = units.map(u => {
        const lafazHeader = u.lafaz_frasa ? `Takwil firman Allah: ${u.lafaz_frasa}\n` : '';
        return lafazHeader + (u.ringkasan_takwil || '');
      }).join('\n\n');
      return {
        teks_asli: combined,
        karakter_count: combined.length,
        estimasi_baca_menit: Math.max(1, Math.round(combined.split(/\s+/).length / 150))
      };
    }
    return null;
  }, [fullTafsir, units]);

  // Helper: Format naskah asli menjadi paragraf-paragraf rapi
  const paragraphs = useMemo(() => {
    let raw = fullTextData?.teks_asli;
    if (!raw || !raw.trim()) return [];
    // Normalisasi newline
    raw = raw.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

    // Jika masih ada sisa header duplikat teks Arab / terjemahan AI sebelum takwil, bersihkan
    const takwilMatch = raw.match(/(Takwil firman Allah[\s\S]*|Abu Ja['’]far berkata[\s\S]*)/i);
    if (takwilMatch) {
      raw = takwilMatch[1].trim();
    }

    // Pisahkan berdasarkan newline ganda atau tunggal yang signifikan
    const parts = raw.split(/\n\s*\n/).map(p => p.trim()).filter(Boolean);
    if (parts.length <= 1) {
      const singleParts = raw.split(/\n+/).map(p => p.trim()).filter(Boolean);
      return singleParts.length > 0 ? singleParts : [raw.trim()];
    }
    return parts;
  }, [fullTextData]);

  // Filter paragraf jika ada pencarian kata kunci
  const filteredParagraphs = useMemo(() => {
    if (!searchQuery.trim()) return paragraphs;
    const q = searchQuery.toLowerCase();
    return paragraphs.filter(p => p.toLowerCase().includes(q));
  }, [paragraphs, searchQuery]);

  const isArabic = (text) => {
    const arabicChars = (text.match(/[\u0600-\u06FF]/g) || []).length;
    return arabicChars > 15 && (arabicChars / text.trim().length) > 0.4;
  };

  return (
    <div className="w-full min-h-full pb-20 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto transition-colors">
      {/* Top Header & Breadcrumb */}
      <div className="pt-6 pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-islamic-200 dark:border-islamic-800/60">
        <button
          onClick={() => navigate(`/surah/${currentSurahNo}`)}
          className="inline-flex items-center gap-2 text-sm font-bold text-emerald-600 dark:text-emerald-400 hover:text-emerald-500 transition-colors"
        >
          <ArrowLeft size={18} />
          <span>Kembali ke Ayat QS {surahMeta.namaLatin}</span>
        </button>

        {/* Prev / Next Ayat Tafsir Navigation */}
        <div className="flex items-center gap-2">
          <button
            disabled={currentAyahNo <= 1}
            onClick={() => navigate(`/surah/${currentSurahNo}/ayat/${currentAyahNo - 1}`)}
            className="px-3 py-1.5 rounded-xl theme-card text-xs font-semibold theme-muted disabled:opacity-30 disabled:cursor-not-allowed hover:text-emerald-600"
          >
            ← Ayat Sebelumnya
          </button>
          <span className="text-xs font-extrabold theme-title px-2">
            Ayat {currentAyahNo}
          </span>
          <button
            disabled={surahMeta.jumlahAyat && currentAyahNo >= surahMeta.jumlahAyat}
            onClick={() => navigate(`/surah/${currentSurahNo}/ayat/${currentAyahNo + 1}`)}
            className="px-3 py-1.5 rounded-xl theme-card text-xs font-semibold theme-muted disabled:opacity-30 disabled:cursor-not-allowed hover:text-emerald-600"
          >
            Ayat Berikutnya →
          </button>
        </div>
      </div>

      {/* Main Title Badge */}
      <div className="mt-6 mb-6">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30 mb-2">
          <BookOpen size={13} className="text-emerald-600 dark:text-emerald-400" />
          <span>Tafsir Ath-Thabari (Jami' al-Bayan 'an Ta'wil Ay al-Qur'an)</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold theme-title">
          Tafsir QS {surahMeta.namaLatin} [{currentSurahNo}]: Ayat {currentAyahNo}
        </h1>
      </div>

      {/* 1. Ayat Recap Box */}
      {currentAyat && (
        <div className="mb-6 rounded-2xl p-6 theme-card shadow-sm">
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-islamic-200 dark:border-islamic-800/40">
            <span className="text-xs font-bold text-emerald-700 dark:text-emerald-400">
              Teks Ayat & Terjemahan
            </span>
            <button
              onClick={handleCopyTafsir}
              className="text-xs theme-muted hover:text-emerald-600 flex items-center gap-1.5 transition-colors font-medium"
            >
              {copied ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
              <span>{copied ? "Tersalin!" : "Salin"}</span>
            </button>
          </div>

          <p className="quran-text font-quran text-2xl sm:text-3xl font-bold theme-arabic mb-4 leading-loose" dir="rtl">
            {currentAyat.teks_arab}
          </p>

          <p className="text-sm sm:text-base theme-body leading-relaxed font-sans pt-2 border-t border-islamic-200 dark:border-islamic-800/40">
            <span className="font-bold text-emerald-700 dark:text-emerald-400 mr-2">Terjemahan:</span>
            {currentAyat.terjemahan ? currentAyat.terjemahan.replace(/<sup[^>]*>.*?<\/sup>/g, '') : "Memuat terjemahan..."}
          </p>
        </div>
      )}

      {/* 2. Tafsir Content Section */}
      {loading ? (
        <div className="p-16 text-center theme-muted flex flex-col items-center justify-center gap-3">
          <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm font-medium">Memuat takwil dan riwayat Ath-Thabari...</p>
        </div>
      ) : !fullTextData && units.length === 0 ? (
        <div className="p-10 text-center rounded-2xl theme-card shadow-sm">
          <Info size={36} className="mx-auto text-amber-500 mb-3" />
          <h3 className="text-base font-bold theme-title mb-1">Tafsir Belum Tersedia dalam Database</h3>
          <p className="text-xs max-w-md mx-auto theme-muted mb-5 leading-relaxed">
            Data takwil Ath-Thabari untuk ayat ini belum dimasukkan atau berada di luar cakupan volume aktif (QS 11-24). Anda tetap dapat bertanya langsung kepada Asisten AI.
          </p>
          <button
            onClick={() => handleAskAI()}
            className="px-5 py-2.5 rounded-xl font-bold text-xs bg-emerald-600 hover:bg-emerald-500 text-white shadow-md inline-flex items-center gap-2"
          >
            <MessageSquare size={16} />
            <span>Tanyakan Penafsiran Ayat Ini ke AI Chatbot</span>
          </button>
        </div>
      ) : (
        /* ================= MODE 2: NASKAH LENGKAP (ASLI) ================= */
        <motion.div 
          key="full-mode"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="rounded-3xl p-6 sm:p-8 theme-card shadow-md"
        >
          {/* Card Top Action Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 mb-6 border-b border-islamic-200 dark:border-islamic-800/40">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 flex items-center justify-center flex-shrink-0">
                <BookOpen size={20} />
              </div>
              <div>
                <h3 className="text-base sm:text-lg font-bold theme-title">
                  Naskah Lengkap Tafsir Ath-Thabari
                </h3>
                <p className="text-xs theme-muted">
                  Teks asli bersambung tanpa pemisahan unit (*Kitab Jami' al-Bayan*)
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2.5 self-end sm:self-auto">
              {/* Font Size Selector */}
              <div className="flex items-center rounded-xl p-1 bg-islamic-100/60 dark:bg-islamic-900/60 border border-islamic-200 dark:border-islamic-800/40">
                <button
                  onClick={() => setFontSize('compact')}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all ${
                    fontSize === 'compact' ? 'bg-emerald-600 text-white' : 'theme-muted hover:text-emerald-600'
                  }`}
                  title="Ukuran font kecil"
                >
                  A-
                </button>
                <button
                  onClick={() => setFontSize('normal')}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all ${
                    fontSize === 'normal' ? 'bg-emerald-600 text-white' : 'theme-muted hover:text-emerald-600'
                  }`}
                  title="Ukuran font normal"
                >
                  A
                </button>
                <button
                  onClick={() => setFontSize('large')}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all ${
                    fontSize === 'large' ? 'bg-emerald-600 text-white' : 'theme-muted hover:text-emerald-600'
                  }`}
                  title="Ukuran font besar"
                >
                  A+
                </button>
              </div>

              {/* Copy Full Text */}
              <button
                onClick={handleCopyFullTafsir}
                className="px-3 py-1.5 rounded-xl border border-islamic-200 dark:border-islamic-800/60 text-xs font-semibold theme-muted hover:text-emerald-600 flex items-center gap-1.5 transition-colors"
              >
                {fullCopied ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
                <span>{fullCopied ? "Tersalin!" : "Salin Naskah"}</span>
              </button>
            </div>
          </div>

          {/* Quick Search inside Full Text */}
          <div className="mb-6 relative">
            <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 theme-muted" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cari kata kunci dalam naskah ini (mis. Mujahid, Qatadah, takwil, riwayat)..."
              className="w-full pl-9 pr-8 py-2 rounded-xl text-xs theme-input border border-islamic-200 dark:border-islamic-800/60 focus:outline-none focus:border-emerald-500 transition-colors"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-xs theme-muted hover:text-emerald-500"
              >
                ✕
              </button>
            )}
          </div>

          {searchQuery && (
            <div className="mb-4 text-xs theme-muted flex items-center justify-between">
              <span>Menampilkan {filteredParagraphs.length} dari {paragraphs.length} bagian yang cocok:</span>
              <button 
                onClick={() => setSearchQuery('')}
                className="text-emerald-600 dark:text-emerald-400 font-bold hover:underline"
              >
                Reset pencarian
              </button>
            </div>
          )}

          {/* Full Text Paragraphs */}
          <div className="theme-card-secondary p-5 sm:p-7 rounded-2xl flex flex-col gap-4">
            {paragraphs.length === 0 ? (
              <div className="py-12 text-center theme-muted text-xs flex flex-col items-center justify-center gap-3">
                <div className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                <p>Sedang memuat naskah asli Tafsir Ath-Thabari...</p>
              </div>
            ) : filteredParagraphs.length === 0 ? (
              <div className="py-8 text-center theme-muted text-xs">
                Tidak ada teks yang cocok dengan kata kunci "{searchQuery}".
              </div>
            ) : (
              filteredParagraphs.map((para, idx) => {
                const arabic = isArabic(para);
                return (
                  <p
                    key={idx}
                    dir={arabic ? 'rtl' : 'ltr'}
                    className={`leading-relaxed ${
                      arabic 
                        ? 'font-quran text-xl sm:text-2xl font-bold theme-arabic py-2 text-right leading-loose' 
                        : fontSize === 'compact'
                        ? 'text-xs sm:text-sm theme-body font-sans'
                        : fontSize === 'large'
                        ? 'text-base sm:text-lg theme-body font-sans leading-loose'
                        : 'text-sm sm:text-base theme-body font-sans'
                    }`}
                  >
                    {para}
                  </p>
                );
              })
            )}
          </div>

          {/* Bottom CTA to Chatbot */}
          <div className="mt-8 pt-6 border-t border-islamic-200 dark:border-islamic-800/40 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="text-xs theme-muted">
              Ingin merangkum, mencari faedah fikih, atau menanyakan perawi dari naskah ini?
            </div>
            <button
              onClick={() => handleAskAI()}
              className="px-5 py-2.5 rounded-xl font-bold text-xs sm:text-sm bg-gradient-to-r from-emerald-600 to-islamic-600 hover:from-emerald-500 hover:to-islamic-500 text-white shadow-md transition-all inline-flex items-center justify-center gap-2"
            >
              <MessageSquare size={16} />
              <span>Tanyakan Seluruh Naskah ke AI Chatbot</span>
            </button>
          </div>
        </motion.div>
      )}
    </div>
  );
}
