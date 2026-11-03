import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './pages/Dashboard';
import { SetupCenter } from './pages/SetupCenter';
import { CharacterVault } from './pages/CharacterVault';
import { EpisodeStudio } from './pages/EpisodeStudio';
import { RenderPublish } from './pages/RenderPublish';
import { useStore } from './store/useStore';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export const App: React.FC = () => {
  const { toasts, removeToast, fetchSettings, fetchServicesStatus } = useStore();

  useEffect(() => {
    // Laad services status en configuratie bij initiële load
    fetchSettings();
    fetchServicesStatus();
  }, [fetchSettings, fetchServicesStatus]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 text-slate-100 font-sans selection:bg-indigo-500 selection:text-white">
      {/* Studio Navigation Sidebar */}
      <Sidebar />

      {/* Main Studio Viewport */}
      <main className="flex-1 h-screen overflow-y-auto custom-scrollbar relative bg-[#0b0f19]">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/setup" element={<SetupCenter />} />
          <Route path="/characters" element={<CharacterVault />} />
          <Route path="/episodes/:id" element={<EpisodeStudio />} />
          <Route path="/render/:id" element={<RenderPublish />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>

        {/* Global Toast Notifications Container */}
        <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2.5 max-w-sm pointer-events-none">
          {toasts.map((toast) => (
            <div
              key={toast.id}
              className={`pointer-events-auto flex items-start gap-3 p-4 rounded-2xl border shadow-2xl backdrop-blur-md animate-in slide-in-from-bottom-5 duration-200 ${
                toast.type === 'success'
                  ? 'bg-emerald-950/90 border-emerald-500/40 text-emerald-200'
                  : toast.type === 'error'
                  ? 'bg-rose-950/90 border-rose-500/40 text-rose-200'
                  : 'bg-slate-900/90 border-slate-700/60 text-slate-200'
              }`}
            >
              {toast.type === 'success' && <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />}
              {toast.type === 'error' && <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />}
              {toast.type === 'info' && <Info className="w-5 h-5 text-indigo-400 shrink-0" />}

              <div className="text-xs font-medium leading-relaxed flex-1">{toast.message}</div>

              <button
                onClick={() => removeToast(toast.id)}
                className="text-slate-400 hover:text-slate-100 p-0.5 rounded transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
};

export default App;

