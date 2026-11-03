import React from 'react';
import {
  Image as ImageIcon,
  Mic,
  Clock,
  Sparkles,
  Trash2,
  AlertTriangle,
  Video,
} from 'lucide-react';
import type { Scene } from '../api/client';
import { StatusBadge } from './StatusBadge';

interface SceneCardProps {
  scene: Scene;
  isSelected: boolean;
  onSelect: () => void;
  onGenerateImage: () => void;
  onGenerateAudio: () => void;
  onDelete: () => void;
  isGeneratingImage?: boolean;
  isGeneratingAudio?: boolean;
}

export const SceneCard: React.FC<SceneCardProps> = ({
  scene,
  isSelected,
  onSelect,
  onGenerateImage,
  onGenerateAudio,
  onDelete,
  isGeneratingImage = false,
  isGeneratingAudio = false,
}) => {
  return (
    <div
      onClick={onSelect}
      className={`group relative flex flex-col md:flex-row gap-4 p-4 rounded-2xl border transition-all duration-200 cursor-pointer ${
        isSelected
          ? 'bg-slate-800/90 border-indigo-500 shadow-xl shadow-indigo-500/10 ring-1 ring-indigo-500'
          : 'bg-slate-900/80 border-slate-800/80 hover:border-slate-700 hover:bg-slate-850'
      }`}
    >
      {/* Thumbnail / Image Preview */}
      <div className="relative w-full md:w-48 h-32 rounded-xl bg-slate-950 border border-slate-800 shrink-0 overflow-hidden flex items-center justify-center">
        {scene.image_url ? (
          <img
            src={scene.image_url}
            alt={scene.narration?.slice(0, 30) || 'Scène'}
            className="w-full h-full object-cover transition-transform group-hover:scale-105 duration-300"
          />
        ) : (
          <div className="flex flex-col items-center gap-1.5 text-slate-500">
            <ImageIcon className="w-8 h-8 opacity-40" />
            <span className="text-[11px] font-medium">Geen afbeelding</span>
          </div>
        )}

        {/* Scene number tag */}
        <div className="absolute top-2 left-2 px-2 py-0.5 rounded-md bg-slate-900/80 backdrop-blur-md border border-slate-700/60 text-xs font-bold text-slate-200">
          #{scene.order}
        </div>

        {/* Video Animation Badge */}
        {scene.video_clip_url && (
          <div className="absolute top-2 right-2 px-1.5 py-0.5 rounded-md bg-rose-600/90 text-white text-[10px] font-bold flex items-center gap-1 shadow-md">
            <Video className="w-2.5 h-2.5" />
            <span>Animatie</span>
          </div>
        )}

        {/* Duration tag */}
        <div className="absolute bottom-2 right-2 px-2 py-0.5 rounded-md bg-slate-900/80 backdrop-blur-md border border-slate-700/60 text-[11px] font-medium text-slate-300 flex items-center gap-1">
          <Clock className="w-3 h-3 text-amber-400" />
          <span>{scene.duration || 8}s</span>
        </div>
      </div>

      {/* Content & Narration */}
      <div className="flex-1 flex flex-col justify-between min-w-0">
        <div>
          <div className="flex items-center justify-between gap-2 mb-2">
            <div className="flex items-center gap-2 flex-wrap">
              <StatusBadge status={scene.status} />
              {scene.chapter_type && scene.chapter_type !== 'chapter' && (
                <span className="text-[10px] uppercase tracking-wide font-bold text-purple-300 bg-purple-500/10 border border-purple-500/20 px-1.5 py-0.5 rounded">
                  {scene.chapter_type}
                </span>
              )}
              <span className="text-xs text-slate-400 font-mono">
                {scene.animation_type} • {scene.transition_type}
              </span>
            </div>

            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors opacity-0 group-hover:opacity-100"
              title="Scène verwijderen"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>

          {/* Narration Preview */}
          <p className="text-sm text-slate-200 font-medium line-clamp-2 leading-relaxed mb-2">
            {scene.narration || <span className="italic text-slate-500">Nog geen gesproken tekst ingevoerd...</span>}
          </p>

          {/* Visual prompt snippet */}
          {scene.visual_prompt && (
            <p className="text-xs text-slate-400 line-clamp-1 italic bg-slate-950/40 px-2 py-1 rounded border border-slate-800/40">
              Prompt: {scene.visual_prompt}
            </p>
          )}

          {scene.guardrail_warnings?.length > 0 && (
            <div className="mt-2 flex items-start gap-1.5 text-[11px] text-amber-300 bg-amber-500/10 border border-amber-500/20 rounded-lg px-2 py-1.5">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span className="line-clamp-2">{scene.guardrail_warnings.join(' • ')}</span>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2 pt-3 mt-2 border-t border-slate-800/60 flex-wrap">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onGenerateImage();
            }}
            disabled={isGeneratingImage}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 text-xs font-semibold transition-colors disabled:opacity-50"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{isGeneratingImage ? 'Bezig...' : scene.image_url ? 'Opnieuw Beeld' : 'Genereer Beeld'}</span>
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              onGenerateAudio();
            }}
            disabled={isGeneratingAudio || !scene.narration}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/30 text-emerald-300 text-xs font-semibold transition-colors disabled:opacity-50"
          >
            <Mic className="w-3.5 h-3.5" />
            <span>{isGeneratingAudio ? 'Bezig...' : scene.audio_url ? 'Opnieuw Audio' : 'Genereer Audio'}</span>
          </button>

          {scene.audio_url && (
            <audio controls className="h-7 w-48 ml-auto" src={scene.audio_url}>
              Je browser ondersteunt geen audio afspelen.
            </audio>
          )}
        </div>
      </div>
    </div>
  );
};
