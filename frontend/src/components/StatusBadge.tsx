import React from 'react';
import {
  FileText,
  Clock,
  CheckCircle2,
  AlertCircle,
  Video,
  UploadCloud,
  Sparkles,
} from 'lucide-react';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'sm' }) => {
  const s = (status || '').toLowerCase();

  let label = status;
  let bg = 'bg-slate-700/50 text-slate-300 border-slate-600/50';
  let Icon = Clock;

  switch (s) {
    case 'draft':
      label = 'Concept';
      bg = 'bg-slate-700/60 text-slate-300 border-slate-600/50';
      Icon = FileText;
      break;
    case 'scripting':
    case 'scripted':
      label = 'Script Klaar';
      bg = 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      Icon = Sparkles;
      break;
    case 'image_generated':
      label = 'Beeld Klaar';
      bg = 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      Icon = CheckCircle2;
      break;
    case 'audio_generated':
      label = 'Audio Klaar';
      bg = 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30';
      Icon = CheckCircle2;
      break;
    case 'rendering':
    case 'generating':
      label = 'Bezig met Renderen';
      bg = 'bg-amber-500/20 text-amber-300 border-amber-500/40 animate-pulse';
      Icon = Clock;
      break;
    case 'rendered':
      label = 'Gerenderd';
      bg = 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
      Icon = Video;
      break;
    case 'complete':
      label = 'Klaar';
      bg = 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
      Icon = CheckCircle2;
      break;
    case 'uploading':
      label = 'Uploaden naar YouTube';
      bg = 'bg-purple-500/20 text-purple-300 border-purple-500/40 animate-pulse';
      Icon = UploadCloud;
      break;
    case 'published':
      label = 'Gepubliceerd';
      bg = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
      Icon = CheckCircle2;
      break;
    case 'error':
    case 'failed':
      label = 'Mislukt';
      bg = 'bg-rose-500/20 text-rose-300 border-rose-500/40';
      Icon = AlertCircle;
      break;
  }

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm font-semibold';

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium border ${bg} ${sizeClasses}`}
    >
      <Icon className={size === 'sm' ? 'w-3 h-3' : 'w-4 h-4'} />
      <span>{label}</span>
    </span>
  );
};

