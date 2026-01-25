import React, { useState, useRef, useEffect } from "react";
import { Send, Paperclip, ArrowUp, Eye, EyeOff, Sparkles } from "lucide-react";
import { MarkdownRenderer } from "./ChatArea";

interface MessageInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export const MessageInput: React.FC<MessageInputProps> = ({
  onSend,
  disabled,
}) => {
  const [text, setText] = useState("");
  const [showPreview, setShowPreview] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const adjustHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      const newHeight = Math.min(textarea.scrollHeight, 200);
      textarea.style.height = `${newHeight}px`;
    }
  };

  useEffect(() => {
    adjustHeight();
  }, [text]);

  const handleSend = () => {
    if (text.trim() && !disabled) {
      onSend(text.trim());
      setText("");
      setShowPreview(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="w-full bg-gradient-to-t from-[#212121] via-[#212121] to-transparent pb-6 pt-2">
      <div className="mx-auto max-w-3xl px-4 md:px-6">
        {/* Live Preview Area */}
        {showPreview && text.trim() && (
          <div className="mb-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <div className="flex items-center gap-2 mb-2 px-2">
              <Sparkles size={12} className="text-[#10a37f]" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-white/40">
                Preview Rendering
              </span>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 text-[15px] max-h-[300px] overflow-y-auto shadow-2xl backdrop-blur-sm">
              <MarkdownRenderer content={text} />
            </div>
          </div>
        )}

        {/* Input Bar */}
        <div
          className={`relative flex flex-col rounded-2xl border border-white/10 bg-[#2f2f2f] shadow-2xl transition-all duration-300 ${disabled ? "opacity-50" : "focus-within:border-white/20"}`}
        >
          <div className="flex items-end p-2 md:p-3">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="mb-1 flex h-9 w-9 items-center justify-center rounded-lg text-white/50 hover:bg-white/5 hover:text-white transition-all"
              title="Upload file"
            >
              <Paperclip size={18} />
              <input type="file" ref={fileInputRef} className="hidden" />
            </button>

            <textarea
              ref={textareaRef}
              rows={1}
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message Gemini..."
              disabled={disabled}
              className="max-h-[200px] flex-1 resize-none bg-transparent px-3 py-2 text-[15px] leading-relaxed text-white placeholder-white/30 outline-none"
            />

            <div className="flex items-center gap-1 mb-1">
              <button
                onClick={() => setShowPreview(!showPreview)}
                className={`flex h-9 w-9 items-center justify-center rounded-lg transition-all ${
                  showPreview
                    ? "bg-[#10a37f]/20 text-[#10a37f]"
                    : "text-white/50 hover:bg-white/5 hover:text-white"
                }`}
                title={showPreview ? "Hide preview" : "Show preview"}
              >
                {showPreview ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>

              <button
                onClick={handleSend}
                disabled={!text.trim() || disabled}
                className={`flex h-9 w-9 items-center justify-center rounded-lg transition-all ${
                  text.trim() && !disabled
                    ? "bg-white text-black hover:bg-white/90 scale-100 active:scale-95"
                    : "bg-white/5 text-white/20 cursor-not-allowed"
                }`}
              >
                {disabled ? (
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                ) : (
                  <ArrowUp size={18} strokeWidth={3} />
                )}
              </button>
            </div>
          </div>
        </div>

        <p className="mt-3 text-center text-[11px] text-white/20 font-medium">
          Gemini can make mistakes. Check important info.
        </p>
      </div>
    </div>
  );
};
