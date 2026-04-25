import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { useTaskStore } from '../../store/useTaskStore';
import { useAuthStore } from '../../store/useAuthStore';
import { LocalFileSystemService } from '../../services/localFileSystem';
import { 
  FileUp, 
  Info, 
  CheckCircle2, 
  Loader2, 
  FileText, 
  Music, 
  Sparkles, 
  X, 
  Download, 
  AlertCircle, 
  ExternalLink, 
  Trash2, 
  History,
  FolderOpen,
  Plus,
  LayoutGrid,
  Check,
  TrendingUp
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import ProviderIcon from './ProviderIcon';

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
  const [autoStart, setAutoStart] = useState(false);
  const [downloadTarget, setDownloadTarget] = useState<'local' | 'playlist'>('local');
  const [selectedTargetPlaylist, setSelectedTargetPlaylist] = useState<string | null>(null);
  const [showNewPlaylistInput, setShowNewPlaylistInput] = useState(false);
  const [newPlaylistName, setNewPlaylistName] = useState('');
  const [pendingUploads, setPendingUploads] = useState<PendingUpload[]>([]);
  const { addTask, pollTaskStatus, addNotification, refreshTrigger, stagedTracks, setStagedTracks, localDirectorySelected, setLocalDirectorySelected, tasks } = useTaskStore();
  const { providerStatus, accessToken } = useAuthStore();
  const [userPlaylists, setUserPlaylists] = useState<any[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const previewRef = useRef<HTMLDivElement>(null);

  // Charger les uploads en attente au montage et lors d'un trigger
  useEffect(() => {
    fetchPendingUploads();
  }, [accessToken, refreshTrigger]);

  useEffect(() => {
    if (stagedTracks.length > 0 && previewRef.current) {
      previewRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [stagedTracks]);

  useEffect(() => {
    if (stagedTracks.length > 0 && downloadTarget === 'playlist' && accessToken) {
      fetchUserPlaylists();
    }
  }, [downloadTarget, stagedTracks]);

  const handleCreateAndSelectPlaylist = async () => {
    if (!newPlaylistName.trim()) return;
    const provider = stagedTracks[0]?.provider || 'spotify';
    try {
      const res = await axios.post('/api/playlist/manage/', {
        action: 'CREATE',
        provider: provider,
        provider_url: `https://${provider === 'apple_music' ? 'music.apple' : provider}.com`,
        name: newPlaylistName
      });
      addNotification('success', `Playlist "${newPlaylistName}" créée !`);
      await fetchUserPlaylists();
      setSelectedTargetPlaylist(res.data.playlist_id);
      setShowNewPlaylistInput(false);
      setNewPlaylistName('');
    } catch (err) {
      addNotification('error', "Erreur lors de la création");
    }
  };

  const fetchUserPlaylists = async () => {
    const provider = stagedTracks[0]?.provider || 'spotify';
    try {
      const res = await axios.post('/api/playlist/manage/', {
        action: 'GET_LIST',
        provider: provider,
        provider_url: `https://${provider === 'apple_music' ? 'music.apple' : provider}.com`
      });
      setUserPlaylists(res.data.playlists || []);
    } catch (err) {}
  };

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
    setStagedTracks([]);
    
    try {
      const response = await axios.post('/api/csv/upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const data = response.data;
      setStagedTracks(data.tracks);
      addNotification('success', `${data.tracks.length} morceaux analysés`);
      
      // Rafraîchir la liste des uploads en attente
      fetchPendingUploads();

      if (autoStart && data.tracks.length > 0) {
        startDownloads(data.tracks);
      }

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

  const handleSelectLocalDir = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    setDownloadTarget('local');
    
    try {
      const success = await LocalFileSystemService.selectDirectory();
      if (success) {
        setLocalDirectorySelected(true);
        addNotification('success', "Dossier local configuré !");
      }
    } catch (err) {}
  };

  const startDownloads = async (tracksToDownload?: ParsedTrack[]) => {
    const tracks = Array.isArray(tracksToDownload) ? tracksToDownload : stagedTracks;
    
    // On ne relance pas si des tâches sont déjà en cours pour cette liste
    const isAnyTaskActive = tracks.some(t => {
      const task = t.taskId ? tasks[t.taskId] : null;
      return task && (task.status === 'PROCESSING' || task.status === 'PENDING');
    });

    if (isAnyTaskActive && !tracksToDownload) {
      addNotification('info', "Des téléchargements sont déjà en cours");
      return;
    }

    if (downloadTarget === 'playlist' && !selectedTargetPlaylist) {
      addNotification('error', "Veuillez choisir ou créer une playlist de destination");
      return;
    }

    if (downloadTarget === 'local' && !LocalFileSystemService.getHandle()) {
      const success = await LocalFileSystemService.selectDirectory();
      if (!success) return;
      setLocalDirectorySelected(true);
    }

    const readyTracks = tracks.filter(t => 
      t.status === 'ready' && 
      t.url && 
      isProviderConnected(t.provider)
    );
    
    if (readyTracks.length === 0) {
      addNotification('error', "Aucun morceau prêt à être téléchargé");
      return;
    }

    try {
      if (!tracksToDownload) setUploading(true);

      const saveDir = downloadTarget === 'local' ? `Batch_${new Date().toLocaleDateString().replace(/\//g, '-')}` : undefined;

      if (downloadTarget === 'playlist' && selectedTargetPlaylist) {
        await axios.post('/api/playlist/manage/', {
          action: 'ADD_TRACKS',
          playlist_id: selectedTargetPlaylist,
          track_urls: readyTracks.map(t => t.url),
          provider_url: `https://${readyTracks[0].provider}.com`
        });
      }

      const response = await axios.post('/api/download/bulk/', {
        urls: readyTracks.map(t => t.url),
        media_type: 'AUDIO',
        quality: '192'
      });

      if (response.data.tasks) {
        // Créer une copie des morceaux pour mettre à jour les taskId
        const updatedStagedTracks = [...stagedTracks];

        response.data.tasks.forEach((backendTask: any) => {
          // On ajoute la tâche au store global
          addTask({
            id: backendTask.task_id,
            status: backendTask.status || 'PENDING',
            progress: 0,
            original_url: backendTask.url,
            title: backendTask.title || backendTask.url,
            provider: backendTask.provider || 'batch',
            save_to_dir: saveDir
          });
          pollTaskStatus(backendTask.task_id);

          // On lie le taskId au morceau dans la liste locale
          const trackIdx = updatedStagedTracks.findIndex(t => t.url === backendTask.url);
          if (trackIdx !== -1) {
            updatedStagedTracks[trackIdx] = {
              ...updatedStagedTracks[trackIdx],
              taskId: backendTask.task_id
            };
          }
        });

        setStagedTracks(updatedStagedTracks);
        addNotification('success', `${response.data.count} téléchargements lancés`);
      }
    } catch (err: any) {
      addNotification('error', "Erreur lors du lancement");
    } finally {
      if (!tracksToDownload) setUploading(false);
    }
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
    if (!provider || provider === 'Source directe' || provider === 'unknown' || provider === 'batch') return true;
    const p = provider.toLowerCase();
    if (p.includes('spotify')) return providerStatus.spotify;
    if (p.includes('deezer')) return providerStatus.deezer;
    if (p.includes('apple')) return providerStatus.apple_music;
    if (p.includes('boomplay')) return providerStatus.boomplay;
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

            <div className="flex items-center gap-3 pt-2">
              <label className="relative inline-flex items-center cursor-pointer">
                <input 
                  type="checkbox" 
                  className="sr-only peer" 
                  checked={autoStart}
                  onChange={() => setAutoStart(!autoStart)}
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
                <span className="ml-3 text-sm font-bold text-gray-500 dark:text-gray-400">Lancer automatiquement</span>
              </label>
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
        {pendingUploads.length > 0 && stagedTracks.length === 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="space-y-4"
          >
            <div className="flex items-center gap-2 px-6">
              <History size={16} className="text-gray-400" />
              <span className="text-xs font-black uppercase tracking-widest text-gray-400">Uploads en attente</span>
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
                  className="bg-white dark:bg-slate-900 p-5 rounded-3xl border border-gray-100 dark:border-slate-800 flex items-center gap-4 group"
                >
                  <div className="w-12 h-12 bg-blue-50 dark:bg-blue-900/20 rounded-2xl flex items-center justify-center text-blue-600 dark:text-blue-400">
                    <FileText size={20} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h5 className="text-sm font-black text-gray-900 dark:text-white truncate">{upload.filename}</h5>
                    <p className="text-[10px] font-bold text-gray-400 uppercase">{upload.tracks.length} morceaux • {new Date(upload.created_at).toLocaleDateString()}</p>
                  </div>
                  <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => cancelUpload(upload.id)}
                      className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                      title="Supprimer"
                    >
                      <Trash2 size={18} />
                    </button>
                    <button
                      onClick={() => restoreUpload(upload)}
                      className="px-4 py-2 bg-blue-600 text-white rounded-xl text-xs font-black"
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

      <AnimatePresence>
        {stagedTracks.length > 0 && (
          <motion.div
            ref={previewRef}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-white dark:bg-slate-900 rounded-[2.5rem] p-8 border border-gray-100 dark:border-slate-800 shadow-xl scroll-mt-10"
          >
            {/* Destination Selector */}
            <div className="grid grid-cols-2 gap-4 mb-8">
              <button
                onClick={handleSelectLocalDir}
                className={`p-6 rounded-3xl border-2 transition-all flex flex-col items-center gap-3 relative ${
                  downloadTarget === 'local' 
                    ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400' 
                    : 'border-gray-100 dark:border-slate-800 hover:border-gray-200'
                }`}
              >
                <FolderOpen size={32} />
                <div className="text-center">
                  <div className="flex items-center justify-center gap-2">
                    <p className="font-black uppercase tracking-widest text-xs">Stockage Local</p>
                    {localDirectorySelected && <Check size={14} className="text-green-500" />}
                  </div>
                  <p className="text-[10px] font-medium opacity-60 mt-1">
                    {localDirectorySelected ? 'Dossier configuré' : 'Choisir l\'emplacement'}
                  </p>
                </div>
              </button>
              <button
                onClick={() => setDownloadTarget('playlist')}
                className={`p-6 rounded-3xl border-2 transition-all flex flex-col items-center gap-3 ${
                  downloadTarget === 'playlist' 
                    ? 'border-emerald-500 bg-emerald-50/50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400' 
                    : 'border-gray-100 dark:border-slate-800 hover:border-gray-200'
                }`}
              >
                <LayoutGrid size={32} />
                <div className="text-center">
                  <p className="font-black uppercase tracking-widest text-xs">Cible Provider</p>
                  <p className="text-[10px] font-medium opacity-60 mt-1">Envoyer vers une playlist Spotify/Deezer...</p>
                </div>
              </button>
            </div>

            {downloadTarget === 'playlist' && (
              <motion.div 
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-8 p-6 bg-gray-50 dark:bg-slate-800/50 rounded-3xl space-y-4"
              >
                <div className="flex items-center justify-between">
                  <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Choisir une playlist existante</label>
                  <button 
                    onClick={() => setShowNewPlaylistInput(!showNewPlaylistInput)}
                    className="flex items-center gap-1 text-[10px] font-black text-emerald-500 hover:underline"
                  >
                    <Plus size={12} /> {showNewPlaylistInput ? 'Annuler' : 'Nouvelle playlist'}
                  </button>
                </div>
                
                {showNewPlaylistInput ? (
                  <div className="flex gap-2">
                    <input 
                      type="text"
                      value={newPlaylistName}
                      onChange={(e) => setNewPlaylistName(e.target.value)}
                      placeholder="Nom de la nouvelle playlist..."
                      className="flex-1 bg-white dark:bg-slate-900 border-2 border-emerald-100 dark:border-emerald-900/30 rounded-2xl px-4 py-3 font-bold outline-none focus:border-emerald-500 transition-all text-sm"
                    />
                    <button 
                      onClick={handleCreateAndSelectPlaylist}
                      disabled={!newPlaylistName.trim()}
                      className="px-6 py-3 bg-emerald-500 text-white rounded-2xl font-black text-xs hover:bg-emerald-600 transition-all disabled:opacity-50"
                    >
                      Créer
                    </button>
                  </div>
                ) : (
                  <select 
                    value={selectedTargetPlaylist || ''}
                    onChange={(e) => setSelectedTargetPlaylist(e.target.value)}
                    className="w-full bg-white dark:bg-slate-900 border-2 border-gray-100 dark:border-slate-800 rounded-2xl px-4 py-3 font-bold outline-none focus:border-emerald-500 transition-all"
                  >
                    <option value="">Sélectionner une playlist...</option>
                    {userPlaylists.map(pl => (
                      <option key={pl.id} value={pl.id}>{pl.name}</option>
                    ))}
                  </select>
                )}
              </motion.div>
            )}

            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-2xl flex items-center justify-center text-blue-600 dark:text-blue-400">
                  <Sparkles size={24} />
                </div>
                <div>
                  <h4 className="text-xl font-black text-gray-900 dark:text-white tracking-tight">
                    {stagedTracks.length} morceaux détectés
                  </h4>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <button
                  onClick={() => {
                    const isAnyActive = stagedTracks.some(t => {
                      const task = t.taskId ? tasks[t.taskId] : null;
                      return task && (task.status === 'PROCESSING' || task.status === 'PENDING');
                    });
                    if (isAnyActive) {
                      if (window.confirm("Certains téléchargements sont en cours. Voulez-vous vraiment fermer cette liste ?")) {
                        setStagedTracks([]);
                      }
                    } else {
                      setStagedTracks([]);
                    }
                  }}
                  className="px-6 py-3 rounded-2xl font-bold text-sm text-gray-500 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors flex items-center gap-2"
                >
                  <X size={18} />
                  Annuler
                </button>
                <button
                  onClick={() => startDownloads()}
                  disabled={stagedTracks.some(t => {
                    const task = t.taskId ? tasks[t.taskId] : null;
                    return task && (task.status === 'PROCESSING' || task.status === 'PENDING');
                  })}
                  className={`px-8 py-3 rounded-2xl font-black text-sm shadow-xl transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed ${
                    downloadTarget === 'playlist' 
                      ? 'bg-emerald-500 hover:bg-emerald-600 text-white shadow-emerald-500/20' 
                      : 'bg-blue-600 hover:bg-blue-700 text-white shadow-blue-500/20'
                  }`}
                >
                  {stagedTracks.some(t => {
                    const task = t.taskId ? tasks[t.taskId] : null;
                    return task && (task.status === 'PROCESSING' || task.status === 'PENDING');
                  }) ? (
                    <>
                      <Loader2 size={18} className="animate-spin" />
                      Téléchargement...
                    </>
                  ) : (
                    <>
                      <Download size={18} />
                      {downloadTarget === 'playlist' ? 'Envoyer & Télécharger' : 'Tout télécharger'}
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="max-h-[500px] overflow-y-auto pr-4 space-y-4 custom-scrollbar">
              {stagedTracks.map((track, idx) => {
                const activeTask = track.taskId ? tasks[track.taskId] : null;
                const isProcessing = activeTask && (activeTask.status === 'PROCESSING' || activeTask.status === 'PENDING');
                const isCompleted = activeTask?.status === 'COMPLETED';
                const isFailed = activeTask?.status === 'FAILED';

                return (
                  <div 
                    key={idx}
                    className={`flex flex-col p-5 rounded-[2rem] border transition-all ${
                      isProcessing 
                        ? 'bg-blue-50/30 border-blue-100 dark:bg-blue-900/10 dark:border-blue-800/50' 
                        : isCompleted
                        ? 'bg-green-50/30 border-green-100 dark:bg-green-900/10 dark:border-green-800/50'
                        : 'bg-gray-50 dark:bg-slate-800/50 border-transparent hover:border-blue-100 dark:hover:border-blue-900/30'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-4">
                      <div className="flex items-center gap-4 flex-1 min-w-0">
                        <div className="w-12 h-12 bg-white dark:bg-slate-700 rounded-2xl flex items-center justify-center text-gray-400 shadow-sm overflow-hidden relative">
                          {track.cover_url ? (
                            <img src={track.cover_url} alt="" className="w-full h-full object-cover" />
                          ) : (
                            <Music size={24} />
                          )}
                          {isProcessing && (
                            <div className="absolute inset-0 bg-blue-600/20 flex items-center justify-center">
                              <Loader2 size={20} className="text-blue-600 animate-spin" />
                            </div>
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-black text-gray-900 dark:text-white leading-tight truncate">
                            {track.title || track.url}
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            <ProviderIcon provider={track.provider} size={14} />
                            <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest truncate">
                              {track.artist || 'Artiste inconnu'} • <span className="text-blue-500">{track.provider || 'Source directe'}</span>
                            </p>
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex flex-col items-end gap-1">
                        {isProcessing ? (
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-black text-blue-600 dark:text-blue-400 uppercase tracking-tighter bg-blue-50 dark:bg-blue-900/30 px-2 py-1 rounded-lg">
                              {activeTask?.progress || 0}%
                            </span>
                          </div>
                        ) : isCompleted ? (
                          <div className="flex items-center gap-2 px-3 py-1 bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 rounded-xl text-[10px] font-black uppercase tracking-widest border border-green-100 dark:border-green-800">
                            <CheckCircle2 size={12} />
                            Prêt
                          </div>
                        ) : isFailed ? (
                          <div className="flex items-center gap-2 px-3 py-1 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl text-[10px] font-black uppercase tracking-widest border border-red-100 dark:border-red-800">
                            <AlertCircle size={12} />
                            Erreur
                          </div>
                        ) : (
                          <div className="flex items-center gap-2 px-3 py-1 bg-gray-100 dark:bg-slate-700 text-gray-400 rounded-xl text-[10px] font-black uppercase tracking-widest">
                            Attente
                          </div>
                        )}
                      </div>
                    </div>

                    {isProcessing && (
                      <div className="mt-4 space-y-3">
                        <div className="w-full h-1.5 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden">
                          <motion.div 
                            initial={{ width: 0 }}
                            animate={{ width: `${activeTask?.progress || 0}%` }}
                            className="h-full bg-blue-600 shadow-[0_0_10px_rgba(37,99,235,0.5)]"
                          />
                        </div>
                        <div className="flex items-center justify-between text-[9px] font-black uppercase tracking-widest text-gray-400">
                          <div className="flex items-center gap-3">
                            <span className="flex items-center gap-1">
                              <TrendingUp size={10} className="text-blue-500" />
                              {activeTask?.speed || '0 KB/s'}
                            </span>
                            <span className="flex items-center gap-1">
                              <History size={10} className="text-purple-500" />
                              Restant: {activeTask?.eta || '--:--'}
                            </span>
                          </div>
                          <span className="text-blue-600 dark:text-blue-400">
                            {activeTask?.message || 'Initialisation...'}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default CSVUpload;
