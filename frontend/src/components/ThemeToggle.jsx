import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export default function ThemeToggle({ showLabel = false, className = '' }) {
  const { isDark, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      title={isDark ? "Beralih ke Mode Terang (Hijau Terang)" : "Beralih ke Mode Gelap (Hijau Gelap)"}
      className={`relative inline-flex items-center gap-2 p-2 rounded-xl transition-all duration-200 border ${
        isDark
          ? 'bg-islamic-850/80 hover:bg-islamic-800 text-gold-300 border-islamic-700/60 shadow-inner'
          : 'bg-white hover:bg-islamic-50 text-islamic-700 border-islamic-200 shadow-sm'
      } ${className}`}
      aria-label="Toggle Theme"
    >
      <div className="relative w-5 h-5 flex items-center justify-center">
        {isDark ? (
          <Sun size={18} className="text-amber-300 transition-transform hover:rotate-45" />
        ) : (
          <Moon size={18} className="text-islamic-700 transition-transform -rotate-12" />
        )}
      </div>
      {showLabel && (
        <span className="text-xs font-semibold select-none pr-1">
          {isDark ? "Mode Terang" : "Mode Gelap"}
        </span>
      )}
    </button>
  );
}
