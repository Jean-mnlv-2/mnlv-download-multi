import React, { useState } from 'react';
import { useTaskStore } from '../../store/useTaskStore';
import { useAuthStore } from '../../store/useAuthStore';
import axios from 'axios';
import { Search, Download, Music, Video, Loader2, Sparkles, Link as LinkIcon, AlertCircle, ExternalLink } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';

const URLInput: React.FC = () => {
  const { t } = useTranslation();
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [mediaType, setMediaType] = useState<'AUDIO' | 'VIDEO'>('AUDIO');
  const { addTask, pollTaskStatus, addNotification } = useTaskStore();
  const { providerStatus, accessToken } = useAuthStore();

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

  const isUrlRequiringAuth = (url: string) => {
    if (url.includes('spotify.com') && !providerStatus.spotify) return 'spotify';
    // On peut ajouter d'autres providers ici
    return null;
  };

  const authRequired = isUrlRequiringAuth(url);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) return;

    setLoading(true);
    try {
      const response = await axios.post('/api/download/', { 
        url,
        media_type: mediaType 
      });
      const data = response.data;

      if (data.type === 'playlist') {
        data.tasks.forEach((t: any) => {
          addTask({ 
            id: t.task_id, 
            status: 'PENDING', 
            progress: 0, 
            original_url: url, 
            provider: t.provider || 'spotify' 
            });
          pollTaskStatus(t.task_id);
        });
        addNotification('success', `${data.tasks.length} ${t('processing')}`);
      } else {
        addTask({ 
          id: data.task_id, 
          status: 'PENDING', 
          progress: 0, 
          original_url: url, 
          provider: data.provider 
        });
        pollTaskStatus(data.task_id);
        addNotification('info', t('processing'));
      }
      setUrl('');
    } catch (error: any) {
      addNotification('error', error.response?.data?.error || t('failed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      {authRequired && (
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
              <p className="text-sm font-black text-orange-900 dark:text-white">Connexion {authRequired === 'spotify' ? 'Spotify' : ''} requise</p>
              <p className="text-xs font-bold text-orange-600 dark:text-orange-400/70">Certaines fonctionnalités avancées nécessitent d'être connecté.</p>
            </div>
          </div>
          <button 
            type="button"
            onClick={() => handleConnectProvider(authRequired)}
            className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-xl text-xs font-black flex items-center gap-2 transition-colors"
          >
            Se connecter
            <ExternalLink size={14} />
          </button>
        </motion.div>
      )}

      <form onSubmit={handleSubmit} className="relative group">
        <div className="absolute inset-y-0 left-6 flex items-center pointer-events-none text-gray-400 group-focus-within:text-blue-500 transition-colors">
          <LinkIcon size={20} />
        </div>
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder={t('search_placeholder')}
          className="w-full pl-14 pr-40 py-6 bg-white dark:bg-slate-900 border-2 border-transparent dark:border-slate-800 rounded-[2rem] shadow-2xl shadow-gray-200/50 dark:shadow-none focus:bg-white dark:focus:bg-slate-900 focus:border-blue-500 focus:ring-8 focus:ring-blue-500/5 outline-none transition-all font-bold text-gray-700 dark:text-white"
        />
        <div className="absolute inset-y-2 right-2 flex items-center gap-2">
          <div className="flex bg-gray-100 dark:bg-slate-800 p-1 rounded-2xl mr-2">
            <button
              type="button"
              onClick={() => setMediaType('AUDIO')}
              className={`p-2 rounded-xl transition-all ${mediaType === 'AUDIO' ? 'bg-white dark:bg-slate-700 text-blue-600 shadow-sm' : 'text-gray-400'}`}
              title="MP3"
            >
              <Music size={18} />
            </button>
            <button
              type="button"
              onClick={() => setMediaType('VIDEO')}
              className={`p-2 rounded-xl transition-all ${mediaType === 'VIDEO' ? 'bg-white dark:bg-slate-700 text-blue-600 shadow-sm' : 'text-gray-400'}`}
              title="MP4"
            >
              <Video size={18} />
            </button>
          </div>
          <button
            type="submit"
            disabled={loading || !url}
            className="h-full px-8 bg-gray-900 dark:bg-blue-600 hover:bg-black dark:hover:bg-blue-500 text-white rounded-[1.5rem] font-black text-sm transition-all shadow-lg active:scale-95 disabled:bg-gray-200 dark:disabled:bg-slate-800 disabled:text-gray-400 disabled:shadow-none flex items-center gap-2"
          >
            {loading ? <Loader2 className="animate-spin" size={18} /> : <Download size={18} />}
            <span className="hidden sm:inline">{t('download')}</span>
          </button>
        </div>
      </form>

      <div className="flex items-center justify-center gap-6">
        <div className="flex items-center gap-2 text-[10px] font-black text-gray-400 uppercase tracking-widest">
          <Sparkles size={12} className="text-yellow-500" />
          <span>Compatible Spotify, Deezer, Apple Music & YouTube</span>
        </div>
      </div>
    </div>
  );
};

export default URLInput;
