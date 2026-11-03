import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus,
  Clapperboard,
  Users,
  Video,
  ArrowRight,
  Trash2,
  Calendar,
  Layers,
} from 'lucide-react';
import { useStore } from '../store/useStore';
import { Modal } from '../components/Modal';
import { EmptyState } from '../components/EmptyState';
import { StatusBadge } from '../components/StatusBadge';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const {
    projects,
    projectsLoading,
    fetchProjects,
    createProject,
    deleteProject,
    currentProject,
    setCurrentProject,
    episodes,
    episodesLoading,
    fetchEpisodes,
    createEpisode,
    deleteEpisode,
    setCurrentEpisode,
  } = useStore();

  const [isNewProjectModalOpen, setIsNewProjectModalOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDesc, setNewProjectDesc] = useState('');

  const [isNewEpisodeModalOpen, setIsNewEpisodeModalOpen] = useState(false);
  const [newEpisodeTitle, setNewEpisodeTitle] = useState('');
  const [newEpisodeDesc, setNewEpisodeDesc] = useState('');

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  useEffect(() => {
    if (!currentProject && projects.length > 0) {
      setCurrentProject(projects[0]);
    }
  }, [currentProject, projects, setCurrentProject]);

  useEffect(() => {
    if (currentProject) {
      fetchEpisodes(currentProject.id);
    }
  }, [currentProject, fetchEpisodes]);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;
    const proj = await createProject({
      name: newProjectName.trim(),
      description: newProjectDesc.trim(),
    });
    setNewProjectName('');
    setNewProjectDesc('');
    setIsNewProjectModalOpen(false);
    setCurrentProject(proj);
  };

  const handleCreateEpisode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentProject || !newEpisodeTitle.trim()) return;
    const ep = await createEpisode({
      project_id: currentProject.id,
      title: newEpisodeTitle.trim(),
      description: newEpisodeDesc.trim(),
    });
    setNewEpisodeTitle('');
    setNewEpisodeDesc('');
    setIsNewEpisodeModalOpen(false);
    setCurrentEpisode(ep);
    navigate(`/episodes/${ep.id}`);
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-300">
      {/* Top Banner / Welcome */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight flex items-center gap-2.5">
            <span>KidsEdu Video Studio</span>
            <span className="text-sm font-semibold px-2.5 py-0.5 rounded-full bg-gradient-to-r from-amber-500/20 to-orange-500/20 text-amber-300 border border-amber-500/30">
              10-15 Min Formaat
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Creëer, animeer en publiceer virale educatieve kindercontent voor YouTube Kids.
          </p>
        </div>

        <button
          onClick={() => setIsNewProjectModalOpen(true)}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition-all shadow-lg shadow-indigo-600/20 active:scale-95 shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>Nieuw Project</span>
        </button>
      </div>

      {/* Projects Horizontal Bar / Selector */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-200 flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            <span>Jouw Series & Kanalen ({projects.length})</span>
          </h2>
        </div>

        {projects.length === 0 && !projectsLoading ? (
          <EmptyState
            icon={Clapperboard}
            title="Nog geen projecten"
            description="Start je eerste kindervideoserie door een project aan te maken."
            actionLabel="Maak Eerste Project"
            onAction={() => setIsNewProjectModalOpen(true)}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {projects.map((proj) => {
              const isSelected = currentProject?.id === proj.id;
              return (
                <div
                  key={proj.id}
                  onClick={() => setCurrentProject(proj)}
                  className={`p-5 rounded-2xl border transition-all duration-200 cursor-pointer flex flex-col justify-between ${
                    isSelected
                      ? 'bg-slate-800/90 border-indigo-500 shadow-xl shadow-indigo-500/10 ring-2 ring-indigo-500/40'
                      : 'bg-slate-900/80 border-slate-800 hover:border-slate-700 hover:bg-slate-850'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/60">
                        Leeftijd: 3 - 7 jr
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (confirm(`Project "${proj.name}" verwijderen?`)) {
                            deleteProject(proj.id);
                          }
                        }}
                        className="p-1 text-slate-500 hover:text-rose-400 transition-colors"
                        title="Verwijder project"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    <h3 className="font-bold text-base text-slate-100 truncate">{proj.name}</h3>
                    <p className="text-xs text-slate-400 line-clamp-2 mt-1">
                      {proj.description || 'Geen beschrijving opgegeven.'}
                    </p>
                  </div>

                  <div className="flex items-center justify-between pt-4 mt-4 border-t border-slate-800/60 text-xs text-slate-400">
                    <span className="flex items-center gap-1">
                      <Video className="w-3.5 h-3.5 text-indigo-400" />
                      {proj.episode_count || 0} afleveringen
                    </span>
                    <span className="flex items-center gap-1">
                      <Users className="w-3.5 h-3.5 text-amber-400" />
                      {proj.character_count || 0} karakters
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Episodes Section of Selected Project */}
      {currentProject && (
        <div className="space-y-4 pt-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-200 flex items-center gap-2">
                <Video className="w-5 h-5 text-indigo-400" />
                <span>Afleveringen in "{currentProject.name}"</span>
              </h2>
              <p className="text-xs text-slate-400">
                Kies een aflevering om het script te bewerken, scènes te animeren of te renderen.
              </p>
            </div>

            <button
              onClick={() => setIsNewEpisodeModalOpen(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-100 font-semibold text-xs transition-all active:scale-95"
            >
              <Plus className="w-4 h-4 text-indigo-400" />
              <span>Nieuwe Aflevering</span>
            </button>
          </div>

          {episodes.length === 0 && !episodesLoading ? (
            <EmptyState
              icon={Video}
              title="Geen afleveringen gevonden"
              description="Deze serie heeft nog geen afleveringen. Maak er nu één aan om te beginnen met het script!"
              actionLabel="Maak Aflevering"
              onAction={() => setIsNewEpisodeModalOpen(true)}
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {episodes.map((ep) => (
                <div
                  key={ep.id}
                  className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700 hover:bg-slate-850 transition-all flex flex-col justify-between group"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-3">
                      <StatusBadge status={ep.status} />
                      <button
                        onClick={() => {
                          if (confirm(`Aflevering "${ep.title}" verwijderen?`)) {
                            deleteEpisode(ep.id);
                          }
                        }}
                        className="p-1 text-slate-500 hover:text-rose-400 transition-colors opacity-0 group-hover:opacity-100"
                        title="Verwijder aflevering"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    <h3 className="font-bold text-base text-slate-100 group-hover:text-indigo-400 transition-colors">
                      {ep.title}
                    </h3>
                    <p className="text-xs text-slate-400 line-clamp-2 mt-1">
                      {ep.description || 'Nog geen beschrijving.'}
                    </p>
                  </div>

                  <div className="pt-4 mt-4 border-t border-slate-800/60 flex items-center justify-between">
                    <span className="text-xs text-slate-500 flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5" />
                      {new Date(ep.created_at).toLocaleDateString('nl-NL')}
                    </span>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => {
                          setCurrentEpisode(ep);
                          navigate(`/render/${ep.id}`);
                        }}
                        className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700/80 transition-colors"
                      >
                        Render / Publish
                      </button>
                      <button
                        onClick={() => {
                          setCurrentEpisode(ep);
                          navigate(`/episodes/${ep.id}`);
                        }}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all shadow-md shadow-indigo-600/20"
                      >
                        <span>Studio</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Modal: Nieuw Project */}
      <Modal
        isOpen={isNewProjectModalOpen}
        onClose={() => setIsNewProjectModalOpen(false)}
        title="Nieuw Project Aanmaken"
      >
        <form onSubmit={handleCreateProject} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Projectnaam (bv. Vrolijke Vriendjes Club)
            </label>
            <input
              type="text"
              required
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              placeholder="bv. Dieren Avonturen met Boris"
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Beschrijving & Kanaal Doel
            </label>
            <textarea
              rows={3}
              value={newProjectDesc}
              onChange={(e) => setNewProjectDesc(e.target.value)}
              placeholder="Educatieve animatieserie voor peuters en kleuters over kleuren, tellen en vriendschap..."
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3">
            <button
              type="button"
              onClick={() => setIsNewProjectModalOpen(false)}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs"
            >
              Annuleren
            </button>
            <button
              type="submit"
              className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-600/20"
            >
              Project Opslaan
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Nieuwe Aflevering */}
      <Modal
        isOpen={isNewEpisodeModalOpen}
        onClose={() => setIsNewEpisodeModalOpen(false)}
        title="Nieuwe Aflevering Aanmaken"
      >
        <form onSubmit={handleCreateEpisode} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Aflevering Titel
            </label>
            <input
              type="text"
              required
              value={newEpisodeTitle}
              onChange={(e) => setNewEpisodeTitle(e.target.value)}
              placeholder="bv. Aflevering 1: Boris leert de kleuren van de regenboog"
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Korte Notities
            </label>
            <textarea
              rows={3}
              value={newEpisodeDesc}
              onChange={(e) => setNewEpisodeDesc(e.target.value)}
              placeholder="In deze aflevering ontdekt Boris een magische boom..."
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3">
            <button
              type="button"
              onClick={() => setIsNewEpisodeModalOpen(false)}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs"
            >
              Annuleren
            </button>
            <button
              type="submit"
              className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-600/20"
            >
              Naar Studio
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
