import React from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { BookOpen, MessageSquare } from 'lucide-react';
import { ThemeProvider } from './context/ThemeContext';
import ThemeToggle from './components/ThemeToggle';
import HomePage from './pages/HomePage';
import SurahDetailPage from './pages/SurahDetailPage';
import AyatTafsirPage from './pages/AyatTafsirPage';
import ChatPage from './pages/ChatPage';

function Header() {
  const location = useLocation();
  const isChat = location.pathname.startsWith('/chat');

  return (
    <header className="sticky top-0 z-50 flex items-center justify-between px-4 sm:px-6 h-[64px] theme-header backdrop-blur-md transition-colors flex-shrink-0">
      {/* Brand Identity */}
      <Link to="/" className="flex items-center gap-3 no-underline group">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center font-bold text-lg shadow-md transition-transform group-hover:scale-105 bg-gradient-to-br from-emerald-600 to-islamic-700 text-white border border-emerald-500/30">
          <BookOpen size={18} className="text-gold-200" />
        </div>
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <h1 className="text-base sm:text-lg font-extrabold tracking-tight theme-title leading-tight">
              Tafsir Ath-Thabari
            </h1>
            <span className="hidden md:inline-flex items-center text-[10px] font-bold px-2 py-0.5 rounded-full theme-pill">
              QS Hud - An-Nur
            </span>
          </div>
          <p className="text-[11px] theme-muted font-medium">Kitab Jami' al-Bayan & Asisten Cerdas</p>
        </div>
      </Link>

      {/* Right Actions: Navigation, Chatbot CTA & Theme Toggle */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Nav link: Surah */}
        <Link
          to="/"
          className={`px-3 py-1.5 rounded-xl text-xs sm:text-sm font-semibold transition-all ${
            !isChat 
              ? 'bg-emerald-600/20 text-emerald-600 dark:text-emerald-400 font-bold border border-emerald-500/30' 
              : 'theme-muted hover:text-emerald-600 dark:hover:text-emerald-400'
          }`}
        >
          Daftar Surah
        </Link>

        {/* Nav link: Chatbot AI */}
        <Link 
          to="/chat" 
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-bold transition-all shadow-sm ${
            isChat
              ? 'bg-gradient-to-r from-emerald-600 to-islamic-600 text-white ring-2 ring-emerald-500/40'
              : 'bg-gradient-to-r from-emerald-600 to-islamic-600 hover:from-emerald-500 hover:to-islamic-500 text-white'
          }`}
        >
          <MessageSquare size={15} />
          <span>Tanya Chatbot</span>
        </Link>

        {/* Theme Toggle Button */}
        <ThemeToggle showLabel={false} />
      </div>
    </header>
  );
}

function MainLayout() {
  const location = useLocation();
  const isChat = location.pathname.startsWith('/chat');

  return (
    <div className={`w-full theme-app-bg theme-body flex flex-col font-sans transition-colors duration-200 ${
      isChat ? 'h-screen max-h-screen overflow-hidden' : 'min-h-screen'
    }`}>
      <Header />

      {/* Main Content Area: Fixed 100vh viewport for /chat with min-h-0, auto-scroll for standard reading pages */}
      <main className={`w-full ${
        isChat ? 'flex-1 min-h-0 h-[calc(100vh-64px)] overflow-hidden flex flex-col' : 'flex-1 overflow-y-auto'
      }`}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/surah/:surahNo" element={<SurahDetailPage />} />
          <Route path="/surah/:surahNo/ayat/:ayahNo" element={<AyatTafsirPage />} />
          <Route path="/tafsir/:surahNo/:ayahNo" element={<AyatTafsirPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/chat/:sessionUuid" element={<ChatPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <MainLayout />
    </ThemeProvider>
  );
}
