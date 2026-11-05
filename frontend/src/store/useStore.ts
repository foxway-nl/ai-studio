import { create } from 'zustand';
import * as api from '../api/client';
import type {
  Project,
  Character,
  Episode,
  Scene,
  Settings,
  ServiceStatus,
  TaskProgress,
  ProjectCreate,
  CharacterCreate,
  CharacterUpdate,
  EpisodeCreate,
  EpisodeUpdate,
  SceneCreate,
  SceneUpdate,
  GeneratedSeo,
  GeneratedThumbnail,
} from '../api/client';

// ─── Toast ───────────────────────────────────────────────────────────────────

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
}

// ─── Store Shape ─────────────────────────────────────────────────────────────

interface StoreState {
  // Projects
  projects: Project[];
  projectsLoading: boolean;
  currentProject: Project | null;

  // Characters
  characters: Character[];
  charactersLoading: boolean;

  // Episodes
  episodes: Episode[];
  episodesLoading: boolean;
  currentEpisode: Episode | null;

  // Scenes
  scenes: Scene[];
  scenesLoading: boolean;

  // Settings
  settings: Settings | null;
  servicesStatus: ServiceStatus[];
  settingsLoading: boolean;

  // Tasks
  activeTasks: Record<string, TaskProgress>;
  _taskCallbacks: Record<string, { onComplete?: () => void; onError?: () => void }>;

  // Toasts
  toasts: Toast[];

  // Auto-save timers
  _autoSaveTimers: Record<string, ReturnType<typeof setTimeout>>;

  // ─── Project Actions ─────────────────────────────────────────────────────
  fetchProjects: () => Promise<void>;
  fetchProject: (id: string) => Promise<void>;
  createProject: (data: ProjectCreate) => Promise<Project>;
  updateProject: (id: string, data: Partial<ProjectCreate>) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
  setCurrentProject: (project: Project | null) => void;

  // ─── Character Actions ───────────────────────────────────────────────────
  fetchCharacters: (projectId: string) => Promise<void>;
  createCharacter: (data: CharacterCreate) => Promise<Character>;
  updateCharacter: (id: string, data: CharacterUpdate) => Promise<void>;
  deleteCharacter: (id: string) => Promise<void>;
  generateSprite: (characterId: string, emotion?: string) => Promise<void>;
  uploadExpression: (characterId: string, name: string, file: File) => Promise<void>;

  // ─── Episode Actions ─────────────────────────────────────────────────────
  fetchEpisodes: (projectId: string) => Promise<void>;
  fetchEpisode: (id: string) => Promise<void>;
  createEpisode: (data: EpisodeCreate) => Promise<Episode>;
  updateEpisode: (id: string, data: EpisodeUpdate) => Promise<void>;
  deleteEpisode: (id: string) => Promise<void>;
  setCurrentEpisode: (episode: Episode | null) => void;
  autoSaveEpisode: (id: string, data: EpisodeUpdate) => void;

  // ─── Scene Actions ───────────────────────────────────────────────────────
  fetchScenes: (episodeId: string) => Promise<void>;
  createScene: (data: SceneCreate) => Promise<Scene>;
  updateScene: (id: string, data: SceneUpdate) => Promise<void>;
  deleteScene: (id: string) => Promise<void>;
  reorderScenes: (episodeId: string, order: { scene_id: string; order: number }[]) => Promise<void>;
  autoSaveScene: (id: string, data: SceneUpdate) => void;

  // ─── Generation Actions ──────────────────────────────────────────────────
  generateScript: (episodeId: string, topic: string, characterIds?: string[]) => Promise<string>;
  generateViralIdeas: (episodeId: string, audience?: string) => Promise<string[]>;
  generateImage: (sceneId: string) => Promise<string>;
  generateAudio: (sceneId: string) => Promise<string>;
  generateBulkAudio: (episodeId: string) => Promise<string>;
  generateEpisodeSeo: (episodeId: string) => Promise<GeneratedSeo>;
  generateEpisodeThumbnail: (episodeId: string, prompt?: string) => Promise<GeneratedThumbnail>;
  selectSceneImage: (sceneId: string, path: string) => Promise<void>;

  // ─── Render & Publish ────────────────────────────────────────────────────
  startRender: (episodeId: string, resolution: string, fps: number) => Promise<string>;
  publishToYouTube: (episodeId: string, privacyStatus: string, madeForKids: boolean) => Promise<string>;
  getYouTubeAuthUrl: () => Promise<string>;

  // ─── Settings Actions ────────────────────────────────────────────────────
  fetchSettings: () => Promise<void>;
  saveSettings: (data: Partial<Settings>) => Promise<void>;
  testConnection: (service: string) => Promise<api.TestConnectionResponse>;
  fetchServicesStatus: () => Promise<void>;
  testGeminiApiKey: (apiKey?: string) => Promise<api.GeminiTestResponse>;
  getAvailableVoices: () => Promise<api.VoicesMap>;
  testVoice: (data: api.VoiceTestRequest) => Promise<api.VoiceTestResponse>;
  getYouTubeChannel: () => Promise<api.YouTubeChannelResponse>;
  disconnectYouTube: () => Promise<void>;

  // ─── Animation & Flow Actions ─────────────────────────────────────────────
  animateScene: (sceneId: string, engine?: string, motionPrompt?: string) => Promise<api.AnimateSceneResponse>;
  animateSceneLocal: (sceneId: string) => Promise<api.AnimateSceneResponse>;
  animateEpisodeLocalBulk: (episodeId: string) => Promise<any>;
  uploadSceneClip: (sceneId: string, file: File) => Promise<api.AnimateSceneResponse>;
  generateSceneMotionPrompt: (sceneId: string) => Promise<string>;
  exportGoogleFlow: (episodeId: string) => Promise<api.ExportFlowResponse>;
  uploadCharacterReference: (characterId: string, file: File) => Promise<void>;
  deleteCharacterReference: (characterId: string, index: number) => Promise<void>;

  // ─── Task Progress ───────────────────────────────────────────────────────
  trackTask: (taskId: string, onComplete?: () => void, onError?: () => void) => void;
  updateTaskProgress: (taskId: string, progress: TaskProgress) => void;
  removeTask: (taskId: string) => void;

  // ─── Toasts ──────────────────────────────────────────────────────────────
  addToast: (type: Toast['type'], message: string) => void;
  removeToast: (id: string) => void;
}

// ─── Store ───────────────────────────────────────────────────────────────────

export const useStore = create<StoreState>((set, get) => ({
  // Initial state
  projects: [],
  projectsLoading: false,
  currentProject: null,

  characters: [],
  charactersLoading: false,

  episodes: [],
  episodesLoading: false,
  currentEpisode: null,

  scenes: [],
  scenesLoading: false,

  settings: null,
  servicesStatus: [],
  settingsLoading: false,

  activeTasks: {},
  _taskCallbacks: {},
  toasts: [],
  _autoSaveTimers: {},

  // ─── Project Actions ───────────────────────────────────────────────────────

  fetchProjects: async () => {
    set({ projectsLoading: true });
    try {
      const projects = await api.getProjects();
      set({ projects, projectsLoading: false });
    } catch {
      set({ projectsLoading: false });
      get().addToast('error', 'Kon projecten niet laden');
    }
  },

  fetchProject: async (id: string) => {
    try {
      const project = await api.getProject(id);
      set({ currentProject: project });
    } catch {
      get().addToast('error', 'Kon project niet laden');
    }
  },

  createProject: async (data: ProjectCreate) => {
    try {
      const project = await api.createProject(data);
      set((state) => ({ projects: [...state.projects, project] }));
      get().addToast('success', 'Project aangemaakt!');
      return project;
    } catch {
      get().addToast('error', 'Kon project niet aanmaken');
      throw new Error('Failed to create project');
    }
  },

  updateProject: async (id: string, data: Partial<ProjectCreate>) => {
    try {
      const updated = await api.updateProject(id, data);
      set((state) => ({
        projects: state.projects.map((p) => (p.id === id ? updated : p)),
        currentProject: state.currentProject?.id === id ? updated : state.currentProject,
      }));
    } catch {
      get().addToast('error', 'Kon project niet bijwerken');
    }
  },

  deleteProject: async (id: string) => {
    try {
      await api.deleteProject(id);
      set((state) => ({
        projects: state.projects.filter((p) => p.id !== id),
        currentProject: state.currentProject?.id === id ? null : state.currentProject,
      }));
      get().addToast('success', 'Project verwijderd');
    } catch {
      get().addToast('error', 'Kon project niet verwijderen');
    }
  },

  setCurrentProject: (project: Project | null) => {
    set({ currentProject: project });
  },

  // ─── Character Actions ─────────────────────────────────────────────────────

  fetchCharacters: async (projectId: string) => {
    set({ charactersLoading: true });
    try {
      const characters = await api.getCharacters(projectId);
      set({ characters, charactersLoading: false });
    } catch {
      set({ charactersLoading: false });
      get().addToast('error', 'Kon karakters niet laden');
    }
  },

  createCharacter: async (data: CharacterCreate) => {
    try {
      const character = await api.createCharacter(data);
      set((state) => ({ characters: [...state.characters, character] }));
      get().addToast('success', 'Karakter aangemaakt!');
      return character;
    } catch {
      get().addToast('error', 'Kon karakter niet aanmaken');
      throw new Error('Failed to create character');
    }
  },

  updateCharacter: async (id: string, data: CharacterUpdate) => {
    try {
      const updated = await api.updateCharacter(id, data);
      set((state) => ({
        characters: state.characters.map((c) => (c.id === id ? updated : c)),
      }));
    } catch {
      get().addToast('error', 'Kon karakter niet bijwerken');
    }
  },

  deleteCharacter: async (id: string) => {
    try {
      await api.deleteCharacter(id);
      set((state) => ({
        characters: state.characters.filter((c) => c.id !== id),
      }));
      get().addToast('success', 'Karakter verwijderd');
    } catch {
      get().addToast('error', 'Kon karakter niet verwijderen');
    }
  },

  generateSprite: async (characterId: string, emotion = 'blij') => {
    try {
      const { task_id } = await api.generateSprite(characterId, emotion);
      const projectId = get().currentProject?.id;
      get().trackTask(
        task_id,
        () => {
          if (projectId) get().fetchCharacters(projectId);
          get().addToast('success', `Sprite (${emotion}) gegenereerd!`);
        },
        () => get().addToast('error', 'Sprite generatie mislukt')
      );
      get().addToast('info', `Sprite (${emotion}) wordt gegenereerd…`);
    } catch {
      get().addToast('error', 'Kon sprite niet genereren');
    }
  },

  uploadExpression: async (characterId: string, name: string, file: File) => {
    try {
      const expression = await api.uploadExpression(characterId, name, file);
      set((state) => ({
        characters: state.characters.map((c) =>
          c.id === characterId
            ? { ...c, expressions: [...c.expressions, expression] }
            : c
        ),
      }));
      get().addToast('success', 'Expressie geüpload!');
    } catch {
      get().addToast('error', 'Kon expressie niet uploaden');
    }
  },

  // ─── Episode Actions ───────────────────────────────────────────────────────

  fetchEpisodes: async (projectId: string) => {
    set({ episodesLoading: true });
    try {
      const episodes = await api.getEpisodes(projectId);
      set({ episodes, episodesLoading: false });
    } catch {
      set({ episodesLoading: false });
      get().addToast('error', 'Kon afleveringen niet laden');
    }
  },

  fetchEpisode: async (id: string) => {
    try {
      const episode = await api.getEpisode(id);
      set({ currentEpisode: episode });
    } catch {
      get().addToast('error', 'Kon aflevering niet laden');
    }
  },

  createEpisode: async (data: EpisodeCreate) => {
    try {
      const episode = await api.createEpisode(data);
      set((state) => ({ episodes: [...state.episodes, episode] }));
      get().addToast('success', 'Aflevering aangemaakt!');
      return episode;
    } catch {
      get().addToast('error', 'Kon aflevering niet aanmaken');
      throw new Error('Failed to create episode');
    }
  },

  updateEpisode: async (id: string, data: EpisodeUpdate) => {
    try {
      const updated = await api.updateEpisode(id, data);
      set((state) => ({
        episodes: state.episodes.map((e) => (e.id === id ? updated : e)),
        currentEpisode: state.currentEpisode?.id === id ? updated : state.currentEpisode,
      }));
    } catch {
      get().addToast('error', 'Kon aflevering niet bijwerken');
    }
  },

  deleteEpisode: async (id: string) => {
    try {
      await api.deleteEpisode(id);
      set((state) => ({
        episodes: state.episodes.filter((e) => e.id !== id),
        currentEpisode: state.currentEpisode?.id === id ? null : state.currentEpisode,
      }));
      get().addToast('success', 'Aflevering verwijderd');
    } catch {
      get().addToast('error', 'Kon aflevering niet verwijderen');
    }
  },

  setCurrentEpisode: (episode: Episode | null) => {
    set({ currentEpisode: episode });
  },

  autoSaveEpisode: (id: string, data: EpisodeUpdate) => {
    const timers = get()._autoSaveTimers;
    const timerKey = `episode_${id}`;
    if (timers[timerKey]) {
      clearTimeout(timers[timerKey]);
    }
    const timer = setTimeout(async () => {
      try {
        const updated = await api.updateEpisode(id, data);
        set((state) => ({
          episodes: state.episodes.map((e) => (e.id === id ? updated : e)),
          currentEpisode: state.currentEpisode?.id === id ? updated : state.currentEpisode,
        }));
      } catch {
        get().addToast('error', 'Automatisch opslaan mislukt');
      }
    }, 500);
    set((state) => ({
      _autoSaveTimers: { ...state._autoSaveTimers, [timerKey]: timer },
    }));
  },

  // ─── Scene Actions ─────────────────────────────────────────────────────────

  fetchScenes: async (episodeId: string) => {
    set({ scenesLoading: true });
    try {
      const scenes = await api.getScenes(episodeId);
      set({ scenes: scenes.sort((a, b) => a.order - b.order), scenesLoading: false });
    } catch {
      set({ scenesLoading: false });
      get().addToast('error', 'Kon scènes niet laden');
    }
  },

  createScene: async (data: SceneCreate) => {
    try {
      const scene = await api.createScene(data);
      set((state) => ({
        scenes: [...state.scenes, scene].sort((a, b) => a.order - b.order),
      }));
      get().addToast('success', 'Scène toegevoegd!');
      return scene;
    } catch {
      get().addToast('error', 'Kon scène niet aanmaken');
      throw new Error('Failed to create scene');
    }
  },

  updateScene: async (id: string, data: SceneUpdate) => {
    try {
      const updated = await api.updateScene(id, data);
      set((state) => ({
        scenes: state.scenes
          .map((s) => (s.id === id ? updated : s))
          .sort((a, b) => a.order - b.order),
      }));
    } catch {
      get().addToast('error', 'Kon scène niet bijwerken');
    }
  },

  deleteScene: async (id: string) => {
    try {
      await api.deleteScene(id);
      set((state) => ({
        scenes: state.scenes.filter((s) => s.id !== id),
      }));
      get().addToast('success', 'Scène verwijderd');
    } catch {
      get().addToast('error', 'Kon scène niet verwijderen');
    }
  },

  reorderScenes: async (
    episodeId: string,
    order: { scene_id: string; order: number }[]
  ) => {
    try {
      const updated = await api.reorderScenes(episodeId, order);
      set({ scenes: updated.sort((a, b) => a.order - b.order) });
    } catch {
      get().addToast('error', 'Kon volgorde niet bijwerken');
    }
  },

  autoSaveScene: (id: string, data: SceneUpdate) => {
    const timers = get()._autoSaveTimers;
    const timerKey = `scene_${id}`;
    if (timers[timerKey]) {
      clearTimeout(timers[timerKey]);
    }
    const timer = setTimeout(async () => {
      try {
        const updated = await api.updateScene(id, data);
        set((state) => ({
          scenes: state.scenes
            .map((s) => (s.id === id ? updated : s))
            .sort((a, b) => a.order - b.order),
        }));
      } catch {
        get().addToast('error', 'Automatisch opslaan mislukt');
      }
    }, 500);
    set((state) => ({
      _autoSaveTimers: { ...state._autoSaveTimers, [timerKey]: timer },
    }));
  },

  // ─── Generation ────────────────────────────────────────────────────────────

  generateScript: async (
    episodeId: string,
    topic: string,
    characterIds?: string[]
  ) => {
    try {
      const { task_id } = await api.generateScript({
        episode_id: episodeId,
        topic,
        character_ids: characterIds,
      });
      get().trackTask(task_id);
      get().addToast('info', 'Script wordt gegenereerd…');
      return task_id;
    } catch {
      get().addToast('error', 'Kon script niet genereren');
      throw new Error('Failed to generate script');
    }
  },

  generateViralIdeas: async (episodeId: string, audience?: string) => {
    try {
      get().addToast('info', 'AI bedenkt 5 virale concepten…');
      const ideas = await api.generateViralIdeas(episodeId, audience || 'kids', 5);
      return ideas;
    } catch {
      get().addToast('error', 'Kon ideeën niet ophalen');
      return [];
    }
  },

  generateImage: async (sceneId: string) => {
    try {
      const { task_id } = await api.generateImage({ scene_id: sceneId });
      const episodeId = get().currentEpisode?.id;
      get().trackTask(task_id, () => {
        if (episodeId) {
          get().fetchScenes(episodeId);
          get().fetchEpisode(episodeId);
        }
        get().addToast('success', 'Afbeelding gegenereerd!');
      });
      get().addToast('info', 'Afbeelding wordt gegenereerd…');
      return task_id;
    } catch {
      get().addToast('error', 'Kon afbeelding niet genereren');
      throw new Error('Failed to generate image');
    }
  },

  generateAudio: async (sceneId: string) => {
    try {
      const { task_id } = await api.generateAudio({ scene_id: sceneId });
      const episodeId = get().currentEpisode?.id;
      get().trackTask(task_id, () => {
        if (episodeId) {
          get().fetchScenes(episodeId);
          get().fetchEpisode(episodeId);
        }
        get().addToast('success', 'Audio gegenereerd!');
      });
      get().addToast('info', 'Audio wordt gegenereerd…');
      return task_id;
    } catch {
      get().addToast('error', 'Kon audio niet genereren');
      throw new Error('Failed to generate audio');
    }
  },

  generateBulkAudio: async (episodeId: string) => {
    try {
      const { task_id, scene_count } = await api.generateBulkAudio(episodeId);
      get().trackTask(task_id, () => {
        get().fetchScenes(episodeId);
        get().fetchEpisode(episodeId);
        get().addToast('success', 'Audio voor alle scènes gegenereerd!');
      });
      get().addToast('info', `Audio voor ${scene_count} scènes wordt gegenereerd…`);
      return task_id;
    } catch {
      get().addToast('error', 'Kon bulk-audio niet genereren');
      throw new Error('Failed to generate bulk audio');
    }
  },

  generateEpisodeSeo: async (episodeId: string) => {
    try {
      const seo = await api.generateEpisodeSeo(episodeId);
      get().fetchEpisode(episodeId);
      get().addToast('success', 'SEO metadata gegenereerd!');
      return seo;
    } catch {
      get().addToast('error', 'Kon SEO metadata niet genereren');
      throw new Error('Failed to generate SEO');
    }
  },

  generateEpisodeThumbnail: async (episodeId: string, prompt?: string) => {
    try {
      const thumbnail = await api.generateEpisodeThumbnail(episodeId, prompt);
      get().fetchEpisode(episodeId);
      get().addToast('success', 'Thumbnail gegenereerd!');
      return thumbnail;
    } catch {
      get().addToast('error', 'Kon thumbnail niet genereren');
      throw new Error('Failed to generate thumbnail');
    }
  },

  selectSceneImage: async (sceneId: string, path: string) => {
    try {
      const updated = await api.selectSceneImage(sceneId, path);
      set((state) => ({
        scenes: state.scenes
          .map((s) => (s.id === sceneId ? updated : s))
          .sort((a, b) => a.order - b.order),
      }));
      get().addToast('success', 'Afbeelding uit geschiedenis gekozen');
    } catch {
      get().addToast('error', 'Kon afbeelding niet selecteren');
    }
  },

  // ─── Render & Publish ──────────────────────────────────────────────────────

  startRender: async (episodeId: string, resolution: string, fps: number) => {
    try {
      const { task_id } = await api.startRender({
        episode_id: episodeId,
        resolution,
        fps,
      });
      get().trackTask(task_id);
      get().addToast('info', 'Render gestart…');
      return task_id;
    } catch {
      get().addToast('error', 'Kon render niet starten');
      throw new Error('Failed to start render');
    }
  },

  publishToYouTube: async (
    episodeId: string,
    privacyStatus: string,
    madeForKids: boolean
  ) => {
    try {
      const { task_id } = await api.publishToYouTube({
        episode_id: episodeId,
        privacy_status: privacyStatus as 'public' | 'unlisted' | 'private',
        made_for_kids: madeForKids,
      });
      get().trackTask(task_id);
      get().addToast('info', 'Upload naar YouTube gestart…');
      return task_id;
    } catch {
      get().addToast('error', 'Kon niet publiceren naar YouTube');
      throw new Error('Failed to publish');
    }
  },

  getYouTubeAuthUrl: async () => {
    try {
      const { auth_url } = await api.getYouTubeAuthUrl();
      return auth_url;
    } catch {
      get().addToast('error', 'Kon YouTube autorisatie URL niet ophalen');
      throw new Error('Failed to get auth URL');
    }
  },

  // ─── Settings ──────────────────────────────────────────────────────────────

  fetchSettings: async () => {
    set({ settingsLoading: true });
    try {
      const settings = await api.getSettings();
      set({ settings, settingsLoading: false });
    } catch {
      set({ settingsLoading: false });
      get().addToast('error', 'Kon instellingen niet laden');
    }
  },

  saveSettings: async (data: Partial<Settings>) => {
    try {
      const settings = await api.saveSettings(data);
      set({ settings });
      get().addToast('success', 'Instellingen opgeslagen!');
    } catch {
      get().addToast('error', 'Kon instellingen niet opslaan');
    }
  },

  testConnection: async (service: string) => {
    try {
      const result = await api.testConnection(service);
      get().addToast(
        result.connected ? 'success' : 'error',
        result.message
      );
      return result;
    } catch {
      get().addToast('error', `Kon verbinding met ${service} niet testen`);
      throw new Error('Failed to test connection');
    }
  },

  fetchServicesStatus: async () => {
    try {
      const servicesStatus = await api.getServicesStatus();
      set({ servicesStatus });
    } catch {
      get().addToast('error', 'Kon service status niet laden');
    }
  },

  testGeminiApiKey: async (apiKey?: string) => {
    return await api.testGeminiApiKey(apiKey);
  },

  getAvailableVoices: async () => {
    return await api.getAvailableVoices();
  },

  testVoice: async (data: api.VoiceTestRequest) => {
    return await api.testVoice(data);
  },

  getYouTubeChannel: async () => {
    return await api.getYouTubeChannel();
  },

  disconnectYouTube: async () => {
    try {
      await api.disconnectYouTube();
      await get().fetchSettings();
      await get().fetchServicesStatus();
      get().addToast('info', 'YouTube account succesvol ontkoppeld.');
    } catch {
      get().addToast('error', 'Kon YouTube account niet ontkoppelen');
    }
  },

  animateScene: async (sceneId: string, engine = 'veo', motionPrompt?: string) => {
    try {
      const res = await api.animateScene(sceneId, engine, motionPrompt);
      set((state) => ({
        scenes: state.scenes.map((sc) =>
          sc.id === sceneId
            ? {
                ...sc,
                video_clip_url: res.video_clip_url,
                video_clip_path: res.video_clip_path,
                animation_engine: res.animation_engine,
                motion_prompt: motionPrompt || sc.motion_prompt,
              }
            : sc
        ),
      }));
      get().addToast('success', res.message || 'Animatieclip gegenereerd!');
      return res;
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Animatie mislukt';
      get().addToast('error', msg);
      throw err;
    }
  },

  animateSceneLocal: async (sceneId: string) => {
    try {
      const res = await api.animateSceneLocal(sceneId);
      set((state) => ({
        scenes: state.scenes.map((sc) =>
          sc.id === sceneId
            ? {
                ...sc,
                video_clip_url: res.video_clip_url,
                video_clip_path: res.video_clip_path,
                animation_engine: 'local_2_5d',
              }
            : sc
        ),
      }));
      get().addToast('success', 'Lokale 60fps 2.5D animatie gereed!');
      return res;
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Lokale animatie mislukt';
      get().addToast('error', msg);
      throw err;
    }
  },

  animateEpisodeLocalBulk: async (episodeId: string) => {
    try {
      const res = await api.animateEpisodeLocalBulk(episodeId);
      await get().fetchScenes(episodeId);
      get().addToast('success', res.message || 'Bulk lokale animatie voltooid!');
      return res;
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Bulk animatie mislukt';
      get().addToast('error', msg);
      throw err;
    }
  },

  uploadSceneClip: async (sceneId: string, file: File) => {
    try {
      const res = await api.uploadSceneClip(sceneId, file);
      set((state) => ({
        scenes: state.scenes.map((sc) =>
          sc.id === sceneId
            ? {
                ...sc,
                video_clip_url: res.video_clip_url,
                video_clip_path: res.video_clip_path,
                animation_engine: 'manual_upload',
              }
            : sc
        ),
      }));
      get().addToast('success', 'Videoclip succesvol geüpload en gekoppeld!');
      return res;
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Upload mislukt';
      get().addToast('error', msg);
      throw err;
    }
  },

  generateSceneMotionPrompt: async (sceneId: string) => {
    try {
      const res = await api.generateSceneMotionPrompt(sceneId);
      set((state) => ({
        scenes: state.scenes.map((sc) =>
          sc.id === sceneId ? { ...sc, motion_prompt: res.motion_prompt } : sc
        ),
      }));
      get().addToast('success', 'Motion prompt gegenereerd!');
      return res.motion_prompt;
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Kon motion prompt niet genereren';
      get().addToast('error', msg);
      throw err;
    }
  },

  exportGoogleFlow: async (episodeId: string) => {
    try {
      const res = await api.exportGoogleFlow(episodeId);
      get().addToast('success', res.message || 'Google Flow export gereed!');
      if (res.zip_url) {
        window.open(res.zip_url, '_blank');
      }
      return res;
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Export mislukt';
      get().addToast('error', msg);
      throw err;
    }
  },

  uploadCharacterReference: async (characterId: string, file: File) => {
    try {
      const updated = await api.uploadCharacterReference(characterId, file);
      set((state) => ({
        characters: state.characters.map((c) => (c.id === characterId ? updated : c)),
      }));
      get().addToast('success', 'Referentie-afbeelding opgeslagen!');
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Upload mislukt';
      get().addToast('error', msg);
      throw err;
    }
  },

  deleteCharacterReference: async (characterId: string, index: number) => {
    try {
      const updated = await api.deleteCharacterReference(characterId, index);
      set((state) => ({
        characters: state.characters.map((c) => (c.id === characterId ? updated : c)),
      }));
      get().addToast('success', 'Referentie-afbeelding verwijderd');
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Verwijderen mislukt';
      get().addToast('error', msg);
      throw err;
    }
  },

  // ─── Task Progress ─────────────────────────────────────────────────────────

  trackTask: (taskId: string, onComplete?: () => void, onError?: () => void) => {
    const initialProgress: TaskProgress = {
      task_id: taskId,
      status: 'running',
      progress: 0,
      step: 'Starten…',
      message: '',
    };
    set((state) => ({
      activeTasks: { ...state.activeTasks, [taskId]: initialProgress },
      _taskCallbacks: {
        ...state._taskCallbacks,
        [taskId]: { onComplete, onError },
      },
    }));

    api.subscribeToTaskProgress(
      taskId,
      (progress) => {
        get().updateTaskProgress(taskId, progress);
      },
      () => {
        get().updateTaskProgress(taskId, {
          ...initialProgress,
          status: 'failed',
          message: 'Verbinding verloren',
        });
      }
    );
  },

  updateTaskProgress: (taskId: string, progress: TaskProgress) => {
    const callbacks = get()._taskCallbacks[taskId];
    set((state) => {
      const nextCallbacks = { ...state._taskCallbacks };
      if (progress.status === 'completed' || progress.status === 'failed') {
        delete nextCallbacks[taskId];
      }
      return {
        activeTasks: { ...state.activeTasks, [taskId]: progress },
        _taskCallbacks: nextCallbacks,
      };
    });
    if (progress.status === 'completed') {
      get().addToast('success', progress.message || 'Taak voltooid!');
      callbacks?.onComplete?.();
    } else if (progress.status === 'failed') {
      get().addToast('error', progress.message || 'Taak mislukt');
      callbacks?.onError?.();
    }
  },

  removeTask: (taskId: string) => {
    set((state) => {
      const tasks = { ...state.activeTasks };
      delete tasks[taskId];
      return { activeTasks: tasks };
    });
  },

  // ─── Toasts ────────────────────────────────────────────────────────────────

  addToast: (type: Toast['type'], message: string) => {
    const id = `toast_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    set((state) => ({
      toasts: [...state.toasts, { id, type, message }],
    }));
    setTimeout(() => {
      get().removeToast(id);
    }, 4000);
  },

  removeToast: (id: string) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }));
  },
}));
