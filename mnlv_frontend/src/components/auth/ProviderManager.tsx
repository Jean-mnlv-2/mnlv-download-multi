import React, { useState } from 'react';
import { useAuthStore } from '../../store/useAuthStore';
import { useTaskStore } from '../../store/useTaskStore';
import axios from 'axios';
import { 
  Music, 
  CheckCircle2, 
  AlertCircle, 
  ExternalLink, 
  Loader2, 
  Settings2,
  RefreshCw,
  Unplug
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ProviderIcon from '../downloader/ProviderIcon';

interface ProviderConfig {
  id: string;
  name: string;
  color: string;
  loginUrl: string;
  description: string;
}

const ProviderManager: React.FC = () => {
  const { providerStatus, fetchProviderStatus } = useAuthStore();
  const { addNotification } = useTaskStore();
  const [loading, setLoading] = useState<string | null>(null);

  const providers: ProviderConfig[] = [
    { 
      id: 'spotify', 
      name: 'Spotify', 
      color: '#1DB954', 
      loginUrl: '/api/auth/providers/spotify/login/',
      description: 'Accédez à vos playlists et titres favoris'
    },
    { 
      id: 'deezer', 
      name: 'Deezer', 
      color: '#A238FF', 
      loginUrl: '/api/auth/providers/deezer/login/',
      description: 'Importez votre Flow et vos coups de cœur'
    },
    { 
      id: 'apple_music', 
      name: 'Apple Music', 
      color: '#FA243C', 
      loginUrl: '/api/auth/providers/apple-music/login/',
      description: 'Synchronisez votre bibliothèque iCloud'
    },
    { 
      id: 'soundcloud', 
      name: 'SoundCloud', 
      color: '#FF5500', 
      loginUrl: '/api/auth/providers/soundcloud/login/',
      description: 'Connectez vos tracks et playlists'
    },
    { 
      id: 'tidal', 
      name: 'Tidal', 
      color: '#000000', 
      loginUrl: '/api/auth/providers/tidal/login/',
      description: 'Accédez à votre contenu haute fidélité'
    },
    { 
      id: 'amazon_music', 
      name: 'Amazon Music', 
      color: '#00A8E1', 
      loginUrl: '/api/auth/providers/amazon-music/login/',
      description: 'Connectez votre compte Amazon Music'
    },
    { 
      id: 'youtube_music', 
      name: 'YouTube Music', 
      color: '#FF0000', 
      loginUrl: '', 
      description: 'Explorez le catalogue YouTube Music'
    },
    { 
      id: 'boomplay', 
      name: 'Boomplay', 
      color: '#0000FF', 
      loginUrl: '', 
      description: 'Explorez et téléchargez depuis Boomplay'
    }
  ];

  const handleConnect = async (provider: ProviderConfig) => {
    setLoading(provider.id);
    try {
      // Cas spécial pour Apple Music (MusicKit JS)
      if (provider.id === 'apple_music') {
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
          app: { name: 'MNLV Music', build: '2.0.0' }
        });

        const musicUserToken = await music.authorize();
        await axios.post('/api/auth/providers/apple-music/login/', {
          music_user_token: musicUserToken
        });

        addNotification('success', "Apple Music connecté");
        await fetchProviderStatus();
        return;
      }

      if (provider.id === 'youtube_music') {
        const authData = window.prompt("Veuillez coller votre clé API YouTube v3 ou vos headers d'authentification JSON (ytmusicapi) :");
        if (!authData) {
          setLoading(null);
          return;
        }

        await axios.post('/api/auth/providers/youtube-music/connect/', {
          auth_data: authData
        });

        addNotification('success', "YouTube Music configuré");
        await fetchProviderStatus();
        setLoading(null);
        return;
      }

      // Autres providers (OAuth2)
      if (!provider.loginUrl) {
        addNotification('info', "La connexion directe pour ce service sera bientôt disponible.");
        return;
      }
      const response = await axios.get(provider.loginUrl);
      if (response.data.auth_url) {
        window.location.href = response.data.auth_url;
      } else if (response.data.message) {
        addNotification('info', response.data.message);
      }
    } catch (err: any) {
      addNotification('error', "Échec de la connexion");
    } finally {
      setLoading(null);
    }
  };

  const handleDisconnect = async (providerId: string) => {
    if (!window.confirm(`Êtes-vous sûr de vouloir déconnecter ${providerId.replace('_', ' ')} ?`)) {
      return;
    }

    setLoading(providerId);
    try {
      await axios.post('/api/auth/providers/disconnect/', {
        provider: providerId
      });
      addNotification('success', `Déconnecté de ${providerId.replace('_', ' ')}`);
      await fetchProviderStatus();
    } catch (err: any) {
      addNotification('error', "Échec de la déconnexion");
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h3 className="text-xl font-black text-gray-900 dark:text-white tracking-tight">Services Connectés</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">Gérez vos connexions aux plateformes musicales</p>
        </div>
        <button 
          onClick={() => fetchProviderStatus()}
          className="p-2 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-xl transition-colors text-gray-400 hover:text-blue-500"
          title="Actualiser les statuts"
        >
          <RefreshCw size={20} />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {providers.map((provider) => {
          const isConnected = (providerStatus as any)[provider.id];
          const isBtnLoading = loading === provider.id;

          return (
            <motion.div
              key={provider.id}
              whileHover={{ y: -2 }}
              className={`p-5 rounded-[2rem] border-2 transition-all duration-300 ${
                isConnected 
                  ? 'bg-white dark:bg-slate-900 border-green-100 dark:border-green-900/30 shadow-sm' 
                  : 'bg-gray-50/50 dark:bg-slate-900/50 border-transparent hover:border-gray-200 dark:hover:border-slate-800'
              }`}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-2xl bg-white dark:bg-slate-800 shadow-sm flex items-center justify-center overflow-hidden p-2 border border-gray-100 dark:border-slate-800">
                    <ProviderIcon provider={provider.id} size={32} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="font-black text-gray-900 dark:text-white">{provider.name}</h4>
                      {isConnected && (
                        <span className="flex items-center gap-1 text-[10px] font-black text-green-500 uppercase tracking-widest bg-green-50 dark:bg-green-900/20 px-2 py-0.5 rounded-full border border-green-100 dark:border-green-900/30">
                          <CheckCircle2 size={10} /> Connecté
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-400 font-bold uppercase tracking-tighter mt-0.5">
                      {isConnected ? 'Compte actif' : 'Non configuré'}
                    </p>
                  </div>
                </div>

                <div className="flex gap-2">
                  {!isConnected && (
                    <Settings2 size={18} className="text-gray-300" />
                  )}
                </div>
              </div>

              <p className="text-sm text-gray-500 dark:text-gray-400 font-medium mb-6 leading-relaxed">
                {provider.description}
              </p>

              <button
                onClick={() => isConnected ? handleDisconnect(provider.id) : handleConnect(provider)}
                disabled={isBtnLoading}
                className={`w-full py-3.5 rounded-2xl font-black text-sm transition-all flex items-center justify-center gap-2 shadow-sm active:scale-95 ${
                  isConnected
                    ? 'bg-red-50 dark:bg-red-900/10 text-red-500 border-2 border-red-100 dark:border-red-900/30 hover:bg-red-100 dark:hover:bg-red-900/20'
                    : 'bg-white dark:bg-slate-800 text-gray-900 dark:text-white border-2 border-gray-100 dark:border-slate-700 hover:border-blue-500 hover:text-blue-500'
                }`}
              >
                {isBtnLoading ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : isConnected ? (
                  <>
                    <Unplug size={16} />
                    Gérer la connexion (Déconnecter)
                  </>
                ) : (
                  <>
                    <ExternalLink size={16} />
                    Se connecter à {provider.name}
                  </>
                )}
              </button>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};

export default ProviderManager;
