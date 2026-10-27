import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import ChatSidebar from '../components/ChatSidebar';
import ChatWindow from '../components/ChatWindow';
import { getSessionMessages } from '../api';

export default function ChatPage() {
  const { sessionUuid } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  // Sidebar toggle state (defaults to open on desktop screens >= 768px)
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('thabari_chat_sidebar');
      if (saved !== null) return saved === 'true';
      return window.innerWidth >= 768;
    }
    return true;
  });

  const [messages, setMessages] = useState([]);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Read initial query parameter if coming from Tafsir page
  const queryParam = new URLSearchParams(location.search).get('query');

  useEffect(() => {
    localStorage.setItem('thabari_chat_sidebar', String(isSidebarOpen));
  }, [isSidebarOpen]);

  // Keyboard shortcut Ctrl+B or Cmd+B to toggle sidebar
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
        e.preventDefault();
        setIsSidebarOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    if (sessionUuid) {
      loadSession(sessionUuid);
    } else {
      setMessages([]);
    }
  }, [sessionUuid]);

  const loadSession = async (uuid) => {
    try {
      const data = await getSessionMessages(uuid);
      setMessages(data || []);
    } catch (e) {
      console.error("Gagal memuat sesi:", e);
    }
  };

  const handleNewChat = () => {
    navigate('/chat');
    setMessages([]);
  };

  const toggleSidebar = () => {
    setIsSidebarOpen(prev => !prev);
  };

  return (
    <div className="flex-1 min-h-0 h-full w-full overflow-hidden flex theme-app-bg theme-body relative">
      {/* Collapsible Sidebar */}
      <ChatSidebar 
        isOpen={isSidebarOpen}
        onToggle={toggleSidebar}
        currentSessionUuid={sessionUuid} 
        onNewChat={handleNewChat}
        refreshTrigger={refreshTrigger}
      />

      {/* Main Chat Area */}
      <ChatWindow 
        messages={messages} 
        setMessages={setMessages} 
        sessionUuid={sessionUuid}
        initialQuery={queryParam}
        isSidebarOpen={isSidebarOpen}
        onToggleSidebar={toggleSidebar}
        onNewChat={handleNewChat}
        onSessionCreated={(uuid) => {
          navigate(`/chat/${uuid}`);
          setRefreshTrigger(prev => prev + 1);
        }}
      />
    </div>
  );
}
