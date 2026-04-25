import React from 'react';
import { Task } from '../../store/useTaskStore';
import { LocalFileSystemService } from '../../services/localFileSystem';
import { 
  Play, 
  Download, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Music, 
  Video, 
  ExternalLink,
  MoreVertical,
  Disc,
  Radio,
  Cloud,
  Youtube,
  Trash2,
  FolderOpen
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import ProviderIcon from './ProviderIcon';

interface DownloadCardProps {
  task: Task;
  onPreviewVideo?: (url: string) => void;
}

const DownloadCard: React.FC<DownloadCardProps> = ({ task, onPreviewVideo }) => {
  const { t } = useTranslation();
  const isCompleted = task.status === 'COMPLETED';
  const isFailed = task.status === 'FAILED';
  const isProcessing = task.status === 'PROCESSING' || task.status === 'PENDING';
  const isVideo = task.result_file?.endsWith('.mp4') || task.result_file_url?.endsWith('.mp4');

  const downloadHref = (() => {
    const raw = task.result_file_url || task.result_file;
    if (!raw) return null;
    if (raw.startsWith('http://') || raw.startsWith('https://')) return raw;
    if (raw.startsWith('/media/')) return raw;
    if (raw.startsWith('media/')) return `/${raw}`;
    return `/media/${raw.startsWith('/') ? raw.slice(1) : raw}`;
  })();

  const handleLocalDownload = async () => {
    try {
      const finalUrl = `/api/task/${task.id}/download/`;
      
      const response = await fetch(finalUrl, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('mnlv_access_token')}`
        }
      });

      if (!response.ok) {
        throw new Error('Erreur lors de la récupération du fichier');
      }

      const blob = await response.blob();
      const fileExtension = task.result_file?.split('.').pop() || 'mp3';
      let suggestedName = "";
      
      if (task.track && task.track.title && task.track.artist) {
        suggestedName = `${task.track.artist} - ${task.track.title}.${fileExtension}`;
      } else if (task.title) {
        suggestedName = `${task.title}.${fileExtension}`;
      } else {
        suggestedName = `download-${task.id.slice(0, 8)}.${fileExtension}`;
      }

      const saved = await LocalFileSystemService.saveFile(blob, suggestedName, task.save_to_dir, true);
      
      if (saved) {
        return;
      }

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', suggestedName);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {}
  };

  return (
    <motion.div 
      layout
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      whileHover={{ y: -4 }}
      className="group bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-[2rem] p-4 flex items-center gap-5 transition-all hover:shadow-2xl hover:shadow-blue-500/10 dark:hover:shadow-none hover:border-blue-100 dark:hover:border-blue-900/30"
    >
      {/* Thumbnail with Overlay */}
      <div className="relative w-20 h-20 flex-shrink-0 group/thumb">
        <div className="w-full h-full bg-gray-100 dark:bg-slate-800 rounded-[1.5rem] overflow-hidden shadow-inner border border-gray-50 dark:border-slate-700">
          {task.track?.cover_url ? (
            <img 
              src={task.track.cover_url} 
              alt={task.track.title} 
              className="w-full h-full object-cover transition-transform duration-700 group-hover/thumb:scale-110"
              onError={(e) => {
                (e.target as HTMLImageElement).src = 'https://ui-avatars.com/api/?name=Music&background=random';
              }}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gray-300 dark:text-gray-600">
              {isVideo ? <Video size={32} /> : <Music size={32} />}
            </div>
          )}
          
          {/* Status Overlay */}
          <AnimatePresence>
            {isProcessing && (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="absolute inset-0 bg-black/40 backdrop-blur-[2px] flex items-center justify-center"
              >
                <Loader2 size={24} className="animate-spin text-white" />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        
        {isCompleted && (
          <motion.div 
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="absolute -top-1.5 -right-1.5 bg-green-500 text-white rounded-full p-1.5 shadow-xl ring-4 ring-white dark:ring-slate-900"
          >
            <CheckCircle2 size={14} strokeWidth={3} />
          </motion.div>
        )}
      </div>

      {/* Info & Progress */}
      <div className="flex-grow min-w-0 space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="text-lg font-black text-gray-900 dark:text-white truncate tracking-tight leading-tight">
              {task.track?.title || (isProcessing ? 'Initialisation...' : t('processing'))}
            </h3>
            <div className="flex items-center gap-2 mt-0.5">
              <ProviderIcon provider={task.provider} size={14} />
              <p className="text-[11px] font-bold text-gray-400 dark:text-gray-500 truncate uppercase tracking-widest">
                {task.track?.artist || (isProcessing ? (task.message || 'Préparation...') : 'Source externe')}
              </p>
              {task.track?.explicit && (
                <span className="text-[8px] font-black bg-gray-100 dark:bg-slate-800 text-gray-500 dark:text-gray-400 px-1.5 py-0.5 rounded-sm border border-gray-200 dark:border-slate-700">
                  E
                </span>
              )}
            </div>
          </div>
          <div className="flex flex-col items-end gap-1">
            <span className="text-[9px] font-black bg-gray-50 dark:bg-slate-800 text-gray-400 dark:text-gray-500 px-2.5 py-1 rounded-full uppercase tracking-widest border border-gray-100 dark:border-slate-700">
              {task.media_type}
            </span>
            {isVideo && (
              <span className="text-[9px] font-black bg-blue-50 dark:bg-blue-900/20 text-blue-500 px-2.5 py-1 rounded-full uppercase tracking-widest border border-blue-100/50 dark:border-blue-800/50">
                4K / MP4
              </span>
            )}
          </div>
        </div>

        {/* Progress Section */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-gray-400">
            <div className="flex items-center gap-1.5">
              {isFailed ? (
                <span className="text-red-500 flex items-center gap-1">
                  <AlertCircle size={10} /> Échec
                </span>
              ) : isCompleted ? (
                <span className="text-green-500 flex items-center gap-1">
                  <CheckCircle2 size="10" /> Terminé
                </span>
              ) : (
                <div className="flex flex-col gap-0.5">
                  <span className="text-blue-500 flex items-center gap-1">
                    <Loader2 size={10} className="animate-spin" /> 
                    {task.message && (
                    <span className="animate-pulse truncate max-w-[150px]">{task.message}</span>
                  )}
                  {(!task.message && task.progress > 0) && <span>Téléchargement</span>}
                  {(!task.message && task.progress === 0) && <span>En attente</span>}
                </span>
                {!isCompleted && !isFailed && (task.speed || task.eta) && (
                  <span className="text-[8px] text-gray-400 lowercase font-medium flex items-center gap-1">
                    {task.speed && <span>{task.speed}</span>}
                    {task.speed && task.eta && <span>•</span>}
                    {task.eta && <span>{task.eta} restant</span>}
                  </span>
                )}
                </div>
              )}
            </div>
            <span className={isCompleted ? 'text-green-500' : 'text-gray-500 font-mono'}>
              {isFailed ? 'Error' : isCompleted ? '100%' : `${task.progress}%`}
            </span>
          </div>
          <div className="h-2.5 bg-gray-100 dark:bg-slate-800 rounded-full overflow-hidden p-0.5 border border-gray-50 dark:border-slate-700/50 relative">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: isFailed ? '100%' : `${task.progress}%` }}
              className={`h-full rounded-full transition-all duration-700 relative z-10 ${
                isFailed ? 'bg-red-500/20' : isCompleted ? 'bg-green-500 shadow-[0_0_12px_rgba(34,197,94,0.4)]' : 'bg-gradient-to-r from-blue-600 to-indigo-500 shadow-[0_0_12px_rgba(37,99,235,0.3)]'
              }`}
            />
            {!isCompleted && !isFailed && (
              <motion.div 
                animate={{ x: ['-100%', '200%'] }}
                transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
                className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent z-20 w-1/2"
              />
            )}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 pl-2">
        <AnimatePresence mode="wait">
          {isCompleted && downloadHref ? (
            <motion.div 
              key="actions"
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-2"
            >
              {isVideo && onPreviewVideo && (
                <button
                  onClick={() => onPreviewVideo(downloadHref)}
                  className="w-12 h-12 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-2xl flex items-center justify-center transition-all hover:bg-blue-600 hover:text-white shadow-sm active:scale-90"
                  title={t('preview')}
                >
                  <Play size={20} fill="currentColor" />
                </button>
              )}
              <button
                onClick={handleLocalDownload}
                className="w-12 h-12 bg-gray-900 dark:bg-blue-600 text-white rounded-2xl flex items-center justify-center transition-all hover:bg-blue-600 dark:hover:bg-blue-500 shadow-xl shadow-gray-200 dark:shadow-blue-500/20 active:scale-90"
                title="Enregistrer sous..."
              >
                <FolderOpen size={20} strokeWidth={2.5} />
              </button>
            </motion.div>
          ) : isFailed ? (
            <motion.div 
              key="failed"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              className="w-12 h-12 bg-red-50 dark:bg-red-900/10 text-red-500 rounded-2xl flex items-center justify-center border border-red-100 dark:border-red-900/30" 
              title={task.error_message}
            >
              <AlertCircle size={22} />
            </motion.div>
          ) : (
            <div key="placeholder" className="w-12 h-12" />
          )}
        </AnimatePresence>

        <button className="w-10 h-10 text-gray-300 dark:text-gray-700 hover:text-gray-900 dark:hover:text-white transition-all hover:bg-gray-50 dark:hover:bg-slate-800 rounded-xl flex items-center justify-center">
          <MoreVertical size={20} />
        </button>
      </div>
    </motion.div>
  );
};

export default DownloadCard;
