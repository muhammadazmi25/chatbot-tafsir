import React, { useState, useRef } from 'react';
import { ArrowUp, Loader2 } from 'lucide-react';

export default function ChatInput({ onSendMessage, disabled }) {
  const [input, setInput] = useState("");
  const textareaRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSendMessage(input.trim());
      setInput("");
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleInput = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-3 pt-1 select-none flex-shrink-0">
      <form onSubmit={handleSubmit} className="relative flex items-end theme-card rounded-2xl shadow-sm border focus-within:border-emerald-500 focus-within:ring-2 focus-within:ring-emerald-500/20 transition-all p-1.5">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder="Tanyakan takwil ayat, asbabun nuzul, atau riwayat salaf..."
          disabled={disabled}
          rows={1}
          className="w-full bg-transparent resize-none py-1.5 pl-3 pr-10 text-xs sm:text-sm theme-title placeholder-islamic-400/50 outline-none leading-relaxed scrollbar-thin"
          style={{ minHeight: '38px', maxHeight: '150px' }}
        />
        
        <button
          type="submit"
          disabled={!input.trim() || disabled}
          className="w-8 h-8 rounded-xl flex items-center justify-center bg-emerald-600 hover:bg-emerald-500 text-white disabled:opacity-30 disabled:cursor-not-allowed shadow-xs transition-all flex-shrink-0 mb-0.5 mr-0.5"
          title="Kirim (Enter)"
        >
          {disabled ? <Loader2 size={16} className="animate-spin" /> : <ArrowUp size={16} />}
        </button>
      </form>

      <p className="text-center text-[10px] theme-muted mt-1.5 opacity-60">
        RAG AI merujuk langsung ke Kitab Jami' al-Bayan (QS 11-24). Harap teliti kembali konteks asli riwayat.
      </p>
    </div>
  );
}
