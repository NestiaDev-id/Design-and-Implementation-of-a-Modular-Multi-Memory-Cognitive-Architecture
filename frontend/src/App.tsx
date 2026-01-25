import React, { useState, useEffect } from "react";
import { Sidebar } from "../components/Sidebar";
import { ChatArea } from "../components/ChatArea";
import { MessageInput } from "../components/MessageInput";
import { ProfileModal } from "../components/ProfileModal";
import type { ChatSession, Message } from "../types";
import { v4 as uuidv4 } from "uuid";

// API Configuration
const API_BASE_URL = "http://localhost:8000";

// API Helper Functions
const api = {
  async createSession(title: string = "New Chat") {
    const response = await fetch(`${API_BASE_URL}/sessions/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    return response.json();
  },

  async listSessions() {
    const response = await fetch(`${API_BASE_URL}/sessions/`);
    return response.json();
  },

  async getSession(sessionId: string) {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`);
    return response.json();
  },

  async deleteSession(sessionId: string) {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
      method: "DELETE",
    });
    return response.json();
  },

  async chat(sessionId: string, message: string) {
    const response = await fetch(`${API_BASE_URL}/chat/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    });
    return response.json();
  },

  async chatStream(sessionId: string, message: string) {
    const response = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    });
    return response;
  },

  async regenerate(sessionId: string, messageId: string) {
    const response = await fetch(`${API_BASE_URL}/chat/regenerate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message_id: messageId }),
    });
    return response.json();
  },

  async deleteMessage(sessionId: string, messageId: string) {
    const response = await fetch(
      `${API_BASE_URL}/sessions/${sessionId}/messages/${messageId}`,
      { method: "DELETE" }
    );
    return response.json();
  },
};

const App: React.FC = () => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [isOnline, setIsOnline] = useState(false);

  // Check API health and load sessions
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
          setIsOnline(true);
          loadSessions();
        }
      } catch {
        setIsOnline(false);
        // Fallback to local storage
        const savedSessions = localStorage.getItem("gemini_chats");
        if (savedSessions) {
          const parsed = JSON.parse(savedSessions).map((s: any) => ({
            ...s,
            updatedAt: new Date(s.updatedAt),
            messages: s.messages.map((m: any) => ({
              ...m,
              timestamp: new Date(m.timestamp),
            })),
          }));
          setSessions(parsed);
          if (parsed.length > 0) setActiveSessionId(parsed[0].id);
        } else {
          handleNewChat();
        }
      }
    };

    checkHealth();
  }, []);

  const loadSessions = async () => {
    try {
      const data = await api.listSessions();
      const loadedSessions: ChatSession[] = data.sessions.map((s: any) => ({
        id: s.id,
        title: s.title,
        messages: [],
        updatedAt: new Date(s.updated_at),
      }));
      setSessions(loadedSessions);
      if (loadedSessions.length > 0) {
        setActiveSessionId(loadedSessions[0].id);
        // Load messages for first session
        const sessionDetail = await api.getSession(loadedSessions[0].id);
        loadedSessions[0].messages = sessionDetail.messages.map((m: any) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          timestamp: new Date(m.timestamp),
        }));
        setSessions([...loadedSessions]);
      } else {
        handleNewChat();
      }
    } catch (error) {
      console.error("Failed to load sessions:", error);
    }
  };

  // Save to local storage as backup
  useEffect(() => {
    if (sessions.length > 0) {
      localStorage.setItem("gemini_chats", JSON.stringify(sessions));
    }
  }, [sessions]);

  const activeSession = sessions.find((s) => s.id === activeSessionId);

  const handleNewChat = async () => {
    if (isOnline) {
      try {
        const data = await api.createSession("New Chat");
        const newSession: ChatSession = {
          id: data.id,
          title: data.title,
          messages: [],
          updatedAt: new Date(data.updated_at),
        };
        setSessions((prev) => [newSession, ...prev]);
        setActiveSessionId(newSession.id);
      } catch (error) {
        console.error("Failed to create session:", error);
      }
    } else {
      // Offline fallback
      const newSession: ChatSession = {
        id: uuidv4(),
        title: "New Chat",
        messages: [],
        updatedAt: new Date(),
      };
      setSessions((prev) => [newSession, ...prev]);
      setActiveSessionId(newSession.id);
    }
  };

  const handleSelectSession = async (sessionId: string) => {
    setActiveSessionId(sessionId);

    if (isOnline) {
      try {
        const sessionDetail = await api.getSession(sessionId);
        setSessions((prev) =>
          prev.map((s) =>
            s.id === sessionId
              ? {
                  ...s,
                  messages: sessionDetail.messages.map((m: any) => ({
                    id: m.id,
                    role: m.role,
                    content: m.content,
                    timestamp: new Date(m.timestamp),
                  })),
                }
              : s
          )
        );
      } catch (error) {
        console.error("Failed to load session:", error);
      }
    }
  };

  const handleSendMessage = async (text: string) => {
    if (!text.trim() || !activeSessionId) return;

    const userMsg: Message = {
      id: uuidv4(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };

    // Optimistically add user message
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id === activeSessionId) {
          const isFirstMessage = s.messages.length === 0;
          return {
            ...s,
            title: isFirstMessage
              ? text.slice(0, 30) + (text.length > 30 ? "..." : "")
              : s.title,
            messages: [...s.messages, userMsg],
            updatedAt: new Date(),
          };
        }
        return s;
      })
    );

    setIsTyping(true);

    try {
      if (isOnline) {
        // Use SSE streaming
        const aiMsgId = uuidv4();

        // Add placeholder for AI message
        setSessions((prev) =>
          prev.map((s) => {
            if (s.id === activeSessionId) {
              return {
                ...s,
                messages: [
                  ...s.messages,
                  {
                    id: aiMsgId,
                    role: "model" as const,
                    content: "",
                    timestamp: new Date(),
                    isStreaming: true,
                  },
                ],
              };
            }
            return s;
          })
        );

        const response = await api.chatStream(activeSessionId, text);
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let fullContent = "";

        if (reader) {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split("\n");

            for (const line of lines) {
              if (line.startsWith("data: ")) {
                try {
                  const data = JSON.parse(line.slice(6));
                  if (data.content) {
                    fullContent += data.content;
                    setSessions((prev) =>
                      prev.map((s) => {
                        if (s.id === activeSessionId) {
                          return {
                            ...s,
                            messages: s.messages.map((m) =>
                              m.id === aiMsgId
                                ? { ...m, content: fullContent }
                                : m
                            ),
                          };
                        }
                        return s;
                      })
                    );
                  }
                  if (data.done) {
                    setSessions((prev) =>
                      prev.map((s) => {
                        if (s.id === activeSessionId) {
                          return {
                            ...s,
                            messages: s.messages.map((m) =>
                              m.id === aiMsgId
                                ? { ...m, isStreaming: false }
                                : m
                            ),
                          };
                        }
                        return s;
                      })
                    );
                  }
                } catch {
                  // Ignore parse errors
                }
              }
            }
          }
        }
      } else {
        // Offline fallback - show error
        const errorMsg: Message = {
          id: uuidv4(),
          role: "model",
          content: "⚠️ API tidak tersedia. Silakan jalankan server API terlebih dahulu.",
          timestamp: new Date(),
        };
        setSessions((prev) =>
          prev.map((s) =>
            s.id === activeSessionId
              ? { ...s, messages: [...s.messages, errorMsg] }
              : s
          )
        );
      }
    } catch (error) {
      console.error("Chat error:", error);
      const errorMsg: Message = {
        id: uuidv4(),
        role: "model",
        content: "Maaf, terjadi kesalahan. Silakan coba lagi.",
        timestamp: new Date(),
      };
      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSessionId
            ? { ...s, messages: [...s.messages, errorMsg] }
            : s
        )
      );
    } finally {
      setIsTyping(false);
    }
  };

  const handleEditMessage = async (messageId: string, newContent: string) => {
    if (!activeSessionId || !newContent.trim()) return;
    const session = sessions.find((s) => s.id === activeSessionId);
    if (!session) return;
    const msgIndex = session.messages.findIndex((m) => m.id === messageId);
    if (msgIndex === -1) return;

    const updatedMessages = session.messages
      .slice(0, msgIndex + 1)
      .map((m) =>
        m.id === messageId
          ? { ...m, content: newContent, timestamp: new Date() }
          : m
      );

    setSessions((prev) =>
      prev.map((s) =>
        s.id === activeSessionId
          ? { ...s, messages: updatedMessages, updatedAt: new Date() }
          : s
      )
    );

    // Re-send the edited message
    const editedMessage = updatedMessages[msgIndex];
    if (editedMessage.role === "user") {
      await handleSendMessage(newContent);
    }
  };

  const handleDeleteMessage = async (messageId: string) => {
    if (!activeSessionId) return;

    if (isOnline) {
      try {
        await api.deleteMessage(activeSessionId, messageId);
      } catch (error) {
        console.error("Failed to delete message:", error);
      }
    }

    setSessions((prev) =>
      prev.map((s) =>
        s.id === activeSessionId
          ? {
              ...s,
              messages: s.messages.filter((m) => m.id !== messageId),
              updatedAt: new Date(),
            }
          : s
      )
    );
  };

  const handleRegenerate = async (messageId: string) => {
    if (!activeSessionId || !isOnline) return;

    setIsTyping(true);

    try {
      const response = await api.regenerate(activeSessionId, messageId);

      // Reload session to get updated messages
      const sessionDetail = await api.getSession(activeSessionId);
      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSessionId
            ? {
                ...s,
                messages: sessionDetail.messages.map((m: any) => ({
                  id: m.id,
                  role: m.role,
                  content: m.content,
                  timestamp: new Date(m.timestamp),
                })),
                updatedAt: new Date(),
              }
            : s
        )
      );
    } catch (error) {
      console.error("Regenerate error:", error);
    } finally {
      setIsTyping(false);
    }
  };

  const handleDeleteSession = async (id: string) => {
    if (isOnline) {
      try {
        await api.deleteSession(id);
      } catch (error) {
        console.error("Failed to delete session:", error);
      }
    }

    setSessions((prev) => prev.filter((s) => s.id !== id));
    if (activeSessionId === id) {
      const remaining = sessions.filter((s) => s.id !== id);
      if (remaining.length > 1) setActiveSessionId(remaining[0].id);
      else handleNewChat();
    }
  };

  const handleExportData = () => {
    const dataStr = JSON.stringify(sessions, null, 2);
    const blob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `cognitive-memory-export-${new Date().toISOString().split("T")[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleClearHistory = () => {
    if (
      confirm(
        "Apakah Anda yakin ingin menghapus semua chat history? Tindakan ini tidak dapat dibatalkan."
      )
    ) {
      localStorage.removeItem("gemini_chats");
      setSessions([]);
      handleNewChat();
      setIsProfileModalOpen(false);
    }
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#212121] text-[#ececec]">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        onOpenProfile={() => setIsProfileModalOpen(true)}
      />
      <main className="relative flex flex-1 flex-col overflow-hidden">
        {/* API Status Indicator */}
        <div className="absolute top-2 right-2 z-10">
          <div
            className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs ${
              isOnline
                ? "bg-green-500/20 text-green-400"
                : "bg-red-500/20 text-red-400"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isOnline ? "bg-green-400" : "bg-red-400"
              }`}
            />
            {isOnline ? "Qwen API" : "Offline"}
          </div>
        </div>

        <ChatArea
          messages={activeSession?.messages || []}
          isTyping={isTyping}
          onDeleteMessage={handleDeleteMessage}
          onEditMessage={handleEditMessage}
          onRegenerate={handleRegenerate}
        />
        <MessageInput onSend={handleSendMessage} disabled={isTyping} />
      </main>

      {isProfileModalOpen && (
        <ProfileModal
          onClose={() => setIsProfileModalOpen(false)}
          onExport={handleExportData}
          onClearHistory={handleClearHistory}
          totalSessions={sessions.length}
        />
      )}
    </div>
  );
};

export default App;
