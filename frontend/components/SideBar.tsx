import React, { useMemo } from "react";
import {
  Plus,
  MessageSquare,
  Trash2,
  User,
  MoreVertical,
  LogOut,
  Settings,
} from "lucide-react";
import { ChatSession, TimeGroup } from "../types";

interface SidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onDeleteSession: (id: string) => void;
  onOpenProfile: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  onOpenProfile,
}) => {
  const groupedSessions = useMemo(() => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const lastWeek = new Date(today);
    lastWeek.setDate(lastWeek.getDate() - 7);

    const groups: Record<TimeGroup, ChatSession[]> = {
      Today: [],
      Yesterday: [],
      "Last 7 Days": [],
      Older: [],
    };

    sessions.forEach((session) => {
      const date = new Date(session.updatedAt);
      if (date >= today) groups["Today"].push(session);
      else if (date >= yesterday) groups["Yesterday"].push(session);
      else if (date >= lastWeek) groups["Last 7 Days"].push(session);
      else groups["Older"].push(session);
    });

    return groups;
  }, [sessions]);

  return (
    <aside className="moving-bg relative flex h-full w-[260px] flex-col border-r border-white/10 p-2 transition-all duration-300">
      {/* New Chat Button */}
      <button
        onClick={onNewChat}
        className="mb-4 flex w-full items-center gap-3 rounded-xl border border-white/10 bg-white/5 p-3 text-sm font-semibold hover:bg-white/10 transition-all active:scale-[0.98] shadow-sm"
      >
        <Plus size={18} className="text-[#10a37f]" />
        New Chat
      </button>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto pr-1">
        {(Object.entries(groupedSessions) as [TimeGroup, ChatSession[]][]).map(
          ([group, groupSessions]) =>
            groupSessions.length > 0 && (
              <div key={group} className="mb-6">
                <h3 className="mb-2 px-3 text-[10px] font-black uppercase tracking-[0.1em] text-white/30">
                  {group}
                </h3>
                <div className="space-y-1">
                  {groupSessions.map((session) => (
                    <div
                      key={session.id}
                      onClick={() => onSelectSession(session.id)}
                      className={`group relative flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all duration-200 hover:bg-white/5 ${
                        activeSessionId === session.id
                          ? "bg-white/10 shadow-sm"
                          : ""
                      }`}
                    >
                      <MessageSquare
                        size={14}
                        className={`shrink-0 ${activeSessionId === session.id ? "text-[#10a37f]" : "text-white/40"}`}
                      />
                      <span
                        className={`flex-1 truncate transition-colors ${activeSessionId === session.id ? "text-white font-medium" : "text-white/70"}`}
                      >
                        {session.title}
                      </span>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteSession(session.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 text-white/30 hover:text-red-400 transition-all hover:scale-110"
                      >
                        <Trash2 size={14} />
                      </button>

                      {activeSessionId === session.id && (
                        <div className="absolute left-0 h-4 w-1 bg-[#10a37f] rounded-r-full" />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ),
        )}
      </div>

      {/* User Profile Footer */}
      <div className="mt-auto border-t border-white/10 pt-2">
        <button
          onClick={onOpenProfile}
          className="flex w-full items-center gap-3 rounded-xl p-3 text-sm hover:bg-white/10 transition-all active:scale-[0.98] group"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-[#10a37f] to-[#0d8a6c] text-[10px] font-black text-white shadow-lg group-hover:scale-105 transition-transform">
            JD
          </div>
          <div className="flex flex-1 flex-col items-start truncate">
            <span className="font-bold text-white/90 text-xs">John Doe</span>
            <span className="text-[10px] text-white/30 font-medium">
              Free Plan
            </span>
          </div>
          <MoreVertical
            size={14}
            className="text-white/20 group-hover:text-white/50 transition-colors"
          />
        </button>
      </div>
    </aside>
  );
};
