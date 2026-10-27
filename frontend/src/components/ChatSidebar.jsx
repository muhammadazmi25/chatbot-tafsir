import React, { useState, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { 
  SquarePen, MessageSquare, Trash2, 
  Search, X, History, Loader2
} from 'lucide-react';
import { getSessions, deleteSession } from '../api';

export default function ChatSidebar({ 
  isOpen, 
  onToggle, 
  currentSessionUuid, 
  onNewChat, 
  refreshTrigger 
}) {
  const [sessions, setSessions] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [sessionToDelete, setSessionToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    loadSessions();
  }, [refreshTrigger, currentSessionUuid]);

  // Handle ESC key to dismiss modal
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && sessionToDelete && !isDeleting) {
        setSessionToDelete(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [sessionToDelete, isDeleting]);

  const loadSessions = async () => {
    try {
      const data = await getSessions();
      setSessions(data || []);
    } catch (e) {
      console.error("Gagal memuat riwayat sesi:", e);
    }
  };

  const handleDeleteClick = (e, session) => {
    e.preventDefault();
    e.stopPropagation();
    setSessionToDelete(session);
  };

  const confirmDelete = async () => {
    if (!sessionToDelete) return;
    setIsDeleting(true);
    try {
      await deleteSession(sessionToDelete.session_uuid);
      if (currentSessionUuid === sessionToDelete.session_uuid) {
        onNewChat();
      } else {
        loadSessions();
      }
      setSessionToDelete(null);
    } catch (err) {
      console.error("Gagal menghapus percakapan:", err);
    } finally {
      setIsDeleting(false);
    }
  };

  const filteredSessions = useMemo(() => {
    if (!searchQuery.trim()) return sessions;
    const q = searchQuery.toLowerCase();
    return sessions.filter(s => (s.title || '').toLowerCase().includes(q));
  }, [sessions, searchQuery]);

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div 
          onClick={onToggle}
          className="fixed inset-0 bg-black/50 backdrop-blur-xs z-40 md:hidden transition-opacity"
          aria-hidden="true"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-50 md:z-auto h-full flex flex-col theme-card-secondary border-r border-islamic-200 dark:border-islamic-800/80 transition-all duration-200 ease-in-out flex-shrink-0 select-none ${
          isOpen 
            ? 'w-64 sm:w-72 translate-x-0' 
            : 'w-0 -translate-x-full md:translate-x-0 md:w-0 overflow-hidden pointer-events-none border-r-0'
        }`}
      >
        {/* Header Bar: Actions & Toggle */}
        <div className="h-12 px-3 border-b border-islamic-200 dark:border-islamic-800/80 flex items-center justify-between gap-1 flex-shrink-0">
          <div className="flex items-center gap-1.5 text-xs font-bold theme-title pl-1">
            <History size={15} className="text-emerald-600 dark:text-emerald-400" />
            <span>Riwayat Chat</span>
          </div>

          <div className="flex items-center gap-1">
            {/* New Chat icon */}
            <button
              onClick={onNewChat}
              className="p-1.5 rounded-lg theme-muted hover:theme-title hover:bg-emerald-500/10 transition-colors"
              title="Percakapan Baru"
            >
              <SquarePen size={16} />
            </button>

            {/* Close Toggle (Hanya untuk mobile, di desktop ditutup via tombol 'Tutup Panel' di main bar) */}
            <button
              onClick={onToggle}
              className="md:hidden p-1.5 rounded-lg theme-muted hover:theme-title hover:bg-emerald-500/10 transition-colors"
              title="Tutup Sidebar"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Quick New Chat Button */}
        <div className="p-2.5 pb-1.5 flex-shrink-0">
          <button
            onClick={onNewChat}
            className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl font-bold text-xs bg-emerald-600 hover:bg-emerald-500 text-white shadow-xs transition-all"
          >
            <SquarePen size={14} />
            <span>Chat Baru</span>
          </button>
        </div>

        {/* Search Bar */}
        <div className="px-2.5 py-1.5 flex-shrink-0">
          <div className="relative flex items-center">
            <Search size={13} className="absolute left-2.5 theme-muted pointer-events-none opacity-60" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cari topik riwayat..."
              className="w-full pl-7 pr-2.5 py-1.5 rounded-lg text-[11px] theme-input outline-none focus:ring-1 focus:ring-emerald-500 placeholder-islamic-400/50"
            />
          </div>
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto scrollbar-thin px-2 py-1 flex flex-col gap-0.5">
          {filteredSessions.map(s => {
            const isActive = currentSessionUuid === s.session_uuid;
            return (
              <Link
                key={s.id}
                to={`/chat/${s.session_uuid}`}
                className={`group relative flex items-center gap-2 px-2.5 py-2 rounded-lg transition-colors text-xs ${
                  isActive
                    ? 'bg-emerald-600/15 text-emerald-800 dark:text-emerald-200 font-bold border-l-2 border-emerald-500'
                    : 'theme-muted hover:theme-title hover:bg-emerald-500/5'
                }`}
              >
                <MessageSquare 
                  size={14} 
                  className={`flex-shrink-0 ${isActive ? 'text-emerald-600 dark:text-emerald-400' : 'opacity-60'}`} 
                />
                <span className="truncate flex-1 text-[12px]">
                  {s.title || 'Percakapan Baru'}
                </span>
                
                {/* Delete button on hover */}
                <button 
                  onClick={(e) => handleDeleteClick(e, s)}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-500 transition-opacity rounded"
                  title="Hapus Percakapan"
                  aria-label="Hapus percakapan"
                >
                  <Trash2 size={12} />
                </button>
              </Link>
            );
          })}

          {filteredSessions.length === 0 && (
            <div className="text-center theme-muted text-[11px] py-12 px-2 opacity-60">
              {searchQuery ? "Tidak ada riwayat yang cocok" : "Belum ada riwayat percakapan"}
            </div>
          )}
        </div>
      </aside>

      {/* Modal Dialog Konfirmasi Hapus Percakapan */}
      {typeof document !== 'undefined' && createPortal(
        <AnimatePresence>
          {sessionToDelete && (
            <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
              {/* Backdrop */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => !isDeleting && setSessionToDelete(null)}
                className="fixed inset-0 bg-black/60 dark:bg-black/75 backdrop-blur-xs transition-opacity"
              />

              {/* Dialog Card */}
              <motion.div
                initial={{ opacity: 0, scale: 0.94, y: 8 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.94, y: 8 }}
                transition={{ type: "spring", duration: 0.22, bounce: 0.1 }}
                className="relative w-full max-w-sm rounded-2xl theme-card p-5 shadow-2xl border border-islamic-200 dark:border-islamic-700/80 overflow-hidden z-10"
                onClick={(e) => e.stopPropagation()}
              >
                {/* Subtle Ambient Glow */}
                <div className="absolute -top-10 -left-10 w-24 h-24 bg-rose-500/15 rounded-full blur-2xl pointer-events-none" />
                <div className="absolute -bottom-10 -right-10 w-24 h-24 bg-emerald-500/10 rounded-full blur-2xl pointer-events-none" />

                {/* Close Button */}
                <button
                  type="button"
                  onClick={() => !isDeleting && setSessionToDelete(null)}
                  disabled={isDeleting}
                  className="absolute top-3.5 right-3.5 p-1.5 rounded-lg theme-muted hover:theme-title hover:bg-emerald-500/10 transition-colors disabled:opacity-40"
                  aria-label="Tutup dialog"
                >
                  <X size={15} />
                </button>

                <div className="flex items-start gap-3.5">
                  {/* Danger Icon Badge */}
                  <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-rose-500/10 dark:bg-rose-500/20 border border-rose-500/20 text-rose-500 flex items-center justify-center shadow-xs">
                    <Trash2 size={19} className="stroke-[2.2]" />
                  </div>

                  <div className="flex-1 min-w-0 pr-3">
                    <h3 className="text-sm font-bold theme-title leading-snug">
                      Hapus Percakapan?
                    </h3>
                    <p className="text-[12px] theme-muted mt-1 leading-relaxed">
                      Percakapan berikut akan dihapus permanen dari riwayat Anda:
                    </p>
                    <div className="mt-2.5 px-3 py-2 rounded-xl bg-emerald-500/5 dark:bg-emerald-950/40 border border-emerald-500/15 text-[11px] font-medium theme-title truncate">
                      "{sessionToDelete.title || 'Percakapan Baru'}"
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="mt-5 flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setSessionToDelete(null)}
                    disabled={isDeleting}
                    className="px-3.5 py-2 rounded-xl text-xs font-semibold theme-muted hover:theme-title hover:bg-emerald-500/10 border border-islamic-300 dark:border-islamic-700/60 transition-colors disabled:opacity-50 cursor-pointer"
                  >
                    Batal
                  </button>
                  <button
                    type="button"
                    onClick={confirmDelete}
                    disabled={isDeleting}
                    className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-500 active:bg-rose-700 text-white shadow-md shadow-rose-900/25 transition-all flex items-center gap-1.5 disabled:opacity-60 cursor-pointer"
                  >
                    {isDeleting ? (
                      <>
                        <Loader2 size={13} className="animate-spin" />
                        <span>Menghapus...</span>
                      </>
                    ) : (
                      <>
                        <Trash2 size={13} />
                        <span>Hapus Percakapan</span>
                      </>
                    )}
                  </button>
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>,
        document.body
      )}
    </>
  );
}
