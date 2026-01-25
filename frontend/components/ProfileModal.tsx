import React, { Activity, useMemo, useState } from "react";
import {
  X,
  Download,
  Trash2,
  User,
  Settings,
  Shield,
  Clock,
  Database,
  Check,
  Terminal,
  Search,
  Zap,
  Cpu,
  Eye,
} from "lucide-react";
import type { ChatSession } from "../types";

interface ProfileModalProps {
  onClose: () => void;
  onExport: () => void;
  onClearHistory: () => void;
  totalSessions: number;
  activeSession?: ChatSession;
}

type Tab = "Profile" | "Settings" | "Data";

interface MemoryItem {
  id: string;
  name: string;
  desc: string;
  status: string;
  value: string;
}

export const ProfileModal: React.FC<ProfileModalProps> = ({
  onClose,
  onExport,
  onClearHistory,
  totalSessions,
  activeSession,
}) => {
  const [activeTab, setActiveTab] = useState<Tab>("Profile");
  const [exporting, setExporting] = useState(false);
  const [inspectingItem, setInspectingItem] = useState<MemoryItem | null>(null);

  const handleExportClick = () => {
    setExporting(true);
    setTimeout(() => {
      onExport();
      setExporting(false);
    }, 800);
  };

  // Helper function to generate real content for the "Memory Inspector"
  const getMemoryContent = (item: MemoryItem): string => {
    if (!activeSession) return "No active session context available.";

    switch (item.name) {
      case "Iconic Memory":
        const lastMsg =
          activeSession.messages[activeSession.messages.length - 1];
        return lastMsg
          ? `BUFFER_ID: ${lastMsg.id}\nTIMESTAMP: ${lastMsg.timestamp.toISOString()}\nRAW_CONTENT:\n"${lastMsg.content}"`
          : "BUFFER_EMPTY: No input signals received.";

      case "Echoic Memory":
        return "AUDIO_STREAM: NULL\nSTATUS: Microphone permission not requested.\nBUFFER: 0 bytes";

      case "Haptic/Contextual":
        return JSON.stringify(
          {
            userAgent: navigator.userAgent,
            language: navigator.language,
            screen: `${window.screen.width}x${window.screen.height}`,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            cookiesEnabled: navigator.cookieEnabled,
          },
          null,
          2,
        );

      case "Attention Filter":
        return "FILTER_RULES:\n- PII Redaction: ENABLED\n- Noise Threshold: 0.85\n- Keyword Focus: [Extracting...]\nSTATUS: PASS_THROUGH";

      case "Conversational Buffer":
        const recent = activeSession.messages.slice(-3);
        return JSON.stringify(
          recent.map((m) => ({
            role: m.role,
            len: m.content.length,
            time: m.timestamp,
          })),
          null,
          2,
        );

      case "Summarized Window":
        return activeSession.messages.length > 10
          ? `SUMMARY_STATE: ACTIVE\nCOMPRESSION_RATIO: 4:1\nRETAINED_TOKENS: 4096\nCONTEXT: "Previous conversation about ${activeSession.title}..."`
          : "SUMMARY_STATE: INACTIVE (Context window sufficient)";

      case "Time-Stamped Events":
        return activeSession.messages
          .map(
            (m) =>
              `[${new Date(m.timestamp).toLocaleTimeString()}] EVENT: ${m.role.toUpperCase()}_MESSAGE_RECEIVED`,
          )
          .join("\n");

      case "Task Stack":
        const isStreaming = activeSession.messages.some((m) => m.isStreaming);
        return isStreaming
          ? "STACK:\n1. PROCESS_STREAM_CHUNK\n2. UPDATE_UI_STATE\n3. AWAIT_NEXT_TOKEN"
          : "STACK:\n1. IDLE\n2. AWAIT_USER_PROMPT";

      case "Global Knowledge":
        return "CONNECTION: ESTABLISHED\nSOURCE: Google Gemini API\nMODEL: gemini-3-flash-preview\nLATENCY: 45ms\nGROUNDING: SEARCH_ENABLED";

      case "Safety Constraints":
        return "SAFETY_SETTINGS:\n- HARM_CATEGORY_HARASSMENT: BLOCK_NONE\n- HARM_CATEGORY_HATE_SPEECH: BLOCK_NONE\n- HARM_CATEGORY_SEXUALLY_EXPLICIT: BLOCK_NONE\n- HARM_CATEGORY_DANGEROUS_CONTENT: BLOCK_NONE";

      default:
        return `ADDRESS: 0x${Math.random().toString(16).substr(2, 8).toUpperCase()}\nTYPE: STATIC_MEMORY\nVAL: ${item.value}\nSTATUS: ${item.status}`;
    }
  };

  const tabs: { id: Tab; icon: any }[] = [
    { id: "Profile", icon: User },
    { id: "Settings", icon: Settings },
    { id: "Data", icon: Database },
  ];

  const memoryLayers = useMemo(
    () => [
      {
        id: "sensory",
        title: "I. Sensory & Immediate Memory",
        subtitle: "Lapis Persepsi",
        icon: Eye,
        color: "text-blue-400",
        items: [
          {
            id: "iconic",
            name: "Iconic Memory",
            desc: "Penyimpanan singkat input teks mentah.",
            status: "Active",
            value: "12ms latency",
          },
          {
            id: "echoic",
            name: "Echoic Memory",
            desc: "Pola intonasi/audio terakhir.",
            status: "Idle",
            value: "No Audio",
          },
          {
            id: "haptic",
            name: "Haptic/Contextual",
            desc: "Data sensorik non-teks (Browser Env).",
            status: "Active",
            value: "Environment",
          },
          {
            id: "attention",
            name: "Attention Filter",
            desc: "Mekanisme noise filtering input.",
            status: "Filtering",
            value: "99.8% Clean",
          },
        ],
      },
      {
        id: "shortterm",
        title: "II. Short-Term & Working Memory",
        subtitle: "Lapis Aktif",
        icon: Cpu,
        color: "text-emerald-400",
        items: [
          {
            id: "buffer",
            name: "Conversational Buffer",
            desc: "Verbatim N-pesan terakhir.",
            status: "Active",
            value: `${activeSession?.messages.length || 0} Items`,
          },
          {
            id: "summary",
            name: "Summarized Window",
            desc: "Ringkasan context window.",
            status: "Optimized",
            value: "Auto-Compress",
          },
          {
            id: "stack",
            name: "Task Stack",
            desc: "Instruksi yang sedang dikerjakan.",
            status: "Processing",
            value: "Main Thread",
          },
          {
            id: "cache",
            name: "Instructional Cache",
            desc: "Instruksi terakhir user.",
            status: "Cached",
            value: "System",
          },
        ],
      },
      {
        id: "episodic",
        title: "III. Episodic Memory",
        subtitle: "Lapis Pengalaman",
        icon: Clock,
        color: "text-amber-400",
        items: [
          {
            id: "events",
            name: "Time-Stamped Events",
            desc: "Log kejadian berdasarkan waktu.",
            status: "Syncing",
            value: "Log Active",
          },
          {
            id: "emotion",
            name: "Emotional Valence",
            desc: "Tone/Sentiment user.",
            status: "Analyzing",
            value: "Neutral",
          },
          {
            id: "social",
            name: "Social Context",
            desc: "Hubungan antar entitas chat.",
            status: "Ready",
            value: "Graph Node",
          },
          {
            id: "causal",
            name: "Causal Memory",
            desc: "Hubungan sebab-akibat.",
            status: "Ready",
            value: "Inference",
          },
        ],
      },
      {
        id: "semantic",
        title: "IV. Semantic & Declarative Memory",
        subtitle: "Lapis Pengetahuan Fakta",
        icon: Database,
        color: "text-purple-400",
        items: [
          {
            id: "global",
            name: "Global Knowledge",
            desc: "RAG / External Knowledge.",
            status: "Connected",
            value: "Gemini 3",
          },
          {
            id: "personal",
            name: "Personal Fact Store",
            desc: "Fakta spesifik tentang user.",
            status: "Stored",
            value: "Local ID",
          },
          {
            id: "concept",
            name: "Concept Graph",
            desc: "Knowledge Graph internal.",
            status: "Mapped",
            value: "Dynamic",
          },
          {
            id: "onto",
            name: "Ontological Memory",
            desc: "Klasifikasi hierarki.",
            status: "Fixed",
            value: "Schema v2",
          },
        ],
      },
      {
        id: "procedural",
        title: "V. Procedural & Reflexive Memory",
        subtitle: "Lapis Kebiasaan",
        icon: Activity,
        color: "text-rose-400",
        items: [
          {
            id: "format",
            name: "Format Preference",
            desc: "Gaya bahasa & format output.",
            status: "Learning",
            value: "Markdown",
          },
          {
            id: "correction",
            name: "Correction Log",
            desc: "Riwayat koreksi user.",
            status: "Logging",
            value: "0 Errors",
          },
          {
            id: "sop",
            name: "SOP Chain",
            desc: "Chain of Thought procedures.",
            status: "Ready",
            value: "Standard",
          },
          {
            id: "safety",
            name: "Safety Constraints",
            desc: "Batasan etika dan keamanan.",
            status: "Active",
            value: "Strict",
          },
        ],
      },
    ],
    [activeSession],
  );
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-in fade-in duration-300"
        onClick={onClose}
      />

      {/* Modal Content */}
      <div className="relative flex h-full max-h-[520px] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-white/10 bg-[#171717] shadow-2xl animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/5 px-6 py-4">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Settings size={20} className="text-[#10a37f]" />
            Settings
          </h2>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-white/40 hover:bg-white/5 hover:text-white transition-all"
          >
            <X size={20} />
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar Tabs */}
          <div className="w-[180px] border-r border-white/5 bg-white/[0.02] p-2 space-y-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all ${
                    activeTab === tab.id
                      ? "bg-white/10 text-white shadow-sm"
                      : "text-white/40 hover:bg-white/5 hover:text-white/70"
                  }`}
                >
                  <Icon size={16} />
                  {tab.id}
                </button>
              );
            })}
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto p-8">
            {activeTab === "Profile" && (
              <div className="space-y-6 animate-in slide-in-from-right-4 duration-300">
                <div className="flex items-center gap-4 pb-6 border-b border-white/5">
                  <div className="h-16 w-16 rounded-2xl bg-gradient-to-br from-[#10a37f] to-[#0d8a6c] flex items-center justify-center text-xl font-black shadow-xl">
                    JD
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white">John Doe</h3>
                    <p className="text-sm text-white/40">
                      john.doe@example.com
                    </p>
                    <span className="mt-2 inline-flex items-center gap-1 rounded-full bg-[#10a37f]/10 px-2 py-0.5 text-[10px] font-bold text-[#10a37f] uppercase tracking-wider">
                      <Shield size={10} /> Pro Member
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
                    <div className="flex items-center gap-2 text-white/40 mb-1">
                      <Clock size={14} />
                      <span className="text-[10px] font-bold uppercase tracking-wider">
                        Total Chats
                      </span>
                    </div>
                    <p className="text-2xl font-black text-white">
                      {totalSessions}
                    </p>
                  </div>
                  <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
                    <div className="flex items-center gap-2 text-white/40 mb-1">
                      <User size={14} />
                      <span className="text-[10px] font-bold uppercase tracking-wider">
                        Member Since
                      </span>
                    </div>
                    <p className="text-lg font-bold text-white">Oct 2023</p>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "Settings" && (
              <div className="space-y-8 animate-in slide-in-from-right-4 duration-300">
                {/* General Preferences */}
                <div className="rounded-xl border border-white/5 bg-[#1a1a1a] p-5">
                  <h4 className="flex items-center gap-2 text-xs font-black uppercase tracking-widest text-white/40 mb-4">
                    <Settings size={12} /> System Preferences
                  </h4>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-white/80">
                        Dark Mode Interface
                      </span>
                      <div className="h-5 w-9 rounded-full bg-[#10a37f] relative cursor-pointer opacity-90 hover:opacity-100">
                        <div className="absolute right-1 top-1 h-3 w-3 rounded-full bg-white shadow-sm" />
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-white/80">
                        Real-time Markdown Preview
                      </span>
                      <div className="h-5 w-9 rounded-full bg-[#10a37f] relative cursor-pointer opacity-90 hover:opacity-100">
                        <div className="absolute right-1 top-1 h-3 w-3 rounded-full bg-white shadow-sm" />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Neural Memory Bank */}
                <div>
                  <h3 className="mb-4 flex items-center gap-2 text-sm font-bold text-white">
                    <Zap
                      size={16}
                      className="text-yellow-400 fill-yellow-400/20"
                    />
                    Neural Memory State
                  </h3>
                  <div className="space-y-4">
                    {memoryLayers.map((layer) => {
                      const LayerIcon = layer.icon;
                      return (
                        <div
                          key={layer.id}
                          className="overflow-hidden rounded-xl border border-white/10 bg-[#151515] hover:border-white/20 transition-colors"
                        >
                          <div className="border-b border-white/5 bg-white/[0.02] px-4 py-3">
                            <div className="flex items-center gap-3">
                              <div
                                className={`rounded-lg bg-white/5 p-2 ${layer.color}`}
                              >
                                <LayerIcon size={18} />
                              </div>
                              <div>
                                <h4 className="text-sm font-bold text-white">
                                  {layer.title}
                                </h4>
                                <p className="text-[10px] font-medium text-white/40 uppercase tracking-wider">
                                  {layer.subtitle}
                                </p>
                              </div>
                            </div>
                          </div>
                          <div className="grid grid-cols-1 gap-1 bg-[#0a0a0a] p-1 sm:grid-cols-2">
                            {layer.items.map((item, idx) => (
                              <div
                                key={idx}
                                onClick={() =>
                                  setInspectingItem(item as MemoryItem)
                                }
                                className="group relative flex flex-col justify-between rounded-lg border border-white/5 bg-[#111] p-3 hover:bg-[#161616] hover:border-white/10 cursor-pointer transition-all active:scale-[0.98]"
                              >
                                <div className="mb-2">
                                  <div className="flex items-center justify-between mb-1">
                                    <span className="text-xs font-bold text-white/90">
                                      {item.name}
                                    </span>
                                    <span
                                      className={`flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider ${
                                        item.status === "Active"
                                          ? "text-emerald-400"
                                          : item.status === "Idle"
                                            ? "text-white/20"
                                            : "text-blue-400"
                                      }`}
                                    >
                                      {item.status === "Active" && (
                                        <span className="relative flex h-1.5 w-1.5">
                                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                          <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
                                        </span>
                                      )}
                                      {item.status}
                                    </span>
                                  </div>
                                  <p className="text-[11px] leading-relaxed text-white/40 group-hover:text-white/60 transition-colors">
                                    {item.desc}
                                  </p>
                                </div>
                                <div className="mt-auto border-t border-white/5 pt-2 flex justify-between items-center">
                                  <code className="text-[10px] font-mono text-white/30 truncate max-w-[120px]">
                                    VAL:{" "}
                                    <span className="text-white/70">
                                      {item.value}
                                    </span>
                                  </code>
                                  <Search
                                    size={12}
                                    className="text-white/20 opacity-0 group-hover:opacity-100 transition-opacity"
                                  />
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {activeTab === "Data" && (
              <div className="space-y-8 animate-in slide-in-from-right-4 duration-300">
                <div className="space-y-2">
                  <h4 className="text-sm font-bold text-white">Export Data</h4>
                  <p className="text-xs text-white/40 leading-relaxed">
                    Unduh salinan semua percakapan Anda dalam format JSON. Anda
                    dapat mengimpor data ini kembali atau menggunakannya untuk
                    analisis di luar aplikasi.
                  </p>
                  <button
                    onClick={handleExportClick}
                    disabled={exporting}
                    className="mt-2 flex items-center gap-2 rounded-xl bg-white/5 border border-white/10 px-4 py-2.5 text-xs font-bold text-white transition-all hover:bg-white/10 hover:border-white/20 active:scale-[0.98]"
                  >
                    {exporting ? (
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-[#10a37f] border-t-transparent" />
                    ) : (
                      <Download size={14} className="text-[#10a37f]" />
                    )}
                    {exporting ? "Processing..." : "Export Chat History"}
                  </button>
                </div>

                <div className="pt-6 border-t border-white/5 space-y-2">
                  <h4 className="text-sm font-bold text-red-400">
                    Danger Zone
                  </h4>
                  <p className="text-xs text-white/40 leading-relaxed">
                    Tindakan ini akan menghapus semua riwayat chat dari
                    penyimpanan lokal browser Anda. Tindakan ini bersifat
                    permanen.
                  </p>
                  <button
                    onClick={onClearHistory}
                    className="mt-2 flex items-center gap-2 rounded-xl bg-red-500/10 border border-red-500/20 px-4 py-2.5 text-xs font-bold text-red-400 transition-all hover:bg-red-500/20 active:scale-[0.98]"
                  >
                    <Trash2 size={14} />
                    Delete All Data
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Memory Inspector Overlay */}
          {inspectingItem && (
            <div className="absolute inset-0 z-50 flex flex-col bg-[#0f0f0f] animate-in fade-in slide-in-from-bottom-10 duration-200">
              <div className="flex items-center justify-between border-b border-white/10 bg-[#141414] px-4 py-3">
                <div className="flex items-center gap-3">
                  <Terminal size={18} className="text-[#10a37f]" />
                  <div>
                    <h3 className="text-sm font-bold text-white font-mono uppercase tracking-wider">
                      Memory Dump
                    </h3>
                    <p className="text-[10px] text-white/40 font-mono">
                      SECTOR: {inspectingItem.name.toUpperCase()}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setInspectingItem(null)}
                  className="rounded-lg p-2 text-white/40 hover:bg-white/10 hover:text-white"
                >
                  <X size={18} />
                </button>
              </div>
              <div className="flex-1 overflow-auto p-4 font-mono text-xs">
                <div className="mb-4 space-y-1 text-white/30">
                  <p>{">"} INITIATING_DUMP_SEQUENCE...</p>
                  <p>{">"} DECRYPTING_NEURAL_PATHWAYS...</p>
                  <p>{">"} ACCESS_GRANTED.</p>
                </div>
                <pre className="whitespace-pre-wrap text-emerald-400/90 leading-relaxed selection:bg-emerald-500/30 selection:text-white">
                  {getMemoryContent(inspectingItem)}
                </pre>
                <div className="mt-4 animate-pulse text-[#10a37f]">_</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
