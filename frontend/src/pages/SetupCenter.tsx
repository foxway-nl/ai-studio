import React, { useEffect, useState, useRef } from 'react';
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
  Volume2,
  Play,
  LogOut,
} from 'lucide-react';
import { useStore } from '../store/useStore';
import type { Settings, YouTubeChannelResponse, GeminiTestResponse } from '../api/client';

export const SetupCenter: React.FC = () => {
  const {
    settings,
    servicesStatus,
    fetchSettings,
    fetchServicesStatus,
    saveSettings,
    testConnection,
    testGeminiApiKey,
    testVoice,
    getYouTubeChannel,
    disconnectYouTube,
    getYouTubeAuthUrl,
  } = useStore();

  const [formData, setFormData] = useState<Partial<Settings>>({
    gemini_api_key: '',
    gemini_model: 'gemini-2.5-flash',
    default_image_provider: 'gemini',
    ollama_url: '',
    sd_webui_url: '',
    piper_path: '',
    kokoro_url: '',
    youtube_client_id: '',
    youtube_client_secret: '',
  });

  // Gemini Test state
  const [testingGemini, setTestingGemini] = useState(false);
  const [geminiResult, setGeminiResult] = useState<GeminiTestResponse | null>(null);
  const [availableGeminiModels, setAvailableGeminiModels] = useState<string[]>([
    'gemini-2.5-flash',
    'gemini-2.5-pro',
    'gemini-2.0-flash',
  ]);

  // General service test state
  const [testingService, setTestingService] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { connected: boolean; message: string }>>({});
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Voice Tester state
  const [testVoiceId, setTestVoiceId] = useState('nl-NL-FennaNeural');
  const [testVoiceProvider, setTestVoiceProvider] = useState('edge_tts');
  const [testVoicePitch, setTestVoicePitch] = useState('+15Hz');
  const [testVoiceRate, setTestVoiceRate] = useState('+0%');
  const [testSentence, setTestSentence] = useState('Hoi allemaal! Vandaag gaan we samen op avontuur, doen jullie mee?');
  const [testingVoice, setTestingVoice] = useState(false);
  const [testAudioUrl, setTestAudioUrl] = useState<string | null>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  // YouTube Channel state
  const [youtubeChannel, setYoutubeChannel] = useState<YouTubeChannelResponse | null>(null);
  const [loadingChannel, setLoadingChannel] = useState(false);

  useEffect(() => {
    fetchSettings();
    fetchServicesStatus();
    loadYouTubeChannel();
  }, [fetchSettings, fetchServicesStatus]);

  const loadYouTubeChannel = async () => {
    setLoadingChannel(true);
    try {
      const channel = await getYouTubeChannel();
      setYoutubeChannel(channel);
    } catch {
      setYoutubeChannel(null);
    } finally {
      setLoadingChannel(false);
    }
  };

  useEffect(() => {
    if (settings) {
      setFormData({
        gemini_api_key: settings.gemini_api_key || '',
        gemini_model: settings.gemini_model || 'gemini-2.5-flash',
        default_image_provider: settings.default_image_provider || 'gemini',
        wan_api_url: settings.wan_api_url || 'http://host.docker.internal:8188',
        wan_api_key: settings.wan_api_key || '',
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

  const handleSave = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    await saveSettings(formData);
    await fetchServicesStatus();
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  // 1. Gemini Verbindingstest
  const handleTestGemini = async () => {
    setTestingGemini(true);
    setGeminiResult(null);
    try {
      const res = await testGeminiApiKey(formData.gemini_api_key);
      setGeminiResult(res);
      if (res.valid && res.text_models && res.text_models.length > 0) {
        setAvailableGeminiModels(res.text_models);
        if (!formData.gemini_model || !res.text_models.includes(formData.gemini_model)) {
          setFormData((prev) => ({ ...prev, gemini_model: res.text_models[0] }));
        }
      }
      await fetchServicesStatus();
    } finally {
      setTestingGemini(false);
    }
  };

  // 2. Algemene Service Test
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

  // 3. Spraak / TTS Testen
  const handleTestVoiceAudio = async () => {
    setTestingVoice(true);
    try {
      const res = await testVoice({
        voice_id: testVoiceId,
        voice_provider: testVoiceProvider,
        text: testSentence,
        pitch: testVoicePitch,
        rate: testVoiceRate,
      });
      setTestAudioUrl(res.audio_url);
      setTimeout(() => {
        if (audioPlayerRef.current) {
          audioPlayerRef.current.play().catch(() => {});
        }
      }, 100);
    } finally {
      setTestingVoice(false);
    }
  };

  // 4. YouTube koppelen / ontkoppelen
  const handleConnectYouTube = async () => {
    try {
      const authUrl = await getYouTubeAuthUrl();
      window.location.href = authUrl;
    } catch (err: any) {
      alert(`Kon YouTube authenticatie URL niet openen: ${err?.message || err}`);
    }
  };

  const handleDisconnectYouTube = async () => {
    if (confirm('Weet je zeker dat je het gekoppelde YouTube account wilt ontkoppelen?')) {
      await disconnectYouTube();
      await loadYouTubeChannel();
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
            Configureer hieronder je gewenste AI services. Alle instellingen en API-sleutels worden dynamisch
            opgeslagen in je gemounte Docker volume (<code className="text-indigo-300 font-mono">/data</code>).
          </p>
        </div>

        <button
          onClick={() => handleSave()}
          className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm transition-all shadow-lg shadow-indigo-600/25 active:scale-95 shrink-0"
        >
          <Save className="w-4 h-4" />
          <span>{saveSuccess ? 'Opgeslagen!' : 'Instellingen Opslaan'}</span>
        </button>
      </div>

      <form onSubmit={(e) => { e.preventDefault(); handleSave(); }} className="space-y-6">
        
        {/* ─────────────────────────────────────────────────────────────
            1. GOOGLE GEMINI API (Met Live Modellen & Exacte Error Codes)
        ───────────────────────────────────────────────────────────── */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                  <span>Google Gemini API</span>
                  {getServiceConnected('gemini') || geminiResult?.valid ? (
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
                  Verzorgt scriptgeneratie, YouTube Kids SEO/GEO, en Imagen 3 beeldgeneratie.
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={handleTestGemini}
              disabled={testingGemini}
              className="px-3.5 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30 text-blue-300 text-xs font-semibold flex items-center gap-1.5 transition-colors shrink-0 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${testingGemini ? 'animate-spin' : ''}`} />
              <span>{testingGemini ? 'Testen...' : 'Test Verbinding'}</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2 space-y-1">
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
              <p className="text-[11px] text-slate-400 flex items-center gap-1.5 pt-1">
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

            <div className="space-y-1">
              <label className="block text-xs font-semibold text-slate-300">Voorkeursmodel</label>
              <select
                value={formData.gemini_model || 'gemini-2.5-flash'}
                onChange={(e) => handleInputChange('gemini_model', e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-100 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {availableGeminiModels.map((m) => (
                  <option key={m} value={m}>
                    {m} {m.includes('2.5') ? '⚡ (Aanbevolen)' : ''}
                  </option>
                ))}
              </select>
              <p className="text-[10px] text-slate-400 pt-1">
                Dynamisch opgehaald uit je Gemini API sleutel.
              </p>
            </div>
          </div>

          {/* Resultaat Banner met Exacte Foutmelding */}
          {geminiResult && (
            <div
              className={`p-3.5 rounded-xl text-xs flex items-start gap-2.5 ${
                geminiResult.valid
                  ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20'
                  : 'bg-rose-500/10 text-rose-300 border border-rose-500/20'
              }`}
            >
              {geminiResult.valid ? (
                <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
              ) : (
                <XCircle className="w-4 h-4 shrink-0 mt-0.5" />
              )}
              <div className="space-y-1">
                <p className="font-semibold">{geminiResult.message}</p>
                {geminiResult.error && (
                  <p className="font-mono text-[11px] bg-rose-950/60 p-2 rounded border border-rose-800/40 text-rose-200">
                    {geminiResult.error}
                  </p>
                )}
                {geminiResult.valid && geminiResult.text_models && (
                  <p className="text-[11px] opacity-80">
                    Beschikbare tekstmodellen: {geminiResult.text_models.slice(0, 5).join(', ')}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ─────────────────────────────────────────────────────────────
            2. BEELDGENERATIE & ENGINE KEUZE (Gemini, Pollinations, SD Forge)
        ───────────────────────────────────────────────────────────── */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                <Video className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                  <span>Beeldgeneratie Engine</span>
                  <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                    <CheckCircle2 className="w-3 h-3" /> Klaar
                  </span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Kies hoe achtergronden, 2.5D karaktersprites en thumbnails gegenereerd worden.
                </p>
              </div>
            </div>
          </div>

          {/* Engine Selector Radio Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {/* Optie 1: Gemini / Imagen 3 */}
            <label
              className={`p-4 rounded-xl border cursor-pointer transition-all flex flex-col justify-between ${
                formData.default_image_provider === 'gemini'
                  ? 'bg-indigo-600/15 border-indigo-500 ring-1 ring-indigo-500'
                  : 'bg-slate-800/60 border-slate-700/80 hover:border-slate-600'
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className="font-bold text-xs text-slate-100 flex items-center gap-1.5">
                    <span>Google Gemini / Imagen 3</span>
                  </span>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Primaire cloud engine. Gebruikt je ingevulde Gemini sleutel (geen lokale software nodig).
                  </p>
                </div>
                <input
                  type="radio"
                  name="image_provider"
                  checked={formData.default_image_provider === 'gemini'}
                  onChange={() => handleInputChange('default_image_provider', 'gemini')}
                  className="mt-1"
                />
              </div>
              <span className="mt-3 text-[10px] font-bold text-indigo-400 uppercase tracking-wider">
                ★ Aanbevolen
              </span>
            </label>

            {/* Optie 2: Pollinations Flux API */}
            <label
              className={`p-4 rounded-xl border cursor-pointer transition-all flex flex-col justify-between ${
                formData.default_image_provider === 'pollinations'
                  ? 'bg-indigo-600/15 border-indigo-500 ring-1 ring-indigo-500'
                  : 'bg-slate-800/60 border-slate-700/80 hover:border-slate-600'
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className="font-bold text-xs text-slate-100 flex items-center gap-1.5">
                    <span>Ingebouwde Cloud Generator</span>
                  </span>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Gratis, sleutelloze Flux API via Pollinations. Werkt altijd direct out-of-the-box.
                  </p>
                </div>
                <input
                  type="radio"
                  name="image_provider"
                  checked={formData.default_image_provider === 'pollinations'}
                  onChange={() => handleInputChange('default_image_provider', 'pollinations')}
                  className="mt-1"
                />
              </div>
              <span className="mt-3 text-[10px] font-bold text-emerald-400 uppercase tracking-wider">
                ✓ Zero-Config Fallback
              </span>
            </label>

            {/* Optie 3: SD WebUI Forge */}
            <label
              className={`p-4 rounded-xl border cursor-pointer transition-all flex flex-col justify-between ${
                formData.default_image_provider === 'sdwebui'
                  ? 'bg-indigo-600/15 border-indigo-500 ring-1 ring-indigo-500'
                  : 'bg-slate-800/60 border-slate-700/80 hover:border-slate-600'
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className="font-bold text-xs text-slate-100 flex items-center gap-1.5">
                    <span>SD WebUI Forge</span>
                  </span>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Optionele lokale engine op poort 7860 voor custom SDXL checkpoints.
                  </p>
                </div>
                <input
                  type="radio"
                  name="image_provider"
                  checked={formData.default_image_provider === 'sdwebui'}
                  onChange={() => handleInputChange('default_image_provider', 'sdwebui')}
                  className="mt-1"
                />
              </div>
              <span className="mt-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                Optioneel (Lokaal)
              </span>
            </label>
          </div>

          {/* SD WebUI URL & Test (alleen relevant als gebruiker dit wil testen) */}
          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-300">
                SD WebUI Forge REST URL (Optioneel lokaal)
              </label>
              <button
                type="button"
                onClick={() => handleTest('sd_webui')}
                disabled={testingService === 'sd_webui'}
                className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1 transition-colors"
              >
                <RefreshCw className={`w-3 h-3 ${testingService === 'sd_webui' ? 'animate-spin' : ''}`} />
                <span>Test poort 7860</span>
              </button>
            </div>
            <input
              type="text"
              value={formData.sd_webui_url || ''}
              onChange={(e) => handleInputChange('sd_webui_url', e.target.value)}
              placeholder="http://host.docker.internal:7860"
              className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-100 text-xs font-mono"
            />
            {testResults['sd_webui'] && (
              <div
                className={`p-2.5 rounded-lg text-xs ${
                  testResults['sd_webui'].connected
                    ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20'
                    : 'bg-amber-500/10 text-amber-300 border border-amber-500/20'
                }`}
              >
                {testResults['sd_webui'].message}
              </div>
            )}
          </div>
        </div>

        {/* ─────────────────────────────────────────────────────────────
            2B. IMAGE-TO-VIDEO ANIMATIE (Google Veo & Wan 2.1)
        ───────────────────────────────────────────────────────────── */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
                <Video className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                  <span>Image-to-Video Animatie (Google Veo & Wan 2.1)</span>
                  <span className="flex items-center gap-1 text-[11px] font-bold text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded-full border border-rose-500/20">
                    <CheckCircle2 className="w-3 h-3" /> Start-Frame Lock Actief
                  </span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Converteert het goedgekeurde Start-Frame naar levendige 16:9 videoclips waarin karakters daadwerkelijk bewegen, lopen en praten.
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Wan 2.1 / ComfyUI Endpoint URL (Optioneel lokaal / cloud)
              </label>
              <input
                type="text"
                value={formData.wan_api_url || ''}
                onChange={(e) => handleInputChange('wan_api_url', e.target.value)}
                placeholder="http://host.docker.internal:8188"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-100 text-xs font-mono"
              />
              <p className="text-[11px] text-slate-500 mt-1">
                Lokale Wan 2.1 ComfyUI server of Fal.ai endpoint voor alternatieve open-source videoclip generatie.
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Wan API Sleutel (Optioneel voor cloud providers)
              </label>
              <input
                type="password"
                value={formData.wan_api_key || ''}
                onChange={(e) => handleInputChange('wan_api_key', e.target.value)}
                placeholder="fal_key_... of laat leeg voor lokaal"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-100 text-xs font-mono"
              />
            </div>
          </div>
        </div>

        {/* ─────────────────────────────────────────────────────────────
            3. TEXT-TO-SPEECH MET INTERACTIEVE VOICE TESTER (Edge-TTS, Piper, Kokoro)
        ───────────────────────────────────────────────────────────── */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                <Mic className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                  <span>Text-to-Speech & Stemmen Centrum</span>
                  <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                    <CheckCircle2 className="w-3 h-3" /> Microsoft Edge TTS Actief
                  </span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Natuurlijke Nederlandse kinder- en vertelstemmen met automatische woord-level timestamps.
                </p>
              </div>
            </div>
          </div>

          {/* Interactieve Voice Tester Paneel */}
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
              <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                <Volume2 className="w-4 h-4 text-emerald-400" />
                <span>Interactieve Voice Tester (Direct Beluisteren)</span>
              </span>
              <span className="text-[11px] text-emerald-400 font-semibold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                Gratis & Onbeperkt
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
              <div className="md:col-span-2 space-y-1">
                <label className="font-semibold text-slate-300">Stemkeuze</label>
                <select
                  value={`${testVoiceProvider}:${testVoiceId}`}
                  onChange={(e) => {
                    const [prov, vid] = e.target.value.split(':');
                    setTestVoiceProvider(prov);
                    setTestVoiceId(vid);
                  }}
                  className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-100 font-semibold"
                >
                  <optgroup label="Microsoft Edge TTS (Aanbevolen Cloud Stemmen)">
                    <option value="edge_tts:nl-NL-FennaNeural">Fenna (nl-NL) - Vrolijk & Helder (Peuters/Kleuters)</option>
                    <option value="edge_tts:nl-NL-MaartenNeural">Maarten (nl-NL) - Warm & Vriendelijk</option>
                    <option value="edge_tts:nl-BE-DenaNeural">Dena (nl-BE) - Vlaams & Zacht</option>
                    <option value="edge_tts:en-US-AnaNeural">Ana (en-US) - Vrolijke Kinderstem</option>
                  </optgroup>
                  <optgroup label="Google Cloud WaveNet">
                    <option value="google:nl-NL-Wavenet-A">Google WaveNet Vrouw (nl-NL)</option>
                    <option value="google:nl-NL-Wavenet-B">Google WaveNet Man (nl-NL)</option>
                  </optgroup>
                  <optgroup label="Piper TTS (Lokaal)">
                    <option value="piper:nl_NL-mls-medium">Piper MLS Medium (nl-NL)</option>
                  </optgroup>
                </select>
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-slate-300 flex items-center justify-between">
                  <span>Pitch (Toonhoogte)</span>
                  <span className="text-emerald-400 font-mono">{testVoicePitch}</span>
                </label>
                <select
                  value={testVoicePitch}
                  onChange={(e) => setTestVoicePitch(e.target.value)}
                  className="w-full px-2.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-100 font-mono"
                >
                  <option value="+0Hz">+0Hz (Standaard)</option>
                  <option value="+10Hz">+10Hz (Iets Vrolijker)</option>
                  <option value="+15Hz">+15Hz (Kinderkarakter effect)</option>
                  <option value="+25Hz">+25Hz (Hoog speels karakter)</option>
                  <option value="-10Hz">-10Hz (Diepe rustige verteller)</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-slate-300 flex items-center justify-between">
                  <span>Snelheid</span>
                  <span className="text-emerald-400 font-mono">{testVoiceRate}</span>
                </label>
                <select
                  value={testVoiceRate}
                  onChange={(e) => setTestVoiceRate(e.target.value)}
                  className="w-full px-2.5 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-100 font-mono"
                >
                  <option value="-10%">-10% (Rustig voor peuters)</option>
                  <option value="+0%">+0% (Normaal tempo)</option>
                  <option value="+10%">+10% (Enthousiast & vlot)</option>
                </select>
              </div>
            </div>

            {/* Test Zin Input & Luister Knop */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-300">Test Zin</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={testSentence}
                  onChange={(e) => setTestSentence(e.target.value)}
                  className="flex-1 px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-100 text-xs"
                />
                <button
                  type="button"
                  onClick={handleTestVoiceAudio}
                  disabled={testingVoice || !testSentence.trim()}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-2 transition-all shadow-md shadow-emerald-600/20 disabled:opacity-50 shrink-0"
                >
                  {testingVoice ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Play className="w-3.5 h-3.5 fill-current" />
                  )}
                  <span>{testingVoice ? 'Genereren...' : 'Luister Stem'}</span>
                </button>
              </div>
            </div>

            {/* Audio Speler */}
            {testAudioUrl && (
              <div className="flex items-center gap-3 p-3 rounded-lg bg-slate-900 border border-emerald-500/30">
                <audio
                  ref={audioPlayerRef}
                  controls
                  src={testAudioUrl}
                  className="w-full h-8"
                />
              </div>
            )}
          </div>
        </div>

        {/* ─────────────────────────────────────────────────────────────
            4. YOUTUBE KANAAL BEHEER & DOELGROEP INFO (COPPA vs General)
        ───────────────────────────────────────────────────────────── */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
                <Video className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                  <span>YouTube Data API v3 (OAuth2 & Publiceren)</span>
                  {youtubeChannel?.connected ? (
                    <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                      <CheckCircle2 className="w-3 h-3" /> Gekoppeld
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[11px] font-bold text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full border border-slate-700">
                      Niet gekoppeld
                    </span>
                  )}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Publiceer direct naar YouTube met ondersteuning voor zowel Mode A (Kids / COPPA) als Mode B (Algemeen).
                </p>
              </div>
            </div>
          </div>

          {/* Actief Gekoppeld Kanaal Kaart */}
          {loadingChannel ? (
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-center text-xs text-slate-400 gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-slate-400" />
              <span>YouTube kanaalstatus laden...</span>
            </div>
          ) : youtubeChannel?.connected ? (
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-3.5">
                {youtubeChannel.avatar_url ? (
                  <img
                    src={youtubeChannel.avatar_url}
                    alt={youtubeChannel.title || 'Kanaal'}
                    className="w-12 h-12 rounded-full border border-slate-700 object-cover"
                  />
                ) : (
                  <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 font-bold">
                    YT
                  </div>
                )}
                <div>
                  <h4 className="font-bold text-sm text-slate-100">{youtubeChannel.title}</h4>
                  <p className="text-xs text-slate-400">
                    {youtubeChannel.subscriber_count} abonnees • {youtubeChannel.video_count} video's
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleConnectYouTube}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors"
                >
                  Wissel Account
                </button>
                <button
                  type="button"
                  onClick={handleDisconnectYouTube}
                  className="px-3 py-1.5 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/30 text-rose-300 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Ontkoppel</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex flex-col md:flex-row items-center justify-between gap-4">
              <div>
                <p className="text-xs font-semibold text-slate-300">Geen YouTube account actief gekoppeld</p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Koppel je Google account om video's met één klik te uploaden.
                </p>
              </div>
              <button
                type="button"
                onClick={handleConnectYouTube}
                disabled={!formData.youtube_client_id}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs flex items-center gap-2 shadow-md shadow-rose-600/20 disabled:opacity-50 shrink-0"
              >
                <Video className="w-4 h-4" />
                <span>Koppel YouTube Kanaal</span>
              </button>
            </div>
          )}

          {/* Client ID & Secret velden */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">YouTube Client ID</label>
              <input
                type="text"
                value={formData.youtube_client_id || ''}
                onChange={(e) => handleInputChange('youtube_client_id', e.target.value)}
                placeholder="123456...apps.googleusercontent.com"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-100 text-xs font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">YouTube Client Secret</label>
              <input
                type="password"
                value={formData.youtube_client_secret || ''}
                onChange={(e) => handleInputChange('youtube_client_secret', e.target.value)}
                placeholder="GOCSPX-..."
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-100 text-xs font-mono"
              />
            </div>
          </div>
        </div>

        {/* ─────────────────────────────────────────────────────────────
            5. OLLAMA (LOKALE LLM - OPTIONEEL)
        ───────────────────────────────────────────────────────────── */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                <Cpu className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                  <span>Ollama (Lokale LLM - Optioneel)</span>
                  {getServiceConnected('ollama') ? (
                    <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                      <CheckCircle2 className="w-3 h-3" /> Actief
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[11px] font-bold text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full border border-slate-700">
                      Optioneel / Standby
                    </span>
                  )}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Lokale AI voor snelle vertalingen en kindveiligheidschecks zonder tokens te verbruiken.
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

          <div className="space-y-1">
            <label className="block text-xs font-semibold text-slate-300">Ollama API URL</label>
            <div className="relative">
              <Server className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
              <input
                type="text"
                value={formData.ollama_url || ''}
                onChange={(e) => handleInputChange('ollama_url', e.target.value)}
                placeholder="http://host.docker.internal:11434"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-100 placeholder-slate-500 text-xs font-mono"
              />
            </div>
          </div>
        </div>

        {/* Bottom Save Bar */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-800">
          <div className="text-xs text-slate-400">
            Alle wijzigingen worden direct actief en persistent bewaard in <code className="text-indigo-300">/data/config.json</code>.
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
