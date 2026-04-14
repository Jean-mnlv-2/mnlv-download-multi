import React from 'react';
import { Task } from '../../store/useTaskStore';
import { 
  Play, 
  Download, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Music, 
  Video, 
  ExternalLink,
  MoreVertical
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';

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

  return (
    <motion.div 
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      className="group bg-white dark:bg-slate-900/50 border border-gray-100 dark:border-slate-800 rounded-3xl p-5 flex items-center gap-6 transition-all hover:shadow-xl hover:shadow-gray-200/50 dark:hover:shadow-none hover:border-blue-200 dark:hover:border-blue-900/50"
    >
      {/* Thumbnail */}
      <div className="relative w-16 h-16 flex-shrink-0">
        <div className="w-full h-full bg-gray-100 dark:bg-slate-800 rounded-2xl overflow-hidden shadow-inner border border-gray-50 dark:border-slate-700">
          {task.track?.cover_url ? (
            <img 
              src={task.track.cover_url} 
              alt={task.track.title} 
              className="w-full h-full object-cover transition-transform group-hover:scale-110"
              onError={(e) => {
                (e.target as HTMLImageElement).src = 'https://via.placeholder.com/150?text=No+Cover';
              }}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gray-300 dark:text-gray-600">
              {isVideo ? <Video size={28} /> : <Music size={28} />}
            </div>
          )}
        </div>
        
        {isCompleted && (
          <div className="absolute -top-1 -right-1 bg-green-500 text-white rounded-full p-1 shadow-lg ring-2 ring-white dark:ring-slate-900">
            <CheckCircle2 size={12} strokeWidth={3} />
          </div>
        )}
      </div>

      {/* Info & Progress */}
      <div className="flex-grow min-w-0 space-y-2">
        <div className="flex items-start justify-between">
          <div className="min-w-0">
            <h3 className="text-base font-black text-gray-900 dark:text-white truncate tracking-tight">
              {task.track?.title || t('processing')}
            </h3>
            <p className="text-xs font-bold text-gray-400 dark:text-gray-500 truncate uppercase tracking-widest">
              {task.track?.artist || (isProcessing ? t('processing') : task.original_url)}
            </p>
          </div>
          <span className="text-[10px] font-black bg-gray-50 dark:bg-slate-800 text-gray-400 dark:text-gray-500 px-3 py-1 rounded-lg uppercase tracking-widest border border-gray-100 dark:border-slate-700">
            {task.provider || 'URL'}
          </span>
        </div>

        {/* Progress Section */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-tighter text-gray-400">
            <span>{isFailed ? t('failed') : isCompleted ? t('completed') : `${task.progress}%`}</span>
            {isProcessing && <Loader2 size={10} className="animate-spin text-blue-500" />}
          </div>
          <div className="h-1.5 bg-gray-100 dark:bg-slate-800 rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${task.progress}%` }}
              className={`h-full rounded-full transition-all duration-500 ${
                isFailed ? 'bg-red-500' : isCompleted ? 'bg-green-500' : 'bg-blue-600 shadow-[0_0_8px_rgba(37,99,235,0.4)]'
              }`}
            />
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {isCompleted && downloadHref && (
          <>
            {isVideo && onPreviewVideo && (
              <button
                onClick={() => onPreviewVideo(downloadHref)}
                className="w-10 h-10 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-xl flex items-center justify-center transition-all hover:bg-blue-600 hover:text-white shadow-sm active:scale-95"
                title={t('preview')}
              >
                <Play size={18} fill="currentColor" />
              </button>
            )}
            <a
              href={downloadHref}
              download
              className="w-10 h-10 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-xl flex items-center justify-center transition-all hover:bg-blue-600 dark:hover:bg-blue-500 dark:hover:text-white shadow-xl shadow-gray-200 dark:shadow-none active:scale-95"
              title={t('download')}
            >
              <Download size={18} />
            </a>
          </>
        )}
        
        {isFailed && (
          <div className="w-10 h-10 bg-red-50 dark:bg-red-900/20 text-red-500 rounded-xl flex items-center justify-center border border-red-100 dark:border-red-900/50" title={task.error_message}>
            <AlertCircle size={18} />
          </div>
        )}

        <button className="w-8 h-8 text-gray-300 dark:text-gray-700 hover:text-gray-900 dark:hover:text-white transition-colors">
          <MoreVertical size={18} />
        </button>
      </div>
    </motion.div>
  );
};

export default DownloadCard;
