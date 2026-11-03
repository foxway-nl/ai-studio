import React, { useEffect, useState } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Save,
  RefreshCw,
  ExternalLink,
  Key,
  Server,
  Cpu,
  Video,
  Mic,
  Sparkles,
} from 'lucide-react';
import { useStore } from '../store/useStore';
import type { Settings } from '../api/client';

export const SetupCenter: React.FC = () => {
  const {
    settings,
    servicesStatus,
    fetchSettings,
    fetchServicesStatus,
    saveSettings,
    testConnection,
  } = useStore();

  const [formData, setFormData] = useState<Partial<Settings>>({
    gemini_api_key: '',
    ollama_url: '',
    sd_webui_url: '',
    piper_path: '',
    kokoro_url: '',
    youtube_client_id: '',
    youtube_client_secret: '',
  });

  const [testingService, setTestingService] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { connected: boolean; message: string }>>({});
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    fetchSettings();
    fetchServicesStatus();
  }, [fetchSettings, fetchServicesStatus]);

  useEffect(() => {
    if (settings) {
      setFormData({
        gemini_api_key: settings.gemini_api_key || '',
        ollama_url: settings.ollama_url || 'http://host.docker.internal:11434',
        sd_webui_url: settings.sd_webui_url || 'http://host.docker.internal:7860',
        piper_path: settings.piper_path || '/data/piper-models',
        kokoro_url: settings.kokoro_url || 'http://host.docker.internal:8080',
        youtube_client_id: settings.youtube_client_id || '',
        youtube_client_secret: settings.youtube_client_secret || '',
      });
    }
  }, [settings]);

  const handleInputChange = (field: keyof Settings, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    await saveSettings(formData);
    await fetchServicesStatus();
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  const handleTest = async (serviceName: string) => {
    setTestingService(serviceName);
    try {
      const res = await testConnection(serviceName);
      setTestResults((prev) => ({
        ...prev,
        [serviceName]: { connected: res.connected, message: res.message },
      }));
      await fetchServicesStatus();
    } finally {
      setTestingService(null);
    }
  };

  const getServiceConnected = (name: string): boolean => {
    const s = servicesStatus.find((item) => item.name.toLowerCase().includes(name.toLowerCase()));
    return s?.connected ?? false;
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <ShieldCheck className="w-8 h-8 text-indigo-400" />
            <span>Setup & Status Centrum</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            AI-Studio vereist geen verplichte cloud API's om te starten. Configureer hieronder je gewenste
            services. Alle sleutels worden veilig opgeslagen in je lokale Docker-volume (<code className="text-indigo-300 font-mono">/data</code>).
          </p>
        </div>

        <button
          onClick={handleSave}
          className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm transition-all shadow-lg shadow-indigo-600/25 active:scale-95 shrink-0"
        >
          <Save className="w-4 h-4" />
          <span>{saveSuccess ? 'Opgeslagen!' : 'Instellingen Opslaan'}</span>
        </button>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* 1. Google Gemini API */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                  <span>Google Gemini API</span>
                  {getServiceConnected('gemini') ? (
                    <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                      <CheckCircle2 className="w-3 h-3" /> Verbonden
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[11px] font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
                      Niet gekoppeld
                    </span>
                  )}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Verzorgt scriptgeneratie voor kleuters, virale YouTube SEO, promptvertaling en Imagen 3.
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => handleTest('gemini')}
              disabled={testingService === 'gemini'}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition-colors shrink-0 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${testingService === 'gemini' ? 'animate-spin' : ''}`} />
              <span>Test Verbinding</span>
            </button>
          </div>

          <div className="space-y-2">
            <label className="block text-xs font-semibold text-slate-300">Gemini API-sleutel</label>
            <div className="relative">
              <Key className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
              <input
                type="password"
                value={formData.gemini_api_key || ''}
                onChange={(e) => handleInputChange('gemini_api_key', e.target.value)}
                placeholder="AIzaSy..."
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm font-mono"
              />
            </div>
            <p className="text-xs text-slate-400 flex items-center gap-1.5 pt-1">
              <HelpCircle className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              <span>Gratis sleutel aanmaken via</span>
              <a
                href="https://aistudio.google.com/apikey"
                target="_blank"
                rel="noreferrer"
                className="text-indigo-400 hover:underline flex items-center gap-0.5"
              >
                Google AI Studio <ExternalLink className="w-3 h-3" />
              </a>
            </p>
          </div>

          {testResults['gemini'] && (
            <div
              className={`p-3 rounded-xl text-xs flex items-center gap-2 ${
                testResults['gemini'].connected
                  ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20'
                  : 'bg-rose-500/10 text-rose-300 border border-rose-500/20'
              }`}
            >
              {testResults['gemini'].connected ? (
                <CheckCircle2 className="w-4 h-4 shrink-0" />
              ) : (
                <XCircle className="w-4 h-4 shrink-0" />
              )}
              <span>{testResults['gemini'].message}</span>
            </div>
          )}
        </div>

        {/* 2. Lokale LLM (Ollama) */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                <Cpu className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                  <span>Ollama (Lokale LLM)</span>
                  {getServiceConnected('ollama') ? (
                    <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                      <CheckCircle2 className="w-3 h-3" /> Actief
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[11px] font-bold text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full border border-slate-700">
                      Optioneel / Uit
                    </span>
                  )}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Lokale privacy-vriendelijke AI voor promptverbetering en veiligheidschecks zonder API kosten.
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => handleTest('ollama')}
              disabled={testingService === 'ollama'}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition-colors shrink-0 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${testingService === 'ollama' ? 'animate-spin' : ''}`} />
              <span>Test Verbinding</span>
            </button>
          </div>

          <div className="space-y-2">
            <label className="block text-xs font-semibold text-slate-300">Ollama API URL</label>
            <div className="relative">
              <Server className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
              <input
                type="text"
                value={formData.ollama_url || ''}
                onChange={(e) => handleInputChange('ollama_url', e.target.value)}
                placeholder="http://host.docker.internal:11434"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm font-mono"
              />
            </div>
            <p className="text-xs text-slate-400 pt-1">
              Standaard op macOS/Docker: <code className="text-indigo-300">http://host.docker.internal:11434</code>. Aanbevolen model: <code className="text-indigo-300">llama3.1:8b</code>.
            </p>
          </div>
        </div>

        {/* 3. Stable Diffusion WebUI Forge */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                <Video className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                  <span>Stable Diffusion WebUI Forge</span>
                  {getServiceConnected('sd_webui') ? (
                    <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                      <CheckCircle2 className="w-3 h-3" /> Verbonden
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[11px] font-bold text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full border border-slate-700">
                      Optioneel / Standby
                    </span>
                  )}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Lokaal genereren van kleurrijke 2.5D achtergronden en karakter sprites via SDXL / Pony modellen.
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => handleTest('sd_webui')}
              disabled={testingService === 'sd_webui'}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition-colors shrink-0 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${testingService === 'sd_webui' ? 'animate-spin' : ''}`} />
              <span>Test Verbinding</span>
            </button>
          </div>

          <div className="space-y-2">
            <label className="block text-xs font-semibold text-slate-300">SD WebUI REST URL</label>
            <div className="relative">
              <Server className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
              <input
                type="text"
                value={formData.sd_webui_url || ''}
                onChange={(e) => handleInputChange('sd_webui_url', e.target.value)}
                placeholder="http://host.docker.internal:7860"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm font-mono"
              />
            </div>
            <p className="text-xs text-slate-400 pt-1">
              Start SD WebUI Forge met het vlaggetje <code className="text-amber-300 font-mono">--api --listen</code>.
            </p>
          </div>
        </div>

        {/* 4. Text-to-Speech (Piper / Kokoro) */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                <Mic className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                  <span>Piper & Kokoro Text-to-Speech</span>
                  <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                    <CheckCircle2 className="w-3 h-3" /> Ingebouwd
                  </span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Lokale, supersnelle Nederlandse stemmen voor kinderverhalen met woord-level lip-sync analyse.
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Piper Modellen Pad</label>
              <input
                type="text"
                value={formData.piper_path || ''}
                onChange={(e) => handleInputChange('piper_path', e.target.value)}
                placeholder="/data/piper-models"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-100 text-sm font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Kokoro TTS URL</label>
              <input
                type="text"
                value={formData.kokoro_url || ''}
                onChange={(e) => handleInputChange('kokoro_url', e.target.value)}
                placeholder="http://host.docker.internal:8080"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-100 text-sm font-mono"
              />
            </div>
          </div>
        </div>

        {/* 5. YouTube Data API v3 */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
                <Video className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-slate-100">YouTube Data API v3 (OAuth2)</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Direct uploaden en publiceren naar je kinderkanaal met automatische 'Made for Kids' COPPA markering.
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">YouTube Client ID</label>
              <input
                type="text"
                value={formData.youtube_client_id || ''}
                onChange={(e) => handleInputChange('youtube_client_id', e.target.value)}
                placeholder="123456...apps.googleusercontent.com"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-100 text-sm font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">YouTube Client Secret</label>
              <input
                type="password"
                value={formData.youtube_client_secret || ''}
                onChange={(e) => handleInputChange('youtube_client_secret', e.target.value)}
                placeholder="GOCSPX-..."
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-100 text-sm font-mono"
              />
            </div>
          </div>
        </div>

        {/* Bottom Save Bar */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-800">
          <div className="text-xs text-slate-400">
            Wijzigingen worden direct actief zonder Docker herstart.
          </div>
          <button
            type="submit"
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm transition-all shadow-lg shadow-indigo-600/25 active:scale-95"
          >
            <Save className="w-4 h-4" />
            <span>{saveSuccess ? 'Opgeslagen!' : 'Instellingen Opslaan'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
