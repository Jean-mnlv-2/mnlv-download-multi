import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { useTaskStore } from '../../store/useTaskStore';
import { useAuthStore } from '../../store/useAuthStore';
import { 
  FileUp, 
  Loader2, 
  FileText, 
  Trash2, 
  History
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';

interface ParsedTrack {
  title: string | null;
  artist: string | null;
  url: string | null;
  provider: string | null;
  status: 'ready' | 'not_found' | 'error';
  taskId?: string;
}

interface PendingUpload {
  id: string;
  filename: string;
  tracks: ParsedTrack[];
  created_at: string;
}

const CSVUpload: React.FC = () => {
  const { t } = useTranslation();
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [pendingUploads, setPendingUploads] = useState<PendingUpload[]>([]);
  const { addNotification, refreshTrigger, setStagedTracks, stagedTracks } = useTaskStore();
  const { accessToken } = useAuthStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchPendingUploads();
  }, [accessToken, refreshTrigger]);

  const fetchPendingUploads = async () => {
    if (!accessToken) return;
    try {
      const response = await axios.get('/api/csv/pending/');
      setPendingUploads(response.data);
    } catch (error) {}
  };

  const handleFileUpload = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    setUploading(true);
    
    try {
      const response = await axios.post('/api/csv/upload/', formData);
      const data = response.data;
      
      setStagedTracks(data.tracks);
      addNotification('success', `${data.tracks.length} morceaux analysés`);
      
      fetchPendingUploads();
    } catch (error: any) {
      addNotification('error', error.response?.data?.error || t('failed'));
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const cancelUpload = async (id?: string) => {
    try {
      const url = id ? `/api/csv/pending/?id=${id}` : '/api/csv/pending/';
      await axios.delete(url);
      if (id) {
        setPendingUploads(prev => prev.filter(u => u.id !== id));
        addNotification('success', "Upload annulé");
      } else {
        setPendingUploads([]);
        addNotification('success', "Tous les uploads ont été annulés");
      }
    } catch (error) {
      addNotification('error', "Erreur lors de l'annulation");
    }
  };

  const restoreUpload = (upload: PendingUpload) => {
    setStagedTracks(upload.tracks);
    addNotification('info', `Restauration de : ${upload.filename}`);
  };

  const onDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="w-full space-y-6">
      <AnimatePresence>
        {stagedTracks.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="bg-white dark:bg-mnlv-slate-900 rounded-[2rem] p-6 border border-mnlv-slate-200/50 dark:border-mnlv-slate-800/50 shadow-sm"
          >
            <div className="flex flex-col md:flex-row items-center gap-6">
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2 text-mnlv-blue font-black text-[10px] uppercase tracking-widest">
                  <FileText size={14} />
                  <span>Importation massive</span>
                </div>
                <h3 className="text-xl font-black tracking-tight">Fichiers CSV / Excel / Texte</h3>
                <p className="text-mnlv-slate-500 text-xs font-medium">Glissez vos listes d'URLs ou fichiers de titres ici.</p>
              </div>

              <div className="w-full md:w-64">
                <input
                  ref={fileInputRef}
                  type="file"
                  id="csv-file-upload"
                  className="hidden"
                  accept=".csv,.txt"
                  onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
                />
                
                <motion.div
                  onDragEnter={onDrag}
                  onDragLeave={onDrag}
                  onDragOver={onDrag}
                  onDrop={onDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`
                    relative cursor-pointer group h-32 w-full rounded-2xl border-2 border-dashed transition-all flex flex-col items-center justify-center p-4 text-center
                    ${dragActive 
                      ? 'border-mnlv-blue bg-mnlv-blue/5' 
                      : 'border-mnlv-slate-100 dark:border-mnlv-slate-800 bg-mnlv-slate-50/50 dark:bg-mnlv-slate-800/30 hover:border-mnlv-blue/30'
                    }
                  `}
                >
                  <div className="w-10 h-10 bg-white dark:bg-mnlv-slate-800 rounded-xl flex items-center justify-center mb-2 shadow-sm group-hover:scale-110 transition-transform">
                    {uploading ? (
                      <Loader2 className="text-mnlv-blue animate-spin" size={20} />
                    ) : (
                      <FileUp className="text-mnlv-blue" size={20} />
                    )}
                  </div>
                  <p className="text-[10px] font-black text-mnlv-slate-400 uppercase tracking-widest">
                    {uploading ? 'Analyse...' : 'Déposer ou cliquer'}
                  </p>
                </motion.div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {pendingUploads.length > 0 && stagedTracks.length === 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="space-y-4"
          >
            <div className="flex items-center gap-2 px-6">
              <History size={16} className="text-gray-400" />
              <span className="text-xs font-black uppercase tracking-widest text-gray-400">
                <span className="text-mnlv-blue">Maxi 24h</span> : Uploads en attente
              </span>
              <button 
                onClick={() => cancelUpload()}
                className="ml-auto text-[10px] font-black uppercase tracking-widest text-red-500 hover:text-red-600 transition-colors"
              >
                Tout effacer
              </button>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {pendingUploads.map((upload) => (
                <motion.div
                  key={upload.id}
                  layoutId={upload.id}
                  className="bg-white dark:bg-mnlv-slate-900 p-5 rounded-3xl border border-mnlv-slate-100 dark:border-mnlv-slate-800 flex items-center gap-4 group shadow-sm"
                >
                  <div className="w-12 h-12 bg-mnlv-blue/5 rounded-2xl flex items-center justify-center text-mnlv-blue">
                    <FileText size={20} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h5 className="text-sm font-black text-mnlv-slate-900 dark:text-white truncate">{upload.filename}</h5>
                    <p className="text-[10px] font-bold text-mnlv-slate-400 uppercase tracking-widest">
                      {upload.tracks.length} morceaux • {new Date(upload.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => cancelUpload(upload.id)}
                      className="p-2 text-mnlv-slate-400 hover:text-mnlv-red transition-colors"
                      title="Supprimer"
                    >
                      <Trash2 size={18} />
                    </button>
                    <button
                      onClick={() => restoreUpload(upload)}
                      className="px-4 py-2 bg-mnlv-blue text-white rounded-xl text-xs font-black shadow-pro-blue active:scale-95 transition-all"
                    >
                      Reprendre
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default CSVUpload;
