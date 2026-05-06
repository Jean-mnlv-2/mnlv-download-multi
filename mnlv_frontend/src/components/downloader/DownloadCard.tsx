import React from 'react';
import { Task } from '../../store/useTaskStore';
import { LocalFileSystemService } from '../../services/localFileSystem';
import { 
  Play, 
  Download, 
  Loader2, 
  Music, 
  Video, 
  Trash2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import ProviderIcon from './ProviderIcon';

interface DownloadCardProps {
  task: Task;
  onPreviewVideo?: (url: string) => void;
}

const DownloadCard: React.FC<DownloadCardProps> = ({ task, onPreviewVideo }) => {
  const isCompleted = task.status === 'COMPLETED';
  const isFailed = task.status === 'FAILED';
  const isProcessing = task.status === 'PROCESSING' || task.status === 'PENDING';

  const handleLocalDownload = async () => {
    try {
      const finalUrl = `/api/task/${task.id}/download/`;
      const response = await fetch(finalUrl, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('mnlv_access_token')}`
        }
      });

      if (!response.ok) throw new Error('Download failed');

      const blob = await response.blob();
      const fileExtension = task.result_file?.split('.').pop() || 'mp3';
      const suggestedName = task.track?.title && task.track?.artist 
        ? `${task.track.artist} - ${task.track.title}.${fileExtension}`
        : `download-${task.id.slice(0, 8)}.${fileExtension}`;

      await LocalFileSystemService.saveFile(blob, suggestedName, task.save_to_dir, true);
    } catch (err) {}
  };

  return (
    <motion.div 
      layout
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
      className="bg-white dark:bg-mnlv-slate-900 border border-mnlv-slate-200 dark:border-mnlv-slate-800 rounded-2xl p-5 shadow-pro hover:shadow-pro-blue transition-all group"
    >
      <div className="flex gap-4">
        {/* Artwork */}
        <div className="relative w-16 h-16 flex-shrink-0">
          <div className="w-full h-full bg-mnlv-slate-100 dark:bg-mnlv-slate-800 rounded-xl overflow-hidden border border-mnlv-slate-50 dark:border-mnlv-slate-700 shadow-inner">
            {task.track?.cover_url ? (
              <img 
                src={task.track.cover_url} 
                alt="" 
                className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-mnlv-slate-400">
                {task.media_type === 'VIDEO' ? <Video size={24} /> : <Music size={24} />}
              </div>
            )}
            
            {isProcessing && (
              <div className="absolute inset-0 bg-black/40 backdrop-blur-[1px] flex items-center justify-center">
                <Loader2 size={20} className="animate-spin text-white" />
              </div>
            )}
          </div>
          
          <div className="absolute -bottom-1.5 -right-1.5 bg-white dark:bg-mnlv-slate-900 rounded-full p-1 border border-mnlv-slate-100 dark:border-mnlv-slate-800 shadow-sm">
            <ProviderIcon provider={task.provider} size={12} />
          </div>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="font-bold text-sm truncate leading-tight">
                {task.track?.title || task.title || (isProcessing ? 'Chargement...' : 'Morceau inconnu')}
              </h3>
              <p className="text-[10px] font-bold text-mnlv-slate-400 dark:text-mnlv-slate-500 uppercase tracking-widest mt-1">
                {task.track?.artist || 'Source externe'}
              </p>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-[9px] font-black bg-mnlv-slate-50 dark:bg-mnlv-slate-800 px-2 py-0.5 rounded-md border border-mnlv-slate-100 dark:border-mnlv-slate-700 text-mnlv-slate-400">
                {task.media_type}
              </span>
            </div>
          </div>

          {/* Progress */}
          <div className="mt-4 space-y-2">
            <div className="flex items-center justify-between text-[9px] font-black uppercase tracking-widest">
              <span className={isFailed ? 'text-mnlv-red' : isCompleted ? 'text-green-500' : 'text-mnlv-blue'}>
                {isFailed ? 'Erreur' : isCompleted ? 'Terminé' : (task.message || 'Téléchargement')}
              </span>
              <span className="text-mnlv-slate-400 font-mono">{task.progress}%</span>
            </div>
            <div className="h-1.5 bg-mnlv-slate-100 dark:bg-mnlv-slate-800 rounded-full overflow-hidden">
              <motion.div 
                initial={{ width: 0 }}
                animate={{ width: `${task.progress}%` }}
                className={`h-full rounded-full ${
                  isFailed ? 'bg-mnlv-red' : isCompleted ? 'bg-green-500' : 'bg-mnlv-blue shadow-pro-blue'
                }`}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Actions (Bottom Bar) */}
      <AnimatePresence>
        {isCompleted && (
          <motion.div 
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            className="mt-4 pt-4 border-t border-mnlv-slate-50 dark:border-mnlv-slate-800 flex items-center justify-between"
          >
            <div className="flex items-center gap-2">
              <button 
                onClick={handleLocalDownload}
                className="flex items-center gap-2 px-3 py-1.5 bg-mnlv-blue text-white text-[10px] font-bold rounded-lg hover:bg-mnlv-blue-dark transition-colors shadow-sm"
              >
                <Download size={14} />
                <span>Enregistrer</span>
              </button>
              {task.media_type === 'VIDEO' && onPreviewVideo && (
                <button 
                  onClick={() => onPreviewVideo(task.result_file_url || '')}
                  className="p-1.5 text-mnlv-blue hover:bg-mnlv-blue/10 rounded-lg transition-colors"
                >
                  <Play size={16} fill="currentColor" />
                </button>
              )}
            </div>
            <button className="p-1.5 text-mnlv-slate-400 hover:text-mnlv-red hover:bg-mnlv-red/10 rounded-lg transition-colors">
              <Trash2 size={16} />
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default DownloadCard;
