import React, { useState, useRef } from 'react';
import axios from 'axios';
import { useTaskStore } from '../../store/useTaskStore';
import { useAuthStore } from '../../store/useAuthStore';
import { FileUp, Info, CheckCircle2, Loader2, FileText, Music, Sparkles, X, Download, AlertCircle, ExternalLink } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';

interface ParsedTrack {
  title: string | null;
  artist: string | null;
  url: string | null;
  provider: string | null;
  status: 'ready' | 'not_found' | 'error';
}

const CSVUpload: React.FC = () => {
  const { t } = useTranslation();
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [analyzedTracks, setAnalyzedTracks] = useState<ParsedTrack[]>([]);
  const { addTask, pollTaskStatus, addNotification } = useTaskStore();
  const { providerStatus, accessToken } = useAuthStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    setUploading(true);
    setAnalyzedTracks([]);
    try {
      const response = await axios.post('/api/csv/upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const data = response.data;
      setAnalyzedTracks(data.tracks);
      addNotification('success', `${data.tracks.length} morceaux analysés`);

    } catch (error: any) {
      addNotification('error', error.response?.data?.error || t('failed'));
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleConnectProvider = async (provider: string) => {
    if (provider === 'spotify') {
      try {
        const response = await axios.get('/api/auth/providers/spotify/login/');
        if (response.data.auth_url) {
          window.location.href = response.data.auth_url;
        }
      } catch (error: any) {
        addNotification('error', "Impossible de se connecter à Spotify");
      }
    } else {
      addNotification('info', "Ce provider sera bientôt disponible");
    }
  };

  const startDownloads = async () => {
    const readyTracks = analyzedTracks.filter(t => t.status === 'ready' && t.url);
    
    if (readyTracks.length === 0) {
      addNotification('error', "Aucun morceau prêt à être téléchargé");
      return;
    }

    let launchedCount = 0;
    for (const track of readyTracks) {
      try {
        const response = await axios.post('/api/download/', {
          url: track.url,
          media_type: 'AUDIO',
          quality: '192'
        });

        if (response.data.task_id) {
          addTask({
            id: response.data.task_id,
            status: 'PENDING',
            progress: 0,
            original_url: track.url!,
            provider: track.provider || 'spotify'
          });
          pollTaskStatus(response.data.task_id);
          launchedCount++;
        }
      } catch (err) {
        console.error("Erreur lancement tâche:", err);
      }
    }

    addNotification('success', `${launchedCount} téléchargements lancés`);
    setAnalyzedTracks([]);
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

  const isProviderConnected = (provider: string | null) => {
    if (!provider) return true; // Source directe
    if (provider === 'spotify') return providerStatus.spotify;
    if (provider === 'deezer') return providerStatus.deezer;
    if (provider === 'apple_music') return providerStatus.apple_music;
    return true;
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      {/* Provider Connection Warning */}
      {!providerStatus.spotify && (
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-orange-50 dark:bg-orange-900/20 border border-orange-100 dark:border-orange-800 p-4 rounded-3xl flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-orange-100 dark:bg-orange-900/30 rounded-full flex items-center justify-center text-orange-600 dark:text-orange-400">
              <AlertCircle size={20} />
            </div>
            <div>
              <p className="text-sm font-black text-orange-900 dark:text-white">Connexion requise</p>
              <p className="text-xs font-bold text-orange-600 dark:text-orange-400/70">Connectez vos comptes musicaux pour explorer vos playlists et les télécharger en un clic.</p>
            </div>
          </div>
          <button 
            onClick={() => handleConnectProvider('spotify')}
            className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-xl text-xs font-black flex items-center gap-2 transition-colors"
          >
            Connecter Spotify
            <ExternalLink size={14} />
          </button>
        </motion.div>
      )}

      <div className="bg-white dark:bg-slate-900 rounded-[2.5rem] p-10 border border-gray-100 dark:border-slate-800 shadow-sm relative overflow-hidden">
        {/* Decorative background element */}
        <div className="absolute -top-24 -right-24 w-64 h-64 bg-blue-500/5 rounded-full blur-3xl pointer-events-none" />
        
        <div className="flex flex-col md:flex-row items-center gap-10">
          <div className="flex-1 space-y-6">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400 font-black text-xs uppercase tracking-widest">
                <FileText size={14} />
                <span>Importation de masse</span>
              </div>
              <h3 className="text-3xl font-black text-gray-900 dark:text-white tracking-tight leading-tight">
                Importez vos listes CSV ou Texte
              </h3>
            </div>
            
            <p className="text-gray-500 dark:text-gray-400 font-medium leading-relaxed">
              Glissez-déposez un fichier contenant des URLs (Spotify, Deezer, etc.) ou une liste de titres au format <code className="bg-gray-100 dark:bg-slate-800 px-2 py-0.5 rounded text-blue-600 dark:text-blue-400 font-bold text-xs">Artiste - Titre</code>.
            </p>

            <div className="flex items-center gap-4 text-xs font-bold text-gray-400 dark:text-gray-500">
              <div className="flex items-center gap-1">
                <CheckCircle2 size={14} className="text-green-500" />
                <span>Tous Providers</span>
              </div>
              <div className="flex items-center gap-1">
                <CheckCircle2 size={14} className="text-green-500" />
                <span>Sans en-têtes</span>
              </div>
              <div className="flex items-center gap-1">
                <CheckCircle2 size={14} className="text-green-500" />
                <span>Auto-Matching</span>
              </div>
            </div>
          </div>

          <div className="w-full md:w-80 flex-shrink-0">
            <input
              ref={fileInputRef}
              type="file"
              id="csv-file-upload"
              name="csv-file-upload"
              accept=".csv,.txt"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
            />
            
            <motion.div
              onDragEnter={onDrag}
              onDragLeave={onDrag}
              onDragOver={onDrag}
              onDrop={onDrop}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => fileInputRef.current?.click()}
              className={`
                relative cursor-pointer group h-64 w-full rounded-[2rem] border-4 border-dashed transition-all flex flex-col items-center justify-center p-6 text-center
                ${dragActive 
                  ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-900/20' 
                  : 'border-gray-100 dark:border-slate-800 bg-gray-50 dark:bg-slate-800/50 hover:border-blue-200 dark:hover:border-blue-900/50'
                }
              `}
            >
              <div className="w-16 h-16 bg-white dark:bg-slate-700 rounded-2xl flex items-center justify-center mb-4 shadow-xl shadow-gray-200/50 dark:shadow-none group-hover:scale-110 transition-transform">
                {uploading ? (
                  <Loader2 className="text-blue-600 dark:text-blue-400 animate-spin" size={32} />
                ) : (
                  <FileUp className="text-blue-600 dark:text-blue-400" size={32} />
                )}
              </div>
              <p className="text-sm font-black text-gray-900 dark:text-white mb-1">
                {uploading ? 'Analyse...' : 'Déposer le fichier'}
              </p>
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                CSV ou TXT (Max 5Mo)
              </p>
            </motion.div>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {analyzedTracks.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-white dark:bg-slate-900 rounded-[2.5rem] p-8 border border-gray-100 dark:border-slate-800 shadow-xl"
          >
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-2xl flex items-center justify-center text-blue-600 dark:text-blue-400">
                  <Sparkles size={24} />
                </div>
                <div>
                  <h4 className="text-xl font-black text-gray-900 dark:text-white tracking-tight">
                    {analyzedTracks.length} morceaux détectés
                  </h4>
                  <p className="text-sm font-bold text-gray-400 uppercase tracking-widest">
                    Vérifiez la liste avant de lancer
                  </p>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setAnalyzedTracks([])}
                  className="px-6 py-3 rounded-2xl font-bold text-sm text-gray-500 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors flex items-center gap-2"
                >
                  <X size={18} />
                  Annuler
                </button>
                <button
                  onClick={startDownloads}
                  className="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl font-black text-sm shadow-xl shadow-blue-500/20 transition-all flex items-center gap-2"
                >
                  <Download size={18} />
                  Tout télécharger
                </button>
              </div>
            </div>

            <div className="max-h-[400px] overflow-y-auto pr-4 space-y-3 custom-scrollbar">
              {analyzedTracks.map((track, idx) => (
                <div 
                  key={idx}
                  className="flex items-center justify-between p-4 bg-gray-50 dark:bg-slate-800/50 rounded-2xl border border-transparent hover:border-blue-100 dark:hover:border-blue-900/30 transition-all group"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-white dark:bg-slate-700 rounded-xl flex items-center justify-center text-gray-400 group-hover:text-blue-500 transition-colors shadow-sm">
                      <Music size={20} />
                    </div>
                    <div>
                      <p className="font-black text-gray-900 dark:text-white leading-tight">
                        {track.title || track.url}
                      </p>
                      <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mt-1">
                        {track.artist || 'Artiste inconnu'} • <span className="text-blue-500">{track.provider || 'Source directe'}</span>
                        {!isProviderConnected(track.provider) && (
                          <span className="ml-2 text-orange-500 font-black tracking-tighter">(Connexion requise)</span>
                        )}
                      </p>
                    </div>
                  </div>
                  
                  <div>
                    {track.status === 'ready' ? (
                      <div className="flex items-center gap-2 px-3 py-1 bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 rounded-lg text-[10px] font-black uppercase tracking-widest border border-green-100 dark:border-green-800">
                        <CheckCircle2 size={12} />
                        Prêt
                      </div>
                    ) : track.status === 'not_found' ? (
                      <div className="flex items-center gap-2 px-3 py-1 bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400 rounded-lg text-[10px] font-black uppercase tracking-widest border border-orange-100 dark:border-orange-800">
                        <AlertCircle size={12} />
                        Non trouvé
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 px-3 py-1 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg text-[10px] font-black uppercase tracking-widest border border-red-100 dark:border-red-800">
                        <AlertCircle size={12} />
                        Erreur
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default CSVUpload;
