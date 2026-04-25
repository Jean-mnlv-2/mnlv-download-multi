import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Music, 
  Layers, 
  ExternalLink, 
  Download, 
  Plus, 
  Loader2, 
  ShieldCheck,
  ChevronRight,
  Library,
  ArrowUp,
  ArrowDown,
  Trash2,
  RefreshCw,
  X,
  BookOpen,
  Book
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { useTaskStore } from '../../store/useTaskStore';
import { useAuthStore } from '../../store/useAuthStore';
import ProviderIcon from './ProviderIcon';

interface Playlist {
  id: string;
  name: string;
  track_count: number;
  owner: string;
  url: string;
  cover_url?: string;
  snapshot_id?: string;
  isSpecial?: boolean;
  tracks?: any[];
  type?: 'playlist' | 'audiobook';
}

interface Provider {
  id: string;
  name: string;
  color: string;
  icon: any;
  loginUrl?: string;
  isPublic?: boolean;
}

const PlaylistExplorer: React.FC = () => {
  const { t } = useTranslation();
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [activeTab, setActiveTab] = useState<'playlists' | 'audiobooks'>('playlists');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { addNotification, addTask, pollTaskStatus } = useTaskStore();
  const { accessToken } = useAuthStore();

  const providers: Provider[] = [
    { id: 'spotify', name: 'Spotify', color: 'bg-emerald-600', icon: Music, loginUrl: '/api/auth/providers/spotify/login/' },
    { id: 'deezer', name: 'Deezer', color: 'bg-purple-600', icon: Library, loginUrl: '/api/auth/providers/deezer/login/' },
    { id: 'apple_music', name: 'Apple Music', color: 'bg-rose-600', icon: Music, loginUrl: '/api/auth/providers/apple-music/login/' },
    { id: 'soundcloud', name: 'SoundCloud', color: 'bg-orange-600', icon: Music, loginUrl: '/api/auth/providers/soundcloud/login/' },
    { id: 'tidal', name: 'Tidal', color: 'bg-slate-900', icon: Music, loginUrl: '/api/auth/providers/tidal/login/' },
    { id: 'amazon_music', name: 'Amazon Music', color: 'bg-blue-400', icon: Music, loginUrl: '/api/auth/providers/amazon-music/login/' },
    { id: 'youtube_music', name: 'YouTube Music', color: 'bg-red-600', icon: Music, isPublic: true },
    { id: 'boomplay', name: 'Boomplay', color: 'bg-blue-600', icon: Music, isPublic: true },
  ];

  const [connectionStatus, setConnectionStatus] = useState<Record<string, boolean>>({});
  const [activeProvider, setActiveTabProvider] = useState('spotify');
  const [activeView, setActiveView] = useState<'playlists' | 'likes' | 'stream'>('playlists');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newPlaylistName, setNewPlaylistName] = useState('');
  const [newPlaylistDescription, setNewPlaylistDescription] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    const checkConnection = async () => {
      try {
        const response = await axios.get('/api/auth/providers/status/');
        setConnectionStatus(response.data);
        if (response.data.spotify) {
          setActiveTabProvider('spotify');
        } else if (response.data.deezer) {
          setActiveTabProvider('deezer');
        } else if (response.data.apple_music) {
          setActiveTabProvider('apple_music');
        }
      } catch (err) {
        // Handle error
      }
    };
    checkConnection();
  }, []);

  const fetchContent = async (view: 'playlists' | 'likes' | 'stream' = activeView) => {
    setLoading(true);
    setError('');
    try {
      let action = 'GET_LIST';
      if (view === 'likes') action = 'GET_LIKES';
      if (view === 'stream') action = 'GET_STREAM';

      const response = await axios.post('/api/playlist/manage/', {
        action: action,
        provider_url: `https://${activeProvider}.com`,
        provider: activeProvider
      });
      
      if (view === 'playlists') {
        setPlaylists(response.data.playlists || []);
      } else {
        const tracksAsPlaylists = [{
          id: view,
          name: view === 'likes' ? 'Titres Likés' : 'Mon Stream',
          track_count: response.data.tracks?.length || 0,
          owner: 'Moi',
          url: '',
          isSpecial: true,
          tracks: response.data.tracks
        }];
        setPlaylists(tracksAsPlaylists as any);
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || "Impossible de récupérer le contenu";
      setError(errorMsg);
      
      if (err.response?.status === 401) {
        addNotification('error', "Session expirée. Veuillez vous reconnecter.");
        setConnectionStatus(prev => ({ ...prev, [activeProvider]: false }));
      } else {
        addNotification('error', errorMsg);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setActiveTab('playlists');
    fetchContent();
  }, [activeProvider]);

  useEffect(() => {
    const hasAudiobooks = playlists.some(item => item.type === 'audiobook');
    if (activeTab === 'audiobooks' && !loading && !hasAudiobooks) {
      setActiveTab('playlists');
    }
  }, [playlists, loading, activeTab]);

  const handleConnect = async (providerId: string) => {
    if (providerId === 'apple_music') {
      try {
        const tokenRes = await axios.get('/api/auth/providers/apple-music/token/');
        const developerToken = tokenRes.data.token;

        if (!(window as any).MusicKit) {
          const script = document.createElement('script');
          script.src = 'https://js-cdn.music.apple.com/musickit/v3/musickit.js';
          document.head.appendChild(script);
          await new Promise((resolve) => { script.onload = resolve; });
        }

        const music = await (window as any).MusicKit.configure({
          developerToken: developerToken,
          app: {
            name: 'MNLV Music',
            build: '2.0.0'
          }
        });

        // 3. Authorize
        const musicUserToken = await music.authorize();

        // 4. Send token to backend
        await axios.post('/api/auth/providers/apple-music/login/', {
          music_user_token: musicUserToken
        });

        addNotification('success', "Apple Music connecté avec succès");
        setConnectionStatus(prev => ({ ...prev, apple_music: true }));
        setActiveTabProvider('apple_music');
      } catch (err: any) {
        addNotification('error', "Échec de la connexion Apple Music");
      }
      return;
    }

    const provider = providers.find(p => p.id === providerId);
    if (provider) {
      if (provider.isPublic || !provider.loginUrl) {
        addNotification('info', "Ce service ne nécessite pas de connexion");
        return;
      }
      try {
        const response = await axios.get(provider.loginUrl);
        if (response.data.auth_url) {
          window.location.href = response.data.auth_url;
        } else if (response.data.message) {
          addNotification('info', response.data.message);
        }
      } catch (err: any) {
        addNotification('error', err.response?.data?.message || "Impossible de se connecter");
      }
    }
  };

  const handleDeezerAction = async (action: 'flow' | 'favorites') => {
    setLoading(true);
    try {
      if (action === 'flow') {
        const response = await axios.get('/api/auth/providers/deezer/flow/');
        response.data.tasks.forEach((t: any) => {
          addTask({ id: t.task_id, status: 'PENDING', progress: 0, original_url: 'Flow Deezer', provider: 'deezer' });
          pollTaskStatus(t.task_id);
        });
        addNotification('success', `Flow Deezer lancé : ${response.data.tasks.length} titres`);
      } else {
        const response = await axios.get('/api/auth/providers/deezer/favorites/');
        const tracks = response.data.map((t: any) => ({
          ...t,
          id: t.isrc || t.original_url,
          name: t.title,
          url: t.original_url
        }));
        setPlaylists([{
          id: 'favorites',
          name: 'Mes Coups de Cœur',
          track_count: tracks.length,
          owner: 'Moi',
          url: 'https://www.deezer.com/my/favorites',
          cover_url: 'https://e-cdns-images.dzcdn.net/images/user/e1a6c4f0-466d-4923-956b-801267868772/250x250-000000-80-0-0.jpg',
          isSpecial: true,
          tracks: tracks
        }]);
      }
    } catch (err: any) {
      addNotification('error', "Erreur Deezer");
    } finally {
      setLoading(false);
    }
  };

  const downloadPlaylist = async (playlist: Playlist) => {
    try {
      const url = playlist.url;
      // Si c'est une vue spéciale (Likes/Stream), on envoie les tracks au lieu de l'URL
      const payload = playlist.isSpecial ? { tracks: playlist.tracks } : { url };
      
      const response = await axios.post('/api/download/', payload);
      const data = response.data;
      if (data.type === 'playlist') {
        data.tasks.forEach((t: any) => {
          addTask({ 
            id: t.task_id, 
            status: 'PENDING', 
            progress: 0, 
            original_url: url, 
            provider: data.provider || activeProvider || 'URL' 
          });
          pollTaskStatus(t.task_id);
        });
        addNotification('success', `${data.tasks.length} ${t('processing')}`);
      }
    } catch (err) {
      addNotification('error', t('failed'));
    }
  };

  const handleCreatePlaylist = async () => {
    if (!newPlaylistName.trim()) {
      addNotification('error', 'Le nom de la playlist est requis');
      return;
    }
    setCreating(true);
    try {
      await axios.post('/api/playlist/manage/', {
        action: 'CREATE',
        provider: activeProvider,
        provider_url: `https://${activeProvider === 'apple_music' ? 'music.apple' : activeProvider}.com`,
        name: newPlaylistName,
        description: newPlaylistDescription
      });
      addNotification('success', 'Playlist créée avec succès');
      setShowCreateModal(false);
      setNewPlaylistName('');
      setNewPlaylistDescription('');
      fetchContent();
    } catch (err: any) {
      addNotification('error', err.response?.data?.error || 'Erreur lors de la création');
    } finally {
      setCreating(false);
    }
  };

  const handleDeletePlaylist = async (playlist: Playlist) => {
    if (!window.confirm(`Voulez-vous vraiment supprimer la playlist "${playlist.name}" ?`)) return;
    
    try {
      await axios.post('/api/playlist/manage/', {
        action: 'DELETE',
        provider: activeProvider,
        provider_url: playlist.url || `https://${activeProvider === 'apple_music' ? 'music.apple' : activeProvider}.com`,
        playlist_id: playlist.id
      });
      addNotification('success', 'Playlist supprimée');
      fetchContent();
    } catch (err: any) {
      addNotification('error', 'Erreur lors de la suppression');
    }
  };

  const handleReorder = async (playlist: Playlist, rangeStart: number, insertBefore: number) => {
    try {
      const response = await axios.post('/api/playlist/manage/', {
        action: 'REORDER',
        provider_url: playlist.url,
        playlist_id: playlist.id,
        range_start: rangeStart,
        insert_before: insertBefore,
        snapshot_id: playlist.snapshot_id
      });
      if (response.data.snapshot_id) {
        setPlaylists(prev => prev.map(p => 
          p.id === playlist.id ? { ...p, snapshot_id: response.data.snapshot_id } : p
        ));
        addNotification('success', 'Ordre mis à jour');
      }
    } catch (err: any) {
      addNotification('error', 'Erreur lors de la réorganisation');
    }
  };

  const filteredItems = playlists.filter(item => {
    if (activeTab === 'audiobooks') return item.type === 'audiobook';
    return !item.type || item.type === 'playlist';
  });

  const hasAudiobooks = playlists.some(item => item.type === 'audiobook');
  const isAnyConnected = Object.values(connectionStatus).some(status => status);

  if (!isAnyConnected) {
    return (
      <div className="w-full max-w-6xl mx-auto space-y-12">
        <div className="text-center py-16 bg-white dark:bg-slate-900 rounded-[3rem] border border-gray-100 dark:border-slate-800 shadow-sm">
          <div className="w-20 h-20 bg-blue-50 dark:bg-blue-900/20 rounded-[2rem] flex items-center justify-center mx-auto mb-8 text-blue-600 dark:text-blue-400">
            <ShieldCheck size={40} />
          </div>
          <h3 className="text-3xl font-black text-gray-900 dark:text-white mb-4 tracking-tight">Connexion requise</h3>
          <p className="text-gray-500 dark:text-gray-400 font-medium max-w-sm mx-auto mb-12 leading-relaxed">
            Connectez vos comptes musicaux pour explorer vos playlists et les télécharger en un clic.
          </p>
          
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 px-10">
            {providers.map((p) => (
              <button
                key={p.id}
                onClick={() => handleConnect(p.id)}
                className={`group relative overflow-hidden p-8 rounded-[2.5rem] border border-gray-100 dark:border-slate-800 transition-all hover:shadow-2xl active:scale-95 flex flex-col items-center gap-4 bg-white dark:bg-slate-900`}
              >
                <div className={`w-14 h-14 bg-white dark:bg-slate-800 rounded-2xl flex items-center justify-center shadow-lg transition-transform group-hover:scale-110 border border-gray-100 dark:border-slate-700`}>
                  <ProviderIcon provider={p.id} size={32} />
                </div>
                <div>
                  <p className="font-black text-gray-900 dark:text-white text-sm">{p.isPublic ? 'Explorer' : 'Connecter'}</p>
                  <p className="font-bold text-gray-400 text-xs uppercase tracking-widest">{p.name}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-black text-xs uppercase tracking-widest">
            <Library size={14} />
            <span>Votre Bibliothèque {activeProvider === 'spotify' ? '(Spotify Full Access)' : ''}</span>
          </div>
          
          <div className="flex items-center gap-8 relative pb-2">
            <button 
              onClick={() => setActiveTab('playlists')}
              className={`relative text-3xl font-black tracking-tight transition-all ${activeTab === 'playlists' ? 'text-gray-900 dark:text-white' : 'text-gray-300 dark:text-gray-600 hover:text-gray-400'}`}
            >
              Mes Playlists
              {activeTab === 'playlists' && (
                <motion.div 
                  layoutId="activeTabUnderline"
                  className="absolute -bottom-2 left-0 right-0 h-1 bg-emerald-500 rounded-full"
                />
              )}
            </button>
            
            {hasAudiobooks && (
              <button 
                onClick={() => setActiveTab('audiobooks')}
                className={`relative text-3xl font-black tracking-tight transition-all ${activeTab === 'audiobooks' ? 'text-gray-900 dark:text-white' : 'text-gray-300 dark:text-gray-600 hover:text-gray-400'}`}
              >
                Livres Audio
                {activeTab === 'audiobooks' && (
                  <motion.div 
                    layoutId="activeTabUnderline"
                    className="absolute -bottom-2 left-0 right-0 h-1 bg-blue-500 rounded-full"
                  />
                )}
              </button>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {connectionStatus.deezer && (
            <div className="flex bg-gray-100 dark:bg-slate-800 p-1 rounded-2xl border border-gray-200 dark:border-slate-700">
              <button 
                onClick={() => handleDeezerAction('flow')}
                className="px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg hover:scale-105 transition-all active:scale-95"
              >
                Mon Flow
              </button>
              <button 
                onClick={() => handleDeezerAction('favorites')}
                className="px-4 py-2 text-gray-500 dark:text-gray-400 hover:text-purple-600 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all"
              >
                Favoris
              </button>
            </div>
          )}
          <button 
            onClick={() => fetchContent()}
            disabled={loading}
            className="p-3 bg-white dark:bg-slate-800 text-gray-400 hover:text-emerald-500 rounded-xl border border-gray-100 dark:border-slate-700 transition-all shadow-sm"
            title="Actualiser la liste"
          >
            <RefreshCw size={20} className={loading ? "animate-spin" : ""} />
          </button>
          <button 
            onClick={() => setShowCreateModal(true)}
            className="p-3 bg-emerald-500 text-white hover:bg-emerald-600 rounded-xl transition-all shadow-lg shadow-emerald-500/20"
            title="Créer une nouvelle playlist"
          >
            <Plus size={20} />
          </button>
        </div>
      </div>

      {/* Tabs de Navigation SoundCloud/Générique */}
      {isAnyConnected && (
        <div className="flex gap-4 mb-8 overflow-x-auto pb-2 custom-scrollbar">
          {providers.map((p) => connectionStatus[p.id] && (
            <button
              key={p.id}
              onClick={() => setActiveTabProvider(p.id)}
              className={`flex items-center gap-3 px-6 py-3 rounded-2xl text-sm font-black transition-all ${activeProvider === p.id ? 'bg-white dark:bg-slate-800 text-gray-900 dark:text-white shadow-xl shadow-gray-200/50 dark:shadow-none ring-1 ring-gray-100 dark:ring-slate-700' : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-200'}`}
            >
              <ProviderIcon provider={p.id} size={20} />
              <span className="uppercase tracking-widest text-[10px]">{p.name}</span>
            </button>
          ))}
        </div>
      )}

      {loading && playlists.length === 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <div key={i} className="h-64 bg-gray-100 dark:bg-slate-800 rounded-[2.5rem] animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
          {filteredItems.map((playlist) => (
            <motion.div
              key={playlist.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              whileHover={{ y: -5 }}
              className="group bg-white dark:bg-slate-900 rounded-[2.5rem] overflow-hidden border border-gray-100 dark:border-slate-800 shadow-sm hover:shadow-2xl hover:shadow-emerald-500/10 transition-all"
            >
              <div className="aspect-square relative overflow-hidden bg-gray-100 dark:bg-slate-800">
                {playlist.cover_url ? (
                  <img 
                    src={playlist.cover_url} 
                    alt={playlist.name}
                    className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-400">
                    <Music size={48} />
                  </div>
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-6">
                  <button 
                    onClick={() => downloadPlaylist(playlist)}
                    className="w-full py-3 bg-emerald-500 text-white rounded-2xl font-black text-sm flex items-center justify-center gap-2 transform translate-y-4 group-hover:translate-y-0 transition-transform"
                  >
                    <Download size={16} />
                    Tout télécharger
                  </button>
                </div>
              </div>
              
              <div className="p-6 space-y-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h4 className="text-lg font-black text-gray-900 dark:text-white truncate tracking-tight">{playlist.name}</h4>
                      {playlist.tracks?.some((t: any) => t.explicit) && (
                        <span className="px-1 text-[10px] font-bold border border-gray-400 text-gray-400 rounded uppercase flex-shrink-0">E</span>
                      )}
                    </div>
                    <p className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">{playlist.track_count} titres</p>
                  </div>
                <div className="flex flex-col gap-1">
                  {!playlist.isSpecial && (
                    <>
                      <button 
                        onClick={() => handleReorder(playlist, 1, 0)}
                        className="p-1.5 text-gray-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-all"
                        title="Remonter le titre"
                      >
                        <ArrowUp size={14} />
                      </button>
                      <button 
                        onClick={() => handleReorder(playlist, 0, 2)}
                        className="p-1.5 text-gray-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-all"
                        title="Descendre le titre"
                      >
                        <ArrowDown size={14} />
                      </button>
                    </>
                  )}
                </div>
                </div>
                
                <div className="flex items-center justify-between pt-2 border-t border-gray-50 dark:border-slate-800">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-black text-gray-300 dark:text-gray-600 uppercase tracking-widest">{playlist.owner}</span>
                    {playlist.snapshot_id && (
                      <span className="w-1.5 h-1.5 bg-green-500 rounded-full" title="Synchronisé" />
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <button 
                      onClick={() => handleDeletePlaylist(playlist)}
                      className="p-2 text-gray-300 hover:text-red-500 transition-colors"
                      title="Supprimer la playlist"
                    >
                      <Trash2 size={16} />
                    </button>
                    <a 
                      href={playlist.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className={`p-2 text-gray-300 hover:text-emerald-500 dark:text-gray-700 dark:hover:text-emerald-400 transition-colors ${playlist.isSpecial ? 'pointer-events-none opacity-20' : ''}`}
                    >
                      <ExternalLink size={16} />
                    </a>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {error && (
        <div className="p-10 text-center bg-red-50 dark:bg-red-900/20 rounded-[2.5rem] border border-red-100 dark:border-red-900/50 space-y-4">
          <p className="text-red-500 font-black uppercase tracking-widest text-xs">{error}</p>
          <div className="flex justify-center gap-4">
            <button 
              onClick={() => fetchContent()}
              className="px-6 py-2 bg-red-500 text-white rounded-xl text-xs font-bold hover:bg-red-600 transition-colors shadow-lg shadow-red-500/20"
            >
              Réessayer
            </button>
            <button 
              onClick={() => handleConnect(activeProvider)}
              className="px-6 py-2 bg-white dark:bg-slate-800 text-red-500 rounded-xl text-xs font-bold border border-red-200 dark:border-red-900/50 hover:bg-red-50 transition-colors"
            >
              Reconnexion
            </button>
          </div>
        </div>
      )}

      {/* Modal de Création de Playlist */}
      <AnimatePresence>
        {showCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowCreateModal(false)}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="relative w-full max-w-md bg-white dark:bg-slate-900 rounded-[2.5rem] p-8 shadow-2xl overflow-hidden"
            >
              <div className="absolute top-0 left-0 w-full h-2 bg-emerald-500" />
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-2xl font-black text-gray-900 dark:text-white tracking-tight">Nouvelle Playlist</h3>
                <button 
                  onClick={() => setShowCreateModal(false)}
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                >
                  <X size={24} />
                </button>
              </div>

              <div className="space-y-6">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Nom de la playlist</label>
                  <input
                    type="text"
                    value={newPlaylistName}
                    onChange={(e) => setNewPlaylistName(e.target.value)}
                    placeholder="Ma super playlist"
                    className="w-full px-6 py-4 bg-gray-50 dark:bg-slate-800 border-2 border-transparent focus:border-emerald-500 rounded-2xl outline-none transition-all font-bold text-gray-700 dark:text-white"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Description (optionnelle)</label>
                  <textarea
                    value={newPlaylistDescription}
                    onChange={(e) => setNewPlaylistDescription(e.target.value)}
                    placeholder="Une petite description..."
                    rows={3}
                    className="w-full px-6 py-4 bg-gray-50 dark:bg-slate-800 border-2 border-transparent focus:border-emerald-500 rounded-2xl outline-none transition-all font-bold text-gray-700 dark:text-white resize-none"
                  />
                </div>

                <div className="flex items-center gap-3 pt-4">
                  <button
                    onClick={() => setShowCreateModal(false)}
                    className="flex-1 py-4 text-sm font-black text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
                  >
                    Annuler
                  </button>
                  <button
                    onClick={handleCreatePlaylist}
                    disabled={creating || !newPlaylistName.trim()}
                    className="flex-[2] py-4 bg-emerald-500 hover:bg-emerald-600 disabled:bg-gray-200 dark:disabled:bg-slate-800 text-white rounded-2xl font-black text-sm transition-all shadow-lg shadow-emerald-500/20 active:scale-95 flex items-center justify-center gap-2"
                  >
                    {creating ? <Loader2 size={18} className="animate-spin" /> : <Plus size={18} />}
                    Créer sur {activeProvider}
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default PlaylistExplorer;

