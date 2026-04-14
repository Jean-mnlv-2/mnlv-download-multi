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
  Library
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { useTaskStore } from '../../store/useTaskStore';
import { useAuthStore } from '../../store/useAuthStore';

interface Playlist {
  id: string;
  name: string;
  track_count: number;
  owner: string;
  url: string;
  cover_url?: string;
}

const PlaylistExplorer: React.FC = () => {
  const { t } = useTranslation();
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const { addNotification, addTask, pollTaskStatus } = useTaskStore();
  const { accessToken } = useAuthStore();

  const providers = [
    { id: 'spotify', name: 'Spotify', color: 'bg-emerald-600', icon: Music, loginUrl: '/api/auth/providers/spotify/login/' },
    { id: 'deezer', name: 'Deezer', color: 'bg-purple-600', icon: Library, loginUrl: '/api/auth/providers/deezer/login/' },
    { id: 'apple_music', name: 'Apple Music', color: 'bg-rose-600', icon: Music, loginUrl: '/api/auth/providers/apple-music/login/' },
  ];

  const [connectionStatus, setConnectionStatus] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const checkConnection = async () => {
      try {
        const response = await axios.get('/api/auth/providers/status/');
        setConnectionStatus(response.data);
        if (response.data.spotify) {
          fetchPlaylists();
        }
      } catch (err) {
        // Handle error
      }
    };
    checkConnection();
  }, []);

  const handleConnect = async (providerId: string) => {
    const provider = providers.find(p => p.id === providerId);
    if (provider) {
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

  const fetchPlaylists = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.post('/api/playlist/manage/', {
        action: 'GET_LIST',
        provider: 'spotify'
      });
      setPlaylists(response.data.playlists);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erreur lors de la récupération des playlists');
    } finally {
      setLoading(false);
    }
  };

  const downloadPlaylist = async (url: string) => {
    try {
      const response = await axios.post('/api/download/', { url });
      const data = response.data;
      if (data.type === 'playlist') {
        data.tasks.forEach((t: any) => {
          addTask({ 
            id: t.task_id, 
            status: 'PENDING', 
            progress: 0, 
            original_url: url, 
            provider: 'spotify' 
          });
          pollTaskStatus(t.task_id);
        });
        addNotification('success', `${data.tasks.length} ${t('processing')}`);
      }
    } catch (err) {
      addNotification('error', t('failed'));
    }
  };

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
                <div className={`w-14 h-14 ${p.color} text-white rounded-2xl flex items-center justify-center shadow-lg transition-transform group-hover:scale-110`}>
                  <p.icon size={28} />
                </div>
                <div>
                  <p className="font-black text-gray-900 dark:text-white text-sm">Connecter</p>
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
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-black text-xs uppercase tracking-widest">
            <Library size={14} />
            <span>Votre Bibliothèque</span>
          </div>
          <h2 className="text-3xl font-black text-gray-900 dark:text-white tracking-tight">Mes Playlists</h2>
        </div>
        <button 
          onClick={fetchPlaylists}
          disabled={loading}
          className="p-3 bg-white dark:bg-slate-800 text-gray-400 hover:text-emerald-500 rounded-xl border border-gray-100 dark:border-slate-700 transition-all shadow-sm"
        >
          {loading ? <Loader2 size={20} className="animate-spin" /> : <Plus size={20} />}
        </button>
      </div>

      {loading && playlists.length === 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <div key={i} className="h-64 bg-gray-100 dark:bg-slate-800 rounded-[2.5rem] animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
          {playlists.map((playlist) => (
            <motion.div
              key={playlist.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              whileHover={{ y: -5 }}
              className="group bg-white dark:bg-slate-900 rounded-[2.5rem] overflow-hidden border border-gray-100 dark:border-slate-800 shadow-sm hover:shadow-2xl hover:shadow-emerald-500/10 transition-all"
            >
              <div className="aspect-square relative overflow-hidden">
                <img 
                  src={playlist.cover_url || 'https://via.placeholder.com/300?text=Playlist'} 
                  alt={playlist.name}
                  className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-6">
                  <button 
                    onClick={() => downloadPlaylist(playlist.url)}
                    className="w-full py-3 bg-emerald-500 text-white rounded-2xl font-black text-sm flex items-center justify-center gap-2 transform translate-y-4 group-hover:translate-y-0 transition-transform"
                  >
                    <Download size={16} />
                    Tout télécharger
                  </button>
                </div>
              </div>
              
              <div className="p-6 space-y-4">
                <div className="min-w-0">
                  <h4 className="text-lg font-black text-gray-900 dark:text-white truncate tracking-tight">{playlist.name}</h4>
                  <p className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">{playlist.track_count} titres</p>
                </div>
                
                <div className="flex items-center justify-between pt-2 border-t border-gray-50 dark:border-slate-800">
                  <span className="text-[10px] font-black text-gray-300 dark:text-gray-600 uppercase tracking-widest">{playlist.owner}</span>
                  <a 
                    href={playlist.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="p-2 text-gray-300 hover:text-emerald-500 dark:text-gray-700 dark:hover:text-emerald-400 transition-colors"
                  >
                    <ExternalLink size={16} />
                  </a>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {error && (
        <div className="p-10 text-center bg-red-50 dark:bg-red-900/20 rounded-[2.5rem] border border-red-100 dark:border-red-900/50">
          <p className="text-red-500 font-bold uppercase tracking-widest text-xs">{error}</p>
        </div>
      )}
    </div>
  );
};

export default PlaylistExplorer;

