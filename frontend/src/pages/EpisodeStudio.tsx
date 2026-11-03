import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Sparkles,
  Clapperboard,
  Plus,
  Film,
  Clock,
  ArrowRight,
  MoveUp,
  MoveDown,
  Image as ImageIcon,
  Mic,
  CheckCircle2,
  AlertTriangle,
  AudioLines,
  History,
  Users,
  Video,
  Upload,
  Copy,
  Check,
  FileDown,
} from 'lucide-react';
import { useStore } from '../store/useStore';
import { SceneCard } from '../components/SceneCard';
import { Modal } from '../components/Modal';
import { EmptyState } from '../components/EmptyState';
import { TaskProgress } from '../components/TaskProgress';
import type { Scene, AnimationType, TransitionType } from '../api/client';

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
    reorderScenes,
    autoSaveScene,
    characters,
    fetchCharacters,
    generateScript,
    generateImage,
    generateAudio,
    generateBulkAudio,
    selectSceneImage,
    animateScene,
    uploadSceneClip,
    generateSceneMotionPrompt,
    exportGoogleFlow,
  } = useStore();

  const [selectedScene, setSelectedScene] = useState<Scene | null>(null);
  const [activeTab, setActiveTab] = useState<'visuals' | 'timeline'>('visuals');

  // Script Modal state
  const [isScriptModalOpen, setIsScriptModalOpen] = useState(false);
  const [scriptTopic, setScriptTopic] = useState('');
  const [selectedCharIds, setSelectedCharIds] = useState<string[]>([]);
  const [activeScriptTaskId, setActiveScriptTaskId] = useState<string | null>(null);
  const [bulkAudioTaskId, setBulkAudioTaskId] = useState<string | null>(null);

  // Active generation & animation tasks per scene
  const [generatingImages, setGeneratingImages] = useState<Record<string, boolean>>({});
  const [generatingAudios, setGeneratingAudios] = useState<Record<string, boolean>>({});
  const [animatingScenes, setAnimatingScenes] = useState<Record<string, boolean>>({});
  const [generatingMotionPrompts, setGeneratingMotionPrompts] = useState<Record<string, boolean>>({});
  const [copiedPromptId, setCopiedPromptId] = useState<string | null>(null);
  const [isExportingFlow, setIsExportingFlow] = useState(false);
  const [bulkVeoProgress, setBulkVeoProgress] = useState<{ current: number; total: number } | null>(null);
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
    }
  }, [currentEpisode, fetchCharacters]);

  useEffect(() => {
    if (scenes.length > 0 && !selectedScene) {
      setSelectedScene(scenes[0]);
    } else if (selectedScene) {
      const updated = scenes.find((s) => s.id === selectedScene.id);
      if (updated) setSelectedScene(updated);
    }
  }, [scenes, selectedScene]);

  // Bereken totale aflevering duur
  const totalDuration = scenes.reduce((acc, sc) => acc + (sc.duration || 8), 0);
  const targetDuration = currentEpisode?.target_duration || 720;
  const targetMinutes = Math.round(targetDuration / 60);
  const totalMinutes = (totalDuration / 60).toFixed(1);

  const handleStartGenerateScript = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!episodeId || !scriptTopic.trim()) return;

    try {
      const taskId = await generateScript(episodeId, scriptTopic.trim(), selectedCharIds);
      setActiveScriptTaskId(taskId);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAddScene = async () => {
    if (!episodeId) return;
    const newSc = await createScene({
      episode_id: episodeId,
      order: scenes.length + 1,
      narration: '',
      visual_prompt: '',
      duration: 10,
    });
    setSelectedScene(newSc);
  };

  const handleMoveScene = async (index: number, direction: 'up' | 'down') => {
    if (!episodeId) return;
    const targetIdx = direction === 'up' ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= scenes.length) return;

    const newScenes = [...scenes];
    const temp = newScenes[index];
    newScenes[index] = newScenes[targetIdx];
    newScenes[targetIdx] = temp;

    const reorderPayload = newScenes.map((sc, idx) => ({
      scene_id: sc.id,
      order: idx + 1,
    }));
    await reorderScenes(episodeId, reorderPayload);
  };

  const handleGenerateSceneImage = async (sceneId: string) => {
    setGeneratingImages((prev) => ({ ...prev, [sceneId]: true }));
    try {
      await generateImage(sceneId);
    } finally {
      setGeneratingImages((prev) => ({ ...prev, [sceneId]: false }));
    }
  };

  const handleGenerateSceneAudio = async (sceneId: string) => {
    setGeneratingAudios((prev) => ({ ...prev, [sceneId]: true }));
    try {
      await generateAudio(sceneId);
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

  const handleAnimateScene = async (sceneId: string, engine = 'veo', motionPrompt?: string) => {
    setAnimatingScenes((prev) => ({ ...prev, [sceneId]: true }));
    try {
      await animateScene(sceneId, engine, motionPrompt);
    } catch (err) {
      console.error('Animatiefout:', err);
    } finally {
      setAnimatingScenes((prev) => ({ ...prev, [sceneId]: false }));
    }
  };

  const handleUploadSceneVideo = async (sceneId: string, file: File) => {
    setAnimatingScenes((prev) => ({ ...prev, [sceneId]: true }));
    try {
      await uploadSceneClip(sceneId, file);
    } catch (err) {
      console.error('Upload fout:', err);
    } finally {
      setAnimatingScenes((prev) => ({ ...prev, [sceneId]: false }));
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

    // Download het start-frame als bestand voor directe upload in Google Flow
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
      console.error('Export flow fout:', err);
    } finally {
      setIsExportingFlow(false);
    }
  };

  const handleBulkAnimateVeo = async () => {
    if (!scenes.length) return;
    const toAnimate = scenes.filter((s) => s.image_url && !s.video_clip_url);
    if (!toAnimate.length) {
      alert('Alle scènes met een Start-Frame zijn al geanimeerd!');
      return;
    }
    setBulkVeoProgress({ current: 0, total: toAnimate.length });
    for (let i = 0; i < toAnimate.length; i++) {
      setBulkVeoProgress({ current: i + 1, total: toAnimate.length });
      try {
        await animateScene(toAnimate[i].id, 'veo');
      } catch (err) {
        console.error('Bulk animatiefout:', err);
      }
    }
    setBulkVeoProgress(null);
  };

  const toggleSceneCharacter = (characterId: string) => {
    if (!selectedScene) return;
    const current = selectedScene.character_ids || [];
    const next = current.includes(characterId)
      ? current.filter((id) => id !== characterId)
      : [...current, characterId];
    setSelectedScene((prev) => (prev ? { ...prev, character_ids: next } : null));
    autoSaveScene(selectedScene.id, { character_ids: next });
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Top Bar / Episode Meta */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 p-6 rounded-2xl bg-slate-900 border border-slate-800">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-indigo-400">
            <Clapperboard className="w-4 h-4" />
            <span>Episode Studio</span>
            <span className="text-slate-600">•</span>
            <span className="text-slate-400">Automatisch Opslaan Actief</span>
          </div>

          <input
            type="text"
            value={currentEpisode?.title || ''}
            onChange={(e) => {
              if (episodeId) {
                autoSaveEpisode(episodeId, { title: e.target.value });
              }
            }}
            placeholder="Titel van de aflevering..."
            className="w-full text-xl md:text-2xl font-black text-slate-100 bg-transparent border-0 border-b border-transparent hover:border-slate-700 focus:border-indigo-500 focus:outline-none py-1 transition-colors"
          />

          <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 pt-1">
            <span className="flex items-center gap-1.5 font-medium">
              <Clock className="w-3.5 h-3.5 text-amber-400" />
              <span>
                Duur: <strong className="text-slate-200">{totalMinutes} min</strong> / doel {targetMinutes} min ({scenes.length} scènes)
              </span>
            </span>

            {/* Doelgroep Selector (Mode A: Kids COPPA vs Mode B: Algemeen) */}
            <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
              <span className="text-[11px] font-semibold text-slate-400">Doelgroep:</span>
              <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
                <button
                  type="button"
                  onClick={() => {
                    if (episodeId) {
                      autoSaveEpisode(episodeId, { target_audience: 'kids', made_for_kids: true });
                    }
                  }}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all ${
                    (currentEpisode?.target_audience ?? 'kids') === 'kids'
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  👶 Kids (COPPA)
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (episodeId) {
                      autoSaveEpisode(episodeId, { target_audience: 'general', made_for_kids: false });
                    }
                  }}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all ${
                    currentEpisode?.target_audience === 'general'
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  🎬 Algemeen
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={handleBulkAudio}
            disabled={scenes.length === 0 || !!bulkAudioTaskId}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-bold text-xs transition-all disabled:opacity-50"
          >
            <AudioLines className="w-4 h-4 text-emerald-400" />
            <span>Alle Stemmen</span>
          </button>

          <button
            onClick={() => setIsScriptModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold text-xs shadow-lg shadow-indigo-600/20 active:scale-95 transition-all"
          >
            <Sparkles className="w-4 h-4" />
            <span>AI Script Genereren</span>
          </button>

          <button
            onClick={() => navigate(`/render/${episodeId}`)}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-lg shadow-emerald-600/20 active:scale-95 transition-all"
          >
            <Film className="w-4 h-4" />
            <span>Renderen & Publiceren</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Guardrail waarschuwingen voor de hele aflevering */}
      {currentEpisode?.guardrail_warnings && currentEpisode.guardrail_warnings.length > 0 && (
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-200">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider mb-2">
            <AlertTriangle className="w-4 h-4" />
            <span>Viral Coach waarschuwingen ({currentEpisode.guardrail_warnings.length})</span>
          </div>
          <ul className="text-xs space-y-1 list-disc list-inside text-amber-200/90">
            {currentEpisode.guardrail_warnings.slice(0, 5).map((warning, idx) => (
              <li key={idx}>{warning}</li>
            ))}
            {currentEpisode.guardrail_warnings.length > 5 && (
              <li className="text-amber-300/70">
                … en nog {currentEpisode.guardrail_warnings.length - 5} waarschuwingen
              </li>
            )}
          </ul>
        </div>
      )}

      {bulkAudioTaskId && (
        <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800">
          <TaskProgress
            taskId={bulkAudioTaskId}
            onComplete={() => setBulkAudioTaskId(null)}
          />
        </div>
      )}

      {/* Tabs & Animatie Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setActiveTab('visuals')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'visuals'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/25 ring-1 ring-indigo-400'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            <Video className="w-4 h-4 text-rose-400" />
            <span>Tab 3: Visuele & Animatie Studio (Image-to-Video)</span>
            <span className="ml-1 px-1.5 py-0.5 rounded-full bg-slate-800 text-[10px] text-slate-300 font-mono">
              {scenes.filter((s) => s.video_clip_url).length}/{scenes.length}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('timeline')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'timeline'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/25 ring-1 ring-indigo-400'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            <Film className="w-4 h-4 text-indigo-400" />
            <span>Tijdlijn & Inspector</span>
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleExportFlow}
            disabled={isExportingFlow || scenes.length === 0}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-semibold transition-colors disabled:opacity-50"
            title="Download alle Start-Frames en Motion Prompts als ZIP voor Google Flow / Gemini Web"
          >
            <FileDown className={`w-3.5 h-3.5 text-amber-400 ${isExportingFlow ? 'animate-bounce' : ''}`} />
            <span>{isExportingFlow ? 'Exporteren…' : 'Exporteer voor Google Flow (.zip)'}</span>
          </button>

          <button
            type="button"
            onClick={handleBulkAnimateVeo}
            disabled={!!bulkVeoProgress || scenes.length === 0}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/30 text-rose-200 text-xs font-semibold transition-colors disabled:opacity-50"
            title="Animeer alle scènes met een Start-Frame achter elkaar via Veo"
          >
            <Sparkles className="w-3.5 h-3.5 text-rose-400" />
            <span>{bulkVeoProgress ? `Veo (${bulkVeoProgress.current}/${bulkVeoProgress.total})…` : 'Bulk Veo Animatie'}</span>
          </button>
        </div>
      </div>

      {/* View Weergave: Tab 3 (Visuele & Animatie Studio) vs Tijdlijn */}
      {activeTab === 'visuals' ? (
        <div className="space-y-6">
          {scenes.length === 0 && !scenesLoading ? (
            <EmptyState
              icon={Film}
              title="Nog geen scènes aangemaakt"
              description="Genereer automatisch een script met de AI Script knop om de studio te vullen."
              actionLabel="AI Script Genereren"
              onAction={() => setIsScriptModalOpen(true)}
            />
          ) : (
            scenes.map((sc) => (
              <div
                key={sc.id}
                className="p-6 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all space-y-4 shadow-lg shadow-black/20"
              >
                {/* Header per scène */}
                <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2.5">
                    <span className="w-8 h-8 rounded-xl bg-indigo-500/20 text-indigo-300 font-black text-sm flex items-center justify-center border border-indigo-500/30">
                      #{sc.order}
                    </span>
                    <div>
                      <h3 className="font-bold text-sm text-slate-100 flex items-center gap-2">
                        <span>{sc.title || `Scène ${sc.order}`}</span>
                        {sc.chapter_type && sc.chapter_type !== 'chapter' && (
                          <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20">
                            {sc.chapter_type}
                          </span>
                        )}
                      </h3>
                      <p className="text-[11px] text-slate-400">
                        Duur: <strong className="text-slate-200">{sc.duration_seconds || 8}s</strong> • Spreker:{' '}
                        <strong className="text-indigo-300">{sc.speaker || 'Verteller'}</strong>
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {sc.video_clip_url ? (
                      <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-bold">
                        <Video className="w-3.5 h-3.5" /> Echte Animatie Actief
                      </span>
                    ) : sc.image_url ? (
                      <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-300 text-xs font-bold">
                        <ImageIcon className="w-3.5 h-3.5" /> Start-Frame Klaar (Wacht op Animatie)
                      </span>
                    ) : (
                      <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-400 text-xs font-medium">
                        Draft
                      </span>
                    )}
                  </div>
                </div>

                {/* 3 Stappen Naast Elkaar */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                  {/* Kolom 1: Tekst & Audio (lg:col-span-4) */}
                  <div className="lg:col-span-4 p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-3.5 flex flex-col justify-between">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                          <Mic className="w-3.5 h-3.5 text-emerald-400" />
                          <span>1. Tekst & Audio</span>
                        </span>
                        {sc.audio_url && (
                          <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded-full flex items-center gap-1">
                            <Check className="w-2.5 h-2.5" /> Audio Klaar
                          </span>
                        )}
                      </div>

                      {/* Spreker selectie */}
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-400 mb-1">Spreker</label>
                        <select
                          value={sc.speaker || ''}
                          onChange={(e) => {
                            const val = e.target.value;
                            autoSaveScene(sc.id, { speaker: val, active_speaker: val || 'verteller' });
                          }}
                          className="w-full px-2.5 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-100 text-xs"
                        >
                          <option value="">Verteller (Voice-Over)</option>
                          {characters.map((c) => (
                            <option key={c.id} value={c.name}>{c.name}</option>
                          ))}
                        </select>
                      </div>

                      {/* Gesproken tekst */}
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-400 mb-1">Gesproken Kindertekst</label>
                        <textarea
                          rows={4}
                          value={sc.narration || ''}
                          onChange={(e) => autoSaveScene(sc.id, { narration: e.target.value })}
                          placeholder="Voer de enthousiaste gesproken tekst in..."
                          className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-xs placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 leading-relaxed"
                        />
                      </div>
                    </div>

                    {/* Audio Controls */}
                    <div className="space-y-2 pt-2 border-t border-slate-800/80">
                      {sc.audio_url && (
                        <audio controls className="w-full h-8 text-xs" src={sc.audio_url} />
                      )}
                      <button
                        type="button"
                        onClick={() => handleGenerateSceneAudio(sc.id)}
                        disabled={generatingAudios[sc.id] || !sc.narration}
                        className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/30 text-emerald-300 font-bold text-xs transition-colors disabled:opacity-50"
                      >
                        <Mic className="w-3.5 h-3.5" />
                        <span>{generatingAudios[sc.id] ? 'Audio genereren…' : sc.audio_url ? 'Opnieuw Audio Genereren' : 'Genereer Stem'}</span>
                      </button>
                    </div>
                  </div>

                  {/* Kolom 2: Stap 1 — Start-Frame Plaatje (lg:col-span-4) */}
                  <div className="lg:col-span-4 p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-3.5 flex flex-col justify-between">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                          <ImageIcon className="w-3.5 h-3.5 text-amber-400" />
                          <span>2. Stap 1: Start-Frame</span>
                        </span>
                        {sc.image_url && (
                          <span className="text-[10px] font-bold text-amber-400 bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 rounded-full flex items-center gap-1">
                            <Check className="w-2.5 h-2.5" /> Lock Klaar
                          </span>
                        )}
                      </div>

                      {/* Preview Image */}
                      <div className="aspect-video w-full rounded-xl bg-black border border-slate-800 overflow-hidden relative flex items-center justify-center group">
                        {sc.image_url ? (
                          <img
                            src={sc.image_url}
                            alt="Start-Frame Lock"
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                          />
                        ) : (
                          <div className="flex flex-col items-center gap-1.5 text-slate-500 text-xs">
                            <ImageIcon className="w-8 h-8 opacity-40" />
                            <span>Geen Start-Frame gegenereerd</span>
                          </div>
                        )}
                      </div>

                      {/* Karakter DNA Selectie */}
                      {characters.length > 0 && (
                        <div>
                          <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">
                            Karakters in beeld (Visueel DNA Lock):
                          </label>
                          <div className="flex flex-wrap gap-1">
                            {characters.map((c) => {
                              const active = (sc.character_ids || []).includes(c.id);
                              return (
                                <button
                                  key={c.id}
                                  type="button"
                                  onClick={() => {
                                    const current = sc.character_ids || [];
                                    const next = current.includes(c.id)
                                      ? current.filter((id) => id !== c.id)
                                      : [...current, c.id];
                                    autoSaveScene(sc.id, { character_ids: next });
                                  }}
                                  className={`px-2 py-0.5 rounded text-[11px] font-semibold border transition-all ${
                                    active
                                      ? 'bg-indigo-600/30 border-indigo-500 text-indigo-200'
                                      : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
                                  }`}
                                >
                                  {active ? '✓ ' : '+ '} {c.name}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Visual Prompt Input */}
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-400 mb-1">Start-Frame Prompt (Engels)</label>
                        <textarea
                          rows={2}
                          value={sc.visual_prompt || ''}
                          onChange={(e) => autoSaveScene(sc.id, { visual_prompt: e.target.value })}
                          placeholder="3D Pixar style vibrant composition, character placed on center..."
                          className="w-full px-3 py-1.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-xs font-mono placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                        />
                      </div>
                    </div>

                    {/* Generate Image Button */}
                    <div className="pt-2 border-t border-slate-800/80">
                      <button
                        type="button"
                        onClick={() => handleGenerateSceneImage(sc.id)}
                        disabled={generatingImages[sc.id]}
                        className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 font-bold text-xs transition-colors disabled:opacity-50"
                      >
                        <Sparkles className={`w-3.5 h-3.5 ${generatingImages[sc.id] ? 'animate-spin' : ''}`} />
                        <span>{generatingImages[sc.id] ? 'Genereren…' : sc.image_url ? 'Opnieuw Start-Frame Maken' : 'Genereer Start-Frame'}</span>
                      </button>
                    </div>
                  </div>

                  {/* Kolom 3: Stap 2 — Echte Animatie (Image-to-Video) (lg:col-span-4) */}
                  <div className="lg:col-span-4 p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-3.5 flex flex-col justify-between">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                          <Video className="w-3.5 h-3.5 text-rose-400" />
                          <span>3. Stap 2: Echte Animatie</span>
                        </span>
                        {sc.video_clip_url && (
                          <span className="text-[10px] font-bold text-rose-400 bg-rose-500/10 border border-rose-500/20 px-1.5 py-0.5 rounded-full flex items-center gap-1">
                            <Check className="w-2.5 h-2.5" /> MP4 Geanimeerd
                          </span>
                        )}
                      </div>

                      {/* Video Clip Player preview */}
                      {sc.video_clip_url ? (
                        <div className="space-y-1.5">
                          <div className="aspect-video w-full rounded-xl bg-black border border-rose-500/40 overflow-hidden relative shadow-md">
                            <video
                              src={sc.video_clip_url}
                              autoPlay
                              loop
                              muted
                              controls
                              className="w-full h-full object-cover"
                            />
                          </div>
                          <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                            <span>Engine: {sc.animation_engine || 'Veo'}</span>
                            <span className="text-emerald-400">Audio Synced ✓</span>
                          </div>
                        </div>
                      ) : (
                        <div
                          onDragOver={(e) => e.preventDefault()}
                          onDrop={(e) => {
                            e.preventDefault();
                            const file = e.dataTransfer.files?.[0];
                            if (file) handleUploadSceneVideo(sc.id, file);
                          }}
                          onClick={() => fileInputRefs.current[sc.id]?.click()}
                          className="aspect-video w-full rounded-xl border-2 border-dashed border-slate-700 hover:border-rose-500/60 bg-slate-900/60 flex flex-col items-center justify-center p-3 text-center cursor-pointer transition-colors group"
                        >
                          <Upload className="w-6 h-6 text-slate-500 group-hover:text-rose-400 transition-colors mb-1" />
                          <span className="text-xs font-bold text-slate-300 group-hover:text-rose-300">
                            Sleep gegenereerde .mp4 hierheen
                          </span>
                          <span className="text-[10px] text-slate-500 mt-0.5">
                            of klik om te uploaden
                          </span>
                          <input
                            ref={(el) => (fileInputRefs.current[sc.id] = el)}
                            type="file"
                            accept="video/mp4,video/quicktime,video/webm"
                            className="hidden"
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file) handleUploadSceneVideo(sc.id, file);
                            }}
                          />
                        </div>
                      )}

                      {/* Motion Prompt Textarea */}
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <label className="text-[11px] font-semibold text-slate-400">
                            Motion Prompt (Bewegingsopdracht)
                          </label>
                          <button
                            type="button"
                            onClick={() => handleGenerateMotionPrompt(sc.id)}
                            disabled={generatingMotionPrompts[sc.id]}
                            className="text-[10px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-semibold"
                          >
                            <Sparkles className="w-2.5 h-2.5" />
                            <span>{generatingMotionPrompts[sc.id] ? 'AI schrijft…' : 'AI Prompt Maken'}</span>
                          </button>
                        </div>
                        <textarea
                          rows={2}
                          value={sc.motion_prompt || ''}
                          onChange={(e) => autoSaveScene(sc.id, { motion_prompt: e.target.value })}
                          placeholder="Adam briskly walks forward smiling, Nora waves enthusiastically..."
                          className="w-full px-3 py-1.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-xs font-mono placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-rose-500"
                        />
                      </div>
                    </div>

                    {/* Image-to-Video Actieknoppen */}
                    <div className="space-y-1.5 pt-2 border-t border-slate-800/80">
                      <div className="grid grid-cols-2 gap-2">
                        <button
                          type="button"
                          onClick={() => handleAnimateScene(sc.id, 'veo', sc.motion_prompt)}
                          disabled={animatingScenes[sc.id] || !sc.image_url}
                          className="flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs shadow-md shadow-rose-600/20 active:scale-95 transition-all disabled:opacity-50"
                          title="Genereer echte videoclip via Google Veo 2.0 API"
                        >
                          <Video className={`w-3.5 h-3.5 ${animatingScenes[sc.id] ? 'animate-spin' : ''}`} />
                          <span>{animatingScenes[sc.id] ? 'Veo Animeert…' : 'Google Veo'}</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => handleAnimateScene(sc.id, 'wan', sc.motion_prompt)}
                          disabled={animatingScenes[sc.id] || !sc.image_url}
                          className="flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-lg bg-purple-600/30 hover:bg-purple-600/40 border border-purple-500/40 text-purple-200 font-bold text-xs transition-colors disabled:opacity-50"
                          title="Genereer videoclip via Wan 2.1 API"
                        >
                          <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                          <span>Wan 2.1 API</span>
                        </button>
                      </div>

                      {/* Google Flow Handmatig Knop */}
                      <button
                        type="button"
                        onClick={() => handleCopyFlowPrompt(sc)}
                        className="w-full flex items-center justify-center gap-1.5 py-1.5 px-2.5 rounded-lg bg-slate-800 hover:bg-slate-750 border border-slate-700 text-slate-300 text-[11px] font-semibold transition-colors"
                        title="Kopieer de prompt en download het start-frame om gratis in Google Flow Web / Gemini te plakken"
                      >
                        {copiedPromptId === sc.id ? (
                          <>
                            <Check className="w-3 h-3 text-emerald-400" />
                            <span className="text-emerald-300">Gekopieerd & Start-Frame Gedownload!</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3 h-3 text-indigo-400" />
                            <span>Google Flow: Kopieer Prompt + Download Frame</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      ) : (
        /* Main Grid: Scene List (Left) + Scene Inspector & Preview (Right) */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Timeline / Scene Cards */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-200 flex items-center gap-2">
              <Film className="w-4 h-4 text-indigo-400" />
              <span>Scène Tijdlijn ({scenes.length})</span>
            </h2>

            <button
              onClick={handleAddScene}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors"
            >
              <Plus className="w-3.5 h-3.5 text-indigo-400" />
              <span>Scène Toevoegen</span>
            </button>
          </div>

          {scenes.length === 0 && !scenesLoading ? (
            <EmptyState
              icon={Film}
              title="Nog geen scènes aangemaakt"
              description="Genereer automatisch een script met de AI Script knop of voeg handmatig scènes toe."
              actionLabel="AI Script Genereren"
              onAction={() => setIsScriptModalOpen(true)}
            />
          ) : (
            <div className="space-y-3">
              {scenes.map((sc, idx) => (
                <div key={sc.id} className="relative flex items-center gap-2">
                  {/* Reorder Buttons */}
                  <div className="flex flex-col gap-1 shrink-0">
                    <button
                      onClick={() => handleMoveScene(idx, 'up')}
                      disabled={idx === 0}
                      className="p-1 rounded bg-slate-800 hover:bg-slate-750 text-slate-400 disabled:opacity-20"
                      title="Omhoog verplaatsen"
                    >
                      <MoveUp className="w-3 h-3" />
                    </button>
                    <button
                      onClick={() => handleMoveScene(idx, 'down')}
                      disabled={idx === scenes.length - 1}
                      className="p-1 rounded bg-slate-800 hover:bg-slate-750 text-slate-400 disabled:opacity-20"
                      title="Omlaag verplaatsen"
                    >
                      <MoveDown className="w-3 h-3" />
                    </button>
                  </div>

                  <div className="flex-1 min-w-0">
                    <SceneCard
                      scene={sc}
                      isSelected={selectedScene?.id === sc.id}
                      onSelect={() => setSelectedScene(sc)}
                      onGenerateImage={() => handleGenerateSceneImage(sc.id)}
                      onGenerateAudio={() => handleGenerateSceneAudio(sc.id)}
                      onDelete={() => deleteScene(sc.id)}
                      isGeneratingImage={generatingImages[sc.id]}
                      isGeneratingAudio={generatingAudios[sc.id]}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Selected Scene Editor */}
        <div className="lg:col-span-5">
          {selectedScene ? (
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-5 sticky top-8">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                  <span>Scène #{selectedScene.order} Bewerken</span>
                </h3>
                <span className="text-xs text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Auto-save
                </span>
              </div>

              {/* Visual Preview */}
              <div className="w-full h-48 rounded-xl bg-slate-950 border border-slate-800 overflow-hidden relative flex items-center justify-center">
                {selectedScene.image_url ? (
                  <img
                    src={selectedScene.image_url}
                    alt="Scène preview"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="flex flex-col items-center gap-2 text-slate-500">
                    <ImageIcon className="w-10 h-10 opacity-30" />
                    <span className="text-xs font-medium">Nog geen achtergrond gegenereerd</span>
                  </div>
                )}
              </div>

              {/* Structuur & spreker */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Hoofdstuktype</label>
                  <select
                    value={selectedScene.chapter_type || 'chapter'}
                    onChange={(e) => {
                      const val = e.target.value;
                      setSelectedScene((prev) => (prev ? { ...prev, chapter_type: val } : null));
                      autoSaveScene(selectedScene.id, { chapter_type: val });
                    }}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-200"
                  >
                    <option value="hook">Hook / Cold Open</option>
                    <option value="intro">Intro Bumper</option>
                    <option value="chapter">Hoofdstuk</option>
                    <option value="question">Kijkersvraag</option>
                    <option value="song">Liedje</option>
                    <option value="outro">Outro</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Spreker</label>
                  <select
                    value={selectedScene.speaker || ''}
                    onChange={(e) => {
                      const val = e.target.value;
                      setSelectedScene((prev) => (prev ? { ...prev, speaker: val } : null));
                      autoSaveScene(selectedScene.id, { speaker: val });
                    }}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-200"
                  >
                    <option value="">Verteller / geen karakter</option>
                    {characters.map((c) => (
                      <option key={c.id} value={c.name}>{c.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Uitspraak & pauze */}
              <div className="grid grid-cols-3 gap-3 text-xs">
                <div className="col-span-2">
                  <label className="block font-semibold text-slate-300 mb-1">
                    Fonetische uitspraak (optioneel)
                  </label>
                  <input
                    type="text"
                    value={selectedScene.phonetic_text || ''}
                    onChange={(e) => {
                      const val = e.target.value;
                      setSelectedScene((prev) => (prev ? { ...prev, phonetic_text: val } : null));
                      autoSaveScene(selectedScene.id, { phonetic_text: val });
                    }}
                    placeholder="bv. kuh-lurr"
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-200"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Pauze (sec)</label>
                  <input
                    type="number"
                    min={0}
                    max={5}
                    step={0.1}
                    value={selectedScene.pause_after_sec ?? 0.4}
                    onChange={(e) => {
                      const val = Number(e.target.value);
                      setSelectedScene((prev) => (prev ? { ...prev, pause_after_sec: val } : null));
                      autoSaveScene(selectedScene.id, { pause_after_sec: val });
                    }}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-200 font-mono"
                  />
                </div>
              </div>

              {/* Multi-Karakters & Slimme Lip-Sync Spreker */}
              <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-slate-200">
                    <Users className="w-4 h-4 text-indigo-400" />
                    <span>Karakters in deze scène</span>
                  </div>
                  <label className="flex items-center gap-1.5 text-[11px] text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedScene.use_2d_sprite}
                      onChange={(e) => {
                        const val = e.target.checked;
                        setSelectedScene((prev) => (prev ? { ...prev, use_2d_sprite: val } : null));
                        autoSaveScene(selectedScene.id, { use_2d_sprite: val });
                      }}
                      className="rounded accent-indigo-500"
                    />
                    <span>2.5D Sprite Overlay</span>
                  </label>
                </div>

                {/* Wie praat er? (Smart Lip-Sync Toewijzing) */}
                <div className="space-y-1">
                  <label className="block text-[11px] font-semibold text-slate-300">
                    Wie praat er in deze scène? (Lip-sync toewijzing)
                  </label>
                  <select
                    value={selectedScene.active_speaker || selectedScene.speaker || 'verteller'}
                    onChange={(e) => {
                      const val = e.target.value;
                      setSelectedScene((prev) => (prev ? { ...prev, active_speaker: val, speaker: val } : null));
                      autoSaveScene(selectedScene.id, { active_speaker: val, speaker: val });
                    }}
                    className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-100 text-xs font-semibold"
                  >
                    <option value="verteller">🎙️ Verteller (Voice-Over - karakters bewegen mond niet)</option>
                    {(selectedScene.character_ids || []).map((cid) => {
                      const ch = characters.find((c) => c.id === cid);
                      return ch ? (
                        <option key={ch.id} value={ch.name}>
                          🗣️ {ch.name} (Alleen {ch.name} praat en beweegt mond)
                        </option>
                      ) : null;
                    })}
                    <option value="samen">👥 Samen (Beide karakters praten / zingen)</option>
                  </select>
                </div>

                {/* Karakters toevoegen aan de scène */}
                {characters.length > 0 ? (
                  <div className="space-y-1.5 pt-1">
                    <label className="block text-[10px] uppercase font-bold text-slate-400">
                      Geselecteerde karakters in beeld:
                    </label>
                    <div className="flex flex-wrap gap-1.5">
                      {characters.map((c) => {
                        const active = (selectedScene.character_ids || []).includes(c.id);
                        return (
                          <button
                            key={c.id}
                            type="button"
                            onClick={() => toggleSceneCharacter(c.id)}
                            className={`px-2.5 py-1 rounded-lg text-xs font-semibold border transition-all ${
                              active
                                ? 'bg-indigo-600/30 border-indigo-500 text-indigo-200'
                                : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
                            }`}
                          >
                            {active ? '✓ ' : '+ '} {c.name}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  <p className="text-[11px] text-slate-500">
                    Voeg karakters toe in de Karakter Kluis om sprites te gebruiken.
                  </p>
                )}
              </div>

              {selectedScene.guardrail_warnings?.length > 0 && (
                <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/25 text-[11px] text-amber-200 space-y-1">
                  <div className="flex items-center gap-1.5 font-bold">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>Scène waarschuwingen</span>
                  </div>
                  <ul className="list-disc list-inside space-y-0.5 text-amber-200/90">
                    {selectedScene.guardrail_warnings.map((warning, idx) => (
                      <li key={idx}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Narration Editor */}
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
                  Gesproken Stemtekst (Nederlands voor kinderen)
                </label>
                <textarea
                  rows={3}
                  value={selectedScene.narration || ''}
                  onChange={(e) => {
                    const val = e.target.value;
                    setSelectedScene((prev) => (prev ? { ...prev, narration: val } : null));
                    autoSaveScene(selectedScene.id, { narration: val });
                  }}
                  placeholder="Hallo kindjes! Vandaag gaan we leren over..."
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                />
              </div>

              {/* Visual Prompt Editor */}
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
                  AI Beeldprompt (Engels voor Stable Diffusion / Imagen)
                </label>
                <textarea
                  rows={2}
                  value={selectedScene.visual_prompt || ''}
                  onChange={(e) => {
                    const val = e.target.value;
                    setSelectedScene((prev) => (prev ? { ...prev, visual_prompt: val } : null));
                    autoSaveScene(selectedScene.id, { visual_prompt: val });
                  }}
                  placeholder="3D Pixar style vibrant sunny meadow with rainbow and flowers..."
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-xs font-mono"
                />
              </div>

              {/* Afbeeldingsgeschiedenis */}
              {selectedScene.image_history?.length > 0 && (
                <div className="space-y-2">
                  <label className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-300">
                    <History className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Eerdere afbeeldingen ({selectedScene.image_history.length})</span>
                  </label>
                  <div className="grid grid-cols-4 gap-2">
                    {selectedScene.image_history.slice(0, 8).map((item, idx) => (
                      <button
                        key={`${item.path}-${idx}`}
                        type="button"
                        onClick={() => selectSceneImage(selectedScene.id, item.path)}
                        title={item.prompt || 'Kies deze afbeelding'}
                        className="aspect-video rounded-lg overflow-hidden border border-slate-700 hover:border-indigo-500 hover:ring-2 hover:ring-indigo-500/30 transition-all bg-slate-950"
                      >
                        {item.url ? (
                          <img
                            src={item.url}
                            alt={item.prompt || 'Vorige afbeelding'}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-slate-600">
                            <ImageIcon className="w-4 h-4" />
                          </div>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Animation & Transitions Settings */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Camerabeweging</label>
                  <select
                    value={selectedScene.animation_type || 'ken_burns'}
                    onChange={(e) => {
                      const val = e.target.value as AnimationType;
                      setSelectedScene((prev) => (prev ? { ...prev, animation_type: val } : null));
                      autoSaveScene(selectedScene.id, { animation_type: val });
                    }}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-200"
                  >
                    <option value="ken_burns">Ken Burns (Vloeiend Zoom)</option>
                    <option value="zoom_in">Langzaam Inzoomen</option>
                    <option value="zoom_out">Langzaam Uitzoomen</option>
                    <option value="pan_left">Pan naar Links</option>
                    <option value="pan_right">Pan naar Rechts</option>
                    <option value="none">Stilstaand</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Overgang (Transition)</label>
                  <select
                    value={selectedScene.transition_type || 'fade'}
                    onChange={(e) => {
                      const val = e.target.value as TransitionType;
                      setSelectedScene((prev) => (prev ? { ...prev, transition_type: val } : null));
                      autoSaveScene(selectedScene.id, { transition_type: val });
                    }}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-200"
                  >
                    <option value="crossfade">Crossfade (Vloeiend)</option>
                    <option value="dissolve">Dissolve</option>
                    <option value="wipe">Wipe</option>
                    <option value="circle_wipe">Circle Wipe</option>
                    <option value="slide_left">Slide Links</option>
                    <option value="slide_right">Slide Rechts</option>
                    <option value="fade_black">Dip naar Zwart</option>
                    <option value="fade_white">Dip naar Wit</option>
                    <option value="cut">Directe Cut</option>
                  </select>
                </div>
              </div>

              {/* Duration Slider */}
              <div className="space-y-1 text-xs">
                <div className="flex justify-between font-semibold text-slate-300">
                  <span>Scèneduur</span>
                  <span className="text-amber-400 font-mono">{selectedScene.duration || 8} seconden</span>
                </div>
                <input
                  type="range"
                  min="3"
                  max="30"
                  step="1"
                  value={selectedScene.duration || 8}
                  onChange={(e) => {
                    const val = Number(e.target.value);
                    setSelectedScene((prev) => (prev ? { ...prev, duration: val } : null));
                    autoSaveScene(selectedScene.id, { duration: val });
                  }}
                  className="w-full accent-indigo-500 cursor-pointer"
                />
              </div>

              {/* Action Buttons */}
              <div className="pt-2 flex gap-3">
                <button
                  onClick={() => handleGenerateSceneImage(selectedScene.id)}
                  disabled={generatingImages[selectedScene.id]}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-indigo-600/30 hover:bg-indigo-600/40 border border-indigo-500/40 text-indigo-200 font-bold text-xs transition-colors"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>{generatingImages[selectedScene.id] ? 'Bezig...' : 'Genereer Beeld'}</span>
                </button>

                <button
                  onClick={() => handleGenerateSceneAudio(selectedScene.id)}
                  disabled={generatingAudios[selectedScene.id] || !selectedScene.narration}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-emerald-600/30 hover:bg-emerald-600/40 border border-emerald-500/40 text-emerald-200 font-bold text-xs transition-colors disabled:opacity-50"
                >
                  <Mic className="w-4 h-4" />
                  <span>{generatingAudios[selectedScene.id] ? 'Bezig...' : 'Genereer Stem'}</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="p-8 rounded-2xl border border-dashed border-slate-800 text-center text-slate-500 text-sm">
              Selecteer een scène links om te bewerken.
            </div>
          )}
        </div>
      </div>
      )}

      {/* Modal: AI Script Generator */}
      <Modal
        isOpen={isScriptModalOpen}
        onClose={() => {
          setIsScriptModalOpen(false);
          setActiveScriptTaskId(null);
        }}
        title="AI Script Generator (KidsEdu Viral)"
      >
        <div className="space-y-5">
          {!activeScriptTaskId ? (
            <form onSubmit={handleStartGenerateScript} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                  Onderwerp / Educatief Thema
                </label>
                <input
                  type="text"
                  required
                  value={scriptTopic}
                  onChange={(e) => setScriptTopic(e.target.value)}
                  placeholder="bv. Kleuren leren herkennen op de boerderij met dieren"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                />
              </div>

              {/* Characters selection */}
              {characters.length > 0 && (
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                    Selecteer Deelnemende Karakters
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {characters.map((c) => {
                      const isChecked = selectedCharIds.includes(c.id);
                      return (
                        <label
                          key={c.id}
                          className={`flex items-center gap-2 p-2.5 rounded-xl border text-xs cursor-pointer transition-colors ${
                            isChecked
                              ? 'bg-indigo-600/20 border-indigo-500/60 text-slate-100'
                              : 'bg-slate-800/60 border-slate-700 text-slate-400'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedCharIds((prev) => [...prev, c.id]);
                              } else {
                                setSelectedCharIds((prev) => prev.filter((x) => x !== c.id));
                              }
                            }}
                            className="hidden"
                          />
                          <span className="font-semibold">{c.name}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="p-3.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-xs text-indigo-300 leading-relaxed">
                ✨ Gemini bouwt automatisch ~10-15 minuten aan pedagogisch verantwoorde scènes op maat van peuters/kleuters, inclusief YouTube SEO en afbeeldingsprompts.
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsScriptModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs"
                >
                  Annuleren
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-600/20"
                >
                  Genereer Volledig Script
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-4">
              <TaskProgress
                taskId={activeScriptTaskId}
                onComplete={() => {
                  if (episodeId) {
                    fetchScenes(episodeId);
                    fetchEpisode(episodeId);
                  }
                  setTimeout(() => {
                    setIsScriptModalOpen(false);
                    setActiveScriptTaskId(null);
                  }, 1200);
                }}
              />
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
};
