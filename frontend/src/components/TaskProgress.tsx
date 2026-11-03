import React, { useEffect, useState } from 'react';
import { Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { subscribeToTaskProgress, TaskProgress as TaskProgressType } from '../api/client';
import { ProgressBar } from './ProgressBar';

interface TaskProgressProps {
  taskId: string;
  onComplete?: () => void;
  onError?: (err: string) => void;
}

export const TaskProgress: React.FC<TaskProgressProps> = ({ taskId, onComplete, onError }) => {
  const [taskData, setTaskData] = useState<TaskProgressType>({
    task_id: taskId,
    status: 'running',
    progress: 0.05,
    step: 'Taak voorbereiden...',
    message: 'Initialiseren...',
  });

  useEffect(() => {
    const unsubscribe = subscribeToTaskProgress(
      taskId,
      (data) => {
        setTaskData(data);
        if (data.status === 'completed' && onComplete) {
          onComplete();
        } else if (data.status === 'failed' && onError) {
          onError(data.message || 'Er is een fout opgetreden.');
        }
      },
      () => {
        // SSE network error fallback
      }
    );

    return () => {
      unsubscribe();
    };
  }, [taskId, onComplete, onError]);

  const isComplete = taskData.status === 'completed';
  const isFailed = taskData.status === 'failed';

  return (
    <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          {!isComplete && !isFailed && (
            <Loader2 className="w-5 h-5 text-indigo-400 animate-spin shrink-0" />
          )}
          {isComplete && <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />}
          {isFailed && <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />}
          <div>
            <div className="text-sm font-semibold text-slate-100">
              {isComplete ? 'Voltooid' : isFailed ? 'Mislukt' : 'Bezig met verwerken'}
            </div>
            <div className="text-xs text-slate-400">{taskData.step || taskData.message}</div>
          </div>
        </div>
      </div>

      <ProgressBar progress={taskData.progress} showPercentage />
    </div>
  );
};

