import React, { useRef, useEffect, useState } from 'react';
import { 
  PanelLeft, PanelLeftClose, SquarePen, 
  ArrowRight, BookOpen
} from 'lucide-react';
import Message from './Message';
import ChatInput from './ChatInput';

export default function ChatWindow({ 
  messages, 
  setMessages, 
  sessionUuid, 
  initialQuery, 
  onSessionCreated,
  isSidebarOpen,
  onToggleSidebar,
  onNewChat
}) {
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef(null);
  const initialSentRef = useRef(false);

  // Auto scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  // Handle initialQuery if present (e.g. from Tafsir page)
  useEffect(() => {
    if (initialQuery && !initialSentRef.current) {
      initialSentRef.current = true;
      handleSendMessage(initialQuery);
    }
  }, [initialQuery]);

  const handleSendMessage = async (text) => {
    if (!text || !text.trim() || isTyping) return;

    const userMsg = {
      id: Date.now(),
      role: "user",
      content: text
    };
    
    setMessages(prev => [...prev, userMsg]);
    setIsTyping(true);

    const botMsgId = Date.now() + 1;
    let botMsg = {
      id: botMsgId,
      role: "assistant",
      content: "",
      sources: []
    };
    setMessages(prev => [...prev, botMsg]);

    try {
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: text,
          session_uuid: sessionUuid || null
        })
      });

      if (!response.ok) throw new Error("Network response was not ok");

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let done = false;

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        const chunkValue = decoder.decode(value, { stream: true });
        
        const lines = chunkValue.split('\n');
        for (let line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '').trim();
            if (dataStr === '[DONE]') break;
            
            try {
              const data = JSON.parse(dataStr);
              
              if (data.type === 'session' && !sessionUuid && onSessionCreated) {
                onSessionCreated(data.session_uuid);
              }
              else if (data.type === 'sources') {
                botMsg.sources = data.sources;
                setMessages(prev => prev.map(m => m.id === botMsgId ? { ...botMsg } : m));
              }
              else if (data.type === 'token') {
                botMsg.content += data.content;
                setMessages(prev => prev.map(m => m.id === botMsgId ? { ...botMsg } : m));
              }
              else if (data.type === 'error') {
                console.error("Stream error:", data.message);
                botMsg.content += "\n\n[Terjadi kesalahan: " + data.message + "]";
                setMessages(prev => prev.map(m => m.id === botMsgId ? { ...botMsg } : m));
              }
            } catch (err) {
              // chunk was partial JSON
            }
          }
        }
      }
    } catch (error) {
      console.error("Gagal mengirim pesan:", error);
      botMsg.content = "Maaf, terjadi kendala saat menghubungkan ke server tafsir.";
      setMessages(prev => prev.map(m => m.id === botMsgId ? { ...botMsg } : m));
    } finally {
      setIsTyping(false);
    }
  };

  // Starter Prompts for Professional Empty State
  const starterPrompts = [
    {
      title: "Kisah Kaum Luth (QS Hud & Al-Hijr)",
      desc: "Bandingkan bagaimana Tafsir Ath-Thabari menjelaskan kisah hancurnya kaum Luth di Surah Hud dan Surah Al-Hijr. Apa detail yang membedakan keduanya?",
      icon: "📖"
    },
    {
      title: "Takwil Mimpi Yusuf (QS 12:4)",
      desc: "Bagaimana takwil Ath-Thabari mengenai mimpi sebelas bintang, matahari, dan bulan pada Surah Yusuf ayat 4?",
      icon: "👑"
    },
    {
      title: "Petir yang Bertasbih (QS 13:13)",
      desc: "Jelaskan riwayat shahabat tentang makna 'Ar-Ra'd' (petir yang bertasbih) dalam takwil Surah Ar-Ra'd.",
      icon: "🌩️"
    },
    {
      title: "Fitnah Al-Ifk (QS 24:11-20)",
      desc: "Bagaimana riwayat dan takwil Ath-Thabari mengenai peristiwa fitnah al-Ifk pada Surah An-Nur?",
      icon: "🛡️"
    }
  ];

  const hasUserMessages = messages.some(m => m.role === 'user');

  return (
    <div className="flex-1 min-h-0 h-full flex flex-col overflow-hidden theme-app-bg transition-colors relative">
      {/* Top Chat Sub-Header: Ultra-slim 40px */}
      <div className="h-10 px-3 border-b border-islamic-200/60 dark:border-islamic-800/80 theme-header flex items-center justify-between gap-2 flex-shrink-0">
        <div className="flex items-center gap-2">
          {/* Toggle Sidebar Button */}
          <button
            onClick={onToggleSidebar}
            className={`p-1 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-colors ${
              !isSidebarOpen 
                ? 'bg-emerald-600/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/40' 
                : 'theme-muted hover:theme-title'
            }`}
            title={isSidebarOpen ? "Sembunyikan Sidebar (Ctrl+B)" : "Buka Sidebar Riwayat (Ctrl+B)"}
          >
            {isSidebarOpen ? <PanelLeftClose size={15} /> : <PanelLeft size={15} />}
            <span className="text-[11px] font-medium hidden sm:inline">
              {isSidebarOpen ? "Tutup Panel" : "Riwayat"}
            </span>
          </button>

          <span className="text-islamic-300 dark:text-islamic-700 hidden sm:inline">|</span>

          {/* RAG Status */}
          <div className="flex items-center gap-1.5 text-[10px] theme-muted font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="hidden sm:inline">Model RAG Jami' al-Bayan Aktif</span>
          </div>
        </div>

        {/* Right side: Quick New Chat */}
        <button
          onClick={onNewChat}
          className="p-1 px-2 rounded-md theme-card text-xs font-medium theme-muted hover:text-emerald-600 dark:hover:text-emerald-400 flex items-center gap-1 transition-colors"
          title="Percakapan Baru"
        >
          <SquarePen size={14} />
          <span className="text-[11px] hidden sm:inline">Chat Baru</span>
        </button>
      </div>

      {/* Messages Stream Area */}
      <div 
        ref={scrollRef}
        className="flex-1 min-h-0 overflow-y-auto scrollbar-thin px-4 sm:px-6 py-4"
      >
        <div className="max-w-3xl mx-auto flex flex-col justify-center min-h-full">
          {/* Empty State: Render ONLY when user has not yet sent any message */}
          {!hasUserMessages ? (
            <div className="py-6 sm:py-10 text-center my-auto">
              <div className="w-12 h-12 rounded-2xl mx-auto mb-3 bg-gradient-to-br from-emerald-600 to-islamic-700 text-white flex items-center justify-center shadow-md">
                <BookOpen size={24} className="text-white" />
              </div>
              <h2 className="text-lg sm:text-xl font-bold theme-title mb-1.5">
                Asisten Akademik Tafsir Ath-Thabari
              </h2>
              <p className="text-xs theme-muted max-w-md mx-auto leading-relaxed mb-6">
                Eksplorasi takwil ilmiah berbasis RAG dari Kitab Jami' al-Bayan (QS Hud hingga An-Nur). Silakan pilih topik di bawah atau ketik pertanyaan Anda.
              </p>

              {/* Starter Suggestion Grid (Clean 2x2, max-w-xl) */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-left max-w-xl mx-auto">
                {starterPrompts.map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(item.desc)}
                    className="p-3 rounded-xl theme-card shadow-xs hover:border-emerald-500/60 hover:bg-emerald-500/5 transition-all group flex flex-col justify-between text-left"
                  >
                    <div>
                      <div className="flex items-center gap-1.5 mb-1">
                        <span className="text-sm select-none">{item.icon}</span>
                        <h3 className="text-xs font-bold theme-title group-hover:text-emerald-600 dark:group-hover:text-emerald-300 transition-colors truncate">
                          {item.title}
                        </h3>
                      </div>
                      <p className="text-[11px] theme-muted leading-relaxed line-clamp-2">
                        {item.desc}
                      </p>
                    </div>
                    <div className="mt-2 flex items-center gap-1 text-[10px] font-bold text-emerald-600 dark:text-emerald-400 group-hover:translate-x-0.5 transition-transform">
                      <span>Tanyakan</span>
                      <ArrowRight size={11} />
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* Active Conversation: Render messages list cleanly */
            <div className="flex flex-col py-2">
              {messages.map(m => (
                <Message key={m.id} message={m} />
              ))}

              {/* Typing Animation */}
              {isTyping && (
                <div className="flex justify-start mb-6">
                  <div className="theme-card rounded-2xl px-4 py-3 flex gap-2 items-center shadow-xs">
                    <span className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    <span className="text-xs theme-muted ml-2 font-medium">
                      Mengolah rujukan Kitab Jami' al-Bayan...
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      
      {/* Pinned Bottom Input */}
      <ChatInput onSendMessage={handleSendMessage} disabled={isTyping} />
    </div>
  );
}
