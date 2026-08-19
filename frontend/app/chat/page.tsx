'use client';

import React, { useState, useEffect, useRef, Suspense } from 'react';
import { useRouter } from 'next/navigation';
import { api, getStoredUser } from '../../services/api';
import { ChatMessage, Book, User, ChatSessionMeta } from '../../types';
import BookDetailModal from '../../components/BookDetailModal';
import MarkdownRenderer from '../../components/MarkdownRenderer';
import { Flame, Leaf, Target, Heart, Zap, Shield, Sparkles, Lightbulb, BookText, MessageSquare, Plus, Trash2, FolderOpen, Check, Copy, Send, Book as BookIcon, User as UserIcon } from 'lucide-react';

const SAMPLE_PROMPTS = [
  'I want chilling horror books like classic horror movies',
  'Recommend books on World War 2 and modern history',
  'Suggest a classic mystery novel with great plot twists',
  'Recommend a science fiction novel exploring artificial consciousness',
  'Suggest books on psychology, human behavior, and habits',
];

const EMOTION_BADGES: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  horror_thrill: { label: 'Horror & Suspense Tone', icon: <Flame size={12} />, color: 'text-purple-400 border-purple-800/50 bg-purple-950/40' },
  comfort_relief: { label: 'Comforting & Cozy Tone', icon: <Leaf size={12} />, color: 'text-teal-400 border-teal-800/50 bg-teal-950/40' },
  frustration: { label: 'Direct & Attentive', icon: <Target size={12} />, color: 'text-amber-400 border-amber-800/50 bg-amber-950/40' },
  sadness: { label: 'Comforting & Empathetic', icon: <Heart size={12} />, color: 'text-teal-400 border-teal-800/50 bg-teal-950/40' },
  anger: { label: 'Validating & Focused', icon: <Zap size={12} />, color: 'text-rose-400 border-rose-800/50 bg-rose-950/40' },
  fear: { label: 'Reassuring & Calming', icon: <Shield size={12} />, color: 'text-blue-400 border-blue-800/50 bg-blue-950/40' },
  joy: { label: 'Energetic & Vibrant', icon: <Sparkles size={12} />, color: 'text-yellow-400 border-yellow-800/50 bg-yellow-950/40' },
  curiosity: { label: 'Inquisitive & Scholarly', icon: <Lightbulb size={12} />, color: 'text-cyan-400 border-cyan-800/50 bg-cyan-950/40' },
  neutral: { label: 'Catalog Assistant', icon: <BookText size={12} />, color: 'text-gray-400 border-gray-800 bg-gray-900/50' },
};

const DEFAULT_WELCOME_MESSAGE: ChatMessage = {
  sender: 'assistant',
  text: "Hello! I am your **University Library AI Assistant**.\n\nI can help you discover books across the catalog, adapt to your mood and tone, explain themes and plots, and recommend titles verified against our live library inventory.\n\nWhat book or topic would you like to explore today?",
};

function formatTimestamp(dateStrOrMs: string | number): string {
  const ms = typeof dateStrOrMs === 'string' ? new Date(dateStrOrMs).getTime() : dateStrOrMs;
  if (isNaN(ms)) return 'Recent';
  const diff = Date.now() - ms;
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days}d ago`;
  return new Date(ms).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function formatExpectedReturnDate(dateStr?: string | null): string {
  if (!dateStr) return 'Soon';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return dateStr;
  }
}

function ChatContent() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [sessions, setSessions] = useState<ChatSessionMeta[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([DEFAULT_WELCOME_MESSAGE]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [selectedBook, setSelectedBook] = useState<Book | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [searchHistoryFilter, setSearchHistoryFilter] = useState('');
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const initialPromptProcessed = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const getUserKey = (u: User | null = user) => (u ? u.roll_number : 'guest');

  // Load user sessions list from backend database
  const fetchDBSessions = async () => {
    const currentUser = getStoredUser();
    if (!currentUser) {
      // Local fallback for guest
      try {
        const stored = localStorage.getItem('portal_chat_sessions_guest');
        if (stored) {
          const parsed = JSON.parse(stored);
          if (Array.isArray(parsed)) setSessions(parsed);
        }
      } catch (e) {
        console.error(e);
      }
      return;
    }

    try {
      const data = await api.getChatSessions();
      setSessions(data);
      localStorage.setItem(`portal_chat_sessions_${currentUser.roll_number}`, JSON.stringify(data));
    } catch (e) {
      console.warn('Could not fetch DB sessions, using fallback:', e);
      const cached = localStorage.getItem(`portal_chat_sessions_${currentUser.roll_number}`);
      if (cached) {
        try {
          setSessions(JSON.parse(cached));
        } catch {}
      }
    }
  };

  // Start fresh new chat session
  const startNewChat = (customUser?: User | null) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const activeUser = customUser !== undefined ? customUser : user;
    const userKey = getUserKey(activeUser);
    const newId = `sess_${userKey}_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    setCurrentSessionId(newId);
    setMessages([DEFAULT_WELCOME_MESSAGE]);
  };

  // Switch to an existing conversation session
  const switchSession = async (sessionId: string) => {
    if (sessionId === currentSessionId) return;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setCurrentSessionId(sessionId);
    setHistoryLoading(true);

    const currentUser = getStoredUser();
    if (currentUser) {
      try {
        const detail = await api.getChatSessionDetail(sessionId);
        if (detail && detail.messages && detail.messages.length > 0) {
          const formatted: ChatMessage[] = detail.messages.map((m) => ({
            id: m.id,
            sender: m.sender as any,
            text: m.text,
            emotion: m.emotion,
            suggestedBooks: m.suggested_books as Book[],
            created_at: m.created_at,
          }));
          setMessages(formatted);
          setHistoryLoading(false);
          return;
        }
      } catch (e) {
        console.warn('Could not load session from DB, trying local storage:', e);
      }
    }

    // Local fallback
    try {
      const userKey = getUserKey(currentUser);
      const stored = localStorage.getItem(`portal_chat_history_${userKey}_${sessionId}`);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setMessages(parsed);
          setHistoryLoading(false);
          return;
        }
      }
    } catch (e) {
      console.error('Error loading fallback history:', e);
    }

    setMessages([DEFAULT_WELCOME_MESSAGE]);
    setHistoryLoading(false);
  };

  // Delete a specific session
  const deleteSession = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    const currentUser = getStoredUser();
    const userKey = getUserKey(currentUser);

    if (currentUser) {
      try {
        await api.deleteChatSession(sessionId);
      } catch (err) {
        console.warn('Could not delete session from DB:', err);
      }
    }

    const filtered = sessions.filter((s) => s.id !== sessionId);
    setSessions(filtered);
    try {
      localStorage.setItem(`portal_chat_sessions_${userKey}`, JSON.stringify(filtered));
      localStorage.removeItem(`portal_chat_history_${userKey}_${sessionId}`);
    } catch (err) {}

    if (sessionId === currentSessionId) {
      if (filtered.length > 0) {
        switchSession(filtered[0].id);
      } else {
        startNewChat(currentUser);
      }
    }
  };

  // Sync user state and load persistent DB conversations on mount
  useEffect(() => {
    const syncUserAndChat = async () => {
      const currentUser = getStoredUser();
      setUser(currentUser);

      if (currentUser) {
        await fetchDBSessions();
      } else {
        const stored = localStorage.getItem('portal_chat_sessions_guest');
        if (stored) {
          try {
            setSessions(JSON.parse(stored));
          } catch {}
        }
      }

      if (!currentSessionId && !initialPromptProcessed.current) {
        initialPromptProcessed.current = true;
        startNewChat(currentUser);
      }
    };

    syncUserAndChat();
    window.addEventListener('library_portal_auth_change', syncUserAndChat);
    return () => {
      window.removeEventListener('library_portal_auth_change', syncUserAndChat);
      initialPromptProcessed.current = false;
    };
  }, []);

  // Handle session storage prompt (e.g. from "Discuss with AI" buttons)
  useEffect(() => {
    const pendingPrompt = sessionStorage.getItem('pending_chat_prompt');
    if (pendingPrompt && currentSessionId && !loading && !isStreaming) {
      sessionStorage.removeItem('pending_chat_prompt');
      handleSendQuery(pendingPrompt);
    }
  }, [currentSessionId, loading, isStreaming]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading, isStreaming]);

  const handleStopGenerating = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
      setLoading(false);
    }
  };

  const handleCopyText = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  const handleSendQuery = async (queryText: string) => {
    if (!queryText.trim() || loading || isStreaming) return;

    const userText = queryText.trim();
    setInput('');

    setMessages((prev) => {
      return [...prev, { sender: 'user', text: userText }, { sender: 'assistant', text: '' }];
    });
    setLoading(true);
    setIsStreaming(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;
    const userKey = getUserKey();

    let accumulated = '';

    await api.streamChatMessage(
      userText,
      currentSessionId,
      {
        onToken: (token) => {
          accumulated += token;
          setLoading(false);
          setMessages((prev) => {
            const next = [...prev];
            const lastIdx = next.length - 1;
            if (next[lastIdx] && next[lastIdx].sender === 'assistant') {
              next[lastIdx] = {
                ...next[lastIdx],
                text: accumulated,
              };
            }
            return next;
          });
        },
        onDone: (data) => {
          setIsStreaming(false);
          setLoading(false);
          setMessages((prev) => {
            const next = [...prev];
            const lastIdx = next.length - 1;
            if (next[lastIdx] && next[lastIdx].sender === 'assistant') {
              next[lastIdx] = {
                ...next[lastIdx],
                text: data.full_text || accumulated,
                emotion: data.emotion,
                suggestedBooks: data.suggested_books as Book[],
              };
            }
            try {
              localStorage.setItem(`portal_chat_history_${userKey}_${currentSessionId}`, JSON.stringify(next));
            } catch (e) {}
            return next;
          });

          if (user) {
            fetchDBSessions();
          } else {
            const existingIdx = sessions.findIndex((s) => s.id === currentSessionId);
            let updatedList: ChatSessionMeta[];
            const nowStr = new Date().toISOString();
            if (existingIdx >= 0) {
              updatedList = [...sessions];
              updatedList[existingIdx] = { ...updatedList[existingIdx], updated_at: nowStr };
              const [target] = updatedList.splice(existingIdx, 1);
              updatedList.unshift(target);
            } else {
              const titleSnippet = userText.slice(0, 35) + (userText.length > 35 ? '...' : '');
              const newSessionMeta: ChatSessionMeta = {
                id: currentSessionId,
                title: titleSnippet,
                created_at: nowStr,
                updated_at: nowStr,
              };
              updatedList = [newSessionMeta, ...sessions];
            }
            setSessions(updatedList);
            localStorage.setItem('portal_chat_sessions_guest', JSON.stringify(updatedList));
          }
        },
        onError: (err) => {
          console.warn('Streaming failed, fallback triggered:', err);
          setIsStreaming(false);
          setLoading(false);
          // Fallback to standard request
          api.sendChatMessage(userText, currentSessionId).then((res) => {
            setMessages((prev) => {
              const next = [...prev];
              const lastIdx = next.length - 1;
              if (next[lastIdx] && next[lastIdx].sender === 'assistant') {
                next[lastIdx] = {
                  ...next[lastIdx],
                  text: res.response,
                  emotion: res.emotion,
                  suggestedBooks: res.suggested_books as Book[],
                };
              }
              return next;
            });
          }).catch(() => {
            setMessages((prev) => {
              const next = [...prev];
              const lastIdx = next.length - 1;
              if (next[lastIdx] && next[lastIdx].sender === 'assistant') {
                next[lastIdx] = {
                  ...next[lastIdx],
                  text: "I am ready to help you explore the library catalog. Ask me about any title, author, or genre!",
                };
              }
              return next;
            });
          });
        },
      },
      controller.signal
    );
  };

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    handleSendQuery(input);
  };

  const handleClearCurrentSession = async () => {
    try {
      await api.resetChatSession(currentSessionId);
    } catch (e) {
      console.warn('Reset error:', e);
    }
    const initialWelcome: ChatMessage[] = [
      {
        sender: 'assistant',
        text: "Started a new conversation. What book or topic would you like to explore?",
      },
    ];
    setMessages(initialWelcome);
  };

  const filteredSessions = sessions.filter((s) =>
    (s.title || '').toLowerCase().includes(searchHistoryFilter.toLowerCase())
  );

  return (
    <div className="max-w-7xl mx-auto space-y-4">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b border-parchment pb-3 gap-2">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-lg portal-stat-card hover:bg-parchment border border-parchment text-navy hover:text-gold transition-colors flex items-center justify-center text-xs"
            title={sidebarOpen ? 'Collapse History Sidebar' : 'Expand History Sidebar'}
          >
            {sidebarOpen ? '◄ Sidebar' : '► History'}
          </button>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-navy tracking-tight flex items-center gap-2">
              <Zap size={24} className="text-gold" /> AI Library Assistant
            </h1>
            <p className="text-xs text-ink-light">
              High-speed ChatGPT-grade assistant with live catalog intelligence and expected return timings.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => startNewChat()}
            className="portal-btn-primary px-3.5 py-1.5 text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-sm"
          >
            <span>+</span> New Chat
          </button>
          <button
            onClick={handleClearCurrentSession}
            className="px-3 py-1.5 text-xs font-medium text-ink-light hover:text-navy bg-cream-light hover:bg-parchment border border-parchment rounded-lg transition-colors"
          >
            Clear Chat
          </button>
        </div>
      </div>

      {/* Main Container with Sidebar + Chat Area */}
      <div className="flex gap-4 items-stretch h-[73vh]">
        {/* ChatGPT Style History Sidebar */}
        {sidebarOpen && (
          <div className="w-64 sm:w-72 shrink-0 bg-cream-light rounded-2xl flex flex-col justify-between overflow-hidden shadow-xl animate-in fade-in duration-200 border border-parchment">
            {/* Sidebar Header & New Chat Button */}
            <div className="p-3 border-b border-parchment space-y-2.5">
              <button
                onClick={() => startNewChat()}
                className="w-full py-2.5 px-3.5 rounded-xl text-xs font-semibold text-navy bg-cream hover:bg-parchment border border-parchment hover:border-gold/50 flex items-center justify-between transition-all group shadow-sm"
              >
                <div className="flex items-center gap-2">
                  <Sparkles size={14} className="group-hover:scale-110 transition-transform" />
                  <span>New Conversation</span>
                </div>
                <Plus size={14} className="text-ink-muted group-hover:text-gold" />
              </button>

              {/* History Search Filter */}
              {sessions.length > 3 && (
                <input
                  type="text"
                  placeholder="Filter past topics..."
                  value={searchHistoryFilter}
                  onChange={(e) => setSearchHistoryFilter(e.target.value)}
                  className="w-full px-3 py-1.5 text-[11px] rounded-lg bg-cream border border-parchment text-ink placeholder-ink-muted focus:outline-none focus:border-gold"
                />
              )}
            </div>

            {/* Past Conversations List */}
            <div className="flex-1 overflow-y-auto p-2 space-y-1.5 pr-1.5 custom-scrollbar">
              <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-ink-muted flex items-center justify-between">
                <span>Chat History ({filteredSessions.length})</span>
                {user && <span className="text-gold text-[9px] lowercase font-normal">● synced</span>}
              </div>

              {filteredSessions.length === 0 ? (
                <div className="p-4 text-center text-xs text-ink-muted">
                  <FolderOpen size={24} className="mb-2 opacity-50 mx-auto" />
                  No past conversations recorded yet. Send a message to save your history!
                </div>
              ) : (
                filteredSessions.map((sess) => {
                  const isActive = sess.id === currentSessionId;
                  return (
                    <div
                      key={sess.id}
                      onClick={() => switchSession(sess.id)}
                      className={`group relative w-full px-3 py-2.5 rounded-xl text-xs flex items-center justify-between cursor-pointer transition-all border ${
                        isActive
                          ? 'bg-gold/10 border-gold/30 text-navy shadow-sm'
                          : 'bg-cream hover:bg-parchment border-transparent hover:border-parchment text-ink-muted hover:text-navy'
                      }`}
                    >
                      <div className="min-w-0 flex-1 pr-2">
                        <div className="flex items-center gap-1.5">
                          <MessageSquare size={12} className="shrink-0" />
                          <span className="truncate font-medium text-xs block">
                            {sess.title || 'Conversation'}
                          </span>
                        </div>
                        <span className="text-[10px] text-ink-light mt-0.5 block pl-4">
                          {formatTimestamp(sess.updated_at || sess.created_at)}
                        </span>
                      </div>

                      {/* Delete Conversation Button */}
                      <button
                        onClick={(e) => deleteSession(e, sess.id)}
                        className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-ink-muted hover:text-red-500 hover:bg-parchment transition-all shrink-0"
                        title="Delete conversation"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  );
                })
              )}
            </div>

            {/* Sidebar Footer User Info */}
            <div className="p-3 border-t border-parchment bg-cream flex items-center justify-between text-xs text-ink-muted">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-7 h-7 rounded-full bg-gold/10 border border-gold/30 flex items-center justify-center text-xs text-gold font-bold shrink-0">
                  {user ? user.name.charAt(0).toUpperCase() : 'G'}
                </div>
                <div className="min-w-0">
                  <div className="text-[11px] font-semibold text-navy truncate">
                    {user ? user.name : 'Guest User'}
                  </div>
                  <div className="text-[10px] text-ink-light font-mono truncate">
                    {user ? `Roll: ${user.roll_number}` : 'Local Browser Session'}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Chat Conversation Area */}
        <div className="flex-1 flex flex-col justify-between portal-card p-4 sm:p-6 shadow-xl relative overflow-hidden">
          {/* Suggested Prompt Chips */}
          <div className="flex items-center gap-2 overflow-x-auto pb-2 mb-2 text-xs text-ink-muted border-b border-parchment shrink-0">
            <span className="text-gold font-semibold shrink-0 text-[11px]">Prompt Ideas:</span>
            {SAMPLE_PROMPTS.map((prompt, idx) => (
              <button
                key={idx}
                onClick={() => handleSendQuery(prompt)}
                disabled={loading || isStreaming || historyLoading}
                className="shrink-0 px-2.5 py-1 rounded-full portal-stat-card border border-parchment text-[11px] text-ink-muted hover:border-gold hover:text-gold transition-colors disabled:opacity-50"
              >
                {prompt}
              </button>
            ))}
          </div>

          {/* Messages Stream */}
          <div className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
            {historyLoading ? (
              <div className="flex items-center justify-center h-full text-xs text-ink-muted">
                <span className="animate-pulse">Loading conversation history from database...</span>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div
                  key={msg.id || idx}
                  className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
                >
                  <div className="flex items-center gap-2 mb-1 px-1">
                    <span className="text-[10px] font-semibold text-ink-muted">
                      {msg.sender === 'user' ? 'You' : 'AI Assistant'}
                    </span>
                    {msg.sender === 'assistant' && msg.emotion && EMOTION_BADGES[msg.emotion] && (
                      <span
                        className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${EMOTION_BADGES[msg.emotion].color} flex items-center gap-1 shadow-sm`}
                      >
                        <span>{EMOTION_BADGES[msg.emotion].icon}</span>
                        <span>{EMOTION_BADGES[msg.emotion].label}</span>
                      </span>
                    )}
                  </div>

                  <div className="relative group max-w-[88%]">
                    <div
                      className={`px-4 py-3 text-sm leading-relaxed ${
                        msg.sender === 'user'
                          ? 'chat-bubble-user whitespace-pre-wrap'
                          : 'chat-bubble-assistant'
                      }`}
                    >
                      {msg.sender === 'assistant' ? (
                        <>
                          <MarkdownRenderer content={msg.text} />
                          {isStreaming && idx === messages.length - 1 && (
                            <span className="inline-block w-1.5 h-4 bg-gold ml-1 align-middle animate-pulse" />
                          )}
                        </>
                      ) : (
                        <div>{msg.text}</div>
                      )}
                    </div>

                    {/* Copy Button on hover */}
                    {msg.text && (
                      <button
                        onClick={() => handleCopyText(msg.text, idx)}
                        className="opacity-0 group-hover:opacity-100 transition-opacity absolute -bottom-3 right-2 text-[10px] bg-cream-light hover:bg-parchment text-ink-muted hover:text-navy px-2 py-0.5 rounded-md border border-parchment shadow flex items-center gap-1 z-10"
                        title="Copy text"
                      >
                        {copiedIdx === idx ? (
                          <>
                            <Check size={12} className="text-gold" />
                            <span>Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy size={12} />
                            <span>Copy</span>
                          </>
                        )}
                      </button>
                    )}
                  </div>

                  {/* Referenced Books with Expected Return Timings */}
                  {msg.suggestedBooks && msg.suggestedBooks.length > 0 && (
                    <div className="mt-3 w-full max-w-[92%] portal-stat-card p-3.5 rounded-xl border border-parchment shadow-inner">
                      <span className="text-xs font-semibold text-gold block mb-2">
                        <BookText size={14} className="inline mr-1" /> Verified Catalog Books ({msg.suggestedBooks.length}):
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                        {msg.suggestedBooks.map((b, bIdx) => (
                          <div
                            key={b.isbn10 || bIdx}
                            onClick={() => setSelectedBook(b)}
                            className="p-2.5 rounded-lg portal-stat-card hover:border-gold cursor-pointer flex gap-3 items-center group transition-all"
                          >
                            <div className="w-10 h-14 bg-parchment rounded overflow-hidden shrink-0 border border-parchment flex items-center justify-center">
                              {b.thumbnail ? (
                                <img src={b.thumbnail} alt={b.title} className="w-full h-full object-cover" />
                              ) : (
                                <BookIcon size={24} className="opacity-50 text-ink-muted" />
                              )}
                            </div>
                            <div className="min-w-0 flex-1">
                              <h4 className="text-xs font-semibold text-navy truncate group-hover:text-gold transition-colors">
                                {b.title}
                              </h4>
                              <p className="text-[11px] text-ink-muted truncate">{b.authors || 'Unknown Author'}</p>
                              <div className="flex flex-wrap items-center gap-2 mt-1">
                                {b.is_available ? (
                                  <span className="text-[10px] font-mono text-emerald-700">✓ In Stock ({b.copies_available || 1})</span>
                                ) : (
                                  <span className="text-[10px] font-mono text-gold font-medium">
                                    ⏳ Back: {formatExpectedReturnDate(b.expected_return_date)}
                                  </span>
                                )}
                                {b.average_rating && (
                                  <span className="text-[10px] text-gold">★ {b.average_rating.toFixed(1)}</span>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}

            {loading && !isStreaming && (
              <div className="flex items-center gap-2 p-3 portal-stat-card rounded-xl max-w-xs text-xs text-ink-muted shadow-sm animate-pulse">
                <Zap size={14} className="animate-pulse text-gold" />
                <span>Generating fast ChatGPT response...</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Bar & Controls */}
          <div className="mt-3 pt-3 border-t border-parchment space-y-2">
            {/* Stop Generating Button */}
            {isStreaming && (
              <div className="flex justify-center">
                <button
                  type="button"
                  onClick={handleStopGenerating}
                  className="px-3 py-1 portal-stat-card hover:bg-parchment border border-parchment text-ink hover:text-navy rounded-lg text-xs font-medium flex items-center gap-1.5 shadow transition-all"
                >
                  <span className="w-2 h-2 bg-red-500 rounded-sm"></span>
                  <span>Stop generating</span>
                </button>
              </div>
            )}

            <form onSubmit={handleSend} className="flex gap-2">
              <input
                type="text"
                placeholder="Ask about a book, genre, theme, author, or mood..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading || isStreaming || historyLoading}
                className="flex-1 px-4 py-2.5 text-sm rounded-xl bg-cream-light border border-navy/30 text-ink placeholder-ink-muted focus:outline-none focus:border-gold focus:ring-1 focus:ring-gold disabled:opacity-50 transition-colors portal-input-gold"
              />
              <button
                type="submit"
                disabled={loading || isStreaming || historyLoading || !input.trim()}
                className="portal-btn-primary px-5 py-2.5 rounded-xl font-semibold text-xs uppercase tracking-wider disabled:opacity-50 shrink-0 shadow-md flex items-center gap-1"
              >
                <span>Send</span>
                <Send size={14} />
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Book Detail Modal */}
      <BookDetailModal
        book={selectedBook}
        onClose={() => setSelectedBook(null)}
      />
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-4xl mx-auto p-8 text-center text-gray-400">
          Loading Assistant...
        </div>
      }
    >
      <ChatContent />
    </Suspense>
  );
}

