import React, { useEffect, useState } from 'react';
import {
  Users,
  Plus,
  Sparkles,
  Upload,
  Trash2,
  Smile,
  Layers,
} from 'lucide-react';
import { useStore } from '../store/useStore';
import { Modal } from '../components/Modal';
import { EmptyState } from '../components/EmptyState';
import type { Character } from '../api/client';

export const CharacterVault: React.FC = () => {
  const {
    projects,
    currentProject,
    setCurrentProject,
    characters,
    charactersLoading,
    fetchCharacters,
    createCharacter,
    deleteCharacter,
    generateSprite,
    uploadExpression,
  } = useStore();

  const [selectedCharacter, setSelectedCharacter] = useState<Character | null>(null);
  const [isNewCharModalOpen, setIsNewCharModalOpen] = useState(false);
  const [newCharName, setNewCharName] = useState('');
  const [newCharDesc, setNewCharDesc] = useState('');
  const [newCharPersonality, setNewCharPersonality] = useState('Nieuwsgierig en altijd vrolijk');
  const [newCharVoice, setNewCharVoice] = useState('nl_NL-mls-medium');
  const [newCharStyle, setNewCharStyle] = useState('3D Pixar style cute friendly animal character');

  const [expressionName, setExpressionName] = useState('blij');
  const [expressionFile, setExpressionFile] = useState<File | null>(null);
  const [isGeneratingSprite, setIsGeneratingSprite] = useState(false);

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
      style_prompt: newCharStyle.trim(),
    });

    setNewCharName('');
    setNewCharDesc('');
    setIsNewCharModalOpen(false);
    setSelectedCharacter(char);
  };

  const handleGenerateSprite = async (charId: string) => {
    setIsGeneratingSprite(true);
    try {
      await generateSprite(charId);
    } finally {
      setIsGeneratingSprite(false);
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
            Beheer herbruikbare 2.5D personages, expressies en stemmen voor al je educatieve video's.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Project Dropdown Selector */}
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
                      <div className="w-16 h-16 rounded-xl bg-slate-950 border border-slate-800 overflow-hidden shrink-0 flex items-center justify-center">
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
                        {char.voice_id}
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

              {/* Sprite Visualizer & Generator */}
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

                <button
                  onClick={() => handleGenerateSprite(selectedCharacter.id)}
                  disabled={isGeneratingSprite}
                  className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>{isGeneratingSprite ? 'Sprite Genereren...' : 'Genereer 2.5D Sprite'}</span>
                </button>
              </div>

              {/* Character Attributes */}
              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-slate-400 font-medium">Persoonlijkheid:</span>
                  <p className="text-slate-200 mt-0.5">{selectedCharacter.personality || 'Niet ingevuld'}</p>
                </div>

                <div>
                  <span className="text-slate-400 font-medium">Stijl Prompt:</span>
                  <p className="text-slate-200 mt-0.5 font-mono text-[11px] bg-slate-950 p-2 rounded border border-slate-800">
                    {selectedCharacter.style_prompt || '3D Pixar style cute friendly animal'}
                  </p>
                </div>
              </div>

              {/* Expressions Section */}
              <div className="space-y-3 pt-4 border-t border-slate-800">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center justify-between">
                  <span>Expressies ({selectedCharacter.expressions?.length || 0})</span>
                  <span className="text-[10px] text-slate-400 lowercase">t.b.v. lip-sync</span>
                </h4>

                <div className="grid grid-cols-3 gap-2">
                  {selectedCharacter.expressions?.map((expr, idx) => (
                    <div
                      key={expr.id || `${expr.name}-${idx}`}
                      className="p-2 rounded-lg bg-slate-950 border border-slate-800 flex flex-col items-center text-center space-y-1"
                    >
                      <div className="w-12 h-12 rounded bg-slate-900 overflow-hidden flex items-center justify-center">
                        {expr.image_url ? (
                          <img
                            src={expr.image_url}
                            alt={expr.name}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <Smile className="w-5 h-5 text-slate-600" />
                        )}
                      </div>
                      <span className="text-[11px] font-medium text-slate-300 truncate w-full">
                        {expr.name}
                      </span>
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
              placeholder="bv. Sam de Schildpad"
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Persoonlijkheid & Doel
            </label>
            <input
              type="text"
              value={newCharPersonality}
              onChange={(e) => setNewCharPersonality(e.target.value)}
              placeholder="bv. Enthousiast, leert kinderen over fruit en groente"
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                Stem Voice ID
              </label>
              <select
                value={newCharVoice}
                onChange={(e) => setNewCharVoice(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-xs"
              >
                <option value="nl_NL-mls-medium">Piper Nederlands (Vrolijk)</option>
                <option value="af_bella">Kokoro Bella (Zacht & Vriendelijk)</option>
                <option value="nl-NL-Wavenet-A">Google Wavenet NL (Vrouwelijk)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                Visuele Stijl
              </label>
              <input
                type="text"
                value={newCharStyle}
                onChange={(e) => setNewCharStyle(e.target.value)}
                placeholder="3D Pixar style"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-xs"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Uiterlijke Beschrijving (voor beeldgeneratie)
            </label>
            <textarea
              rows={2}
              value={newCharDesc}
              onChange={(e) => setNewCharDesc(e.target.value)}
              placeholder="Schattige kleine bruine beer met een gele trui en grote ronde ogen..."
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3">
            <button
              type="button"
              onClick={() => setIsNewCharModalOpen(false)}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs"
            >
              Annuleren
            </button>
            <button
              type="submit"
              className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-600/20"
            >
              Karakter Opslaan
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
