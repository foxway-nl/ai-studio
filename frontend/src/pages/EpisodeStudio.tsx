import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Sparkles,
  Clapperboard,
  Plus,
  Film,
  ArrowRight,
  ArrowLeft,
  Image as ImageIcon,
  Mic,
  AudioLines,
  Users,
  Video,
  Upload,
  Check,
  FileDown,
  Zap,
  Trash2,
  Dice5,
  RotateCcw,
  ExternalLink,
} from 'lucide-react';
import { useStore } from '../store/useStore';
import { Modal } from '../components/Modal';
import { EmptyState } from '../components/EmptyState';
import { TaskProgress } from '../components/TaskProgress';
import type { Scene } from '../api/client';

export const EpisodeStudio: React.FC = () => {
  const { id: episodeId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const {
    currentEpisode,
    fetchEpisode,
    autoSaveEpisode,
    scenes,
    scenesLoading,
    fetchScenes,
    createScene,
    deleteScene,
    autoSaveScene,
    characters,
    fetchCharacters,
    generateScript,
    generateViralIdeas,
    generateImage,
    generateAudio,
    generateBulkAudio,
    animateScene,
    animateSceneLocal,
    animateEpisodeLocalBulk,
    uploadSceneClip,
    generateSceneMotionPrompt,
    exportGoogleFlow,
    addToast,
  } = useStore();

  // ─── 6-Stappen Wizard State ───────────────────────────────────────────────
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3 | 4 | 5 | 6>(1);

  // Script & Ideeën Modal state
  const [isScriptModalOpen, setIsScriptModalOpen] = useState(false);
  const [scriptTopic, setScriptTopic] = useState('');
  const [activeScriptTaskId, setActiveScriptTaskId] = useState<string | null>(null);
  const [bulkAudioTaskId, setBulkAudioTaskId] = useState<string | null>(null);

  // Viral Ideas state
  const [viralIdeas, setViralIdeas] = useState<string[]>([]);
  const [loadingIdeas, setLoadingIdeas] = useState(false);
  const [isIdeasModalOpen, setIsIdeasModalOpen] = useState(false);

  // Active generation tasks
  const [generatingImages, setGeneratingImages] = useState<Record<string, boolean>>({});
  const [generatingAudios, setGeneratingAudios] = useState<Record<string, boolean>>({});
  const [animatingScenes, setAnimatingScenes] = useState<Record<string, boolean>>({});
  const [animatingLocalScenes, setAnimatingLocalScenes] = useState<Record<string, boolean>>({});
  const [isBulkLocalAnimating, setIsBulkLocalAnimating] = useState(false);
  const [generatingMotionPrompts, setGeneratingMotionPrompts] = useState<Record<string, boolean>>({});
  const [copiedPromptId, setCopiedPromptId] = useState<string | null>(null);
  const [isExportingFlow, setIsExportingFlow] = useState(false);
  const fileInputRefs = useRef<Record<string, HTMLInputElement | null>>({});

  useEffect(() => {
    if (episodeId) {
      fetchEpisode(episodeId);
      fetchScenes(episodeId);
    }
  }, [episodeId, fetchEpisode, fetchScenes]);

  useEffect(() => {
    if (currentEpisode) {
      fetchCharacters(currentEpisode.project_id);
      if (currentEpisode.title && !scriptTopic) {
        setScriptTopic(currentEpisode.title);
      }
    }
  }, [currentEpisode, fetchCharacters]);

  // Bepaal of de huidige stap voltooid is voor de groene oplichtende knop
  const isStepComplete = (step: number): boolean => {
    switch (step) {
      case 1:
        return Boolean(currentEpisode?.title && currentEpisode.title.trim().length > 0);
      case 2:
        return characters.length > 0;
      case 3:
        return scenes.length > 0;
      case 4:
        return scenes.length > 0 && scenes.some((s) => Boolean(s.audio_url));
      case 5:
        return scenes.length > 0 && scenes.some((s) => Boolean(s.image_url || s.video_clip_url));
      case 6:
        return scenes.length > 0;
      default:
        return false;
    }
  };

  const WIZARD_STEPS = [
    { step: 1, label: 'Thema & Doelgroep', icon: Clapperboard },
    { step: 2, label: 'Karakter-Check', icon: Users },
    { step: 3, label: 'Script & Scènes', icon: Sparkles },
    { step: 4, label: 'Echte Stemmen', icon: Mic },
    { step: 5, label: 'Start-Frames & Video', icon: Video },
    { step: 6, label: 'Montage & Publicatie', icon: Film },
  ];

  const ASSISTANT_MESSAGES: Record<number, string> = {
    1: 'Stap 1: Kies je doelgroep, voer een leuk onderwerp in (of klik op "🎲 5 virale ideeën") en selecteer welke vriendjes meedoen.',
    2: 'Stap 2: Controleer of Adam en Nora een goedgekeurd referentieportret en echte stem hebben zodat ze er in elke scène consistent uitzien.',
    3: 'Stap 3: Klik op "✨ Schrijf Compleet Script" om de scènes te laten genereren door je gekozen AI-schrijver en pas de teksten naar wens aan.',
    4: 'Stap 4: Klik op "🎙️ Genereer Alle Stemmen" om met echte Edge-TTS de Nederlandse gesproken audio en exacte duur te meten.',
    5: 'Stap 5: Genereer per scène eerst het Start-Frame plaatje en klik vervolgens op "🎬 Animeer Scène" voor echte videobeweging.',
    6: 'Stap 6: Je aflevering is klaar voor de eindmontage! Klik op "🎞️ Render Complete Aflevering" om de film in elkaar te zetten en te publiceren.',
  };

  // ─── Handlers ─────────────────────────────────────────────────────────────

  const handleFetchIdeas = async () => {
    if (!episodeId) return;
    setLoadingIdeas(true);
    setIsIdeasModalOpen(true);
    try {
      const ideas = await generateViralIdeas(episodeId, currentEpisode?.target_audience || 'kids');
      setViralIdeas(ideas);
    } catch {
      setViralIdeas([
        'De Magische Kleurenboom in het Bos',
        'Adam en Nora Leren Tellen met Dieren',
        'Waarom Regen Plonst: Het Water Avontuur',
        'De Trein der Vormen en Cijfers',
        'Samen Delen en Fruit Proeven in de Tuin',
      ]);
    } finally {
      setLoadingIdeas(false);
    }
  };

  const handleSelectIdea = (idea: string) => {
    setScriptTopic(idea);
    if (episodeId) {
      autoSaveEpisode(episodeId, { title: idea });
    }
    setIsIdeasModalOpen(false);
    addToast('success', `Onderwerp gekozen: "${idea}"`);
  };

  const handleRunGenerateScript = async () => {
    if (!episodeId || !scriptTopic.trim()) {
      addToast('error', 'Voer eerst een onderwerp in.');
      return;
    }
    try {
      const taskId = await generateScript(episodeId, scriptTopic.trim(), []);
      setActiveScriptTaskId(taskId);
      setIsScriptModalOpen(false);
    } catch (err) {
      console.error(err);
    }
  };

  const handleGenerateSceneAudio = async (sceneId: string) => {
    setGeneratingAudios((prev) => ({ ...prev, [sceneId]: true }));
    try {
      await generateAudio(sceneId);
    } catch (err) {
      console.error(err);
    } finally {
      setGeneratingAudios((prev) => ({ ...prev, [sceneId]: false }));
    }
  };

  const handleBulkAudio = async () => {
    if (!episodeId) return;
    try {
      const taskId = await generateBulkAudio(episodeId);
      setBulkAudioTaskId(taskId);
    } catch (err) {
      console.error(err);
    }
  };

  const handleGenerateSceneImage = async (sceneId: string) => {
    setGeneratingImages((prev) => ({ ...prev, [sceneId]: true }));
    try {
      await generateImage(sceneId);
    } catch (err) {
      console.error(err);
    } finally {
      setGeneratingImages((prev) => ({ ...prev, [sceneId]: false }));
    }
  };

  const handleAnimateScene = async (sceneId: string, engine: string, motionPrompt?: string) => {
    setAnimatingScenes((prev) => ({ ...prev, [sceneId]: true }));
    try {
      await animateScene(sceneId, engine, motionPrompt);
    } catch (err) {
      console.error(err);
    } finally {
      setAnimatingScenes((prev) => ({ ...prev, [sceneId]: false }));
    }
  };

  const handleAnimateSceneLocal = async (sceneId: string) => {
    setAnimatingLocalScenes((prev) => ({ ...prev, [sceneId]: true }));
    try {
      await animateSceneLocal(sceneId);
    } catch (err) {
      console.error(err);
    } finally {
      setAnimatingLocalScenes((prev) => ({ ...prev, [sceneId]: false }));
    }
  };

  const handleBulkAnimateLocal = async () => {
    if (!episodeId) return;
    setIsBulkLocalAnimating(true);
    try {
      await animateEpisodeLocalBulk(episodeId);
    } catch (err) {
      console.error(err);
    } finally {
      setIsBulkLocalAnimating(false);
    }
  };

  const handleGenerateMotionPrompt = async (sceneId: string) => {
    setGeneratingMotionPrompts((prev) => ({ ...prev, [sceneId]: true }));
    try {
      await generateSceneMotionPrompt(sceneId);
    } catch (err) {
      console.error(err);
    } finally {
      setGeneratingMotionPrompts((prev) => ({ ...prev, [sceneId]: false }));
    }
  };

  const handleCopyFlowPrompt = (scene: Scene) => {
    const text =
      scene.motion_prompt ||
      `Lively 2D cartoon animation: characters move, gesture and talk expressively. ${scene.visual_prompt || scene.narration}`;
    navigator.clipboard.writeText(text);
    setCopiedPromptId(scene.id);
    setTimeout(() => setCopiedPromptId(null), 2500);

    if (scene.image_url) {
      const link = document.createElement('a');
      link.href = scene.image_url;
      link.download = `scene_${scene.order}_start_frame.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const handleExportFlow = async () => {
    if (!episodeId) return;
    setIsExportingFlow(true);
    try {
      await exportGoogleFlow(episodeId);
    } catch (err) {
      console.error(err);
    } finally {
      setIsExportingFlow(false);
    }
  };

  const handleUploadSceneVideo = async (sceneId: string, file: File) => {
    try {
      await uploadSceneClip(sceneId, file);
    } catch (err) {
      console.error(err);
    }
  };

  const handleToggleCharacterInScene = (sc: Scene, charId: string) => {
    const currentCharIds = (sc.character_ids || []).slice();
    const nextIds = currentCharIds.includes(charId)
      ? currentCharIds.filter((id) => id !== charId)
      : [...currentCharIds, charId];

    const activeChars = characters.filter((c) => nextIds.includes(c.id));
    const charsInScene = activeChars.map((c, idx) => ({
      character_id: c.id,
      name: c.name,
      position: (idx === 0 ? 'left' : idx === 1 ? 'right' : 'center') as 'left' | 'center' | 'right',
      emotion: 'blij',
    }));

    autoSaveScene(sc.id, {
      character_ids: nextIds,
      characters_in_scene: charsInScene,
    });
  };

  const handleInjectCharacterDna = (sc: Scene) => {
    const activeChars = characters.filter((c) => (sc.character_ids || []).includes(c.id));
    if (!activeChars.length) {
      alert('Vink eerst minimaal 1 karakter aan in deze scène.');
      return;
    }
    const dnaList = activeChars
      .map((c) => `${c.name}: ${c.visual_dna_prompt || c.description || 'vrolijk kinderkarakter'}`)
      .join('. ');
    const newVisual = `${sc.visual_prompt ? sc.visual_prompt + ' | ' : ''}Characters: ${dnaList}. High quality 3D Pixar render, solid bright colors, kid-friendly.`;
    const charNames = activeChars.map((c) => c.name).join(' and ');
    const newMotion = `${sc.motion_prompt ? sc.motion_prompt + ' | ' : ''}${charNames} moving enthusiastically, smiling and interacting joyfully. Smooth 2D animation.`;

    autoSaveScene(sc.id, {
      visual_prompt: newVisual,
      motion_prompt: newMotion,
    });
    addToast('success', 'Karakter-DNA geïnjecteerd in Start-Frame prompt!');
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300 text-slate-100 pb-28">
      {/* ─────────────────────────────────────────────────────────────
          1. BOVENBALK: STEPPER VOORTGANGSBAR (1 t/m 6)
      ───────────────────────────────────────────────────────────── */}
      <div className="p-6 rounded-3xl bg-slate-900 border border-slate-800 space-y-5 shadow-xl shadow-black/30">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-amber-500 via-rose-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
              <Clapperboard className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-indigo-400">
                <span>Productie Wizard</span>
                <span className="text-slate-600">•</span>
                <span>Stap {currentStep} van 6</span>
              </div>
              <h1 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
                <span>{currentEpisode?.title || 'Naamloze Aflevering'}</span>
              </h1>
            </div>
          </div>

          {/* Wizard Navigatie Knoppen */}
          <div className="flex items-center gap-2.5 shrink-0">
            <button
              type="button"
              onClick={() => setCurrentStep((prev) => Math.max(1, prev - 1) as any)}
              disabled={currentStep === 1}
              className="flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs transition-all disabled:opacity-30"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Vorige</span>
            </button>

            <button
              type="button"
              onClick={() => setCurrentStep((prev) => Math.min(6, prev + 1) as any)}
              disabled={currentStep === 6}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs transition-all shadow-md active:scale-95 ${
                isStepComplete(currentStep)
                  ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-500/25 ring-2 ring-emerald-400 animate-pulse'
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/25'
              }`}
            >
              <span>Volgende Stap</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* De 6 Stappen Knoppenrij */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
          {WIZARD_STEPS.map((s) => {
            const Icon = s.icon;
            const active = currentStep === s.step;
            const completed = isStepComplete(s.step);

            return (
              <button
                key={s.step}
                type="button"
                onClick={() => setCurrentStep(s.step as any)}
                className={`p-3 rounded-2xl flex flex-col items-center gap-1.5 text-center transition-all ${
                  active
                    ? 'bg-indigo-600 text-white font-bold shadow-lg shadow-indigo-600/30 ring-2 ring-indigo-400'
                    : completed
                    ? 'bg-slate-950/70 text-slate-200 border border-emerald-500/30 hover:border-emerald-500'
                    : 'bg-slate-950/40 text-slate-400 border border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <span
                    className={`w-5 h-5 rounded-full text-[10px] font-black flex items-center justify-center ${
                      active
                        ? 'bg-white text-indigo-900'
                        : completed
                        ? 'bg-emerald-500 text-slate-950'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {completed && !active ? '✓' : s.step}
                  </span>
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <span className="text-[11px] leading-tight font-semibold line-clamp-1">{s.label}</span>
              </button>
            );
          })}
        </div>

        {/* ─────────────────────────────────────────────────────────────
            AI ASSISTENT-BALK (BEGELEIDING PER STAP)
        ───────────────────────────────────────────────────────────── */}
        <div className="p-3.5 rounded-2xl bg-indigo-950/40 border border-indigo-500/30 flex items-center gap-3 text-indigo-200 text-xs">
          <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center text-white shrink-0 shadow-sm">
            <Sparkles className="w-4 h-4 animate-spin duration-1000" />
          </div>
          <div className="flex-1 font-medium leading-relaxed">
            <strong className="text-white">AI Assistent: </strong>
            {ASSISTANT_MESSAGES[currentStep]}
          </div>
        </div>
      </div>

      {/* Actieve Achtergrondtaken Voortgang */}
      {activeScriptTaskId && (
        <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800">
          <TaskProgress taskId={activeScriptTaskId} onComplete={() => setActiveScriptTaskId(null)} />
        </div>
      )}
      {bulkAudioTaskId && (
        <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800">
          <TaskProgress taskId={bulkAudioTaskId} onComplete={() => setBulkAudioTaskId(null)} />
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          STAP 1: THEMA, DOELGROEP & FORMAAT KIEZEN
      ───────────────────────────────────────────────────────────── */}
      {currentStep === 1 && (
        <div className="p-8 rounded-3xl bg-slate-900 border border-slate-800 space-y-6 shadow-xl shadow-black/20">
          <div className="border-b border-slate-800 pb-4">
            <h2 className="text-lg font-black text-white flex items-center gap-2">
              <Clapperboard className="w-5 h-5 text-indigo-400" />
              <span>Stap 1: Doelgroep, Onderwerp & Karakters</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Stel de basisparameters van de aflevering in. Kies of de video voor peuters/kleuters (YouTube Kids) of algemeen publiek bedoeld is.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Doelgroep Keuze */}
            <div className="space-y-3">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300">
                Doelgroep & YouTube Formaat
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => {
                    if (episodeId) {
                      autoSaveEpisode(episodeId, { target_audience: 'kids', made_for_kids: true });
                    }
                  }}
                  className={`p-4 rounded-2xl border text-left transition-all ${
                    (currentEpisode?.target_audience ?? 'kids') === 'kids'
                      ? 'bg-indigo-600/20 border-indigo-500 text-indigo-100 ring-2 ring-indigo-500/40'
                      : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <div className="text-sm font-bold flex items-center gap-2 mb-1">
                    <span>👶 YouTube Kids</span>
                    <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-1.5 py-0.5 rounded font-mono">
                      COPPA
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Tot 7 jaar. Korte zinnen, vrolijke intonatie, veilige educatieve thema's.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    if (episodeId) {
                      autoSaveEpisode(episodeId, { target_audience: 'general', made_for_kids: false });
                    }
                  }}
                  className={`p-4 rounded-2xl border text-left transition-all ${
                    currentEpisode?.target_audience === 'general'
                      ? 'bg-indigo-600/20 border-indigo-500 text-indigo-100 ring-2 ring-indigo-500/40'
                      : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <div className="text-sm font-bold flex items-center gap-2 mb-1">
                    <span>🎬 Standaard YouTube</span>
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Algemene educatie & verhalen. Vrijere zinsopbouw en langere scènes.
                  </p>
                </button>
              </div>
            </div>

            {/* Onderwerp & Virale Ideeën Knop */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  Onderwerp / Titel van de Aflevering
                </label>
                <button
                  type="button"
                  onClick={handleFetchIdeas}
                  className="flex items-center gap-1.5 px-3 py-1 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-white text-xs font-bold shadow-md shadow-amber-500/20 transition-all active:scale-95"
                >
                  <Dice5 className="w-3.5 h-3.5" />
                  <span>🎲 5 Virale Ideeën</span>
                </button>
              </div>

              <input
                type="text"
                value={currentEpisode?.title || ''}
                onChange={(e) => {
                  const val = e.target.value;
                  if (episodeId) autoSaveEpisode(episodeId, { title: val });
                  setScriptTopic(val);
                }}
                placeholder="Bijv. Adam en Nora in het Kleurenrijk: Leren Kleuren Mengen..."
                className="w-full px-4 py-3 rounded-2xl bg-slate-950 border border-slate-700 text-sm text-slate-100 font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-inner"
              />
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800 flex justify-end">
            <button
              type="button"
              onClick={() => setCurrentStep(2)}
              disabled={!isStepComplete(1)}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs transition-all disabled:opacity-40"
            >
              <span>Ga naar Stap 2: Karakter-Check</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          STAP 2: KARAKTER-CHECK (KARAKTER KLUIS)
      ───────────────────────────────────────────────────────────── */}
      {currentStep === 2 && (
        <div className="p-8 rounded-3xl bg-slate-900 border border-slate-800 space-y-6 shadow-xl shadow-black/20">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
            <div>
              <h2 className="text-lg font-black text-white flex items-center gap-2">
                <Users className="w-5 h-5 text-indigo-400" />
                <span>Stap 2: Karakter Consistentie & Referentie-Check</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Controleer of de karakters (zoals Adam en Nora) een referentieportret en stem hebben zodat ze er in elke scène identiek uitzien.
              </p>
            </div>

            <button
              type="button"
              onClick={() => navigate('/characters')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
            >
              <span>Open Volledige Karakter Kluis</span>
              <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
            </button>
          </div>

          {characters.length === 0 ? (
            <EmptyState
              icon={Users}
              title="Nog geen karakters aangemaakt"
              description="Maak minimaal 1 karakter (bijv. Adam of Nora) aan in de Karakter Kluis."
              actionLabel="Karakters Aanmaken"
              onAction={() => navigate('/characters')}
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {characters.map((c) => (
                <div
                  key={c.id}
                  className="p-5 rounded-2xl bg-slate-950 border border-slate-800 hover:border-slate-700 transition-all space-y-3.5"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-16 h-16 rounded-2xl bg-black border border-slate-700 overflow-hidden shrink-0 flex items-center justify-center">
                      {(c.sprite_url || (c.reference_image_urls && c.reference_image_urls[0])) ? (
                        <img
                          src={c.sprite_url || (c.reference_image_urls && c.reference_image_urls[0]) || ''}
                          alt={c.name}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <Users className="w-6 h-6 text-slate-600" />
                      )}
                    </div>
                    <div>
                      <h3 className="font-bold text-sm text-white flex items-center gap-1.5">
                        <span>{c.name}</span>
                        <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded font-mono">
                          DNA ✓
                        </span>
                      </h3>
                      <p className="text-[11px] text-slate-400 line-clamp-1">{c.description || 'Kinderheld'}</p>
                      <p className="text-[10px] text-indigo-400 font-mono mt-0.5">
                        Stem: {c.voice_id || 'nl-NL-FennaNeural'}
                      </p>
                    </div>
                  </div>

                  <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-[11px] text-slate-400 space-y-1">
                    <span className="font-bold text-slate-300 block text-[10px] uppercase">Visueel DNA:</span>
                    <p className="italic line-clamp-2">{c.visual_dna_prompt || c.style_prompt || '3D Pixar cartoon'}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="pt-4 border-t border-slate-800 flex justify-between items-center">
            <button
              type="button"
              onClick={() => setCurrentStep(1)}
              className="text-xs text-slate-400 hover:text-slate-200"
            >
              ← Terug naar Thema
            </button>

            <button
              type="button"
              onClick={() => setCurrentStep(3)}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs transition-all"
            >
              <span>Ga naar Stap 3: Het Verhaal & Script</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          STAP 3: HET VERHAAL & SCÈNE-SCRIPT (MET VIRALE GUARDRAILS)
      ───────────────────────────────────────────────────────────── */}
      {currentStep === 3 && (
        <div className="space-y-6">
          <div className="p-6 rounded-3xl bg-slate-900 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-black text-white flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-indigo-400" />
                <span>Stap 3: Het Verhaal & Scène-Script</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Genereer het script met je gekozen AI-schrijver (Groq, Gemini of Ollama) en pas sprekers en teksten aan.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setIsScriptModalOpen(true)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold text-xs shadow-lg shadow-indigo-600/20 active:scale-95 transition-all"
              >
                <Sparkles className="w-4 h-4" />
                <span>✨ Schrijf Compleet Script</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  if (episodeId) {
                    createScene({
                      episode_id: episodeId,
                      order: scenes.length + 1,
                      narration: 'Nieuwe scène tekst...',
                      visual_prompt: 'Kleurrijke educatieve animatie achtergrond',
                    });
                  }
                }}
                className="flex items-center gap-1.5 px-3 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs"
              >
                <Plus className="w-4 h-4" />
                <span>Nieuwe Scène</span>
              </button>
            </div>
          </div>

          {/* Scène Editor Cards */}
          {scenes.length === 0 && !scenesLoading ? (
            <EmptyState
              icon={Film}
              title="Nog geen scènes aangemaakt"
              description="Klik op '✨ Schrijf Compleet Script' om automatisch scènes te genereren met je AI-schrijver."
              actionLabel="AI Script Genereren"
              onAction={() => setIsScriptModalOpen(true)}
            />
          ) : (
            <div className="space-y-4">
              {scenes.map((sc) => (
                <div
                  key={sc.id}
                  className="p-6 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all space-y-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
                    <div className="flex items-center gap-2.5">
                      <span className="w-7 h-7 rounded-xl bg-indigo-500/20 text-indigo-300 font-black text-xs flex items-center justify-center border border-indigo-500/30">
                        #{sc.order}
                      </span>
                      <input
                        type="text"
                        value={sc.title || ''}
                        onChange={(e) => autoSaveScene(sc.id, { title: e.target.value })}
                        placeholder={`Scène ${sc.order} titel...`}
                        className="bg-transparent font-bold text-sm text-white focus:outline-none focus:border-b focus:border-indigo-500"
                      />
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          if (confirm(`Scène #${sc.order} verwijderen?`)) deleteScene(sc.id);
                        }}
                        className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                        title="Verwijder scène"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                    {/* Spreker & Tekst */}
                    <div className="lg:col-span-8 space-y-3">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                          <label className="block text-[11px] font-semibold text-slate-400 mb-1">Wie spreekt er?</label>
                          <select
                            value={sc.speaker || ''}
                            onChange={(e) => {
                              const val = e.target.value;
                              autoSaveScene(sc.id, { speaker: val, active_speaker: val || 'verteller' });
                            }}
                            className="w-full px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-700 text-xs text-slate-100"
                          >
                            <option value="">Verteller (Voice-Over)</option>
                            {characters.map((c) => (
                              <option key={c.id} value={c.name}>{c.name}</option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label className="block text-[11px] font-semibold text-slate-400 mb-1">Pauze na scène (sec)</label>
                          <input
                            type="number"
                            step="0.1"
                            value={sc.pause_after_sec || 0.4}
                            onChange={(e) => autoSaveScene(sc.id, { pause_after_sec: parseFloat(e.target.value) || 0.4 })}
                            className="w-full px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-700 text-xs text-slate-100"
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <label className="text-[11px] font-semibold text-slate-400">Gesproken Nederlandse Tekst</label>
                          <span className="text-[10px] text-emerald-400 flex items-center gap-1 font-semibold">
                            <Check className="w-3 h-3" /> Viral Coach: Kort & Krachtig
                          </span>
                        </div>
                        <textarea
                          rows={3}
                          value={sc.narration || ''}
                          onChange={(e) => autoSaveScene(sc.id, { narration: e.target.value })}
                          placeholder="Voer de enthousiaste gesproken kindertekst in..."
                          className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 leading-relaxed"
                        />
                      </div>
                    </div>

                    {/* Karakters in beeld (Checkboxes) */}
                    <div className="lg:col-span-4 p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-3 flex flex-col justify-between">
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <label className="text-[10px] uppercase font-bold text-slate-400">
                            Karakters in Beeld:
                          </label>
                          <button
                            type="button"
                            onClick={() => handleInjectCharacterDna(sc)}
                            className="text-[10px] text-indigo-400 hover:text-indigo-300 font-semibold"
                            title="Injecteer DNA van geselecteerde karakters"
                          >
                            🧬 DNA Injecteren
                          </button>
                        </div>

                        <div className="flex flex-wrap gap-1.5">
                          {characters.map((c) => {
                            const active = (sc.character_ids || []).includes(c.id);
                            return (
                              <button
                                key={c.id}
                                type="button"
                                onClick={() => handleToggleCharacterInScene(sc, c.id)}
                                className={`px-2.5 py-1 rounded-lg text-xs font-semibold border transition-all ${
                                  active
                                    ? 'bg-indigo-600/30 border-indigo-500 text-indigo-200'
                                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                                }`}
                              >
                                {active ? '✓ ' : '+ '} {c.name}
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      <div className="text-[10px] text-slate-500">
                        Vink de karakters aan die in deze scène te zien moeten zijn voor automatische consistentie.
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="pt-4 border-t border-slate-800 flex justify-between items-center">
            <button
              type="button"
              onClick={() => setCurrentStep(2)}
              className="text-xs text-slate-400 hover:text-slate-200"
            >
              ← Terug naar Karakters
            </button>

            <button
              type="button"
              onClick={() => setCurrentStep(4)}
              disabled={scenes.length === 0}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs transition-all disabled:opacity-40"
            >
              <span>Ga naar Stap 4: Echte Stemmen</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          STAP 4: ECHTE STEMMEN GENEREREN & BELUISTEREN (AUDIO-FIRST)
      ───────────────────────────────────────────────────────────── */}
      {currentStep === 4 && (
        <div className="space-y-6">
          <div className="p-6 rounded-3xl bg-slate-900 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-black text-white flex items-center gap-2">
                <Mic className="w-5 h-5 text-emerald-400" />
                <span>Stap 4: Echte Stemmen (Audio-First Productie)</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Genereer met echte Microsoft Edge-TTS de Nederlandse spraak. De exacte audioduur wordt op de milliseconde berekend.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleBulkAudio}
                disabled={scenes.length === 0 || !!bulkAudioTaskId}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-lg shadow-emerald-600/20 active:scale-95 transition-all disabled:opacity-50"
              >
                <AudioLines className="w-4 h-4" />
                <span>🎙️ Genereer Alle Stemmen</span>
              </button>
            </div>
          </div>

          <div className="space-y-4">
            {scenes.map((sc) => (
              <div
                key={sc.id}
                className="p-5 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-1.5 flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-lg bg-emerald-500/20 text-emerald-300 font-black text-xs flex items-center justify-center">
                      #{sc.order}
                    </span>
                    <strong className="text-xs text-white">{sc.speaker || 'Verteller'}</strong>
                    <span className="text-[10px] text-slate-400 font-mono">
                      Duur: <strong className="text-emerald-300">{sc.duration_seconds || 8}s</strong>
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 italic line-clamp-2">"{sc.narration || 'Geen tekst ingevuld'}"</p>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {sc.audio_url ? (
                    <div className="flex items-center gap-2">
                      <audio controls className="h-8 w-48 text-xs" src={sc.audio_url} />
                      <button
                        type="button"
                        onClick={() => handleGenerateSceneAudio(sc.id)}
                        disabled={generatingAudios[sc.id]}
                        className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs"
                        title="Opnieuw genereren"
                      >
                        <RotateCcw className={`w-3.5 h-3.5 ${generatingAudios[sc.id] ? 'animate-spin' : ''}`} />
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => handleGenerateSceneAudio(sc.id)}
                      disabled={generatingAudios[sc.id] || !sc.narration}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/30 text-emerald-300 font-bold text-xs transition-colors disabled:opacity-40"
                    >
                      <Mic className="w-3.5 h-3.5" />
                      <span>{generatingAudios[sc.id] ? 'Genereren…' : 'Genereer Stem'}</span>
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="pt-4 border-t border-slate-800 flex justify-between items-center">
            <button
              type="button"
              onClick={() => setCurrentStep(3)}
              className="text-xs text-slate-400 hover:text-slate-200"
            >
              ← Terug naar Script
            </button>

            <button
              type="button"
              onClick={() => setCurrentStep(5)}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs transition-all"
            >
              <span>Ga naar Stap 5: Start-Frames & Animatie</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          STAP 5: START-FRAMES & VIDEO-ANIMATIE MAKEN
      ───────────────────────────────────────────────────────────── */}
      {currentStep === 5 && (
        <div className="space-y-6">
          <div className="p-6 rounded-3xl bg-slate-900 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-black text-white flex items-center gap-2">
                <Video className="w-5 h-5 text-rose-400" />
                <span>Stap 5: Start-Frames & Video-Animatie (Image-to-Video)</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Vergrendel eerst het 16:9 Start-Frame en genereer vervolgens echte animatie (ZeroGPU Wan 2.1, Veo of Lokale 60fps).
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={handleBulkAnimateLocal}
                disabled={isBulkLocalAnimating || scenes.length === 0}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-amber-600/20 hover:bg-amber-600/30 border border-amber-500/30 text-amber-200 text-xs font-semibold transition-colors disabled:opacity-50"
                title="Animeer alle scènes lokaal met 60fps 2.5D camerabeweging"
              >
                <Zap className={`w-3.5 h-3.5 text-amber-400 ${isBulkLocalAnimating ? 'animate-spin' : ''}`} />
                <span>{isBulkLocalAnimating ? 'Lokaal Renderen…' : '⚡ Bulk Lokaal Animeren (60fps)'}</span>
              </button>

              <button
                type="button"
                onClick={handleExportFlow}
                disabled={isExportingFlow || scenes.length === 0}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
              >
                <FileDown className="w-3.5 h-3.5 text-amber-400" />
                <span>Google Flow (.zip)</span>
              </button>
            </div>
          </div>

          <div className="space-y-6">
            {scenes.map((sc) => (
              <div
                key={sc.id}
                className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4 shadow-lg shadow-black/20"
              >
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="w-7 h-7 rounded-lg bg-indigo-500/20 text-indigo-300 font-black text-xs flex items-center justify-center">
                      #{sc.order}
                    </span>
                    <strong className="text-sm text-white">{sc.title || `Scène ${sc.order}`}</strong>
                  </div>

                  <div className="flex items-center gap-2">
                    {sc.video_clip_url ? (
                      <span className="px-2.5 py-1 rounded-full bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-bold flex items-center gap-1">
                        <Video className="w-3 h-3" /> Echte Animatie Actief
                      </span>
                    ) : sc.image_url ? (
                      <span className="px-2.5 py-1 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-300 text-xs font-bold flex items-center gap-1">
                        <ImageIcon className="w-3 h-3" /> Start-Frame Klaar
                      </span>
                    ) : (
                      <span className="px-2.5 py-1 rounded-full bg-slate-800 text-slate-400 text-xs">Draft</span>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Kolom Links: Start-Frame */}
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3 flex flex-col justify-between">
                    <div className="space-y-2.5">
                      <div className="flex items-center justify-between text-xs font-bold text-amber-300">
                        <span className="flex items-center gap-1.5">
                          <ImageIcon className="w-3.5 h-3.5" />
                          <span>1. Start-Frame (Referentiebeeld)</span>
                        </span>
                      </div>

                      <div className="aspect-video w-full rounded-xl bg-black border border-slate-800 overflow-hidden relative flex items-center justify-center">
                        {sc.image_url ? (
                          <img src={sc.image_url} alt="Start-Frame" className="w-full h-full object-cover" />
                        ) : (
                          <div className="text-slate-500 text-xs flex flex-col items-center gap-1">
                            <ImageIcon className="w-6 h-6 opacity-30" />
                            <span>Geen Start-Frame gegenereerd</span>
                          </div>
                        )}
                      </div>

                      <textarea
                        rows={2}
                        value={sc.visual_prompt || ''}
                        onChange={(e) => autoSaveScene(sc.id, { visual_prompt: e.target.value })}
                        placeholder="Start-Frame prompt in het Engels..."
                        className="w-full px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 font-mono"
                      />
                    </div>

                    <button
                      type="button"
                      onClick={() => handleGenerateSceneImage(sc.id)}
                      disabled={generatingImages[sc.id]}
                      className="w-full flex items-center justify-center gap-1.5 py-2 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-200 font-bold text-xs transition-colors disabled:opacity-50"
                    >
                      <Sparkles className={`w-3.5 h-3.5 ${generatingImages[sc.id] ? 'animate-spin' : ''}`} />
                      <span>{generatingImages[sc.id] ? 'Genereren…' : sc.image_url ? 'Opnieuw Start-Frame Maken' : '🎨 Genereer Start-Frame'}</span>
                    </button>
                  </div>

                  {/* Kolom Rechts: Echte Video-Animatie */}
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3 flex flex-col justify-between">
                    <div className="space-y-2.5">
                      <div className="flex items-center justify-between text-xs font-bold text-rose-300">
                        <span className="flex items-center gap-1.5">
                          <Video className="w-3.5 h-3.5" />
                          <span>2. Echte Video-Animatie</span>
                        </span>
                      </div>

                      {sc.video_clip_url ? (
                        <div className="aspect-video w-full rounded-xl bg-black border border-rose-500/40 overflow-hidden relative shadow-md">
                          <video src={sc.video_clip_url} autoPlay loop muted controls className="w-full h-full object-cover" />
                        </div>
                      ) : (
                        <div
                          onClick={() => fileInputRefs.current[sc.id]?.click()}
                          className="aspect-video w-full rounded-xl border-2 border-dashed border-slate-700 hover:border-rose-500/60 bg-slate-900/60 flex flex-col items-center justify-center p-3 text-center cursor-pointer transition-colors"
                        >
                          <Upload className="w-6 h-6 text-slate-500 mb-1" />
                          <span className="text-xs font-bold text-slate-300">Sleep .mp4 hierheen of upload</span>
                          <input
                            ref={(el) => (fileInputRefs.current[sc.id] = el)}
                            type="file"
                            accept="video/mp4,video/webm"
                            className="hidden"
                            onChange={(e) => {
                              const f = e.target.files?.[0];
                              if (f) handleUploadSceneVideo(sc.id, f);
                            }}
                          />
                        </div>
                      )}

                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <label className="text-[10px] uppercase font-bold text-slate-400">Motion Prompt</label>
                          <button
                            type="button"
                            onClick={() => handleGenerateMotionPrompt(sc.id)}
                            disabled={generatingMotionPrompts[sc.id]}
                            className="text-[10px] text-indigo-400 hover:text-indigo-300 font-semibold"
                          >
                            {generatingMotionPrompts[sc.id] ? 'AI schrijft…' : 'AI Prompt Maken'}
                          </button>
                        </div>
                        <textarea
                          rows={2}
                          value={sc.motion_prompt || ''}
                          onChange={(e) => autoSaveScene(sc.id, { motion_prompt: e.target.value })}
                          placeholder="Bewegingsopdracht (Adam briskly walks forward smiling)..."
                          className="w-full px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 font-mono"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <button
                        type="button"
                        onClick={() => handleAnimateSceneLocal(sc.id)}
                        disabled={animatingLocalScenes[sc.id] || !sc.image_url}
                        className="w-full flex items-center justify-center gap-1.5 py-2 rounded-xl bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white font-bold text-xs shadow-md shadow-amber-600/20 active:scale-95 transition-all disabled:opacity-50"
                      >
                        <Zap className={`w-3.5 h-3.5 ${animatingLocalScenes[sc.id] ? 'animate-spin' : ''}`} />
                        <span>{animatingLocalScenes[sc.id] ? 'Renderen…' : '⚡ Animeer Lokaal (2.5D Camera 60fps)'}</span>
                      </button>

                      <div className="grid grid-cols-2 gap-2">
                        <button
                          type="button"
                          onClick={() => handleAnimateScene(sc.id, 'hf', sc.motion_prompt)}
                          disabled={animatingScenes[sc.id] || !sc.image_url}
                          className="py-1.5 px-2 rounded-lg bg-yellow-600/20 hover:bg-yellow-600/30 border border-yellow-500/30 text-yellow-300 text-xs font-bold disabled:opacity-50"
                        >
                          ZeroGPU Wan 2.1
                        </button>

                        <button
                          type="button"
                          onClick={() => handleAnimateScene(sc.id, 'veo', sc.motion_prompt)}
                          disabled={animatingScenes[sc.id] || !sc.image_url}
                          className="py-1.5 px-2 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/30 text-rose-300 text-xs font-bold disabled:opacity-50"
                        >
                          Google Veo 2.0
                        </button>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleCopyFlowPrompt(sc)}
                        className="w-full py-1 text-[11px] text-slate-400 hover:text-slate-200 transition-colors"
                      >
                        {copiedPromptId === sc.id ? '✓ Gekopieerd!' : 'Google Flow: Kopieer Prompt + Frame'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="pt-4 border-t border-slate-800 flex justify-between items-center">
            <button
              type="button"
              onClick={() => setCurrentStep(4)}
              className="text-xs text-slate-400 hover:text-slate-200"
            >
              ← Terug naar Stemmen
            </button>

            <button
              type="button"
              onClick={() => setCurrentStep(6)}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs transition-all"
            >
              <span>Ga naar Stap 6: Montage & Publicatie</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          STAP 6: EINDMONTAGE (FFMPEG), SEO & PUBLICATIE
      ───────────────────────────────────────────────────────────── */}
      {currentStep === 6 && (
        <div className="p-8 rounded-3xl bg-slate-900 border border-slate-800 space-y-6 shadow-xl shadow-black/20">
          <div className="border-b border-slate-800 pb-4">
            <h2 className="text-lg font-black text-white flex items-center gap-2">
              <Film className="w-5 h-5 text-emerald-400" />
              <span>Stap 6: Voltooiing, Eindmontage & YouTube Publicatie</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Render alle geanimeerde scènes, stemmen en achtergrondmuziek samen tot één professionele .mp4 video.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-6 rounded-2xl bg-slate-950 border border-slate-800 space-y-4 flex flex-col justify-between">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-1">
                  <Film className="w-4 h-4 text-emerald-400" />
                  <span>1-Klik Complete Aflevering Renderen</span>
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Voegt alle videoclips, stemmen, geluidseffecten en overgangen naadloos samen met audio-ducking en 1080p resolutie.
                </p>
              </div>

              <button
                type="button"
                onClick={() => navigate(`/render/${episodeId}`)}
                className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-xs shadow-lg shadow-emerald-600/20 active:scale-95 transition-all"
              >
                <Film className="w-4 h-4" />
                <span>Open Render & Publicatie Studio</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6 rounded-2xl bg-slate-950 border border-slate-800 space-y-4 flex flex-col justify-between">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-1">
                  <Sparkles className="w-4 h-4 text-purple-400" />
                  <span>Virale YouTube SEO & Thumbnail</span>
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Automatische generatie van SEO titels, uitgebreide beschrijving met hoofdstuk-timestamps en een pakkende thumbnail.
                </p>
              </div>

              <button
                type="button"
                onClick={() => navigate(`/render/${episodeId}`)}
                className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs shadow-lg shadow-purple-600/20 active:scale-95 transition-all"
              >
                <Sparkles className="w-4 h-4" />
                <span>Bekijk SEO & Thumbnail Generator</span>
              </button>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800 flex justify-between items-center">
            <button
              type="button"
              onClick={() => setCurrentStep(5)}
              className="text-xs text-slate-400 hover:text-slate-200"
            >
              ← Terug naar Animatie
            </button>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          MODAL: 5 VIRALE IDEEËN KIEZER
      ───────────────────────────────────────────────────────────── */}
      <Modal
        isOpen={isIdeasModalOpen}
        onClose={() => setIsIdeasModalOpen(false)}
        title="🎲 5 Virale Educatieve YouTube Concepten"
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-400">
            Gegenereerd door je actieve AI-schrijver speciaal voor de doelgroep van deze aflevering. Klik op een idee om het direct te selecteren:
          </p>

          {loadingIdeas ? (
            <div className="py-8 text-center space-y-2 text-xs text-slate-400">
              <Sparkles className="w-6 h-6 text-amber-400 animate-spin mx-auto" />
              <p>AI genereert 5 unieke en virale concepten…</p>
            </div>
          ) : (
            <div className="space-y-2">
              {viralIdeas.map((idea, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleSelectIdea(idea)}
                  className="w-full p-3.5 rounded-xl bg-slate-800/80 hover:bg-indigo-600/20 border border-slate-700/60 hover:border-indigo-500 text-left text-xs font-semibold text-slate-100 transition-all flex items-start gap-2.5 group"
                >
                  <span className="w-5 h-5 rounded-full bg-amber-500/20 text-amber-300 text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                    {idx + 1}
                  </span>
                  <span className="flex-1 group-hover:text-indigo-200">{idea}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </Modal>

      {/* ─────────────────────────────────────────────────────────────
          MODAL: AI SCRIPT GENEREREN
      ───────────────────────────────────────────────────────────── */}
      <Modal
        isOpen={isScriptModalOpen}
        onClose={() => setIsScriptModalOpen(false)}
        title="✨ Schrijf Compleet Script"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Onderwerp</label>
            <input
              type="text"
              value={scriptTopic}
              onChange={(e) => setScriptTopic(e.target.value)}
              placeholder="Bijv. Nora leert Adam tellen tot 10 met appels..."
              className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-slate-100"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsScriptModalOpen(false)}
              className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold"
            >
              Annuleren
            </button>
            <button
              type="button"
              onClick={handleRunGenerateScript}
              disabled={!scriptTopic.trim()}
              className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-md transition-all disabled:opacity-40"
            >
              Start Genereren
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
