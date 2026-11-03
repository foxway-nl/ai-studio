import React, { useEffect, useState, useRef } from 'react';
import {
  Users,
  Plus,
  Sparkles,
  Upload,
  Trash2,
  Smile,
  Layers,
  Volume2,
  Play,
  RefreshCw,
  CheckCircle2,
} from 'lucide-react';
import { useStore } from '../store/useStore';
import { Modal } from '../components/Modal';
import { EmptyState } from '../components/EmptyState';
import type { Character } from '../api/client';

const EMOTIONS = [
  { id: 'blij', label: 'Blij & Enthousiast' },
  { id: 'verbaasd', label: 'Verbaasd & Oogjes wijd' },
  { id: 'denkend', label: 'Denkend & Vragend' },
  { id: 'wijzend', label: 'Wijzend naar iets' },
  { id: 'verdrietig', label: 'Verdrietig / Troost nodig' },
];

export const CharacterVault: React.FC = () => {
  const {
    projects,
    currentProject,
    setCurrentProject,
    characters,
    charactersLoading,
    fetchCharacters,
    createCharacter,
    updateCharacter,
    deleteCharacter,
    generateSprite,
    uploadExpression,
    uploadCharacterReference,
    deleteCharacterReference,
    testVoice,
  } = useStore();

  const [selectedCharacter, setSelectedCharacter] = useState<Character | null>(null);
  const [isNewCharModalOpen, setIsNewCharModalOpen] = useState(false);

  // New Char form state
  const [newCharName, setNewCharName] = useState('');
  const [newCharDesc, setNewCharDesc] = useState('');
  const [newCharPersonality, setNewCharPersonality] = useState('Nieuwsgierig en altijd vrolijk');
  const [newCharVoice, setNewCharVoice] = useState('nl-NL-FennaNeural');
  const [newCharVoiceProvider, setNewCharVoiceProvider] = useState('edge_tts');
  const [newCharVoicePitch, setNewCharVoicePitch] = useState('+15Hz');
  const [newCharVoiceRate, setNewCharVoiceRate] = useState('+0%');
  const [newCharStyle, setNewCharStyle] = useState('3D Pixar style cute friendly character');
  const [newCharVisualDna, setNewCharVisualDna] = useState('5-year-old child, big expressive eyes, curly brown hair, signature blue overalls with bright yellow shirt');

  // Sprite & Expression generation state
  const [selectedEmotion, setSelectedEmotion] = useState('blij');
  const [expressionName, setExpressionName] = useState('blij');
  const [expressionFile, setExpressionFile] = useState<File | null>(null);
  const [isGeneratingSprite, setIsGeneratingSprite] = useState(false);

  // Voice Tester state
  const [isTestingVoice, setIsTestingVoice] = useState(false);
  const [voiceAudioUrl, setVoiceAudioUrl] = useState<string | null>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (currentProject) {
      fetchCharacters(currentProject.id);
    } else if (projects.length > 0) {
      setCurrentProject(projects[0]);
    }
  }, [currentProject, projects, fetchCharacters, setCurrentProject]);

  useEffect(() => {
    if (characters.length > 0 && !selectedCharacter) {
      setSelectedCharacter(characters[0]);
    } else if (selectedCharacter) {
      const updated = characters.find((c) => c.id === selectedCharacter.id);
      if (updated) setSelectedCharacter(updated);
    }
  }, [characters, selectedCharacter]);

  const handleCreateCharacter = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentProject || !newCharName.trim()) return;

    const char = await createCharacter({
      project_id: currentProject.id,
      name: newCharName.trim(),
      description: newCharDesc.trim(),
      personality: newCharPersonality.trim(),
      voice_id: newCharVoice,
      voice_provider: newCharVoiceProvider,
      voice_pitch: newCharVoicePitch,
      voice_rate: newCharVoiceRate,
      style_prompt: newCharStyle.trim(),
      visual_dna_prompt: newCharVisualDna.trim(),
    });

    setNewCharName('');
    setNewCharDesc('');
    setIsNewCharModalOpen(false);
    setSelectedCharacter(char);
  };

  const handleGenerateSprite = async (charId: string) => {
    setIsGeneratingSprite(true);
    try {
      await generateSprite(charId, selectedEmotion);
    } finally {
      setIsGeneratingSprite(false);
    }
  };

  const handleTestCharacterVoice = async (voiceId: string, provider = 'edge_tts', pitch = '+15Hz', rate = '+0%') => {
    setIsTestingVoice(true);
    try {
      const res = await testVoice({
        voice_id: voiceId,
        voice_provider: provider,
        pitch: pitch,
        rate: rate,
        text: 'Hoi allemaal! Vandaag gaan we samen op avontuur, doen jullie mee?',
      });
      setVoiceAudioUrl(res.audio_url);
      setTimeout(() => {
        if (audioPlayerRef.current) {
          audioPlayerRef.current.play().catch(() => {});
        }
      }, 100);
    } finally {
      setIsTestingVoice(false);
    }
  };

  const handleUploadExpression = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCharacter || !expressionFile) return;

    await uploadExpression(selectedCharacter.id, expressionName, expressionFile);
    setExpressionFile(null);
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-300">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <Users className="w-8 h-8 text-indigo-400" />
            <span>Karakter Kluis (Character Vault)</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Beheer 2.5D personages, emotiesprites en kinderstemmen met automatische lip-sync ondersteuning.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <select
              value={currentProject?.id || ''}
              onChange={(e) => {
                const found = projects.find((p) => p.id === e.target.value);
                if (found) setCurrentProject(found);
              }}
              className="px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-500 pr-8"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  Serie: {p.name}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => setIsNewCharModalOpen(true)}
            disabled={!currentProject}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-all shadow-lg shadow-indigo-600/20 active:scale-95 disabled:opacity-50"
          >
            <Plus className="w-4 h-4" />
            <span>Nieuw Karakter</span>
          </button>
        </div>
      </div>

      {/* Main Layout: Characters Grid + Character Detail Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Character Cards List */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-200 flex items-center gap-2">
              <Layers className="w-4 h-4 text-indigo-400" />
              <span>Personages ({characters.length})</span>
            </h2>
          </div>

          {characters.length === 0 && !charactersLoading ? (
            <EmptyState
              icon={Users}
              title="Geen karakters in dit project"
              description="Voeg je eerste vrolijke animatievriendje toe om te gebruiken in scènes en lip-sync video's."
              actionLabel="Maak Karakter Aan"
              onAction={() => setIsNewCharModalOpen(true)}
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {characters.map((char) => {
                const isSelected = selectedCharacter?.id === char.id;
                return (
                  <div
                    key={char.id}
                    onClick={() => setSelectedCharacter(char)}
                    className={`p-5 rounded-2xl border transition-all duration-200 cursor-pointer flex flex-col justify-between ${
                      isSelected
                        ? 'bg-slate-800/90 border-indigo-500 shadow-xl shadow-indigo-500/10 ring-2 ring-indigo-500/40'
                        : 'bg-slate-900/80 border-slate-800 hover:border-slate-700 hover:bg-slate-850'
                    }`}
                  >
                    <div className="flex items-start gap-4">
                      {/* Avatar preview */}
                      <div className="w-16 h-16 rounded-xl bg-slate-950 border border-slate-800 overflow-hidden shrink-0 flex items-center justify-center p-1">
                        {char.sprite_url ? (
                          <img
                            src={char.sprite_url}
                            alt={char.name}
                            className="w-full h-full object-contain"
                          />
                        ) : (
                          <Smile className="w-8 h-8 text-slate-600" />
                        )}
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between">
                          <h3 className="font-bold text-base text-slate-100 truncate">{char.name}</h3>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              if (confirm(`Karakter "${char.name}" verwijderen?`)) {
                                deleteCharacter(char.id);
                              }
                            }}
                            className="p-1 text-slate-500 hover:text-rose-400 transition-colors"
                            title="Verwijder karakter"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                        <p className="text-xs text-slate-400 line-clamp-2 mt-1">
                          {char.personality || char.description || 'Geen omschrijving.'}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-3 mt-3 border-t border-slate-800/60 text-xs text-slate-400">
                      <span className="flex items-center gap-1">
                        <Smile className="w-3.5 h-3.5 text-amber-400" />
                        {char.expressions?.length || 0} expressies
                      </span>
                      <span className="text-[11px] font-mono text-indigo-400 truncate max-w-[120px]">
                        {char.voice_id || 'nl-NL-FennaNeural'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Selected Character Detail Inspector */}
        <div className="space-y-6">
          {selectedCharacter ? (
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-6 sticky top-8">
              <div className="flex items-center justify-between pb-4 border-b border-slate-800">
                <h3 className="font-bold text-base text-slate-100">Karakter Details</h3>
                <span className="text-xs font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                  ID: {selectedCharacter.id.slice(0, 8)}
                </span>
              </div>

              {/* 2.5D Sprite Visualizer & Generator */}
              <div className="flex flex-col items-center p-4 rounded-xl bg-slate-950 border border-slate-800 text-center space-y-3">
                <div className="w-36 h-36 rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden flex items-center justify-center p-2">
                  {selectedCharacter.sprite_url ? (
                    <img
                      src={selectedCharacter.sprite_url}
                      alt={selectedCharacter.name}
                      className="w-full h-full object-contain"
                    />
                  ) : (
                    <div className="text-xs text-slate-500 flex flex-col items-center gap-2">
                      <Smile className="w-10 h-10 opacity-30" />
                      <span>Nog geen sprite gegenereerd</span>
                    </div>
                  )}
                </div>

                {/* Emotie Kiezer voor Generatie */}
                <div className="w-full space-y-2 text-left">
                  <label className="block text-[11px] font-semibold text-slate-300">
                    Kies Emotie voor Sprite:
                  </label>
                  <select
                    value={selectedEmotion}
                    onChange={(e) => setSelectedEmotion(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-100 text-xs font-semibold"
                  >
                    {EMOTIONS.map((em) => (
                      <option key={em.id} value={em.id}>
                        {em.label}
                      </option>
                    ))}
                  </select>

                  <button
                    onClick={() => handleGenerateSprite(selectedCharacter.id)}
                    disabled={isGeneratingSprite}
                    className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50"
                  >
                    <Sparkles className="w-4 h-4" />
                    <span>
                      {isGeneratingSprite
                        ? 'Sprite Genereren...'
                        : `Genereer 2.5D Sprite (${selectedEmotion})`}
                    </span>
                  </button>
                </div>
              </div>

              {/* Stem Tester voor dit karakter */}
              <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                    <Volume2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Karakterstem</span>
                  </span>
                  <button
                    type="button"
                    onClick={() =>
                      handleTestCharacterVoice(
                        selectedCharacter.voice_id || 'nl-NL-FennaNeural',
                        selectedCharacter.voice_provider || 'edge_tts',
                        selectedCharacter.voice_pitch || '+15Hz',
                        selectedCharacter.voice_rate || '+0%'
                      )
                    }
                    disabled={isTestingVoice}
                    className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-[11px] flex items-center gap-1 transition-all"
                  >
                    {isTestingVoice ? (
                      <RefreshCw className="w-3 h-3 animate-spin" />
                    ) : (
                      <Play className="w-3 h-3 fill-current" />
                    )}
                    <span>Luister stem</span>
                  </button>
                </div>
                <div className="text-[11px] text-slate-400 font-mono">
                  {selectedCharacter.voice_id || 'nl-NL-FennaNeural'} ({selectedCharacter.voice_pitch || '+15Hz'})
                </div>

                {voiceAudioUrl && (
                  <audio ref={audioPlayerRef} controls src={voiceAudioUrl} className="w-full h-7 pt-1" />
                )}
              </div>

              {/* Visueel DNA & Consistentie Lock (Prompt + Referentiebeelden) */}
              <div className="space-y-3.5 pt-3 border-t border-slate-800">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Visueel DNA Lock (Consistentie)</span>
                  </h4>
                  <span className="text-[10px] text-indigo-300 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                    Vast Uiterlijk
                  </span>
                </div>

                <div className="space-y-1">
                  <label className="block text-[11px] font-semibold text-slate-400">
                    Vaste Engelse Beschrijving (Kleding, Leeftijd, Kapsel):
                  </label>
                  <textarea
                    rows={3}
                    value={selectedCharacter.visual_dna_prompt || ''}
                    onChange={(e) => {
                      const val = e.target.value;
                      setSelectedCharacter((prev) => (prev ? { ...prev, visual_dna_prompt: val } : null));
                      updateCharacter(selectedCharacter.id, { visual_dna_prompt: val });
                    }}
                    placeholder="5-year-old toddler, big friendly brown eyes, short curly hair, wearing blue denim overalls and a bright yellow t-shirt, cheerful smile"
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-xs font-mono placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-500 leading-relaxed"
                  />
                  <p className="text-[10px] text-slate-500 leading-tight">
                    Wordt automatisch samengevoegd met scène-prompts zodat dit karakter er in elke scène identiek uitziet.
                  </p>
                </div>

                {/* Referentiebeelden Uploader (Max 3) */}
                <div className="space-y-2 pt-1">
                  <div className="flex items-center justify-between text-[11px] font-semibold text-slate-400">
                    <span>Referentiebeelden (max 3):</span>
                    <label className="text-indigo-400 hover:text-indigo-300 cursor-pointer flex items-center gap-1">
                      <Upload className="w-3 h-3" />
                      <span>Upload Referentie</span>
                      <input
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            uploadCharacterReference(selectedCharacter.id, e.target.files[0]);
                          }
                        }}
                      />
                    </label>
                  </div>

                  <div className="grid grid-cols-3 gap-2">
                    {(selectedCharacter.reference_image_urls || []).length > 0 ? (
                      selectedCharacter.reference_image_urls?.map((url, idx) => (
                        <div
                          key={idx}
                          className="group/ref relative aspect-square rounded-xl bg-black border border-slate-800 overflow-hidden"
                        >
                          <img src={url} alt={`Referentie ${idx + 1}`} className="w-full h-full object-cover" />
                          <button
                            type="button"
                            onClick={() => deleteCharacterReference(selectedCharacter.id, idx)}
                            className="absolute top-1 right-1 p-1 rounded-md bg-rose-600/80 hover:bg-rose-600 text-white opacity-0 group-hover/ref:opacity-100 transition-opacity"
                            title="Verwijder referentie"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      ))
                    ) : (
                      <div className="col-span-3 p-3 rounded-xl border border-dashed border-slate-800 text-center text-[11px] text-slate-500">
                        Nog geen referentiebeelden geüpload. Upload er tot 3 voor maximale consistentie.
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Expressions Section met Mond-Sprites Status */}
              <div className="space-y-3 pt-3 border-t border-slate-800">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center justify-between">
                  <span>Expressies ({selectedCharacter.expressions?.length || 0})</span>
                  <span className="text-[10px] text-emerald-400 font-semibold lowercase">
                    ✓ mond-sprites lip-sync
                  </span>
                </h4>

                <div className="grid grid-cols-2 gap-2">
                  {selectedCharacter.expressions?.map((expr, idx) => (
                    <div
                      key={expr.id || `${expr.name}-${idx}`}
                      className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center gap-2.5"
                    >
                      <div className="w-10 h-10 rounded bg-slate-900 overflow-hidden flex items-center justify-center shrink-0">
                        {expr.image_url ? (
                          <img
                            src={expr.image_url}
                            alt={expr.name}
                            className="w-full h-full object-contain"
                          />
                        ) : (
                          <Smile className="w-5 h-5 text-slate-600" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <span className="text-xs font-medium text-slate-200 capitalize block truncate">
                          {expr.name}
                        </span>
                        <span className="text-[10px] text-emerald-400 flex items-center gap-1">
                          <CheckCircle2 className="w-2.5 h-2.5" /> Lip-sync klaar
                        </span>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Upload Expression Form */}
                <form onSubmit={handleUploadExpression} className="space-y-2 pt-2">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="bv. blij, verbaasd"
                      value={expressionName}
                      onChange={(e) => setExpressionName(e.target.value)}
                      className="flex-1 px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-xs"
                    />
                    <label className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 border border-slate-700 text-slate-200 text-xs font-semibold cursor-pointer">
                      <Upload className="w-3.5 h-3.5 text-indigo-400" />
                      <span>Kies</span>
                      <input
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            setExpressionFile(e.target.files[0]);
                          }
                        }}
                      />
                    </label>
                  </div>
                  {expressionFile && (
                    <div className="flex items-center justify-between text-xs text-indigo-300 bg-indigo-500/10 p-1.5 rounded border border-indigo-500/20">
                      <span className="truncate max-w-[150px]">{expressionFile.name}</span>
                      <button
                        type="submit"
                        className="px-2 py-0.5 rounded bg-indigo-600 text-white font-bold text-[10px]"
                      >
                        Upload
                      </button>
                    </div>
                  )}
                </form>
              </div>
            </div>
          ) : (
            <div className="p-8 rounded-2xl border border-dashed border-slate-800 text-center text-slate-500 text-sm">
              Selecteer een karakter links om details en expressies te bewerken.
            </div>
          )}
        </div>
      </div>

      {/* Modal: Nieuw Karakter */}
      <Modal
        isOpen={isNewCharModalOpen}
        onClose={() => setIsNewCharModalOpen(false)}
        title="Nieuw Karakter Aanmaken"
      >
        <form onSubmit={handleCreateCharacter} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Karakternaam (bv. Boris de Beer)
            </label>
            <input
              type="text"
              required
              value={newCharName}
              onChange={(e) => setNewCharName(e.target.value)}
              placeholder="bv. Adam, Nora, Boris de Beer"
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Persoonlijkheid & Rol
            </label>
            <input
              type="text"
              value={newCharPersonality}
              onChange={(e) => setNewCharPersonality(e.target.value)}
              placeholder="bv. Vrolijk, leergierig, stelt vaak vragen aan de kijkers"
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-sm"
            />
          </div>

          {/* Stem Provider, Stem & Pitch Kiezer */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                Provider
              </label>
              <select
                value={newCharVoiceProvider}
                onChange={(e) => setNewCharVoiceProvider(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-xs font-medium"
              >
                <option value="edge_tts">Edge-TTS (Direct)</option>
                <option value="gemini">Google Cloud</option>
                <option value="piper">Piper (Lokaal)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                Stem
              </label>
              <select
                value={newCharVoice}
                onChange={(e) => setNewCharVoice(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-xs font-semibold"
              >
                <option value="nl-NL-FennaNeural">Fenna (nl-NL Kind)</option>
                <option value="nl-NL-MaartenNeural">Maarten (nl-NL Verteller)</option>
                <option value="nl-BE-DenaNeural">Dena (nl-BE Vlaams)</option>
                <option value="en-US-AnaNeural">Ana (en-US Kind)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                Pitch Effect
              </label>
              <select
                value={newCharVoicePitch}
                onChange={(e) => setNewCharVoicePitch(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-xs font-mono"
              >
                <option value="+15Hz">+15Hz (Kinderkarakter)</option>
                <option value="+25Hz">+25Hz (Hoog speels)</option>
                <option value="+0Hz">+0Hz (Natuurlijk)</option>
                <option value="-10Hz">-10Hz (Diepe stem)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                Snelheid
              </label>
              <select
                value={newCharVoiceRate}
                onChange={(e) => setNewCharVoiceRate(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-xs font-mono"
              >
                <option value="-10%">-10% (Rustig)</option>
                <option value="+0%">+0% (Normaal)</option>
                <option value="+10%">+10% (Snel)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Stijl Prompt voor 3D Generatie
            </label>
            <input
              type="text"
              value={newCharStyle}
              onChange={(e) => setNewCharStyle(e.target.value)}
              placeholder="3D Pixar style cute friendly animal character, big expressive eyes"
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-sm font-mono text-xs"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Visueel DNA Lock (Vast Uiterlijk)
            </label>
            <textarea
              rows={2}
              value={newCharVisualDna}
              onChange={(e) => setNewCharVisualDna(e.target.value)}
              placeholder="5-year-old toddler, big friendly brown eyes, curly brown hair, wearing blue denim overalls and yellow shirt"
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-xs font-mono placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setIsNewCharModalOpen(false)}
              className="px-4 py-2 rounded-xl text-slate-400 hover:text-white text-xs font-semibold"
            >
              Annuleren
            </button>
            <button
              type="submit"
              className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-600/20 active:scale-95"
            >
              Karakter Aanmaken
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
