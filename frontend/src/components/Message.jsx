import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { 
  Book, BookOpen, User, Copy, Check, ChevronDown, ChevronUp 
} from 'lucide-react';

export default function Message({ message }) {
  const isBot = message.role === "assistant";
  const [copied, setCopied] = useState(false);
  const [showAllSources, setShowAllSources] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const sources = message.sources || [];
  const hasManySources = sources.length > 4;
  const visibleSources = showAllSources ? sources : sources.slice(0, 4);

  return (
    <div className={`w-full flex ${isBot ? "justify-start" : "justify-end"} mb-6`}>
      {isBot ? (
        /* Assistant Message Card */
        <div className="w-full max-w-3xl theme-card rounded-2xl p-5 sm:p-6 shadow-xs border">
          {/* Header */}
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-islamic-200/50 dark:border-islamic-800/40">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold text-xs flex-shrink-0">
                <BookOpen size={13} />
              </div>
              <span className="font-bold text-xs text-emerald-800 dark:text-emerald-300">
                Asisten Tafsir Ath-Thabari
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full theme-pill font-medium">
                Jami' al-Bayan
              </span>
            </div>

            {/* Copy button */}
            <button
              onClick={handleCopy}
              className="p-1 rounded-md text-xs theme-muted hover:theme-title hover:bg-emerald-500/10 transition-colors flex items-center gap-1"
              title="Salin Jawaban"
            >
              {copied ? (
                <>
                  <Check size={13} className="text-emerald-500" />
                  <span className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">Tersalin</span>
                </>
              ) : (
                <Copy size={13} />
              )}
            </button>
          </div>

          {/* Markdown Content */}
          <div className="text-sm leading-relaxed theme-body font-sans space-y-2.5">
            <ReactMarkdown
              components={{
                p: ({ children }) => <p className="leading-relaxed mb-2 last:mb-0">{children}</p>,
                strong: ({ children }) => (
                  <strong className="font-bold text-emerald-800 dark:text-emerald-200">
                    {children}
                  </strong>
                ),
                em: ({ children }) => <em className="italic text-emerald-700 dark:text-emerald-300">{children}</em>,
                ul: ({ children }) => <ul className="list-disc pl-5 my-2 space-y-1">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal pl-5 my-2 space-y-1">{children}</ol>,
                li: ({ children }) => <li className="leading-relaxed pl-1">{children}</li>,
                h1: ({ children }) => <h1 className="text-base font-bold theme-title mt-3 mb-1.5">{children}</h1>,
                h2: ({ children }) => <h2 className="text-sm font-bold theme-title mt-2.5 mb-1">{children}</h2>,
                h3: ({ children }) => <h3 className="text-xs font-bold text-emerald-700 dark:text-emerald-300 mt-2 mb-1">{children}</h3>,
                blockquote: ({ children }) => (
                  <blockquote className="border-l-3 border-emerald-500 pl-3 py-1 my-2 italic theme-card-secondary rounded-r text-xs">
                    {children}
                  </blockquote>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>

          {/* Collapsible Sources Footer */}
          {sources.length > 0 && (
            <div className="mt-4 pt-3 border-t border-islamic-200/50 dark:border-islamic-800/40">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-bold theme-muted uppercase tracking-wider flex items-center gap-1">
                  <Book size={11} className="text-amber-500" />
                  <span>Rujukan Riwayat Ath-Thabari ({sources.length}):</span>
                </span>

                {hasManySources && (
                  <button
                    onClick={() => setShowAllSources(!showAllSources)}
                    className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 hover:underline flex items-center gap-0.5"
                  >
                    <span>{showAllSources ? "Tampilkan lebih sedikit" : `+${sources.length - 4} lainnya`}</span>
                    {showAllSources ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  </button>
                )}
              </div>

              <div className="flex flex-wrap gap-1.5">
                {visibleSources.map((src, i) => (
                  <span 
                    key={i} 
                    className="inline-flex items-center gap-1 px-2.5 py-0.5 theme-pill rounded-md text-[11px] font-medium"
                  >
                    <span>{src.source || src.title || "Tafsir Ath-Thabari"}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        /* User Message Bubble */
        <div className="max-w-[85%] sm:max-w-xl bg-emerald-600 dark:bg-emerald-700 text-white rounded-2xl rounded-tr-xs px-4 py-3 shadow-xs">
          <div className="text-xs sm:text-sm leading-relaxed whitespace-pre-wrap font-sans">
            {message.content}
          </div>
        </div>
      )}
    </div>
  );
}
