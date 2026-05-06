import React, { useState, useEffect } from 'react';
import { useTaskStore } from '../../store/useTaskStore';
import { useAuthStore } from '../../store/useAuthStore';
import { LocalFileSystemService } from '../../services/localFileSystem';
import axios from 'axios';
import { 
  Music, 
  FolderOpen, 
  LayoutGrid, 
  Check, 
  Plus, 
  X, 
  Download, 
  Loader2, 
  Sparkles,
  ListMusic
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ProviderIcon from './ProviderIcon';

const StagingArea: React.FC = () => {
  const { stagedTracks, setStagedTracks, tasks, addTask, pollTaskStatus, addNotification, localDirectorySelected, setLocalDirectorySelected } = useTaskStore();
  const { providerStatus, accessToken } = useAuthStore();
  
  const [downloadTarget, setDownloadTarget] = useState<'local' | 'playlist'>('local');
  const [selectedTargetPlaylist, setSelectedTargetPlaylist] = useState<string | null>(null);
  const [showNewPlaylistInput, setShowNewPlaylistInput] = useState(false);
  const [newPlaylistName, setNewPlaylistName] = useState('');
  const [userPlaylists, setUserPlaylists] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (stagedTracks.length > 0 && downloadTarget === 'playlist' && accessToken) {
      fetchUserPlaylists();
    }
  }, [downloadTarget, stagedTracks, accessToken]);

  const fetchUserPlaylists = async () => {
    const provider = stagedTracks[0]?.provider || 'spotify';
    if (provider === 'unknown' || provider === 'batch' || provider === 'search') return;
    
    try {
      const res = await axios.post('/api/playlist/manage/', {
        action: 'GET_LIST',
        provider: provider,
        provider_url: `https://${provider === 'apple_music' ? 'music.apple' : provider}.com`
      });
      setUserPlaylists(res.data.playlists || []);
    } catch (err) {}
  };

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

  const handleSelectLocalDir = async () => {
    setDownloadTarget('local');
    try {
      const success = await LocalFileSystemService.selectDirectory();
      if (success) {
        setLocalDirectorySelected(true);
        addNotification('success', "Dossier local configuré !");
      }
    } catch (err) {}
  };

  const startDownloads = async () => {
    if (stagedTracks.length === 0) return;

    if (downloadTarget === 'playlist' && !selectedTargetPlaylist) {
      addNotification('error', "Veuillez choisir ou créer une playlist de destination");
      return;
    }

    if (downloadTarget === 'local' && !LocalFileSystemService.getHandle()) {
      const success = await LocalFileSystemService.selectDirectory();
      if (!success) return;
      setLocalDirectorySelected(true);
    }

    setLoading(true);
    try {
      const readyTracks = stagedTracks.filter(t => t.status === 'ready' && t.url);
      
      if (downloadTarget === 'playlist' && selectedTargetPlaylist) {
        const provider = readyTracks[0]?.provider || 'spotify';
        await axios.post('/api/playlist/manage/', {
          action: 'ADD_TRACKS',
          playlist_id: selectedTargetPlaylist,
          track_urls: readyTracks.map(t => t.url),
          provider: provider,
          provider_url: `https://${provider === 'apple_music' ? 'music.apple' : provider}.com`
        });
      }

      const response = await axios.post('/api/download/bulk/', {
        urls: readyTracks.map(t => t.url),
        media_type: 'AUDIO',
        quality: '320'
      });

      if (response.data.tasks) {
        response.data.tasks.forEach((t: any) => {
          addTask({
            id: t.task_id,
            status: t.status || 'PENDING',
            progress: 0,
            original_url: t.url,
            title: t.title || t.url,
            provider: t.provider || 'URL'
          });
          pollTaskStatus(t.task_id);
        });
        setStagedTracks([]);
        addNotification('success', `${response.data.count} téléchargements lancés`);
      }
    } catch (err) {
      addNotification('error', "Erreur lors du lancement");
    } finally {
      setLoading(false);
    }
  };

  if (stagedTracks.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-mnlv-slate-900 border border-mnlv-slate-200 dark:border-mnlv-slate-800 rounded-2xl overflow-hidden shadow-pro mb-10"
    >
      {/* Header Toolbar */}
      <div className="p-6 border-b border-mnlv-slate-100 dark:border-mnlv-slate-800 bg-mnlv-slate-50/50 dark:bg-mnlv-slate-800/30">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-mnlv-blue/10 rounded-2xl flex items-center justify-center text-mnlv-blue">
              <Sparkles size={24} />
            </div>
            <div>
              <h3 className="font-black text-xl tracking-tight">Prêt à télécharger</h3>
              <p className="text-mnlv-slate-500 text-xs font-bold uppercase tracking-widest">{stagedTracks.length} titres identifiés</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Local Storage Toggle */}
            <button
              onClick={handleSelectLocalDir}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border text-xs font-black transition-all ${
                downloadTarget === 'local' 
                  ? 'bg-mnlv-blue text-white border-mnlv-blue shadow-pro-blue' 
                  : 'bg-white dark:bg-mnlv-slate-900 border-mnlv-slate-200 dark:border-mnlv-slate-700 text-mnlv-slate-500'
              }`}
            >
              <FolderOpen size={16} />
              <span>Stockage Local</span>
              {downloadTarget === 'local' && localDirectorySelected && <Check size={14} />}
            </button>

            {/* Provider Toggle */}
            <button
              onClick={() => setDownloadTarget('playlist')}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border text-xs font-black transition-all ${
                downloadTarget === 'playlist' 
                  ? 'bg-emerald-500 text-white border-emerald-500 shadow-pro' 
                  : 'bg-white dark:bg-mnlv-slate-900 border-mnlv-slate-200 dark:border-mnlv-slate-700 text-mnlv-slate-500'
              }`}
            >
              <LayoutGrid size={16} />
              <span>Cible Provider</span>
            </button>

            <div className="h-8 w-px bg-mnlv-slate-200 dark:bg-mnlv-slate-700 mx-1" />

            <button
              onClick={() => setStagedTracks([])}
              className="p-2.5 text-mnlv-slate-400 hover:text-mnlv-red hover:bg-mnlv-red/5 rounded-xl transition-all"
              title="Tout annuler"
            >
              <X size={20} />
            </button>

            <button
              onClick={startDownloads}
              disabled={loading || (downloadTarget === 'playlist' && !selectedTargetPlaylist)}
              className={`flex items-center gap-2 px-6 py-2.5 rounded-xl font-black text-xs transition-all shadow-pro active:scale-95 disabled:opacity-50 ${
                downloadTarget === 'playlist' ? 'bg-emerald-500 text-white' : 'bg-mnlv-blue text-white'
              }`}
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
              <span>Lancer ({stagedTracks.length})</span>
            </button>
          </div>
        </div>

        {/* Playlist Selection Row */}
        <AnimatePresence>
          {downloadTarget === 'playlist' && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="mt-6 pt-6 border-t border-mnlv-slate-200/50 dark:border-mnlv-slate-700/50"
            >
              <div className="flex flex-col md:flex-row items-center gap-4">
                <div className="flex-1 w-full">
                  {showNewPlaylistInput ? (
                    <div className="flex gap-2">
                      <input 
                        type="text"
                        value={newPlaylistName}
                        onChange={(e) => setNewPlaylistName(e.target.value)}
                        placeholder="Nom de la nouvelle playlist..."
                        className="flex-1 bg-white dark:bg-mnlv-slate-900 border border-mnlv-slate-200 dark:border-mnlv-slate-700 rounded-xl px-4 py-2 text-sm font-bold outline-none focus:border-mnlv-blue"
                      />
                      <button 
                        onClick={handleCreateAndSelectPlaylist}
                        className="px-4 py-2 bg-mnlv-blue text-white rounded-xl text-xs font-black"
                      >
                        Créer
                      </button>
                    </div>
                  ) : (
                    <select 
                      value={selectedTargetPlaylist || ''}
                      onChange={(e) => setSelectedTargetPlaylist(e.target.value)}
                      className="w-full bg-white dark:bg-mnlv-slate-900 border border-mnlv-slate-200 dark:border-mnlv-slate-700 rounded-xl px-4 py-2 text-sm font-bold outline-none focus:border-mnlv-blue"
                    >
                      <option value="">Sélectionner une playlist de destination...</option>
                      {userPlaylists.map(pl => (
                        <option key={pl.id} value={pl.id}>{pl.name} ({pl.track_count} titres)</option>
                      ))}
                    </select>
                  )}
                </div>
                <button 
                  onClick={() => setShowNewPlaylistInput(!showNewPlaylistInput)}
                  className="flex items-center gap-2 text-xs font-black text-mnlv-blue hover:underline whitespace-nowrap"
                >
                  <Plus size={14} />
                  {showNewPlaylistInput ? 'Choisir existante' : 'Nouvelle playlist'}
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Tracks Table */}
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
            {stagedTracks.map((track, i) => (
              <tr key={i} className="hover:bg-mnlv-slate-50 dark:hover:bg-mnlv-slate-800/30 transition-colors group">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="relative w-10 h-10 flex-shrink-0">
                      {track.cover_url ? (
                        <img src={track.cover_url} alt="" className="w-full h-full object-cover rounded-lg shadow-sm" />
                      ) : (
                        <div className="w-full h-full bg-mnlv-slate-100 dark:bg-mnlv-slate-800 rounded-lg flex items-center justify-center text-mnlv-slate-400">
                          <Music size={16} />
                        </div>
                      )}
                      <div className="absolute -bottom-1 -right-1 bg-white dark:bg-mnlv-slate-900 rounded-full p-0.5 border border-mnlv-slate-100 dark:border-mnlv-slate-800">
                        <ProviderIcon provider={track.provider} size={10} />
                      </div>
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-bold truncate">{track.title || track.url}</p>
                      <p className="text-[10px] text-mnlv-slate-500 font-medium truncate uppercase tracking-tight">
                        {track.artist || 'Artiste inconnu'}
                      </p>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-mnlv-blue/10 text-mnlv-blue text-[10px] font-black uppercase tracking-widest">
                    <Sparkles size={10} />
                    Prêt
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-24 h-1.5 bg-mnlv-slate-100 dark:bg-mnlv-slate-800 rounded-full overflow-hidden">
                      <div className="w-0 h-full bg-mnlv-blue/30" />
                    </div>
                    <span className="text-[10px] font-black text-mnlv-slate-400">0%</span>
                  </div>
                </td>
                <td className="px-6 py-4 text-right">
                  <button 
                    onClick={() => setStagedTracks(stagedTracks.filter((_, idx) => idx !== i))}
                    className="p-2 text-mnlv-slate-300 hover:text-mnlv-red transition-colors"
                  >
                    <X size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
};

export default StagingArea;
