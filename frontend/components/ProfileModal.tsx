import React, { useState } from "react";
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
} from "lucide-react";

interface ProfileModalProps {
  onClose: () => void;
  onExport: () => void;
  onClearHistory: () => void;
  totalSessions: number;
}

type Tab = "Profile" | "Settings" | "Data";

export const ProfileModal: React.FC<ProfileModalProps> = ({
  onClose,
  onExport,
  onClearHistory,
  totalSessions,
}) => {
  const [activeTab, setActiveTab] = useState<Tab>("Profile");
  const [exporting, setExporting] = useState(false);

  const handleExportClick = () => {
    setExporting(true);
    setTimeout(() => {
      onExport();
      setExporting(false);
    }, 800);
  };

  const tabs: { id: Tab; icon: any }[] = [
    { id: "Profile", icon: User },
    { id: "Settings", icon: Settings },
    { id: "Data", icon: Database },
  ];

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
              <div className="space-y-6 animate-in slide-in-from-right-4 duration-300">
                <div className="space-y-4">
                  <h4 className="text-[10px] font-black uppercase tracking-widest text-white/20">
                    Preferences
                  </h4>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-white/80">Dark Mode</span>
                    <div className="h-5 w-9 rounded-full bg-[#10a37f] relative">
                      <div className="absolute right-1 top-1 h-3 w-3 rounded-full bg-white shadow-sm" />
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-white/80">Live Preview</span>
                    <div className="h-5 w-9 rounded-full bg-[#10a37f] relative">
                      <div className="absolute right-1 top-1 h-3 w-3 rounded-full bg-white shadow-sm" />
                    </div>
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
        </div>
      </div>
    </div>
  );
};
