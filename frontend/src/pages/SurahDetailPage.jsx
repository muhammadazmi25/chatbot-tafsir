import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  ArrowLeft, BookOpen, Volume2, VolumeX, 
  Copy, Check, ArrowRight, Search
} from 'lucide-react';
import { getAyatList } from '../api';
import { getSurahByNumber, ALL_SURAHS } from '../data/surahData';

export default function SurahDetailPage() {
  const { surahNo } = useParams();
  const navigate = useNavigate();
  const currentSurahNo = parseInt(surahNo, 10);
  
  const surahMeta = getSurahByNumber(currentSurahNo) || {
    nomor: currentSurahNo,
    namaLatin: `Surah ${currentSurahNo}`,
    nama: '',
    arti: '',
    tempatTurun: '',
    jumlahAyat: 0,
    hasTafsirThabari: currentSurahNo >= 11 && currentSurahNo <= 24,
  };

  const [ayatList, setAyatList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Audio state
  const [playingAyah, setPlayingAyah] = useState(null);
  const audioRef = useRef(null);

  // Copy state
  const [copiedAyah, setCopiedAyah] = useState(null);

  // Search/Jump within surah
  const [jumpAyah, setJumpAyah] = useState('');
  const [searchAyahText, setSearchAyahText] = useState('');

  // Display toggles
  const [showLatin, setShowLatin] = useState(true);
  const [arabicFontSize, setArabicFontSize] = useState('text-3xl');

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    loadAyat(currentSurahNo);
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
  }, [currentSurahNo]);

  const loadAyat = async (num) => {
    try {
      setLoading(true);
      setError(null);
      const data = await getAyatList(num);
      setAyatList(data);
    } catch (err) {
      console.error("Gagal memuat ayat:", err);
      setError("Gagal memuat daftar ayat. Silakan coba kembali.");
    } finally {
      setLoading(false);
    }
  };

  const handlePlayAudio = (ayahNo, audioUrl) => {
    if (playingAyah === ayahNo) {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      setPlayingAyah(null);
      return;
    }

    if (!audioUrl) return;

    if (audioRef.current) {
      audioRef.current.pause();
    }

    const audio = new Audio(audioUrl);
    audioRef.current = audio;
    audio.play();
    setPlayingAyah(ayahNo);

    audio.onended = () => {
      setPlayingAyah(null);
    };
    audio.onerror = () => {
      setPlayingAyah(null);
    };
  };

  const handleCopyAyah = (ayat) => {
    const textToCopy = `${ayat.teks_arab}\n\n"${ayat.terjemahan}"\n(QS. ${surahMeta.namaLatin} [${currentSurahNo}]: ${ayat.no_ayat})`;
    navigator.clipboard.writeText(textToCopy);
    setCopiedAyah(ayat.no_ayat);
    setTimeout(() => setCopiedAyah(null), 2000);
  };

  const handleJumpToAyah = (e) => {
    e.preventDefault();
    const target = parseInt(jumpAyah, 10);
    if (!target) return;
    const el = document.getElementById(`ayah-${target}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const filteredAyat = ayatList.filter(a => {
    if (!searchAyahText.trim()) return true;
    const q = searchAyahText.toLowerCase();
    const numMatch = String(a.no_ayat) === q;
    const arabMatch = a.teks_arab?.includes(q);
    const latinMatch = a.teks_latin?.toLowerCase().includes(q);
    const idMatch = a.terjemahan?.toLowerCase().includes(q);
    return numMatch || arabMatch || latinMatch || idMatch;
  });

  return (
    <div className="w-full min-h-full pb-20 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto transition-colors">
      {/* Top Breadcrumb & Controls Bar */}
      <div className="pt-6 pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-islamic-200 dark:border-islamic-800/60">
        <button
          onClick={() => navigate('/')}
          className="inline-flex items-center gap-2 text-sm font-bold text-emerald-600 dark:text-emerald-400 hover:text-emerald-500 transition-colors"
        >
          <ArrowLeft size={18} />
          <span>Kembali ke Daftar Surah</span>
        </button>

        {/* Quick Surah Switcher */}
        <div className="flex items-center gap-3">
          <label className="text-xs theme-muted hidden sm:inline font-medium">Pindah Surah:</label>
          <select
            value={currentSurahNo}
            onChange={(e) => navigate(`/surah/${e.target.value}`)}
            className="px-3 py-1.5 rounded-xl text-xs font-semibold theme-input outline-none focus:ring-1 focus:ring-emerald-500"
          >
            {ALL_SURAHS.map(s => (
              <option key={s.nomor} value={s.nomor} className="bg-white dark:bg-islamic-900 theme-title">
                {s.nomor}. {s.namaLatin} ({s.nama}) {s.hasTafsirThabari ? '• Ath-Thabari' : ''}
              </option>
            ))}
          </select>

          {/* Prev / Next Surah */}
          <div className="flex items-center gap-1">
            <button
              disabled={currentSurahNo <= 1}
              onClick={() => navigate(`/surah/${currentSurahNo - 1}`)}
              className="p-1.5 rounded-lg theme-card disabled:opacity-30 disabled:cursor-not-allowed hover:text-emerald-600 font-bold"
              title="Surah Sebelumnya"
            >
              ←
            </button>
            <button
              disabled={currentSurahNo >= 114}
              onClick={() => navigate(`/surah/${currentSurahNo + 1}`)}
              className="p-1.5 rounded-lg theme-card disabled:opacity-30 disabled:cursor-not-allowed hover:text-emerald-600 font-bold"
              title="Surah Berikutnya"
            >
              →
            </button>
          </div>
        </div>
      </div>

      {/* Surah Hero Card Header */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="mt-6 mb-8 rounded-3xl p-6 sm:p-8 text-center relative overflow-hidden shadow-md border
          bg-gradient-to-b from-emerald-800 via-islamic-850 to-islamic-900 border-emerald-700/40 text-white
          dark:from-islamic-850 dark:to-islamic-900 dark:border-islamic-700/60"
      >
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-200 border border-emerald-500/30 mb-3">
          <BookOpen size={13} className="text-amber-300" />
          <span>{surahMeta.tempatTurun} • {surahMeta.jumlahAyat} Ayat</span>
          {surahMeta.hasTafsirThabari && (
            <>
              <span>•</span>
              <span className="text-amber-300 font-bold">Tafsir Ath-Thabari Tersedia</span>
            </>
          )}
        </div>

        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white mb-1">
          {surahMeta.namaLatin}
        </h1>
        <p className="text-sm font-medium text-emerald-200 mb-4">
          Artinya: "{surahMeta.arti}"
        </p>

        {/* Big Arabic Calligraphy */}
        <div className="font-quran text-4xl sm:text-5xl font-bold text-amber-300 dark:text-gold-300 my-4 select-none" dir="rtl">
          {surahMeta.nama}
        </div>

        {/* Bismillah (except Surah 9 At-Tawbah) */}
        {currentSurahNo !== 9 && (
          <div className="mt-6 pt-6 border-t border-white/15 dark:border-islamic-700/40">
            <p className="font-quran text-2xl sm:text-3xl font-bold text-emerald-100 select-none" dir="rtl">
              بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ
            </p>
            <p className="text-xs text-emerald-200/80 mt-1 italic">
              Dengan nama Allah Yang Maha Pengasih, Maha Penyayang.
            </p>
          </div>
        )}
      </motion.div>

      {/* Toolbar: Jump to Ayah, Search Ayah, Font Size, Toggle Latin */}
      <div className="mb-6 p-4 rounded-2xl theme-card-secondary flex flex-wrap items-center justify-between gap-4">
        {/* Jump to Ayah */}
        <form onSubmit={handleJumpToAyah} className="flex items-center gap-2 text-xs">
          <span className="theme-muted font-medium">Lompat Ayat:</span>
          <input
            type="number"
            min="1"
            max={surahMeta.jumlahAyat}
            value={jumpAyah}
            onChange={(e) => setJumpAyah(e.target.value)}
            placeholder={`1 - ${surahMeta.jumlahAyat}`}
            className="w-20 px-3 py-1.5 rounded-xl theme-input text-xs outline-none focus:ring-1 focus:ring-emerald-500"
          />
          <button
            type="submit"
            className="px-3.5 py-1.5 rounded-xl font-bold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors"
          >
            Tuju
          </button>
        </form>

        {/* Filter / Search within Surah */}
        <div className="flex-1 max-w-xs relative">
          <input
            type="text"
            value={searchAyahText}
            onChange={(e) => setSearchAyahText(e.target.value)}
            placeholder="Cari kata dalam surah..."
            className="w-full pl-8 pr-3 py-1.5 rounded-xl text-xs theme-input placeholder-islamic-400/50 outline-none focus:ring-1 focus:ring-emerald-500"
          />
          <Search size={14} className="absolute left-2.5 top-2.5 theme-muted" />
        </div>

        {/* Display Toggles */}
        <div className="flex items-center gap-3 text-xs">
          <button
            onClick={() => setShowLatin(!showLatin)}
            className={`px-3 py-1.5 rounded-xl font-semibold border transition-colors ${
              showLatin 
                ? 'bg-emerald-600/15 border-emerald-500/40 text-emerald-700 dark:text-emerald-300'
                : 'theme-card theme-muted'
            }`}
          >
            Latin: {showLatin ? 'ON' : 'OFF'}
          </button>

          <div className="flex items-center gap-1 theme-card p-1 rounded-xl">
            <span className="text-[10px] theme-muted px-1 font-semibold">Arab:</span>
            <button
              onClick={() => setArabicFontSize('text-2xl')}
              className={`px-2 py-0.5 rounded-lg text-xs font-bold ${arabicFontSize === 'text-2xl' ? 'bg-emerald-600 text-white' : 'theme-muted'}`}
            >
              A
            </button>
            <button
              onClick={() => setArabicFontSize('text-3xl')}
              className={`px-2 py-0.5 rounded-lg text-xs font-bold ${arabicFontSize === 'text-3xl' ? 'bg-emerald-600 text-white' : 'theme-muted'}`}
            >
              A+
            </button>
            <button
              onClick={() => setArabicFontSize('text-4xl')}
              className={`px-2 py-0.5 rounded-lg text-xs font-bold ${arabicFontSize === 'text-4xl' ? 'bg-emerald-600 text-white' : 'theme-muted'}`}
            >
              A++
            </button>
          </div>
        </div>
      </div>

      {/* Loading & Error States */}
      {loading && (
        <div className="p-16 text-center theme-muted flex flex-col items-center justify-center gap-3">
          <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm font-medium">Memuat ayat surah {surahMeta.namaLatin}...</p>
        </div>
      )}

      {error && (
        <div className="p-6 text-center rounded-2xl bg-red-950/20 border border-red-800/40 text-red-500 text-sm">
          {error}
        </div>
      )}

      {/* List of Ayah Cards */}
      {!loading && (
        <div className="flex flex-col gap-5">
          {filteredAyat.map((ayat) => {
            const ayahNo = ayat.no_ayat;
            const hasUnits = ayat.jumlah_unit > 0;
            const isPlaying = playingAyah === ayahNo;

            return (
              <motion.div
                id={`ayah-${ayahNo}`}
                key={ayahNo}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-2xl p-5 sm:p-7 theme-card shadow-sm hover:shadow-md transition-all"
              >
                {/* 1. Header of Ayah Card */}
                <div className="flex items-center justify-between pb-4 mb-5 border-b border-islamic-200 dark:border-islamic-800/60">
                  <div className="flex items-center gap-2.5">
                    {/* Ayah Badge */}
                    <div className="w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs theme-pill">
                      {currentSurahNo}:{ayahNo}
                    </div>

                    {/* Ath-Thabari Units Badge */}
                    {hasUnits && (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30">
                        <BookOpen size={11} className="text-emerald-600 dark:text-emerald-400" />
                        <span>{ayat.jumlah_unit} Unit Takwil Ath-Thabari</span>
                      </span>
                    )}
                  </div>

                  {/* Actions: Audio, Copy */}
                  <div className="flex items-center gap-1.5">
                    {ayat.audio && (
                      <button
                        onClick={() => handlePlayAudio(ayahNo, ayat.audio)}
                        className={`p-2 rounded-xl border transition-all text-xs font-semibold flex items-center gap-1.5 ${
                          isPlaying
                            ? 'bg-emerald-600 text-white border-emerald-500 shadow-md animate-pulse'
                            : 'theme-pill hover:bg-emerald-600 hover:text-white'
                        }`}
                        title={isPlaying ? "Jeda Audio" : "Putar Qari Misyari Rasyid"}
                      >
                        {isPlaying ? <VolumeX size={15} /> : <Volume2 size={15} />}
                        <span className="hidden sm:inline">{isPlaying ? 'Jeda' : 'Putar'}</span>
                      </button>
                    )}

                    <button
                      onClick={() => handleCopyAyah(ayat)}
                      className="p-2 rounded-xl theme-pill hover:bg-emerald-600 hover:text-white transition-all"
                      title="Salin Ayat & Terjemahan"
                    >
                      {copiedAyah === ayahNo ? <Check size={15} className="text-emerald-500" /> : <Copy size={15} />}
                    </button>
                  </div>
                </div>

                {/* 2. Arabic Text */}
                <div className="my-5">
                  <p 
                    className={`quran-text font-quran ${arabicFontSize} font-bold theme-arabic selection:bg-emerald-500 selection:text-white leading-loose`}
                    dir="rtl"
                  >
                    {ayat.teks_arab}
                  </p>
                </div>

                {/* 3. Latin Transliteration */}
                {showLatin && ayat.teks_latin && (
                  <div className="mb-4 text-xs sm:text-sm text-emerald-700 dark:text-emerald-300/90 italic font-medium leading-relaxed">
                    {ayat.teks_latin}
                  </div>
                )}

                {/* 4. Indonesian Translation (Terjemahan Kemenag) */}
                <div className="mb-6 pt-3 text-sm sm:text-base theme-body leading-relaxed font-sans border-t border-islamic-200 dark:border-islamic-800/40">
                  <span className="font-bold text-emerald-700 dark:text-emerald-400 mr-2">Artinya:</span>
                  {ayat.terjemahan ? ayat.terjemahan.replace(/<sup[^>]*>.*?<\/sup>/g, '') : "Terjemahan belum tersedia."}
                </div>

                {/* 5. TAFSIR NAVIGATION BUTTON (MANDATORY USER REQUIREMENT) */}
                {/* "dan dibawah detaiil ayat dan terjemahan nya ada tombol untuk mengarahkan ke tafsir nya dan berpindah page." */}
                <div className="pt-4 border-t border-islamic-200 dark:border-islamic-800/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="text-xs theme-muted flex items-center gap-1.5">
                    <BookOpen size={14} className="text-amber-500 dark:text-gold-300" />
                    <span>Rujukan: Kitab Jami' al-Bayan 'an Ta'wil Ay al-Qur'an</span>
                  </div>

                  <button
                    onClick={() => navigate(`/surah/${currentSurahNo}/ayat/${ayahNo}`)}
                    className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs sm:text-sm transition-all duration-200 shadow-md group
                      bg-gradient-to-r from-emerald-600 to-islamic-600 hover:from-emerald-500 hover:to-islamic-500 text-white hover:scale-[1.01]"
                  >
                    <BookOpen size={15} />
                    <span>Buka Tafsir Ath-Thabari (Ayat {ayahNo})</span>
                    <ArrowRight size={15} className="group-hover:translate-x-1 transition-transform" />
                  </button>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
