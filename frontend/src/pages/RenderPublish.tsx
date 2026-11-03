import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Film,
  Video,
  UploadCloud,
  CheckCircle2,
  ExternalLink,
  ShieldCheck,
  ArrowLeft,
  Tags,
  Music,
  Image as ImageIcon,
  Save,
  Sparkles,
  AlertTriangle,
} from 'lucide-react';
import { useStore } from '../store/useStore';
import { TaskProgress } from '../components/TaskProgress';
import { StatusBadge } from '../components/StatusBadge';
import { getYouTubeAuthUrl } from '../api/client';

export const RenderPublish: React.FC = () => {
  const { id: episodeId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const {
    currentEpisode,
    fetchEpisode,
    scenes,
    fetchScenes,
    startRender,
    publishToYouTube,
    updateEpisode,
    generateEpisodeSeo,
    generateEpisodeThumbnail,
  } = useStore();

  const [resolution, setResolution] = useState('1920x1080');
  const [fps, setFps] = useState(30);
  const [activeRenderTaskId, setActiveRenderTaskId] = useState<string | null>(null);

  const [privacyStatus, setPrivacyStatus] = useState<'public' | 'unlisted' | 'private'>('private');
  const [madeForKids, setMadeForKids] = useState(true);
  const [activePublishTaskId, setActivePublishTaskId] = useState<string | null>(null);
  const [publishedUrl, setPublishedUrl] = useState<string | null>(null);

  const [seoTitle, setSeoTitle] = useState('');
  const [seoDescription, setSeoDescription] = useState('');
  const [seoTags, setSeoTags] = useState('');
  const [bgMusicPath, setBgMusicPath] = useState('');
  const [isGeneratingSeo, setIsGeneratingSeo] = useState(false);
  const [isGeneratingThumbnail, setIsGeneratingThumbnail] = useState(false);

  useEffect(() => {
    if (episodeId) {
      fetchEpisode(episodeId);
      fetchScenes(episodeId);
    }
  }, [episodeId, fetchEpisode, fetchScenes]);

  useEffect(() => {
    if (currentEpisode?.youtube_url) {
      setPublishedUrl(currentEpisode.youtube_url);
    }
  }, [currentEpisode]);

  useEffect(() => {
    if (currentEpisode) {
      setSeoTitle(currentEpisode.seo_title || '');
      setSeoDescription(currentEpisode.seo_description || '');
      setSeoTags(currentEpisode.seo_tags || '');
      setBgMusicPath(currentEpisode.bg_music_path || '');
    }
  }, [currentEpisode]);

  const handleGenerateSeo = async () => {
    if (!episodeId) return;
    setIsGeneratingSeo(true);
    try {
      const seo = await generateEpisodeSeo(episodeId);
      setSeoTitle(seo.seo_title);
      setSeoDescription(seo.seo_description);
      setSeoTags(seo.seo_tags);
    } finally {
      setIsGeneratingSeo(false);
    }
  };

  const handleSaveMetadata = async () => {
    if (!episodeId) return;
    await updateEpisode(episodeId, {
      seo_title: seoTitle,
      seo_description: seoDescription,
      seo_tags: seoTags,
      bg_music_path: bgMusicPath,
    });
  };

  const handleGenerateThumbnail = async () => {
    if (!episodeId) return;
    setIsGeneratingThumbnail(true);
    try {
      await generateEpisodeThumbnail(episodeId, currentEpisode?.thumbnail_prompt);
    } finally {
      setIsGeneratingThumbnail(false);
    }
  };

  const thumbnailUrl = (() => {
    if (!currentEpisode?.thumbnail_path) return null;
    const filename = currentEpisode.thumbnail_path.split(/[\\/]/).pop();
    return filename ? `/media/images/${filename}` : null;
  })();

  const handleStartRender = async () => {
    if (!episodeId) return;
    const taskId = await startRender(episodeId, resolution, fps);
    setActiveRenderTaskId(taskId);
  };

  const handleStartPublish = async () => {
    if (!episodeId) return;
    const taskId = await publishToYouTube(episodeId, privacyStatus, madeForKids);
    setActivePublishTaskId(taskId);
  };

  const handleConnectYouTube = async () => {
    try {
      const res = await getYouTubeAuthUrl();
      if (res.auth_url) {
        window.open(res.auth_url, '_blank');
      }
    } catch (e) {
      alert('Configureer eerst YouTube Client ID & Secret in het Setup Centrum.');
    }
  };

  const isRendered = currentEpisode?.status === 'rendered' || currentEpisode?.render_url;

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8 animate-in fade-in duration-300">
      {/* Top Header */}
      <div className="flex items-center justify-between pb-6 border-b border-slate-800">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(`/episodes/${episodeId}`)}
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Terug naar Studio"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
              <Film className="w-8 h-8 text-indigo-400" />
              <span>Renderen & Publiceren</span>
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Aflevering: <strong className="text-slate-200">{currentEpisode?.title}</strong> ({scenes.length} scènes)
            </p>
          </div>
        </div>

        {currentEpisode && <StatusBadge status={currentEpisode.status} size="md" />}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Left Column: FFmpeg Video Rendering */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-6 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center gap-3 pb-3 border-b border-slate-800">
              <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                <Video className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-slate-100">1. Video Master Renderen</h3>
                <p className="text-xs text-slate-400">
                  FFmpeg 2.5D Ken Burns, overgangen, lip-sync en -14 LUFS mastering.
                </p>
              </div>
            </div>

            {/* Video Player Preview if Rendered */}
            {currentEpisode?.render_url && (
              <div className="w-full rounded-xl overflow-hidden bg-black border border-slate-800 aspect-video flex items-center justify-center">
                <video
                  controls
                  className="w-full h-full object-contain"
                  src={currentEpisode.render_url}
                >
                  Je browser ondersteunt geen video tags.
                </video>
              </div>
            )}

            {/* Render Settings */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-300 mb-1">Resolutie</label>
                <select
                  value={resolution}
                  onChange={(e) => setResolution(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-200 font-mono"
                >
                  <option value="1920x1080">1080p Full HD (16:9)</option>
                  <option value="1280x720">720p HD</option>
                  <option value="1080x1920">1080x1920 (YouTube Shorts)</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">Framerate (FPS)</label>
                <select
                  value={fps}
                  onChange={(e) => setFps(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-200 font-mono"
                >
                  <option value={30}>30 FPS (Standaard)</option>
                  <option value={60}>60 FPS (Ultra Vloeiend)</option>
                  <option value={24}>24 FPS (Cinematic)</option>
                </select>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60 text-xs text-slate-300 space-y-1">
              <div className="font-semibold text-slate-200">Inbegrepen Mastering Regels:</div>
              <ul className="list-disc list-inside text-slate-400 space-y-0.5">
                <li>Sidechain ducking: muziek dempt automatisch bij stemgeluid</li>
                <li>EBU R128 (-14 LUFS) volume-normalisatie voor YouTube</li>
                <li>Faststart mp4 flags voor directe streaming</li>
              </ul>
            </div>
          </div>

          <div className="space-y-3 pt-4 border-t border-slate-800">
            {activeRenderTaskId && (
              <TaskProgress
                taskId={activeRenderTaskId}
                onComplete={() => {
                  if (episodeId) fetchEpisode(episodeId);
                  setActiveRenderTaskId(null);
                }}
              />
            )}

            <button
              onClick={handleStartRender}
              disabled={!!activeRenderTaskId || scenes.length === 0}
              className="w-full flex items-center justify-center gap-2 py-3 px-5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm shadow-lg shadow-indigo-600/25 active:scale-95 transition-all disabled:opacity-50"
            >
              <Film className="w-4 h-4" />
              <span>{isRendered ? 'Opnieuw Renderen' : 'Start Video Render'}</span>
            </button>
          </div>
        </div>

        {/* Right Column: YouTube Kids Publication */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-6 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center gap-3 pb-3 border-b border-slate-800">
              <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
                <UploadCloud className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-slate-100">2. YouTube Kids Publiceren</h3>
                <p className="text-xs text-slate-400">
                  Resumable upload met strikte COPPA 'Made for Kids' certificering.
                </p>
              </div>
            </div>

            {/* Publication Settings */}
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Zichtbaarheid (Privacy)
                </label>
                <select
                  value={privacyStatus}
                  onChange={(e) => setPrivacyStatus(e.target.value as any)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-sm font-medium"
                >
                  <option value="private">Privé (Alleen jij kunt kijken)</option>
                  <option value="unlisted">Verborgen (Iedereen met de link)</option>
                  <option value="public">Openbaar (Direct online voor publiek)</option>
                </select>
              </div>

              {/* Made for Kids COPPA Checkbox */}
              <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-3">
                <ShieldCheck className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                <div className="text-xs space-y-1">
                  <label className="font-bold text-amber-200 flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={madeForKids}
                      onChange={(e) => setMadeForKids(e.target.checked)}
                      className="rounded accent-amber-500 cursor-pointer"
                    />
                    <span>Made for Kids (Verplicht voor kindercontent)</span>
                  </label>
                  <p className="text-amber-300/80 leading-relaxed">
                    Stelt <code className="font-mono text-amber-200">selfDeclaredMadeForKids=true</code> in via de YouTube API conform COPPA-wetgeving.
                  </p>
                </div>
              </div>

              {/* YouTube OAuth Connect Button */}
              <button
                type="button"
                onClick={handleConnectYouTube}
                className="w-full flex items-center justify-between p-3 rounded-xl bg-slate-800 hover:bg-slate-750 border border-slate-700 text-xs text-slate-300 transition-colors"
              >
                <span className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                  <span>YouTube OAuth Kanaal Koppelingsstatus</span>
                </span>
                <span className="text-indigo-400 font-semibold flex items-center gap-1">
                  Opnieuw Koppelen <ExternalLink className="w-3 h-3" />
                </span>
              </button>
            </div>

            {/* Published Link Result */}
            {publishedUrl && (
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-emerald-400">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Succesvol Gepubliceerd op YouTube!</span>
                </div>
                <a
                  href={publishedUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-indigo-300 hover:underline flex items-center gap-1 font-mono truncate"
                >
                  <span>{publishedUrl}</span>
                  <ExternalLink className="w-3 h-3 shrink-0" />
                </a>
              </div>
            )}
          </div>

          <div className="space-y-3 pt-4 border-t border-slate-800">
            {activePublishTaskId && (
              <TaskProgress
                taskId={activePublishTaskId}
                onComplete={() => {
                  if (episodeId) fetchEpisode(episodeId);
                  setActivePublishTaskId(null);
                }}
              />
            )}

            <button
              onClick={handleStartPublish}
              disabled={!!activePublishTaskId || !isRendered}
              className="w-full flex items-center justify-center gap-2 py-3 px-5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-sm shadow-lg shadow-rose-600/25 active:scale-95 transition-all disabled:opacity-50"
            >
              <UploadCloud className="w-4 h-4" />
              <span>{isRendered ? 'Uploaden naar YouTube Kids' : 'Render eerst de video'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* SEO / GEO metadata & thumbnail */}
      <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
              <Tags className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-slate-100">3. SEO / GEO & Thumbnail</h3>
              <p className="text-xs text-slate-400">
                YouTube Kids metadata, AI-samenvatting en een pakkende thumbnail.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleGenerateSeo}
              disabled={isGeneratingSeo || !currentEpisode?.script_final}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-colors disabled:opacity-50"
            >
              <Sparkles className={`w-3.5 h-3.5 ${isGeneratingSeo ? 'animate-spin' : ''}`} />
              <span>{isGeneratingSeo ? 'Genereren…' : 'Genereer SEO'}</span>
            </button>
            <button
              onClick={handleSaveMetadata}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-bold transition-colors"
            >
              <Save className="w-3.5 h-3.5" />
              <span>Opslaan</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div className="md:col-span-2 space-y-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-300 mb-1">SEO Titel</label>
              <input
                type="text"
                value={seoTitle}
                onChange={(e) => setSeoTitle(e.target.value)}
                placeholder="Pakkende YouTube-titel met emoji"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1">
                SEO Beschrijving (inclusief AI-samenvatting & hoofdstukken)
              </label>
              <textarea
                rows={7}
                value={seoDescription}
                onChange={(e) => setSeoDescription(e.target.value)}
                placeholder="Educatieve beschrijving met leerdoelen en tijdstempels…"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1">
                Tags (komma-gescheiden)
              </label>
              <input
                type="text"
                value={seoTags}
                onChange={(e) => setSeoTags(e.target.value)}
                placeholder="kleuters, leren tellen, kinderliedjes"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100"
              />
            </div>

            <div>
              <label className="flex items-center gap-1.5 font-semibold text-slate-300 mb-1">
                <Music className="w-3.5 h-3.5 text-emerald-400" />
                <span>Achtergrondmuziek pad (optioneel)</span>
              </label>
              <input
                type="text"
                value={bgMusicPath}
                onChange={(e) => setBgMusicPath(e.target.value)}
                placeholder="/media/audio/mijn-vrolijke-muziek.mp3"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 font-mono"
              />
              <p className="text-[11px] text-slate-500 mt-1">
                Wordt bij de render automatisch geduckt onder de stem en op -14 LUFS gemasterd.
              </p>
            </div>
          </div>

          <div className="space-y-3">
            <div className="aspect-video rounded-xl bg-slate-950 border border-slate-800 overflow-hidden flex items-center justify-center">
              {thumbnailUrl ? (
                <img
                  src={thumbnailUrl}
                  alt="YouTube thumbnail"
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="flex flex-col items-center gap-1.5 text-slate-500 text-xs">
                  <ImageIcon className="w-8 h-8 opacity-40" />
                  <span>Nog geen thumbnail</span>
                </div>
              )}
            </div>
            <button
              onClick={handleGenerateThumbnail}
              disabled={isGeneratingThumbnail || !currentEpisode?.thumbnail_prompt}
              className="w-full flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-amber-600/20 hover:bg-amber-600/30 border border-amber-500/40 text-amber-200 font-bold text-xs transition-colors disabled:opacity-50"
            >
              <ImageIcon className="w-3.5 h-3.5" />
              <span>{isGeneratingThumbnail ? 'Thumbnail genereren…' : 'Genereer Thumbnail'}</span>
            </button>
            {!currentEpisode?.thumbnail_prompt && (
              <p className="text-[11px] text-slate-500">
                Genereer eerst SEO om een thumbnail-prompt te maken.
              </p>
            )}
          </div>
        </div>

        {currentEpisode?.guardrail_warnings && currentEpisode.guardrail_warnings.length > 0 && (
          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/25 text-amber-200">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider mb-2">
              <AlertTriangle className="w-4 h-4" />
              <span>Guardrail waarschuwingen</span>
            </div>
            <ul className="text-[11px] space-y-1 list-disc list-inside text-amber-200/90">
              {currentEpisode.guardrail_warnings.slice(0, 8).map((warning, idx) => (
                <li key={idx}>{warning}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};
