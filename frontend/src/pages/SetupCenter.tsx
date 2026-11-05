import React, { useEffect, useState, useRef } from 'react';
import {
  Save,
  RefreshCw,
  ExternalLink,
  Key,
  Server,
  Video,
  Mic,
  Sparkles,
  Volume2,
  Play,
  Eye,
  EyeOff,
  Trash2,
  DownloadCloud,
  Zap,
  Sliders,
  Check,
} from 'lucide-react';
import { useStore } from '../store/useStore';
import {
  Settings,
  YouTubeChannelResponse,
  GeminiTestResponse,
  OllamaModelItem,
  OllamaProgressEvent,
  GroqInfoResponse,
  HfTestResponse,
  getOllamaModels,
  deleteOllamaModel,
  pullOllamaModel,
  getGroqModels,
  testGroqKey,
  testHfToken,
} from '../api/client';

export const SetupCenter: React.FC = () => {
  const {
    settings,
    fetchSettings,
    fetchServicesStatus,
    saveSettings,
    testGeminiApiKey,
    testVoice,
    getYouTubeChannel,
    disconnectYouTube,
    getYouTubeAuthUrl,
    addToast,
  } = useStore();

  const [formData, setFormData] = useState<Partial<Settings>>({
    gemini_api_key: '',
    gemini_model: 'gemini-2.5-flash',
    gemini_text_model: 'gemini-2.5-flash',
    gemini_image_model: 'imagen-3.0-generate-002',
    gemini_video_model: 'veo-2.0-generate-001',
    default_image_provider: 'gemini',
    groq_api_key: '',
    hf_token: '',
    hf_video_space_id: 'multimodalart/Wan2.1-Fast',
    task_script_provider: 'gemini',
    task_script_model: 'gemini-2.5-flash',
    task_prompt_provider: 'gemini',
    task_prompt_model: 'gemini-2.5-flash',
    task_tts_provider: 'edge_tts',
    task_tts_voice: 'nl-NL-FennaNeural',
    task_whisper_provider: 'groq_whisper',
    task_image_provider: 'gemini_imagen',
    task_image_model: 'imagen-3.0-generate-002',
    task_video_provider: 'local_2_5d',
    task_video_model: 'veo-2.0-generate-001',
    ollama_url: 'http://host.docker.internal:11434',
    youtube_client_id: '',
    youtube_client_secret: '',
  });

  const [showGeminiKey, setShowGeminiKey] = useState(false);
  const [showGroqKey, setShowGroqKey] = useState(false);
  const [showHfToken, setShowHfToken] = useState(false);

  // Gemini Test & Models
  const [testingGemini, setTestingGemini] = useState(false);
  const [geminiResult, setGeminiResult] = useState<GeminiTestResponse | null>(null);
  const [availableTextModels, setAvailableTextModels] = useState<string[]>([
    'gemini-2.5-flash',
    'gemini-2.5-pro',
    'gemini-2.0-flash',
  ]);
  const [availableImageModels, setAvailableImageModels] = useState<string[]>([
    'imagen-3.0-generate-002',
    'imagen-3.0-fast-generate-001',
  ]);
  const [availableVideoModels, setAvailableVideoModels] = useState<string[]>([
    'veo-2.0-generate-001',
  ]);

  // Ollama Model Manager state
  const [ollamaConnected, setOllamaConnected] = useState(false);
  const [ollamaModels, setOllamaModels] = useState<OllamaModelItem[]>([]);
  const [loadingOllama, setLoadingOllama] = useState(false);
  const [customModelToPull, setCustomModelToPull] = useState('');
  const [pullProgress, setPullProgress] = useState<OllamaProgressEvent | null>(null);
  const [isPulling, setIsPulling] = useState(false);

  // Groq state
  const [testingGroq, setTestingGroq] = useState(false);
  const [groqResult, setGroqResult] = useState<GroqInfoResponse | null>(null);
  const [groqModels, setGroqModels] = useState<string[]>([
    'llama-3.3-70b-versatile',
    'qwen-qwq-32b',
    'gemma2-9b-it',
    'llama-3.1-8b-instant',
  ]);

  // Hugging Face state
  const [testingHf, setTestingHf] = useState(false);
  const [hfResult, setHfResult] = useState<HfTestResponse | null>(null);

  // Save state
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Voice Tester state
  const [testVoiceId, setTestVoiceId] = useState('nl-NL-FennaNeural');
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
    loadOllamaData();
    loadGroqData();
  }, [fetchSettings, fetchServicesStatus]);

  useEffect(() => {
    if (settings) {
      setFormData((prev) => ({
        ...prev,
        ...settings,
        gemini_api_key: settings.gemini_api_key || '',
        groq_api_key: settings.groq_api_key || '',
        hf_token: settings.hf_token || '',
        hf_video_space_id: settings.hf_video_space_id || 'multimodalart/Wan2.1-Fast',
        task_script_provider: settings.task_script_provider || 'gemini',
        task_script_model: settings.task_script_model || 'gemini-2.5-flash',
        task_prompt_provider: settings.task_prompt_provider || 'gemini',
        task_prompt_model: settings.task_prompt_model || 'gemini-2.5-flash',
        task_tts_provider: settings.task_tts_provider || 'edge_tts',
        task_tts_voice: settings.task_tts_voice || 'nl-NL-FennaNeural',
        task_whisper_provider: settings.task_whisper_provider || 'groq_whisper',
        task_image_provider: settings.task_image_provider || 'gemini_imagen',
        task_image_model: settings.task_image_model || 'imagen-3.0-generate-002',
        task_video_provider: settings.task_video_provider || 'local_2_5d',
        task_video_model: settings.task_video_model || 'veo-2.0-generate-001',
        ollama_url: settings.ollama_url || 'http://host.docker.internal:11434',
      }));

      if (settings.discovered_models) {
        if (settings.discovered_models.text_models && settings.discovered_models.text_models.length > 0) {
          setAvailableTextModels(settings.discovered_models.text_models);
        }
        if (settings.discovered_models.image_models && settings.discovered_models.image_models.length > 0) {
          setAvailableImageModels(settings.discovered_models.image_models);
        }
        if (settings.discovered_models.video_models && settings.discovered_models.video_models.length > 0) {
          setAvailableVideoModels(settings.discovered_models.video_models);
        }
      }
    }
  }, [settings]);

  const loadOllamaData = async () => {
    setLoadingOllama(true);
    try {
      const res = await getOllamaModels();
      setOllamaConnected(res.connected);
      setOllamaModels(res.models || []);
    } catch {
      setOllamaConnected(false);
    } finally {
      setLoadingOllama(false);
    }
  };

  const loadGroqData = async () => {
    try {
      const res = await getGroqModels();
      if (res.models && res.models.length > 0) {
        setGroqModels(res.models);
      }
    } catch {
      // ignore
    }
  };

  const loadYouTubeChannel = async () => {
    setLoadingChannel(true);
    try {
      const ch = await getYouTubeChannel();
      setYoutubeChannel(ch);
    } catch {
      setYoutubeChannel(null);
    } finally {
      setLoadingChannel(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await saveSettings(formData);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
      await fetchServicesStatus();
    } catch (err) {
      console.error('Opslaan mislukt', err);
    }
  };

  // 1. Gemini Test
  const handleTestGemini = async () => {
    setTestingGemini(true);
    setGeminiResult(null);
    try {
      const res = await testGeminiApiKey(formData.gemini_api_key);
      setGeminiResult(res);
      if (res.valid) {
        if (res.text_models && res.text_models.length > 0) {
          setAvailableTextModels(res.text_models);
        }
        if (res.image_models && res.image_models.length > 0) {
          setAvailableImageModels(res.image_models);
        }
        if (res.video_models && res.video_models.length > 0) {
          setAvailableVideoModels(res.video_models);
        }
      }
      await fetchServicesStatus();
    } finally {
      setTestingGemini(false);
    }
  };

  // 2. Groq Test
  const handleTestGroq = async () => {
    setTestingGroq(true);
    setGroqResult(null);
    try {
      const res = await testGroqKey(formData.groq_api_key);
      setGroqResult(res);
      if (res.models && res.models.length > 0) {
        setGroqModels(res.models);
        addToast('success', `Groq verbonden! ${res.models.length} gratis modellen beschikbaar.`);
      } else if (res.connected) {
        addToast('success', 'Groq verbinding geslaagd!');
      } else {
        addToast('error', res.error || 'Groq verificatie mislukt.');
      }
      await fetchServicesStatus();
    } catch (err: any) {
      addToast('error', `Groq test mislukt: ${err.message}`);
    } finally {
      setTestingGroq(false);
    }
  };

  // 3. Hugging Face Test
  const handleTestHf = async () => {
    setTestingHf(true);
    setHfResult(null);
    try {
      const res = await testHfToken(formData.hf_token);
      setHfResult(res);
      if (res.connected) {
        addToast('success', `Hugging Face verbonden als: ${res.user || 'Gebruiker'}`);
      } else {
        addToast('error', res.error || 'Hugging Face token ongeldig.');
      }
      await fetchServicesStatus();
    } catch (err: any) {
      addToast('error', `HF test mislukt: ${err.message}`);
    } finally {
      setTestingHf(false);
    }
  };

  // 4. Ollama Pull
  const handlePullModel = async (modelName: string) => {
    if (!modelName.trim()) return;
    setIsPulling(true);
    setPullProgress({ status: `Starten van download ${modelName}...`, completed: 0, total: 0, percent: 0 });
    try {
      await pullOllamaModel(
        modelName.trim(),
        (progress) => setPullProgress(progress),
        async () => {
          setIsPulling(false);
          setPullProgress(null);
          setCustomModelToPull('');
          addToast('success', `Model '${modelName}' succesvol geïnstalleerd in Ollama!`);
          await loadOllamaData();
        },
        (err) => {
          setIsPulling(false);
          setPullProgress(null);
          addToast('error', `Download mislukt: ${err.message || err}`);
        }
      );
    } catch (err: any) {
      setIsPulling(false);
      setPullProgress(null);
      addToast('error', `Fout bij pull: ${err.message}`);
    }
  };

  // 5. Ollama Delete
  const handleDeleteOllamaModel = async (name: string) => {
    if (!confirm(`Weet je zeker dat je model '${name}' wilt verwijderen uit Ollama?`)) return;
    try {
      await deleteOllamaModel(name);
      addToast('success', `Model '${name}' verwijderd.`);
      await loadOllamaData();
    } catch (err: any) {
      addToast('error', `Verwijderen mislukt: ${err.message}`);
    }
  };

  // 6. Voice Tester
  const handleTestVoice = async () => {
    setTestingVoice(true);
    setTestAudioUrl(null);
    try {
      const res = await testVoice({
        voice_id: testVoiceId,
        voice_provider: 'edge_tts',
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
    } catch (err) {
      console.error('Stemtest mislukt', err);
    } finally {
      setTestingVoice(false);
    }
  };

  const recommendedOllamaModels = [
    { name: 'qwen2.5:3b', desc: 'Snel & Licht (1.9 GB)', tag: 'Aanbevolen voor Mac' },
    { name: 'qwen2.5:7b', desc: 'Beste voor Scripts & Prompts (4.7 GB)', tag: 'Hoge Kwaliteit' },
    { name: 'llama3.2:3b', desc: 'Ultra-licht Llama (2.0 GB)', tag: 'Zeer snel' },
    { name: 'gemma2:9b', desc: 'Google Gemma Nederlands (5.4 GB)', tag: 'Rijke taal' },
  ];

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-10 pb-24 text-slate-100">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-2 text-indigo-400 font-bold text-xs uppercase tracking-wider mb-1">
            <Sliders className="w-4 h-4" />
            <span>AI Model Beheercentrum & Providers</span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">AI Modellen & Providers</h1>
          <p className="text-sm text-slate-400 mt-1">
            Koppel gratis Cloud providers (Groq & Hugging Face ZeroGPU), beheer lokale Ollama modellen en wijs taken toe.
          </p>
        </div>

        <button
          onClick={handleSave}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm shadow-lg shadow-indigo-600/20 active:scale-95 transition-all"
        >
          <Save className="w-4 h-4" />
          <span>{saveSuccess ? 'Opgeslagen! ✓' : 'Alles Opslaan'}</span>
        </button>
      </div>

      <form onSubmit={handleSave} className="space-y-10">
        {/* ─────────────────────────────────────────────────────────────
            SECTIE 0: DE TAAK-ROUTER (DROPDOWNS)
        ───────────────────────────────────────────────────────────── */}
        <div className="p-6 rounded-3xl bg-gradient-to-br from-indigo-950/40 via-slate-900 to-slate-900 border-2 border-indigo-500/30 space-y-6 shadow-xl shadow-indigo-950/20">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-600/30">
                <Sliders className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-lg font-black text-white flex items-center gap-2">
                  <span>Centrale Taak-Router</span>
                  <span className="text-[10px] uppercase font-extrabold px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    Jij Bepaalt de Rollen
                  </span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Selecteer per productiefase welke AI-engine het werk uitvoert. Gratis Cloud en Lokaal worden naadloos gecombineerd.
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 pt-2">
            {/* 1. Script & SEO */}
            <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-2">
              <label className="text-xs font-bold text-indigo-300 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                <span>1. Script & SEO Schrijver</span>
              </label>
              <select
                name="task_script_provider"
                value={formData.task_script_provider || 'gemini'}
                onChange={handleChange}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 font-semibold focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value="gemini">Google Gemini (Officieel)</option>
                <option value="groq">Groq Cloud (Llama 3.3 70B - Gratis & Razendsnel)</option>
                <option value="ollama">Lokaal Ollama ({formData.task_script_model || 'qwen2.5:3b'})</option>
              </select>
            </div>

            {/* 2. Beeld- & Motion-Prompts */}
            <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-2">
              <label className="text-xs font-bold text-purple-300 flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5" />
                <span>2. Beeld- & Motion-Prompts</span>
              </label>
              <select
                name="task_prompt_provider"
                value={formData.task_prompt_provider || 'gemini'}
                onChange={handleChange}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 font-semibold focus:outline-none focus:ring-1 focus:ring-purple-500"
              >
                <option value="gemini">Google Gemini (Flash)</option>
                <option value="groq">Groq Cloud (Llama 3.3 70B / Qwen)</option>
                <option value="ollama">Lokaal Ollama</option>
              </select>
            </div>

            {/* 3. Stemmen (TTS) */}
            <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-2">
              <label className="text-xs font-bold text-emerald-300 flex items-center gap-1.5">
                <Mic className="w-3.5 h-3.5" />
                <span>3. Gesproken Stemmen (TTS)</span>
              </label>
              <select
                name="task_tts_provider"
                value={formData.task_tts_provider || 'edge_tts'}
                onChange={handleChange}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 font-semibold focus:outline-none focus:ring-1 focus:ring-emerald-500"
              >
                <option value="edge_tts">Microsoft Edge Neural TTS (Gratis NL kinderstemmen)</option>
                <option value="google">Google Gemini / Cloud WaveNet TTS</option>
              </select>
            </div>

            {/* 4. Audio Timestamps */}
            <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-2">
              <label className="text-xs font-bold text-amber-300 flex items-center gap-1.5">
                <Volume2 className="w-3.5 h-3.5" />
                <span>4. Audio Woord-Timestamps</span>
              </label>
              <select
                name="task_whisper_provider"
                value={formData.task_whisper_provider || 'groq_whisper'}
                onChange={handleChange}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 font-semibold focus:outline-none focus:ring-1 focus:ring-amber-500"
              >
                <option value="groq_whisper">Groq Whisper Large v3 Turbo (Gratis Cloud - 0.2s)</option>
                <option value="local_whisper">Lokaal faster-whisper (CPU)</option>
              </select>
            </div>

            {/* 5. Start-Frames & Karakters */}
            <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-2">
              <label className="text-xs font-bold text-rose-300 flex items-center gap-1.5">
                <Video className="w-3.5 h-3.5" />
                <span>5. Start-Frame & Karakters Beeld</span>
              </label>
              <select
                name="task_image_provider"
                value={formData.task_image_provider || 'gemini_imagen'}
                onChange={handleChange}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 font-semibold focus:outline-none focus:ring-1 focus:ring-rose-500"
              >
                <option value="gemini_imagen">Google Imagen 3 / Gemini Image (Officiële API)</option>
                <option value="hf_flux">Hugging Face FLUX.1-schnell (Gratis met HF Token)</option>
              </select>
            </div>

            {/* 6. Video-Animaties */}
            <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-2">
              <label className="text-xs font-bold text-cyan-300 flex items-center gap-1.5">
                <Play className="w-3.5 h-3.5" />
                <span>6. Scène Video-Animaties</span>
              </label>
              <select
                name="task_video_provider"
                value={formData.task_video_provider || 'local_2_5d'}
                onChange={handleChange}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 font-semibold focus:outline-none focus:ring-1 focus:ring-cyan-500"
              >
                <option value="local_2_5d">⚡ Lokale 60fps 2.5D Camera Animator (FFmpeg - Direct)</option>
                <option value="hf_zerogpu">Hugging Face ZeroGPU (Wan 2.1 / LTX-Video - Gratis Cloud)</option>
                <option value="veo">Google Veo 2.0 API (veo-2.0-generate-001)</option>
              </select>
            </div>
          </div>
        </div>

        {/* ─────────────────────────────────────────────────────────────
            SECTIE 1: LOKALE OLLAMA MODEL MANAGER
        ───────────────────────────────────────────────────────────── */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                <Server className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                  <span>1. Lokale Ollama Model Manager</span>
                  <span
                    className={`flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full border ${
                      ollamaConnected
                        ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                        : 'text-amber-400 bg-amber-500/10 border-amber-500/20'
                    }`}
                  >
                    {ollamaConnected ? 'Verbonden ✓' : 'Niet bereikbaar'}
                  </span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Bekijk, download en verwijder lokaal draaiende LLM modellen op poort 11434.
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={loadOllamaData}
              disabled={loadingOllama}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingOllama ? 'animate-spin' : ''}`} />
              <span>Vernieuwen</span>
            </button>
          </div>

          {/* Download Voortgangsbalk */}
          {isPulling && pullProgress && (
            <div className="p-4 rounded-xl bg-blue-950/40 border border-blue-500/30 space-y-2">
              <div className="flex items-center justify-between text-xs font-bold text-blue-200">
                <span>{pullProgress.status}</span>
                <span>{pullProgress.percent}%</span>
              </div>
              <div className="w-full h-2.5 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-blue-500 transition-all duration-200"
                  style={{ width: `${Math.min(100, Math.max(2, pullProgress.percent))}%` }}
                />
              </div>
            </div>
          )}

          {/* Aanbevolen Lichte Modellen (1-Klik) */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2.5">
              Aanbevolen Lichte Modellen voor Mac/Mini-PC (1-Klik Installeren)
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {recommendedOllamaModels.map((m) => {
                const isInstalled = ollamaModels.some((x) => x.name.includes(m.name));
                return (
                  <div
                    key={m.name}
                    className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 space-y-2 flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-1 mb-1">
                        <span className="font-mono text-xs font-bold text-slate-200">{m.name}</span>
                        <span className="text-[10px] text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded font-semibold">
                          {m.tag}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400">{m.desc}</p>
                    </div>

                    <button
                      type="button"
                      onClick={() => handlePullModel(m.name)}
                      disabled={isPulling || isInstalled}
                      className={`w-full flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                        isInstalled
                          ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/25 cursor-default'
                          : 'bg-indigo-600 hover:bg-indigo-500 text-white active:scale-95'
                      }`}
                    >
                      {isInstalled ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Geïnstalleerd</span>
                        </>
                      ) : (
                        <>
                          <DownloadCloud className="w-3.5 h-3.5" />
                          <span>Installeer Model</span>
                        </>
                      )}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Eigen model typen */}
          <div className="flex flex-col sm:flex-row items-center gap-2 pt-1">
            <input
              type="text"
              value={customModelToPull}
              onChange={(e) => setCustomModelToPull(e.target.value)}
              placeholder="Typ een andere modelnaam van Ollama Library (bijv. mistral:7b of phi3)..."
              className="flex-1 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            <button
              type="button"
              onClick={() => handlePullModel(customModelToPull)}
              disabled={isPulling || !customModelToPull.trim()}
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shrink-0 transition-colors disabled:opacity-50"
            >
              Download & Installeer
            </button>
          </div>

          {/* Tabel Geïnstalleerde Modellen */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
              Geïnstalleerde Ollama Modellen ({ollamaModels.length})
            </label>
            {ollamaModels.length === 0 ? (
              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-400 text-center">
                Geen lokale modellen gevonden. Installeer hierboven een model om lokaal te draaien.
              </div>
            ) : (
              <div className="rounded-xl border border-slate-800 overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                    <tr>
                      <th className="py-2.5 px-3">Modelnaam</th>
                      <th className="py-2.5 px-3">Grootte (GB)</th>
                      <th className="py-2.5 px-3">Familie</th>
                      <th className="py-2.5 px-3 text-right">Actie</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 bg-slate-900/60">
                    {ollamaModels.map((m) => (
                      <tr key={m.name} className="hover:bg-slate-800/40 transition-colors">
                        <td className="py-2 px-3 font-mono text-slate-200 font-bold">{m.name}</td>
                        <td className="py-2 px-3 text-slate-300 font-mono">{m.size_gb} GB</td>
                        <td className="py-2 px-3 text-slate-400 uppercase text-[10px]">{m.family}</td>
                        <td className="py-2 px-3 text-right">
                          <button
                            type="button"
                            onClick={() => handleDeleteOllamaModel(m.name)}
                            className="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                            title="Verwijder model uit Ollama"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* ─────────────────────────────────────────────────────────────
            SECTIE 2: GROQ CLOUD FREE TIER (TEKST + WHISPER)
        ───────────────────────────────────────────────────────────── */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-400">
                <Zap className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                  <span>2. Groq Cloud Free Tier (Tekst + Whisper Audio)</span>
                  <span className="text-[10px] uppercase font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                    Gratis Snelheidskanon
                  </span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Llama 3.3 70B & Qwen QwQ met honderden tokens per seconde + cloud-based Whisper transcripties.
                </p>
              </div>
            </div>

            <a
              href="https://console.groq.com/keys"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-orange-400 hover:text-orange-300 font-semibold"
            >
              <span>Gratis Sleutel Maken (30 sec)</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Groq API Sleutel (gsk_...)
              </label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <input
                    type={showGroqKey ? 'text' : 'password'}
                    name="groq_api_key"
                    value={formData.groq_api_key || ''}
                    onChange={handleChange}
                    placeholder="gsk_..."
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-slate-100 font-mono focus:outline-none focus:ring-1 focus:ring-orange-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowGroqKey(!showGroqKey)}
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-200"
                  >
                    {showGroqKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
                <button
                  type="button"
                  onClick={handleTestGroq}
                  disabled={testingGroq}
                  className="px-4 py-2 rounded-xl bg-orange-600 hover:bg-orange-500 text-white font-bold text-xs shrink-0 transition-colors disabled:opacity-50"
                >
                  {testingGroq ? 'Valideren…' : 'Test Sleutel'}
                </button>
              </div>
            </div>

            {groqResult && (
              <div
                className={`p-3 rounded-xl border text-xs ${
                  groqResult.connected
                    ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300'
                    : 'bg-rose-950/40 border-rose-500/30 text-rose-300'
                }`}
              >
                {groqResult.connected
                  ? `✓ Groq sleutel is geldig! ${groqModels.length} modellen ontdekt.`
                  : `✕ Fout: ${groqResult.error}`}
              </div>
            )}

            <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 text-[11px] text-slate-400 flex items-center gap-2">
              <span className="text-emerald-400 font-bold">✓ Whisper Turbo Actief:</span>
              <span>Audio timestamps worden direct via Groq Cloud berekend zonder je lokale CPU te belasten.</span>
            </div>
          </div>
        </div>

        {/* ─────────────────────────────────────────────────────────────
            SECTIE 3: HUGGING FACE FREE TIER & ZEROGPU (FLUX + WAN 2.1)
        ───────────────────────────────────────────────────────────── */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-yellow-500/10 border border-yellow-500/20 flex items-center justify-center text-yellow-400">
                <Video className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                  <span>3. Hugging Face Free Tier & ZeroGPU (FLUX.1 + Video)</span>
                  <span className="text-[10px] uppercase font-bold text-yellow-400 bg-yellow-500/10 px-2 py-0.5 rounded-full border border-yellow-500/20">
                    Gratis Cloud GPU
                  </span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Gebruik gratis ZeroGPU quota voor echte Image-to-Video animatie en FLUX.1-schnell beeldgeneratie.
                </p>
              </div>
            </div>

            <a
              href="https://huggingface.co/settings/tokens"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-yellow-400 hover:text-yellow-300 font-semibold"
            >
              <span>Gratis Token Aanmaken</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Hugging Face Access Token (hf_...)
              </label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <input
                    type={showHfToken ? 'text' : 'password'}
                    name="hf_token"
                    value={formData.hf_token || ''}
                    onChange={handleChange}
                    placeholder="hf_..."
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-slate-100 font-mono focus:outline-none focus:ring-1 focus:ring-yellow-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowHfToken(!showHfToken)}
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-200"
                  >
                    {showHfToken ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
                <button
                  type="button"
                  onClick={handleTestHf}
                  disabled={testingHf}
                  className="px-4 py-2 rounded-xl bg-yellow-600 hover:bg-yellow-500 text-white font-bold text-xs shrink-0 transition-colors disabled:opacity-50"
                >
                  {testingHf ? 'Valideren…' : 'Test Token'}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                ZeroGPU Image-to-Video Space ID
              </label>
              <input
                type="text"
                name="hf_video_space_id"
                value={formData.hf_video_space_id || 'multimodalart/Wan2.1-Fast'}
                onChange={handleChange}
                placeholder="multimodalart/Wan2.1-Fast"
                className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-slate-100 font-mono focus:outline-none focus:ring-1 focus:ring-yellow-500"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                Standaard: <code className="text-yellow-300">multimodalart/Wan2.1-Fast</code> of <code className="text-yellow-300">Wan-AI/Wan2.1</code>.
              </p>
            </div>

            {hfResult && (
              <div
                className={`p-3 rounded-xl border text-xs ${
                  hfResult.connected
                    ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300'
                    : 'bg-rose-950/40 border-rose-500/30 text-rose-300'
                }`}
              >
                {hfResult.connected
                  ? `✓ Hugging Face verbonden! Account: ${hfResult.user || 'Geldig'}`
                  : `✕ Fout: ${hfResult.error}`}
              </div>
            )}
          </div>
        </div>

        {/* ─────────────────────────────────────────────────────────────
            SECTIE 4: GOOGLE GEMINI, IMAGEN 3 & VEO
        ───────────────────────────────────────────────────────────── */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                <Key className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                  <span>4. Google Gemini, Imagen 3 & Veo 2.0</span>
                  <span className="text-[10px] uppercase font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full border border-indigo-500/20">
                    Officiële google-genai SDK
                  </span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Voor scripts, SEO, Imagen 3 beeldgeneratie en optionele Veo 2.0 videoclips.
                </p>
              </div>
            </div>

            <a
              href="https://aistudio.google.com/apikey"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
            >
              <span>Google AI Studio Sleutel</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Gemini API-sleutel (AIza...)
              </label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <input
                    type={showGeminiKey ? 'text' : 'password'}
                    name="gemini_api_key"
                    value={formData.gemini_api_key || ''}
                    onChange={handleChange}
                    placeholder="AIzaSy..."
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-slate-100 font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowGeminiKey(!showGeminiKey)}
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-200"
                  >
                    {showGeminiKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
                <button
                  type="button"
                  onClick={handleTestGemini}
                  disabled={testingGemini}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shrink-0 transition-colors disabled:opacity-50"
                >
                  {testingGemini ? 'Testen…' : 'Test & Ontdek Modellen'}
                </button>
              </div>
            </div>

            {geminiResult && (
              <div
                className={`p-3 rounded-xl border text-xs ${
                  geminiResult.valid
                    ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300'
                    : 'bg-rose-950/40 border-rose-500/30 text-rose-300'
                }`}
              >
                {geminiResult.valid ? geminiResult.message : `✕ Fout: ${geminiResult.error}`}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
              <div>
                <label className="block text-[11px] font-semibold text-slate-300 mb-1">Tekst / Script Model</label>
                <select
                  name="gemini_text_model"
                  value={formData.gemini_text_model || 'gemini-2.5-flash'}
                  onChange={handleChange}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-100 font-mono"
                >
                  {availableTextModels.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-300 mb-1">Beeld / Start-Frame Model</label>
                <select
                  name="gemini_image_model"
                  value={formData.gemini_image_model || 'imagen-3.0-generate-002'}
                  onChange={handleChange}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-100 font-mono"
                >
                  {availableImageModels.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-300 mb-1">Video Animatie Model</label>
                <select
                  name="gemini_video_model"
                  value={formData.gemini_video_model || 'veo-2.0-generate-001'}
                  onChange={handleChange}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-100 font-mono"
                >
                  {availableVideoModels.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* ─────────────────────────────────────────────────────────────
            SECTIE 5: STEMMEN-TESTER (MICROSOFT EDGE TTS)
        ───────────────────────────────────────────────────────────── */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <Mic className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                <span>5. Stemmen Tester (Microsoft Edge Neural TTS)</span>
                <span className="text-[10px] uppercase font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                  100% Echte Stemmen
                </span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Beluister direct de natuurlijke kinderstemmen zonder API-kosten of pieptonen.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Kies Stem</label>
              <select
                value={testVoiceId}
                onChange={(e) => setTestVoiceId(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-slate-100"
              >
                <option value="nl-NL-FennaNeural">Fenna (Nederlands - Vrolijk & Helder)</option>
                <option value="nl-NL-MaartenNeural">Maarten (Nederlands - Vriendelijk & Warm)</option>
                <option value="nl-BE-DenaNeural">Dena (Vlaams - Zacht & Vertellend)</option>
                <option value="nl-BE-ArnaudNeural">Arnaud (Vlaams - Rustig)</option>
                <option value="en-US-AnaNeural">Ana (Engels - Peuterstem)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Kinder-Pitch</label>
              <select
                value={testVoicePitch}
                onChange={(e) => setTestVoicePitch(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-slate-100"
              >
                <option value="+0Hz">Normaal (+0Hz)</option>
                <option value="+10Hz">Licht Kinderlijk (+10Hz)</option>
                <option value="+20Hz">Vrolijk Peuter (+20Hz)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Spreeksnelheid</label>
              <select
                value={testVoiceRate}
                onChange={(e) => setTestVoiceRate(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-slate-100"
              >
                <option value="-10%">Rustig (-10%)</option>
                <option value="+0%">Normaal (+0%)</option>
                <option value="+10%">Enthousiast (+10%)</option>
              </select>
            </div>
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              value={testSentence}
              onChange={(e) => setTestSentence(e.target.value)}
              className="flex-1 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-slate-100"
            />
            <button
              type="button"
              onClick={handleTestVoice}
              disabled={testingVoice}
              className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shrink-0 transition-colors disabled:opacity-50 flex items-center gap-1.5"
            >
              <Play className="w-3.5 h-3.5" />
              <span>{testingVoice ? 'Genereren…' : 'Beluister Stem'}</span>
            </button>
          </div>

          {testAudioUrl && (
            <div className="pt-2">
              <audio ref={audioPlayerRef} controls src={testAudioUrl} className="w-full h-9" />
            </div>
          )}
        </div>

        {/* ─────────────────────────────────────────────────────────────
            SECTIE 6: YOUTUBE STUDIO KOPPELING
        ───────────────────────────────────────────────────────────── */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
            <div className="w-10 h-10 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400">
              <Play className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-slate-100">6. YouTube Direct Publicatie</h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Koppel je YouTube-kanaal om voltooide video's direct te uploaden.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">OAuth Client ID</label>
              <input
                type="text"
                name="youtube_client_id"
                value={formData.youtube_client_id || ''}
                onChange={handleChange}
                placeholder="...apps.googleusercontent.com"
                className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-slate-100 font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">OAuth Client Secret</label>
              <input
                type="password"
                name="youtube_client_secret"
                value={formData.youtube_client_secret || ''}
                onChange={handleChange}
                placeholder="GOCSPX-..."
                className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-slate-100 font-mono"
              />
            </div>
          </div>

          <div className="pt-2 border-t border-slate-800">
            {loadingChannel ? (
              <p className="text-xs text-slate-400">Kanaalstatus controleren…</p>
            ) : youtubeChannel?.connected ? (
              <div className="flex items-center justify-between p-3 rounded-xl bg-emerald-950/40 border border-emerald-500/30">
                <span className="text-xs text-emerald-300 font-medium">
                  ✓ Verbonden met YouTube-kanaal: <strong>{youtubeChannel.title}</strong>
                </span>
                <button
                  type="button"
                  onClick={async () => {
                    await disconnectYouTube();
                    await loadYouTubeChannel();
                  }}
                  className="text-xs text-rose-400 hover:text-rose-300 font-semibold"
                >
                  Ontkoppelen
                </button>
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <p className="text-xs text-slate-400">Nog geen kanaal gekoppeld.</p>
                <button
                  type="button"
                  onClick={async () => {
                    const url = await getYouTubeAuthUrl();
                    if (url) window.open(url, '_blank');
                  }}
                  className="px-3 py-1.5 rounded-xl bg-red-600 hover:bg-red-500 text-white font-bold text-xs"
                >
                  Koppel via Google OAuth
                </button>
              </div>
            )}
          </div>
        </div>
      </form>
    </div>
  );
};
