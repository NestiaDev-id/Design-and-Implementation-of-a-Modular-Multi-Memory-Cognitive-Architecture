import React, { useEffect, useRef, useState, useMemo } from "react";
import { Message } from "../types";
import {
  Bot,
  User,
  Sparkles,
  Terminal,
  Copy,
  Check,
  RefreshCw,
  Trash2,
  Edit3,
  X,
} from "lucide-react";
import hljs from "highlight.js";

interface CodeBlockProps {
  code: string;
  language: string;
  isShell: boolean;
}

const CodeBlock: React.FC<CodeBlockProps> = ({ code, language, isShell }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const highlightedCode = useMemo(() => {
    const validLanguage = hljs.getLanguage(language) ? language : "plaintext";
    return hljs.highlight(code.trim(), { language: validLanguage }).value;
  }, [code, language]);

  const lines = useMemo(() => code.trim().split("\n"), [code]);

  return (
    <div className="my-6 overflow-hidden rounded-xl border border-white/10 bg-[#0d0d0d] shadow-2xl group/code">
      <div className="flex items-center justify-between border-b border-white/5 bg-white/5 px-4 py-2">
        <div className="flex items-center gap-2">
          {isShell ? (
            <Terminal size={14} className="text-emerald-400" />
          ) : (
            <div className="h-2 w-2 rounded-full bg-blue-400" />
          )}
          <span className="text-[10px] font-bold uppercase tracking-widest text-white/40">
            {language || "text"}
          </span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 rounded-md px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-white/40 transition-colors hover:bg-white/10 hover:text-white"
        >
          {copied ? (
            <Check size={12} className="text-emerald-400" />
          ) : (
            <Copy size={12} />
          )}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <div className="flex overflow-x-auto font-mono text-sm leading-relaxed p-0">
        <div className="flex flex-col bg-white/[0.02] py-4 px-3 border-r border-white/5 select-none text-right">
          {lines.map((_, i) => (
            <span key={i} className="text-white/20 text-[12px] block h-[21px]">
              {i + 1}
            </span>
          ))}
        </div>
        <div className="flex-1 py-4 px-4 min-w-0">
          <pre className="m-0">
            <code
              className={`hljs ${isShell ? "text-emerald-400" : ""}`}
              dangerouslySetInnerHTML={{ __html: highlightedCode }}
            />
          </pre>
        </div>
      </div>
    </div>
  );
};

const renderInlineStyles = (text: string) => {
  if (!text.trim()) return <span>&nbsp;</span>;

  let segments: (string | React.ReactNode)[] = [text];

  // Inline Code `code`
  segments = segments.flatMap((seg) => {
    if (typeof seg !== "string") return seg;
    const parts = seg.split(/(`[^`]+`)/g);
    return parts.map((p, i) => {
      if (p.startsWith("`") && p.endsWith("`")) {
        return (
          <code
            key={i}
            className="bg-white/10 px-1.5 py-0.5 rounded text-emerald-400 font-mono text-[0.9em]"
          >
            {p.slice(1, -1)}
          </code>
        );
      }
      return p;
    });
  });

  // Bold **bold**
  segments = segments.flatMap((seg) => {
    if (typeof seg !== "string") return seg;
    const parts = seg.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((p, i) => {
      if (p.startsWith("**") && p.endsWith("**")) {
        return (
          <strong key={i} className="font-bold text-white">
            {p.slice(2, -2)}
          </strong>
        );
      }
      return p;
    });
  });

  // Italic *italic*
  segments = segments.flatMap((seg) => {
    if (typeof seg !== "string") return seg;
    const parts = seg.split(/(\*[^*]+\*)/g);
    return parts.map((p, i) => {
      if (p.startsWith("*") && p.endsWith("*")) {
        return (
          <em key={i} className="italic text-white/80">
            {p.slice(1, -1)}
          </em>
        );
      }
      return p;
    });
  });

  return segments;
};

export const MarkdownRenderer: React.FC<{ content: string }> = ({
  content,
}) => {
  const parts = content.split(/(```[\s\S]*?```)/g);

  return (
    <div className="flex flex-col gap-1 w-full">
      {parts.map((part, index) => {
        if (part.startsWith("```")) {
          const match = part.match(/```(\w+)?\n?([\s\S]*?)```/);
          const language = match?.[1] || "";
          const code = match?.[2] || "";
          const isShell = [
            "bash",
            "sh",
            "powershell",
            "ps1",
            "zsh",
            "shell",
          ].includes(language.toLowerCase());
          return (
            <CodeBlock
              key={index}
              code={code}
              language={language}
              isShell={isShell}
            />
          );
        }

        const lines = part.split("\n");
        return (
          <div key={index} className="flex flex-col gap-1">
            {lines.map((line, lineIdx) => {
              // Horizontal Rule (improved to handle longer dashes like ------ as requested)
              if (/^(\s*[-*_]){3,}\s*$/.test(line) || /^[-]{3,}$/.test(line)) {
                return <hr key={lineIdx} className="my-6 border-white/10" />;
              }

              // Headers (handles ### 1. Python correctly)
              const headerMatch = line.match(/^(#{1,6})\s+(.*)$/);
              if (headerMatch) {
                const level = headerMatch[1].length;
                const text = headerMatch[2];
                const fontSize =
                  level === 1
                    ? "text-2xl"
                    : level === 2
                      ? "text-xl"
                      : "text-lg";
                return (
                  <div
                    key={lineIdx}
                    className={`${fontSize} font-bold mt-4 mb-2 text-white leading-tight`}
                  >
                    {renderInlineStyles(text)}
                  </div>
                );
              }

              // List items
              const listMatch = line.match(/^(\s*)([*+-]|\d+\.)\s+(.*)$/);
              if (listMatch) {
                return (
                  <div key={lineIdx} className="flex gap-3 ml-4 my-1">
                    <span className="text-[#10a37f] font-bold select-none min-w-[1.2em]">
                      {listMatch[2]}
                    </span>
                    <span className="flex-1">
                      {renderInlineStyles(listMatch[3])}
                    </span>
                  </div>
                );
              }

              if (!line.trim()) {
                return <div key={lineIdx} className="h-2" />;
              }

              return (
                <div key={lineIdx} className="leading-relaxed">
                  {renderInlineStyles(line)}
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
};

interface ChatAreaProps {
  messages: Message[];
  isTyping: boolean;
  onDeleteMessage: (id: string) => void;
  onEditMessage: (id: string, content: string) => void;
  onRegenerate: (id: string) => void;
}

export const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  isTyping,
  onDeleteMessage,
  onEditMessage,
  onRegenerate,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const formatTime = (date: Date) => {
    return new Intl.DateTimeFormat("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    }).format(date);
  };

  const handleStartEdit = (message: Message) => {
    setEditingMessageId(message.id);
    setEditValue(message.content);
  };

  const handleSaveEdit = (id: string) => {
    onEditMessage(id, editValue);
    setEditingMessageId(null);
  };

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center text-center px-4">
        <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-white/5 text-white/20 shadow-xl border border-white/10">
          <Sparkles size={32} />
        </div>
        <h1 className="mb-2 text-2xl font-bold text-white">
          How can I help you today?
        </h1>
        <p className="max-w-md text-sm text-white/50">
          Tanyakan apa saja, dari penulisan kode, ringkasan teks, hingga diskusi
          kreatif.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto py-10">
      <div className="mx-auto max-w-3xl px-4 md:px-6">
        {messages.map((message) => {
          const isUser = message.role === "user";
          const isEditing = editingMessageId === message.id;

          return (
            <div
              key={message.id}
              className={`mb-10 last:mb-0 flex w-full group ${isUser ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`flex gap-4 md:gap-6 max-w-[90%] ${isUser ? "flex-row-reverse text-right" : "flex-row"}`}
              >
                <div
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl shadow-lg transition-transform hover:scale-105 ${
                    isUser
                      ? "bg-white/10 ring-1 ring-white/10"
                      : "bg-gradient-to-br from-[#10a37f] to-[#0d8a6c]"
                  }`}
                >
                  {isUser ? (
                    <User size={20} className="text-white/80" />
                  ) : (
                    <Bot size={20} className="text-white" />
                  )}
                </div>

                <div
                  className={`flex flex-1 flex-col gap-1.5 overflow-hidden ${isUser ? "items-end" : "items-start"}`}
                >
                  <div
                    className={`flex items-center gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
                  >
                    <p className="text-[10px] font-black text-white uppercase tracking-widest opacity-30">
                      {isUser ? "You" : "Gemini"}
                    </p>
                    <span className="text-[10px] font-medium text-white/20 tabular-nums">
                      {formatTime(message.timestamp)}
                    </span>
                  </div>

                  <div
                    className={`group/bubble relative prose prose-invert max-w-none text-[15px] leading-relaxed text-white/90 whitespace-pre-wrap break-words px-5 py-3 rounded-2xl transition-all duration-200 ${
                      isUser
                        ? "bg-white/[0.03] border border-white/5 text-right rounded-tr-none"
                        : "bg-transparent text-left rounded-tl-none"
                    }`}
                  >
                    {isEditing ? (
                      <div className="flex flex-col gap-2">
                        <textarea
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          className="w-full bg-white/5 border border-white/10 rounded-lg p-2 text-white outline-none focus:ring-1 focus:ring-[#10a37f] min-h-[100px]"
                        />
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => setEditingMessageId(null)}
                            className="p-1 text-white/40 hover:text-white"
                          >
                            <X size={16} />
                          </button>
                          <button
                            onClick={() => handleSaveEdit(message.id)}
                            className="px-3 py-1 bg-[#10a37f] text-white text-xs rounded-md font-bold"
                          >
                            Simpan
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <MarkdownRenderer content={message.content} />
                        {message.isStreaming && (
                          <span className="ml-1 inline-block h-4 w-1 animate-pulse bg-[#10a37f]" />
                        )}
                      </>
                    )}
                  </div>

                  <div
                    className={`flex gap-3 mt-1 opacity-0 group-hover:opacity-100 transition-opacity ${isUser ? "flex-row-reverse" : "flex-row"}`}
                  >
                    {isUser ? (
                      <>
                        <button
                          onClick={() => handleStartEdit(message)}
                          className="flex items-center gap-1 text-[10px] font-bold text-white/30 hover:text-white transition-colors"
                        >
                          <Edit3 size={12} /> Edit
                        </button>
                        <button
                          onClick={() => onDeleteMessage(message.id)}
                          className="flex items-center gap-1 text-[10px] font-bold text-white/30 hover:text-red-400 transition-colors"
                        >
                          <Trash2 size={12} /> Hapus
                        </button>
                      </>
                    ) : (
                      !message.isStreaming && (
                        <button
                          onClick={() => onRegenerate(message.id)}
                          className="flex items-center gap-1 text-[10px] font-bold text-white/30 hover:text-[#10a37f] transition-colors"
                        >
                          <RefreshCw size={12} /> Generate Ulang
                        </button>
                      )
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}

        {isTyping && !messages.some((m) => m.isStreaming) && (
          <div className="flex justify-start mb-8">
            <div className="flex gap-4 md:gap-6 items-start">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-linear-to-br from-[#10a37f] to-[#0d8a6c] shadow-lg animate-pulse">
                <Bot size={20} className="text-white" />
              </div>
              <div className="flex flex-col gap-2 pt-1">
                <div className="flex items-center gap-2">
                  <p className="text-[10px] font-black text-white uppercase tracking-widest opacity-30">
                    Gemini
                  </p>
                </div>
                <div className="flex gap-1.5 mt-1 px-4 py-3 bg-white/5 rounded-2xl rounded-tl-none border border-white/5 shadow-inner">
                  <div className="h-1.5 w-1.5 rounded-full bg-[#10a37f]/80 animate-bounce [animation-delay:-0.3s]"></div>
                  <div className="h-1.5 w-1.5 rounded-full bg-[#10a37f]/80 animate-bounce [animation-delay:-0.15s]"></div>
                  <div className="h-1.5 w-1.5 rounded-full bg-[#10a37f]/80 animate-bounce"></div>
                </div>
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} className="h-20" />
      </div>
    </div>
  );
};
