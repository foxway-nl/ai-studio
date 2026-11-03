import React from 'react';

interface ProgressBarProps {
  progress: number; // 0.0 tot 1.0 of 0 tot 100
  label?: string;
  showPercentage?: boolean;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  label,
  showPercentage = true,
}) => {
  // Normaliseer naar percentage 0-100
  const pct = Math.max(0, Math.min(100, progress > 1 ? progress : Math.round(progress * 100)));

  return (
    <div className="w-full space-y-1.5">
      {(label || showPercentage) && (
        <div className="flex items-center justify-between text-xs">
          {label ? (
            <span className="text-slate-300 font-medium truncate">{label}</span>
          ) : (
            <span />
          )}
          {showPercentage && (
            <span className="text-indigo-400 font-mono font-bold shrink-0">{pct}%</span>
          )}
        </div>
      )}
      <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden border border-slate-700/50 p-0.5">
        <div
          className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 rounded-full transition-all duration-300 ease-out shadow-sm"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
};

