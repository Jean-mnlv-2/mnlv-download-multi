import React, { useState, useMemo, useEffect, useRef } from 'react';
import { useTaskStore } from '../../store/useTaskStore';
import { useAuthStore } from '../../store/useAuthStore';
import axios from 'axios';
import { Search, Download, Music, Video, Loader2, Sparkles, Link as LinkIcon, AlertCircle, ExternalLink, Disc, Radio, Cloud, Youtube, Play as PlayIcon, ShieldCheck, ShieldAlert, History, User } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';

const PROVIDER_CONFIG: { [key: string]: { key: string, label: string, color: string, icon: any } } = {
  'spotify.com': { key: 'spotify', label: 'Spotify', color: 'text-green-500', icon: Disc },
  'deezer.com': { key: 'deezer', label: 'Deezer', color: 'text-pink-500', icon: Radio },
  'apple.com': { key: 'apple_music', label: 'Apple Music', color: 'text-red-500', icon: Music },
  'tidal.com': { key: 'tidal', label: 'Tidal', color: 'text-cyan-400', icon: Disc },
  'soundcloud.com': { key: 'soundcloud', label: 'SoundCloud', color: 'text-orange-500', icon: Cloud },
  'amazon.com': { key: 'amazon_music', label: 'Amazon Music', color: 'text-blue-400', icon: Disc },
  'music.youtube.com': { key: 'youtube_music', label: 'YouTube Music', color: 'text-red-600', icon: Youtube }
};

const URLInput: React.FC = () => {
  const { t } = useTranslation();
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [mediaType, setMediaType] = useState<'AUDIO' | 'VIDEO'>('AUDIO');
  const [preferVideoIfAvailable, setPreferVideoIfAvailable] = useState(true);
  const [explicitFilter, setExplicitFilter] = useState(false);
  const [searchResults, setSearchResults] = useState<any>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const { addTask, pollTaskStatus, addNotification } = useTaskStore();
  const { providerStatus } = useAuthStore();

  const isUrl = useMemo(() => {
    return url.startsWith('http://') || url.startsWith('https://') || url.includes('music.apple.com') || url.includes('spotify.com');
  }, [url]);

  useEffect(() => {
    const delayDebounceFn = setTimeout(async () => {
      if (url && !isUrl && url.length > 2) {
        setIsSearching(true);
        try {
          const response = await axios.get('/api/auth/providers/apple-music/search/', {
            params: { q: url, storefront: 'fr' }
          });
          setSearchResults(response.data);
          setShowResults(true);
        } catch (error) {
          console.error("Search error:", error);
        } finally {
          setIsSearching(false);
        }
      } else {
        setShowResults(false);
      }
    }, 500);

    return () => clearTimeout(delayDebounceFn);
  }, [url, isUrl]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowResults(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const detectedProvider = useMemo(() => {
    if (!url || !isUrl) return null;
    for (const [domain, config] of Object.entries(PROVIDER_CONFIG)) {
      if (url.includes(domain)) return { ...config, domain };
    }
    return null;
  }, [url, isUrl]);

  const authRequired = useMemo(() => {
    if (detectedProvider && !providerStatus[detectedProvider.key as keyof typeof providerStatus]) {
      return detectedProvider.key;
    }
    return null;
  }, [detectedProvider, providerStatus]);

  const handleConnectProvider = async (provider: string) => {
    try {
      const response = await axios.get(`/api/auth/providers/${provider}/login/`);
      if (response.data.auth_url) {
        window.location.href = response.data.auth_url;
      }
    } catch (error: any) {
      const providerName = provider.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
      addNotification('error', `Impossible de se connecter à ${providerName}`);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) return;

    setLoading(true);
    try {
      const response = await axios.post('/api/download/', { 
        url,
        media_type: mediaType,
        prefer_video: preferVideoIfAvailable,
        explicit_filter: explicitFilter
      });
      const data = response.data;

      if (data.type === 'playlist') {
        data.tasks.forEach((t: any) => {
          addTask({ 
            id: t.task_id, 
            status: 'PENDING', 
            progress: 0, 
            original_url: url, 
            provider: t.provider || detectedProvider?.key || 'URL'
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
          provider: data.provider || detectedProvider?.key || 'URL'
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

  const ProviderIcon = detectedProvider?.icon || (isUrl ? LinkIcon : Search);

  const isSoundCloud = detectedProvider?.key === 'soundcloud';

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6" ref={searchRef}>
      <AnimatePresence>
        {isSoundCloud && url && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="flex justify-center"
          >
            <div className="px-4 py-1.5 bg-orange-500/10 border border-orange-500/20 rounded-full flex items-center gap-2">
              <Sparkles size={12} className="text-orange-500" />
              <span className="text-[10px] font-black text-orange-600 uppercase tracking-tighter">Mode SoundCloud HD activé</span>
            </div>
          </motion.div>
        )}
        {authRequired && (
          <motion.div 
            initial={{ opacity: 0, height: 0, y: -20 }}
            animate={{ opacity: 1, height: 'auto', y: 0 }}
            exit={{ opacity: 0, height: 0, y: -20 }}
            className="overflow-hidden"
          >
            <div className="bg-orange-50 dark:bg-orange-900/10 border border-orange-100 dark:border-orange-800/50 p-4 rounded-[2rem] flex items-center justify-between shadow-sm">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-white dark:bg-orange-900/20 rounded-2xl flex items-center justify-center text-orange-500 shadow-sm border border-orange-50 dark:border-orange-800/30">
                  <AlertCircle size={24} />
                </div>
                <div>
                  <p className="text-sm font-black text-orange-900 dark:text-orange-100">
                    Connexion {detectedProvider?.label} requise
                  </p>
                  <p className="text-xs font-bold text-orange-600/80 dark:text-orange-400/60">
                    Connectez votre compte pour accéder à ce contenu.
                  </p>
                </div>
              </div>
              <button 
                type="button"
                onClick={() => handleConnectProvider(authRequired)}
                className="px-6 py-3 bg-orange-500 hover:bg-orange-600 text-white rounded-2xl text-xs font-black flex items-center gap-2 transition-all shadow-lg shadow-orange-500/20 active:scale-95"
              >
                Se connecter
                <ExternalLink size={14} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <form onSubmit={handleSubmit} className="relative">
        <div className="absolute inset-y-0 left-6 flex items-center pointer-events-none transition-all duration-500">
          <motion.div
            key={detectedProvider?.key || 'default'}
            initial={{ scale: 0.5, opacity: 0, rotate: -45 }}
            animate={{ scale: 1, opacity: 1, rotate: 0 }}
            className={`${detectedProvider?.color || 'text-gray-400'}`}
          >
            <ProviderIcon size={24} strokeWidth={2.5} />
          </motion.div>
        </div>
        
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onFocus={() => url && !isUrl && setShowResults(true)}
          placeholder={t('search_placeholder')}
          className="w-full pl-16 pr-44 py-7 bg-white dark:bg-slate-900 border-2 border-transparent dark:border-slate-800 rounded-[2.5rem] shadow-2xl shadow-gray-200/40 dark:shadow-none focus:bg-white dark:focus:bg-slate-900 focus:border-blue-500 focus:ring-[12px] focus:ring-blue-500/5 outline-none transition-all font-bold text-gray-700 dark:text-white text-lg placeholder:text-gray-300 dark:placeholder:text-gray-600"
        />

        {/* Search Results Dropdown */}
        <AnimatePresence>
          {showResults && searchResults && (
            <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              className="absolute top-full left-0 right-0 mt-4 bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-[2.5rem] shadow-2xl overflow-hidden z-50 p-4 max-h-[600px] overflow-y-auto"
            >
              {isSearching && (
                <div className="flex items-center justify-center py-10">
                  <Loader2 className="animate-spin text-blue-500" size={32} />
                </div>
              )}

              {!isSearching && Object.keys(searchResults).length === 0 && (
                <div className="text-center py-10 text-gray-400 font-bold uppercase tracking-widest text-xs">
                  Aucun résultat trouvé sur Apple Music
                </div>
              )}

              {!isSearching && Object.entries(searchResults).map(([type, items]: [any, any]) => (
                <div key={type} className="mb-6 last:mb-0">
                  <h4 className="px-4 mb-3 text-[10px] font-black uppercase tracking-[0.2em] text-gray-400 flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                    {type.replace('music-videos', 'Clips').replace('songs', 'Titres').replace('albums', 'Albums').replace('playlists', 'Playlists')}
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {items.map((item: any) => (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => {
                          setUrl(item.url);
                          setShowResults(false);
                        }}
                        className="flex items-center gap-4 p-3 hover:bg-gray-50 dark:hover:bg-slate-800/50 rounded-2xl transition-all group text-left"
                      >
                        <div className="relative w-12 h-12 flex-shrink-0">
                          {item.cover_url ? (
                            <img src={item.cover_url} alt="" className="w-full h-full object-cover rounded-xl shadow-sm group-hover:shadow-md transition-all" />
                          ) : (
                            <div className="w-full h-full bg-gray-100 dark:bg-slate-800 rounded-xl flex items-center justify-center text-gray-400">
                              <Music size={20} />
                            </div>
                          )}
                          {item.is_video && (
                            <div className="absolute -top-1 -right-1 bg-blue-500 text-white p-1 rounded-lg shadow-sm">
                              <Video size={10} />
                            </div>
                          )}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-black text-gray-900 dark:text-white truncate group-hover:text-blue-500 transition-colors">
                            {item.title}
                          </p>
                          <p className="text-[10px] font-bold text-gray-500 dark:text-gray-400 truncate uppercase tracking-tighter">
                            {item.artist}
                            {item.track_count && ` • ${item.track_count} titres`}
                          </p>
                        </div>
                        <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                          <Download size={16} className="text-blue-500" />
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        <div className="absolute inset-y-2.5 right-2.5 flex items-center gap-3">
          <div className="flex bg-gray-50 dark:bg-slate-800/50 p-1.5 rounded-2xl border border-gray-100 dark:border-slate-700/50">
            <button
              type="button"
              onClick={() => setMediaType('AUDIO')}
              className={`flex items-center gap-2 px-3 py-2 rounded-xl transition-all ${mediaType === 'AUDIO' ? 'bg-white dark:bg-slate-700 text-blue-600 shadow-md ring-1 ring-black/5' : 'text-gray-400 hover:text-gray-600'}`}
              title="Audio (MP3)"
            >
              <Music size={18} strokeWidth={2.5} />
              <span className="text-[10px] font-black tracking-widest uppercase hidden md:inline">MP3</span>
            </button>
            <button
              type="button"
              onClick={() => setMediaType('VIDEO')}
              className={`flex items-center gap-2 px-3 py-2 rounded-xl transition-all ${mediaType === 'VIDEO' ? 'bg-white dark:bg-slate-700 text-blue-600 shadow-md ring-1 ring-black/5' : 'text-gray-400 hover:text-gray-600'}`}
              title="Vidéo (MP4)"
            >
              <Video size={18} strokeWidth={2.5} />
              <span className="text-[10px] font-black tracking-widest uppercase hidden md:inline">MP4</span>
            </button>
            <div className="w-px h-8 bg-gray-200 dark:bg-slate-700 mx-1 self-center" />
            <button
              type="button"
              onClick={() => setExplicitFilter(!explicitFilter)}
              className={`flex items-center gap-2 px-3 py-2 rounded-xl transition-all ${explicitFilter ? 'bg-red-50 dark:bg-red-900/20 text-red-600 shadow-sm' : 'text-gray-400 hover:text-gray-600'}`}
              title={explicitFilter ? "Filtre explicite actif" : "Activer le filtre explicite"}
            >
              {explicitFilter ? <ShieldAlert size={18} strokeWidth={2.5} /> : <ShieldCheck size={18} strokeWidth={2.5} />}
              <span className="text-[10px] font-black tracking-widest uppercase hidden md:inline">CLEAN</span>
            </button>
          </div>

          {mediaType === 'AUDIO' && (
            <button
              type="button"
              onClick={() => setPreferVideoIfAvailable(!preferVideoIfAvailable)}
              className={`hidden sm:flex items-center gap-2 px-4 py-3 rounded-2xl transition-all border ${preferVideoIfAvailable ? 'bg-blue-50 border-blue-100 text-blue-600 dark:bg-blue-900/20 dark:border-blue-800' : 'bg-gray-50 border-gray-100 text-gray-400 dark:bg-slate-800 dark:border-slate-700'}`}
              title="Inclure la vidéo si le titre est un clip"
            >
              <div className="relative">
                <Music size={14} />
                {preferVideoIfAvailable && <Video size={10} className="absolute -top-1 -right-1 text-blue-500" />}
              </div>
              <span className="text-[10px] font-black uppercase tracking-tight">Inclure Vidéo</span>
            </button>
          )}
          
          <button
            type="submit"
            disabled={loading || !url}
            className="h-full px-8 bg-gray-900 dark:bg-blue-600 hover:bg-black dark:hover:bg-blue-500 text-white rounded-[2rem] font-black text-sm transition-all shadow-xl active:scale-95 disabled:bg-gray-100 dark:disabled:bg-slate-800 disabled:text-gray-300 disabled:shadow-none flex items-center gap-3 group/btn"
          >
            {loading ? (
              <Loader2 className="animate-spin" size={20} />
            ) : (
              <Download size={20} className="group-hover/btn:translate-y-0.5 transition-transform" />
            )}
            <span className="hidden sm:inline uppercase tracking-tighter">{t('download')}</span>
          </button>
        </div>
      </form>

      {/* Quick Access Tips */}
      {!url && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-wrap justify-center gap-4 text-gray-400 dark:text-gray-600"
        >
          {Object.entries(PROVIDER_CONFIG).map(([domain, config]) => (
            <div key={domain} className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest grayscale opacity-50 hover:grayscale-0 hover:opacity-100 transition-all cursor-default">
              <config.icon size={12} />
              {config.label}
            </div>
          ))}
        </motion.div>
      )}
    </div>
  );
};

export default URLInput;