import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Search, BookOpen, Compass, 
  ArrowRight, Flame, Layers
} from 'lucide-react';
import { getSurahList } from '../api';
import { ALL_SURAHS } from '../data/surahData';

export default function HomePage() {
  const navigate = useNavigate();
  const [surahs, setSurahs] = useState(ALL_SURAHS);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState('thabari'); // 'thabari' | 'all'
  const [filterRevelation, setFilterRevelation] = useState('all'); // 'all' | 'Makkiyyah' | 'Madaniyyah'

  useEffect(() => {
    loadSurahData();
  }, []);

  const loadSurahData = async () => {
    try {
      setLoading(true);
      const data = await getSurahList();
      if (data && data.length > 0) {
        setSurahs(data);
      }
    } catch (e) {
      console.error("Gagal memuat surah:", e);
    } finally {
      setLoading(false);
    }
  };

  // Quick featured surahs from Ath-Thabari collection (QS 11-24)
  const featuredSurahs = useMemo(() => {
    return [
      { no: 11, name: 'Hud', arab: 'هُود', desc: 'Ayat 1-123' },
      { no: 12, name: 'Yusuf', arab: 'يُوسُف', desc: 'Ayat 1-111' },
      { no: 14, name: 'Ibrahim', arab: 'إِبْرَاهِيم', desc: 'Ayat 1-52' },
      { no: 18, name: 'Al-Kahf', arab: 'الكَهْف', desc: 'Ayat 1-110' },
      { no: 19, name: 'Maryam', arab: 'مَرْيَم', desc: 'Ayat 1-98' },
      { no: 24, name: 'An-Nur', arab: 'النُّور', desc: 'Ayat 1-64' },
    ];
  }, []);

  // Filtered list
  const filteredSurahs = useMemo(() => {
    return surahs.filter(s => {
      // Tab filter
      if (activeTab === 'thabari' && !s.hasTafsirThabari && !(s.no_surah >= 11 && s.no_surah <= 24)) {
        return false;
      }

      // Revelation filter
      if (filterRevelation !== 'all' && s.revelation_place !== filterRevelation && s.tempatTurun !== filterRevelation) {
        return false;
      }

      // Search query
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase().trim();
      const numMatch = String(s.no_surah || s.nomor) === q;
      const nameMatch = (s.nama_surah || s.namaLatin || '').toLowerCase().includes(q);
      const artiMatch = (s.arti_surah || s.arti || '').toLowerCase().includes(q);
      const arabMatch = (s.nama_surah_arab || s.nama || '').includes(q);

      return numMatch || nameMatch || artiMatch || arabMatch;
    });
  }, [surahs, activeTab, filterRevelation, searchQuery]);

  return (
    <div className="w-full min-h-full pb-16 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto transition-colors">
      {/* Top Banner / Feature Card (Inspired by Image 3 "Coba Fitur Dua") */}
      <motion.div 
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="mt-6 mb-8 rounded-3xl p-6 sm:p-7 relative overflow-hidden transition-all duration-300 shadow-md border
          bg-gradient-to-r from-emerald-800 via-islamic-800 to-islamic-900 border-emerald-700/40 text-white
          dark:from-islamic-900 dark:via-islamic-850 dark:to-islamic-800 dark:border-islamic-700/50"
      >
        <div className="absolute right-3 top-2 bottom-0 w-1/3 opacity-10 pointer-events-none flex items-center justify-center font-quran text-8xl text-emerald-200 select-none">
          📖
        </div>

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-5">
          <div className="max-w-xl">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-200 border border-emerald-500/30 mb-3">
              <BookOpen size={13} className="text-emerald-300" />
              <span>Tafsir Ath-Thabari (Jami' al-Bayan)</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white mb-2">
              Jelajahi Takwil Surah Hud hingga An-Nur
            </h2>
            <p className="text-xs sm:text-sm text-emerald-100/90 leading-relaxed">
              Kajian mendalam dengan rujukan riwayat shahih, aqwal para shahabat & tabi'in, serta analisis lughawi dan tarjih Imam Ath-Thabari.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/chat')}
              className="px-5 py-2.5 rounded-xl font-bold text-xs sm:text-sm bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-white shadow-md transition-all flex items-center gap-2"
            >
              <span>Tanya Chatbot</span>
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </motion.div>

      {/* Tabs Navigation (Inspired by Image 3: "Baca", "Belajar", dsb) */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 border-b border-islamic-200 dark:border-islamic-800/60 pb-4">
        <div className="flex items-center gap-1.5 p-1 rounded-2xl theme-card-secondary border border-emerald-500/20 self-start">
          <button
            onClick={() => setActiveTab('thabari')}
            className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all ${
              activeTab === 'thabari'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'theme-muted hover:text-emerald-600 dark:hover:text-emerald-300'
            }`}
          >
            Tafsir Ath-Thabari (QS 11-24)
          </button>
          <button
            onClick={() => setActiveTab('all')}
            className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all ${
              activeTab === 'all'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'theme-muted hover:text-emerald-600 dark:hover:text-emerald-300'
            }`}
          >
            Semua Surah (114)
          </button>
        </div>

        {/* Revelation Filter */}
        <div className="flex items-center gap-1.5 text-xs">
          <span className="theme-muted font-medium hidden sm:inline">Tempat Turun:</span>
          {['all', 'Makkiyyah', 'Madaniyyah'].map(type => (
            <button
              key={type}
              onClick={() => setFilterRevelation(type)}
              className={`px-3 py-1.5 rounded-xl font-semibold transition-all border ${
                filterRevelation === type
                  ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-300 border-emerald-500/40'
                  : 'bg-transparent theme-muted border-transparent hover:theme-card'
              }`}
            >
              {type === 'all' ? 'Semua' : type}
            </button>
          ))}
        </div>
      </div>

      {/* Section "Terbaru / Populer" (Quick Chips - Inspired by Image 3) */}
      <div className="mb-7">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
            <Flame size={14} className="text-amber-500 dark:text-amber-400" />
            <span>Koleksi Ath-Thabari Populer</span>
          </h3>
          <span className="text-[11px] theme-muted">Klik untuk langsung membaca ayat</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2.5">
          {featuredSurahs.map(s => (
            <button
              key={s.no}
              onClick={() => navigate(`/surah/${s.no}`)}
              className="p-3 rounded-2xl theme-card text-left transition-all duration-200 group hover:shadow-md"
            >
              <div className="flex justify-between items-center mb-1">
                <span className="font-quran text-lg font-bold text-emerald-600 dark:text-emerald-300 group-hover:text-amber-500 dark:group-hover:text-gold-300 transition-colors">
                  {s.arab}
                </span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded theme-pill">
                  {s.no}
                </span>
              </div>
              <div className="font-bold text-xs theme-title group-hover:text-emerald-600 dark:group-hover:text-emerald-300 truncate">
                {s.name}
              </div>
              <div className="text-[11px] theme-muted">
                {s.desc}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Search Input Bar */}
      <div className="mb-6 relative">
        <div className="relative flex items-center">
          <Search size={18} className="absolute left-4 text-emerald-500 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Cari surah (contoh: Hud, 11, Yusuf, An-Nur, atau nama Arab)..."
            className="w-full pl-11 pr-4 py-3.5 rounded-2xl text-sm transition-all outline-none theme-input shadow-sm focus:ring-2 focus:ring-emerald-500/20"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-4 text-xs font-semibold theme-muted hover:text-emerald-500"
            >
              Hapus
            </button>
          )}
        </div>
      </div>

      {/* Surah List Section Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-bold theme-title flex items-center gap-2">
          <BookOpen size={18} className="text-emerald-600 dark:text-emerald-400" />
          <span>Daftar Surat</span>
          <span className="text-xs font-normal theme-muted">
            ({filteredSurahs.length} surah)
          </span>
        </h2>
      </div>

      {/* Surah Cards: MEMANJANG (Horizontal elongated cards as requested in Image 3) */}
      <div className="flex flex-col gap-3">
        {filteredSurahs.map((surah) => {
          const noSurah = surah.no_surah || surah.nomor;
          const namaSurah = surah.nama_surah || surah.namaLatin;
          const namaArab = surah.nama_surah_arab || surah.nama;
          const artiSurah = surah.arti_surah || surah.arti;
          const tempatTurun = surah.revelation_place || surah.tempatTurun;
          const jumlahAyat = surah.jumlah_ayat || surah.jumlahAyat;
          const hasThabari = surah.hasTafsirThabari || (noSurah >= 11 && noSurah <= 24);

          return (
            <motion.div
              key={noSurah}
              whileHover={{ y: -2, transition: { duration: 0.15 } }}
              onClick={() => navigate(`/surah/${noSurah}`)}
              className="group cursor-pointer rounded-2xl p-4 sm:p-5 theme-card shadow-sm hover:shadow-md flex items-center justify-between"
            >
              {/* Left Column: Number Badge + Names & Subtitles */}
              <div className="flex items-center gap-4 sm:gap-5 flex-1 min-w-0 pr-4">
                {/* Surah Number Icon Badge */}
                <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-xl flex items-center justify-center font-bold text-sm sm:text-base flex-shrink-0 transition-colors theme-pill group-hover:bg-emerald-600 group-hover:text-white group-hover:border-emerald-500">
                  {noSurah}
                </div>

                {/* Surah Latin Name + Indonesian Meaning */}
                <div className="flex flex-col min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-extrabold text-base sm:text-lg theme-title group-hover:text-emerald-600 dark:group-hover:text-emerald-300 transition-colors truncate">
                      {namaSurah}
                    </h3>
                    {hasThabari && (
                      <span className="inline-flex items-center gap-1.5 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30">
                        <BookOpen size={10} className="text-emerald-600 dark:text-emerald-400" />
                        <span>Tafsir Ath-Thabari</span>
                      </span>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2 text-xs theme-muted mt-0.5">
                    <span className="font-semibold text-emerald-700 dark:text-emerald-300">{artiSurah}</span>
                    <span>•</span>
                    <span>{tempatTurun}</span>
                    <span>•</span>
                    <span>{jumlahAyat} Ayat</span>
                  </div>
                </div>
              </div>

              {/* Right Column: Arabic Calligraphy Name & Chevron */}
              <div className="flex items-center gap-3 sm:gap-5 flex-shrink-0">
                <span className="font-quran text-2xl sm:text-3xl font-bold theme-arabic group-hover:text-amber-600 dark:group-hover:text-gold-300 transition-colors select-none" dir="rtl">
                  {namaArab}
                </span>
                <div className="w-8 h-8 rounded-full flex items-center justify-center theme-muted group-hover:text-emerald-600 dark:group-hover:text-emerald-300 group-hover:translate-x-0.5 transition-all">
                  <ArrowRight size={18} />
                </div>
              </div>
            </motion.div>
          );
        })}

        {filteredSurahs.length === 0 && (
          <div className="p-12 text-center rounded-2xl theme-card border-dashed">
            <BookOpen size={36} className="mx-auto text-emerald-500 mb-3" />
            <p className="text-base font-bold theme-title mb-1">Surah tidak ditemukan</p>
            <p className="text-xs theme-muted">
              Coba kata kunci lain atau periksa filter yang sedang aktif.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
