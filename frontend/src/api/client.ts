import axios, { AxiosInstance } from 'axios';

// ─── TypeScript Interfaces ───────────────────────────────────────────────────

export interface Project {
  id: string;
  name: string;
  description: string;
  target_age_min?: number;
  target_age_max?: number;
  language?: string;
  channel_name?: string;
  episode_count: number;
  character_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  description: string;
}

export interface Character {
  id: string;
  project_id: string;
  name: string;
  description: string;
  personality: string;
  voice_id: string;
  voice_provider?: string;
  voice_pitch?: string;
  voice_rate?: string;
  style_prompt: string;
  visual_dna_prompt?: string;
  color_palette?: string;
  sprite_base_path?: string | null;
  sprite_url: string | null;
  reference_images?: string[];
  reference_image_urls?: string[];
  expressions: CharacterExpression[];
  created_at: string;
  updated_at: string;
}

export interface CharacterExpression {
  id?: string;
  name: string;
  image_url: string | null;
  image_path?: string;
  mouth_open_url?: string | null;
  mouth_closed_url?: string | null;
  created_at?: string;
}

export interface CharacterCreate {
  project_id: string;
  name: string;
  description: string;
  personality: string;
  voice_id: string;
  voice_provider?: string;
  voice_pitch?: string;
  voice_rate?: string;
  style_prompt: string;
  visual_dna_prompt?: string;
}

export interface CharacterUpdate {
  name?: string;
  description?: string;
  personality?: string;
  voice_id?: string;
  voice_provider?: string;
  voice_pitch?: string;
  voice_rate?: string;
  style_prompt?: string;
  visual_dna_prompt?: string;
}

export interface Episode {
  id: string;
  project_id: string;
  title: string;
  description: string;
  episode_number?: number;
  seo_title: string;
  seo_description: string;
  seo_tags: string;
  thumbnail_prompt: string;
  thumbnail_path: string | null;
  target_audience?: 'kids' | 'general';
  made_for_kids?: boolean;
  bg_music_path: string;
  target_duration: number;
  target_duration_seconds: number;
  script_raw: string;
  script_final: string;
  status: EpisodeStatus;
  scene_count: number;
  render_url: string | null;
  youtube_url: string | null;
  youtube_video_id: string;
  guardrail_warnings: string[];
  created_at: string;
  updated_at: string;
}

export type EpisodeStatus =
  | 'draft'
  | 'scripted'
  | 'scripting'
  | 'scenes'
  | 'audio'
  | 'rendering'
  | 'rendered'
  | 'published';

export interface EpisodeCreate {
  project_id: string;
  title: string;
  description: string;
  target_audience?: 'kids' | 'general';
  made_for_kids?: boolean;
}

export interface EpisodeUpdate {
  title?: string;
  description?: string;
  seo_title?: string;
  seo_description?: string;
  seo_tags?: string;
  thumbnail_prompt?: string;
  bg_music_path?: string;
  target_audience?: 'kids' | 'general';
  made_for_kids?: boolean;
  target_duration?: number;
  target_duration_seconds?: number;
  status?: EpisodeStatus;
}

export interface SceneCharacterItem {
  character_id: string;
  name: string;
  position: 'left' | 'center' | 'right';
  emotion: string;
}

export interface SceneHistoryItem {
  path: string;
  url: string | null;
  prompt: string;
  created_at: string;
}

export interface WordTimestamp {
  word: string;
  start: number;
  end: number;
  probability?: number;
}

export interface Scene {
  id: string;
  episode_id: string;
  scene_number: number;
  order: number;
  title: string;
  chapter_type: string;
  speaker: string;
  active_speaker?: string;
  narration_text: string;
  narration: string;
  phonetic_text: string;
  visual_prompt: string;
  background_prompt: string;
  image_prompt: string;
  motion_prompt?: string;
  video_clip_path?: string | null;
  video_clip_url?: string | null;
  animation_engine?: string;
  character_ids: string[];
  characters_in_scene?: SceneCharacterItem[];
  character_positions: string;
  animation_type: AnimationType;
  transition_type: TransitionType;
  use_2d_sprite: boolean;
  sprite_config_json: string;
  sfx_track: string;
  duration_seconds: number;
  pause_after_sec: number;
  duration: number;
  background_image_path: string | null;
  composite_image_path: string | null;
  image_url: string | null;
  image_history: SceneHistoryItem[];
  audio_path: string | null;
  audio_url: string | null;
  word_timestamps: WordTimestamp[];
  start_time: number;
  status: SceneStatus;
  guardrail_warnings: string[];
  created_at: string;
  updated_at: string;
}

export type AnimationType =
  | 'ken_burns'
  | 'none'
  | 'static'
  | 'pan_left'
  | 'pan_right'
  | 'zoom_in'
  | 'zoom_out'
  | 'fade';
export type TransitionType =
  | 'cut'
  | 'fade'
  | 'dissolve'
  | 'crossfade'
  | 'wipe'
  | 'circle_wipe'
  | 'slide'
  | 'slide_left'
  | 'slide_right'
  | 'fade_black'
  | 'fade_white';
export type SceneStatus = 'draft' | 'image_generated' | 'audio_generated' | 'complete';

export interface SceneCreate {
  episode_id: string;
  order: number;
  title?: string;
  chapter_type?: string;
  speaker?: string;
  active_speaker?: string;
  narration: string;
  phonetic_text?: string;
  visual_prompt: string;
  background_prompt?: string;
  image_prompt?: string;
  motion_prompt?: string;
  video_clip_path?: string | null;
  animation_engine?: string;
  character_ids?: string[];
  characters_in_scene?: SceneCharacterItem[];
  animation_type?: AnimationType;
  transition_type?: TransitionType;
  duration?: number;
  pause_after_sec?: number;
  use_2d_sprite?: boolean;
}

export interface SceneUpdate {
  order?: number;
  title?: string;
  chapter_type?: string;
  speaker?: string;
  active_speaker?: string;
  narration?: string;
  phonetic_text?: string;
  visual_prompt?: string;
  background_prompt?: string;
  image_prompt?: string;
  motion_prompt?: string;
  video_clip_path?: string | null;
  animation_engine?: string;
  character_ids?: string[];
  characters_in_scene?: SceneCharacterItem[];
  animation_type?: AnimationType;
  transition_type?: TransitionType;
  duration?: number;
  duration_seconds?: number;
  pause_after_sec?: number;
  use_2d_sprite?: boolean;
  sfx_track?: string;
}

export interface SceneReorder {
  scene_id: string;
  order: number;
}

export interface GenerateScriptRequest {
  episode_id: string;
  topic: string;
  target_duration?: number;
  character_ids?: string[];
}

export interface GenerateImageRequest {
  scene_id: string;
  prompt?: string;
  provider?: string;
  width?: number;
  height?: number;
  use_2d_sprite?: boolean;
  enhance_prompt?: boolean;
}

export interface GenerateAudioRequest {
  scene_id: string;
  provider?: string;
  voice_id?: string;
  text?: string;
}

export interface GuardrailIssue {
  level: 'warning' | 'error';
  message: string;
  scene_id?: string | null;
  scene_number?: number | null;
}

export interface EpisodeGuardrails {
  passed: boolean;
  safety_score: number;
  total_duration_seconds: number;
  scene_count: number;
  issues: GuardrailIssue[];
}

export interface GeneratedSeo {
  seo_title: string;
  seo_description: string;
  seo_tags: string;
  thumbnail_prompt: string;
}

export interface GeneratedThumbnail {
  thumbnail_path: string;
  thumbnail_url: string;
}

export interface GeneratedImagePrompt {
  scene_id: string;
  prompt: string;
}

export interface SceneImageLibrary {
  scene_id: string;
  current: string | null;
  history: SceneHistoryItem[];
}

export interface RenderRequest {
  episode_id: string;
  resolution: string;
  fps: number;
}

export interface PublishRequest {
  episode_id: string;
  privacy_status: 'public' | 'unlisted' | 'private';
  made_for_kids: boolean;
}

export interface ServiceStatus {
  name: string;
  connected: boolean;
  message: string;
}

export interface Settings {
  gemini_api_key: string;
  gemini_api_key_set?: boolean;
  gemini_model?: string;
  gemini_text_model?: string;
  gemini_image_model?: string;
  gemini_video_model?: string;
  discovered_models?: {
    text_models?: string[];
    image_models?: string[];
    video_models?: string[];
    tts_models?: string[];
  };
  default_image_provider?: string;
  wan_api_url?: string;
  wan_api_key?: string;
  ollama_url: string;
  sd_webui_url: string;
  piper_path: string;
  kokoro_url: string;
  youtube_client_id: string;
  youtube_client_secret: string;
}

export interface GeminiTestResponse {
  valid: boolean;
  status_code: number;
  models: string[];
  text_models: string[];
  image_models: string[];
  video_models?: string[];
  tts_models?: string[];
  message: string;
  error?: string | null;
}

export interface VoiceItem {
  id: string;
  name: string;
  gender: string;
  language: string;
  recommended: boolean;
}

export type VoicesMap = Record<string, VoiceItem[]>;

export interface VoiceTestRequest {
  voice_id: string;
  voice_provider: string;
  text: string;
  pitch?: string;
  rate?: string;
}

export interface VoiceTestResponse {
  audio_url: string;
  duration_seconds: number;
  voice_id: string;
  message: string;
}

export interface YouTubeChannelResponse {
  connected: boolean;
  id?: string | null;
  title?: string | null;
  description?: string | null;
  custom_url?: string | null;
  avatar_url?: string | null;
  subscriber_count?: string | null;
  video_count?: string | null;
}

export interface TaskProgress {
  task_id: string;
  status: 'running' | 'completed' | 'failed';
  progress: number;
  step: string;
  message: string;
}

export interface TestConnectionResponse {
  service: string;
  connected: boolean;
  message: string;
}

export interface YouTubeAuthUrl {
  auth_url: string;
}

export interface AnimateSceneRequest {
  animation_engine?: string;
  motion_prompt?: string;
}

export interface AnimateSceneResponse {
  scene_id: string;
  video_clip_url: string;
  video_clip_path: string;
  duration: number;
  animation_engine: string;
  message: string;
}

export interface ExportFlowResponse {
  zip_url: string;
  zip_path: string;
  scene_count: number;
  message: string;
}

// ─── API Client ──────────────────────────────────────────────────────────────

const client: AxiosInstance = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// ─── Projects ────────────────────────────────────────────────────────────────

export async function getProjects(): Promise<Project[]> {
  const res = await client.get<Project[]>('/projects');
  return res.data;
}

export async function getProject(id: string): Promise<Project> {
  const res = await client.get<Project>(`/projects/${id}`);
  return res.data;
}

export async function createProject(data: ProjectCreate): Promise<Project> {
  const res = await client.post<Project>('/projects', data);
  return res.data;
}

export async function updateProject(id: string, data: Partial<ProjectCreate>): Promise<Project> {
  const res = await client.put<Project>(`/projects/${id}`, data);
  return res.data;
}

export async function deleteProject(id: string): Promise<void> {
  await client.delete(`/projects/${id}`);
}

// ─── Characters ──────────────────────────────────────────────────────────────

export async function getCharacters(projectId: string): Promise<Character[]> {
  const res = await client.get<Character[]>(`/projects/${projectId}/characters`);
  return res.data;
}

export async function getCharacter(id: string): Promise<Character> {
  const res = await client.get<Character>(`/characters/${id}`);
  return res.data;
}

export async function createCharacter(data: CharacterCreate): Promise<Character> {
  const res = await client.post<Character>('/characters', data);
  return res.data;
}

export async function updateCharacter(id: string, data: CharacterUpdate): Promise<Character> {
  const res = await client.put<Character>(`/characters/${id}`, data);
  return res.data;
}

export async function deleteCharacter(id: string): Promise<void> {
  await client.delete(`/characters/${id}`);
}

export async function generateSprite(
  characterId: string,
  emotion = 'blij'
): Promise<{ task_id: string; detail?: string }> {
  const res = await client.post<{ task_id: string; detail?: string }>(
    `/characters/${characterId}/generate-sprite`,
    undefined,
    { params: { emotion } }
  );
  return res.data;
}

export async function uploadExpression(
  characterId: string,
  name: string,
  file: File
): Promise<CharacterExpression> {
  const formData = new FormData();
  formData.append('name', name);
  formData.append('file', file);
  const res = await client.post<CharacterExpression>(
    `/characters/${characterId}/expressions`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  );
  return res.data;
}

// ─── Episodes ────────────────────────────────────────────────────────────────

export async function getEpisodes(projectId: string): Promise<Episode[]> {
  const res = await client.get<Episode[]>(`/projects/${projectId}/episodes`);
  return res.data;
}

export async function getEpisode(id: string): Promise<Episode> {
  const res = await client.get<Episode>(`/episodes/${id}`);
  return res.data;
}

export async function createEpisode(data: EpisodeCreate): Promise<Episode> {
  const res = await client.post<Episode>('/episodes', data);
  return res.data;
}

export async function updateEpisode(id: string, data: EpisodeUpdate): Promise<Episode> {
  const res = await client.put<Episode>(`/episodes/${id}`, data);
  return res.data;
}

export async function deleteEpisode(id: string): Promise<void> {
  await client.delete(`/episodes/${id}`);
}

// ─── Scenes ──────────────────────────────────────────────────────────────────

export async function getScenes(episodeId: string): Promise<Scene[]> {
  const res = await client.get<Scene[]>(`/episodes/${episodeId}/scenes`);
  return res.data;
}

export async function getScene(id: string): Promise<Scene> {
  const res = await client.get<Scene>(`/scenes/${id}`);
  return res.data;
}

export async function createScene(data: SceneCreate): Promise<Scene> {
  const res = await client.post<Scene>('/scenes', data);
  return res.data;
}

export async function updateScene(id: string, data: SceneUpdate): Promise<Scene> {
  const res = await client.put<Scene>(`/scenes/${id}`, data);
  return res.data;
}

export async function deleteScene(id: string): Promise<void> {
  await client.delete(`/scenes/${id}`);
}

export async function reorderScenes(episodeId: string, order: SceneReorder[]): Promise<Scene[]> {
  const res = await client.put<Scene[]>(`/episodes/${episodeId}/scenes/reorder`, order);
  return res.data;
}

// ─── Generation ──────────────────────────────────────────────────────────────

export async function generateScript(data: GenerateScriptRequest): Promise<{ task_id: string }> {
  const res = await client.post<{ task_id: string }>('/generate/script', data);
  return res.data;
}

export async function generateImage(data: GenerateImageRequest): Promise<{ task_id: string }> {
  const res = await client.post<{ task_id: string }>('/generate/image', data);
  return res.data;
}

export async function generateAudio(data: GenerateAudioRequest): Promise<{ task_id: string }> {
  const res = await client.post<{ task_id: string }>('/generate/audio', data);
  return res.data;
}

export async function generateBulkAudio(
  episodeId: string,
  provider?: string
): Promise<{ task_id: string; scene_count: number }> {
  const res = await client.post<{ task_id: string; scene_count: number }>(
    `/generate/episodes/${episodeId}/audio`,
    undefined,
    { params: provider ? { provider } : undefined }
  );
  return res.data;
}

export async function generateImagePrompt(
  sceneId: string,
  prompt?: string
): Promise<GeneratedImagePrompt> {
  const res = await client.post<GeneratedImagePrompt>('/generate/image/prompt', {
    scene_id: sceneId,
    prompt,
  });
  return res.data;
}

export async function generateEpisodeSeo(episodeId: string): Promise<GeneratedSeo> {
  const res = await client.post<GeneratedSeo>(`/generate/episodes/${episodeId}/seo`);
  return res.data;
}

export async function generateEpisodeThumbnail(
  episodeId: string,
  prompt?: string,
  provider = 'sdwebui'
): Promise<GeneratedThumbnail> {
  const res = await client.post<GeneratedThumbnail>(
    `/generate/episodes/${episodeId}/thumbnail`,
    { prompt, provider }
  );
  return res.data;
}

export async function getEpisodeGuardrails(episodeId: string): Promise<EpisodeGuardrails> {
  const res = await client.get<EpisodeGuardrails>(`/episodes/${episodeId}/guardrails`);
  return res.data;
}

export async function getSceneImages(sceneId: string): Promise<SceneImageLibrary> {
  const res = await client.get<SceneImageLibrary>(`/scenes/${sceneId}/images`);
  return res.data;
}

export async function selectSceneImage(sceneId: string, path: string): Promise<Scene> {
  const res = await client.post<Scene>(`/scenes/${sceneId}/select-image`, { path });
  return res.data;
}

export async function uploadSceneAudio(sceneId: string, file: File): Promise<Scene> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await client.post<Scene>(`/scenes/${sceneId}/audio/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

// ─── Render & Publish ────────────────────────────────────────────────────────

export async function startRender(data: RenderRequest): Promise<{ task_id: string }> {
  const res = await client.post<{ task_id: string }>('/render', data);
  return res.data;
}

export async function publishToYouTube(data: PublishRequest): Promise<{ task_id: string }> {
  const res = await client.post<{ task_id: string }>('/publish/youtube', data);
  return res.data;
}

export async function getYouTubeAuthUrl(): Promise<YouTubeAuthUrl> {
  const res = await client.get<YouTubeAuthUrl>('/auth/youtube/url');
  return res.data;
}

// ─── Settings ────────────────────────────────────────────────────────────────

export async function getSettings(): Promise<Settings> {
  const res = await client.get<Settings>('/settings');
  return res.data;
}

export async function saveSettings(data: Partial<Settings>): Promise<Settings> {
  const res = await client.put<Settings>('/settings', data);
  return res.data;
}

export async function testConnection(service: string): Promise<TestConnectionResponse> {
  const res = await client.post<TestConnectionResponse>(`/settings/test/${service}`);
  return res.data;
}

export async function getServicesStatus(): Promise<ServiceStatus[]> {
  const res = await client.get<ServiceStatus[]>('/settings/status');
  return res.data;
}

export async function testGeminiApiKey(apiKey?: string): Promise<GeminiTestResponse> {
  const res = await client.post<GeminiTestResponse>('/setup/test-gemini', {
    api_key: apiKey,
  });
  return res.data;
}

export async function getAvailableVoices(): Promise<VoicesMap> {
  const res = await client.get<VoicesMap>('/audio/voices');
  return res.data;
}

export async function testVoice(data: VoiceTestRequest): Promise<VoiceTestResponse> {
  const res = await client.post<VoiceTestResponse>('/audio/test-voice', data);
  return res.data;
}

export async function getYouTubeChannel(): Promise<YouTubeChannelResponse> {
  const res = await client.get<YouTubeChannelResponse>('/setup/youtube-channel');
  return res.data;
}

export async function disconnectYouTube(): Promise<{ detail: string }> {
  const res = await client.post<{ detail: string }>('/setup/youtube-disconnect');
  return res.data;
}

// ─── Image-to-Video Animatie & Google Flow ───────────────────────────────────

export async function animateScene(
  sceneId: string,
  engine: string = 'veo',
  motionPrompt?: string
): Promise<AnimateSceneResponse> {
  const res = await client.post<AnimateSceneResponse>(`/scenes/${sceneId}/animate`, {
    animation_engine: engine,
    motion_prompt: motionPrompt,
  });
  return res.data;
}

export async function animateSceneLocal(sceneId: string): Promise<AnimateSceneResponse> {
  const res = await client.post<AnimateSceneResponse>(`/scenes/${sceneId}/animate-local`);
  return res.data;
}

export async function animateEpisodeLocalBulk(episodeId: string): Promise<{
  episode_id: string;
  success_count: number;
  skipped_count: number;
  message: string;
}> {
  const res = await client.post<{
    episode_id: string;
    success_count: number;
    skipped_count: number;
    message: string;
  }>(`/episodes/${episodeId}/animate-local-bulk`);
  return res.data;
}

export async function getDiscoveredModels(): Promise<{
  text_models: string[];
  image_models: string[];
  video_models: string[];
  tts_models: string[];
}> {
  const res = await client.get<{
    text_models: string[];
    image_models: string[];
    video_models: string[];
    tts_models: string[];
  }>('/setup/models');
  return res.data;
}

export async function uploadSceneClip(sceneId: string, file: File): Promise<AnimateSceneResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await client.post<AnimateSceneResponse>(`/scenes/${sceneId}/upload-clip`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

export async function generateSceneMotionPrompt(
  sceneId: string
): Promise<{ scene_id: string; motion_prompt: string }> {
  const res = await client.post<{ scene_id: string; motion_prompt: string }>(
    `/scenes/${sceneId}/generate-motion-prompt`
  );
  return res.data;
}

export async function exportGoogleFlow(episodeId: string): Promise<ExportFlowResponse> {
  const res = await client.get<ExportFlowResponse>(`/episodes/${episodeId}/export-flow`);
  return res.data;
}

export async function uploadCharacterReference(characterId: string, file: File): Promise<Character> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await client.post<Character>(`/characters/${characterId}/upload-reference`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

export async function deleteCharacterReference(characterId: string, index: number): Promise<Character> {
  const res = await client.delete<Character>(`/characters/${characterId}/reference/${index}`);
  return res.data;
}

// ─── SSE Task Progress ──────────────────────────────────────────────────────

export function subscribeToTaskProgress(
  taskId: string,
  onProgress: (data: TaskProgress) => void,
  onError?: (error: Event) => void
): () => void {
  const url = `/api/tasks/${taskId}/progress`;
  const eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    try {
      const data: TaskProgress = JSON.parse(event.data);
      onProgress(data);
      if (data.status === 'completed' || data.status === 'failed') {
        eventSource.close();
      }
    } catch {
      // ignore parse errors
    }
  };

  eventSource.onerror = (event) => {
    if (onError) {
      onError(event);
    }
    eventSource.close();
  };

  return () => {
    eventSource.close();
  };
}
