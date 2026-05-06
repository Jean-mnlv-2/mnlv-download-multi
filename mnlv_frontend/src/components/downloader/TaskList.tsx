import React from 'react';
import { Task } from '../../store/useTaskStore';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Music, 
  Video, 
  Download,
  Trash2
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import ProviderIcon from './ProviderIcon';
import { LocalFileSystemService } from '../../services/localFileSystem';

interface TaskListProps {
  tasks: Task[];
}

const TaskList: React.FC<TaskListProps> = ({ tasks }) => {
  const handleLocalDownload = async (task: Task) => {
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
    <div className="bg-white dark:bg-mnlv-slate-900 border border-mnlv-slate-200 dark:border-mnlv-slate-800 rounded-2xl overflow-hidden shadow-pro">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-mnlv-slate-100 dark:border-mnlv-slate-800 text-[10px] font-black uppercase tracking-widest text-mnlv-slate-400">
              <th className="px-6 py-4">Morceau / Source</th>
              <th className="px-6 py-4">Statut</th>
              <th className="px-6 py-4">Progression</th>
              <th className="px-6 py-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-mnlv-slate-50 dark:divide-mnlv-slate-800/50">
            <AnimatePresence mode="popLayout">
              {tasks.map((task) => {
                const isCompleted = task.status === 'COMPLETED';
                const isFailed = task.status === 'FAILED';
                const isProcessing = task.status === 'PROCESSING' || task.status === 'PENDING';
                
                return (
                  <motion.tr 
                    layout
                    key={task.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="hover:bg-mnlv-slate-50 dark:hover:bg-mnlv-slate-800/30 transition-colors group"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="relative w-10 h-10 flex-shrink-0">
                          {task.track?.cover_url ? (
                            <img 
                              src={task.track.cover_url} 
                              alt="" 
                              className="w-full h-full object-cover rounded-lg shadow-sm"
                            />
                          ) : (
                            <div className="w-full h-full bg-mnlv-slate-100 dark:bg-mnlv-slate-800 rounded-lg flex items-center justify-center text-mnlv-slate-400">
                              {task.media_type === 'VIDEO' ? <Video size={16} /> : <Music size={16} />}
                            </div>
                          )}
                          <div className="absolute -bottom-1 -right-1 bg-white dark:bg-mnlv-slate-900 rounded-full p-0.5 border border-mnlv-slate-100 dark:border-mnlv-slate-800">
                            <ProviderIcon provider={task.provider} size={10} />
                          </div>
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-bold truncate">{task.track?.title || task.title || 'Inconnu'}</p>
                          <p className="text-[10px] text-mnlv-slate-500 font-medium truncate uppercase tracking-tight">
                            {task.track?.artist || 'Source externe'}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {isCompleted ? (
                          <span className="flex items-center gap-1.5 text-xs font-bold text-green-500">
                            <CheckCircle2 size={14} /> Terminé
                          </span>
                        ) : isFailed ? (
                          <span className="flex items-center gap-1.5 text-xs font-bold text-mnlv-red">
                            <AlertCircle size={14} /> Échec
                          </span>
                        ) : (
                          <span className="flex items-center gap-1.5 text-xs font-bold text-mnlv-blue">
                            <Loader2 size={14} className="animate-spin" /> 
                            {task.message || 'Traitement...'}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3 min-w-[120px]">
                        <div className="flex-1 h-1.5 bg-mnlv-slate-100 dark:bg-mnlv-slate-800 rounded-full overflow-hidden">
                          <motion.div 
                            initial={{ width: 0 }}
                            animate={{ width: `${task.progress}%` }}
                            className={`h-full rounded-full ${
                              isCompleted ? 'bg-green-500' : isFailed ? 'bg-mnlv-red' : 'bg-mnlv-blue'
                            }`}
                          />
                        </div>
                        <span className="text-[10px] font-mono font-bold text-mnlv-slate-400">
                          {task.progress}%
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        {isCompleted && (
                          <button 
                            onClick={() => handleLocalDownload(task)}
                            className="p-2 text-mnlv-blue hover:bg-mnlv-blue/10 rounded-lg transition-colors"
                            title="Enregistrer"
                          >
                            <Download size={16} />
                          </button>
                        )}
                        <button className="p-2 text-mnlv-slate-400 hover:text-mnlv-red hover:bg-mnlv-red/10 rounded-lg transition-colors">
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </motion.tr>
                );
              })}
            </AnimatePresence>
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TaskList;
