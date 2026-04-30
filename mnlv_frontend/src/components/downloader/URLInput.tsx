import React, { useState, useMemo, useEffect, useRef } from 'react';
import { useTaskStore } from '../../store/useTaskStore';
import { useAuthStore } from '../../store/useAuthStore';
import { LocalFileSystemService } from '../../services/localFileSystem';
import axios from 'axios';
import { Search, Download, Music, Video, Loader2, Sparkles, Link as LinkIcon, AlertCircle, ExternalLink, Disc, Radio, Cloud, Youtube, Play as PlayIcon, ShieldCheck, ShieldAlert, History, User, FolderOpen, LayoutGrid, Plus, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import ProviderIcon from './ProviderIcon';

const PROVIDER_CONFIG: { [key: string]: { key: string, label: string, color: string, icon: any } } = {
  'spotify.com': { key: 'spotify', label: 'Spotify', color: 'text-green-500', icon: Disc },
  'deezer.com': { key: 'deezer', label: 'Deezer', color: 'text-pink-500', icon: Radio },
  'apple.com': { key: 'apple_music', label: 'Apple Music', color: 'text-red-500', icon: Music },
  'tidal.com': { key: 'tidal', label: 'Tidal', color: 'text-cyan-400', icon: Disc },
  'soundcloud.com': { key: 'soundcloud', label: 'SoundCloud', color: 'text-orange-500', icon: Cloud },
  'amazon.com': { key: 'amazon_music', label: 'Amazon Music', color: 'text-blue-400', icon: Disc },
  'music.youtube.com': { key: 'youtube_music', label: 'YouTube Music', color: 'text-red-600', icon: Youtube },
  'boomplay.com': { key: 'boomplay', label: 'Boomplay', color: 'text-blue-500', icon: Music },
  'boomplaymusic.com': { key: 'boomplay', label: 'Boomplay', color: 'text-blue-500', icon: Music }
};

const URLInput: React.FC = () => {
  const { t } = useTranslation();
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [mediaType, setMediaType] = useState<string>('AUDIO');
  const [quality, setQuality] = useState('320');
  const [preferVideoIfAvailable, setPreferVideoIfAvailable] = useState(true);
  const [explicitFilter, setExplicitFilter] = useState(false);
  const [searchResults, setSearchResults] = useState<any>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [downloadTarget, setDownloadTarget] = useState<'local' | 'playlist'>('local');
  const [selectedTargetPlaylist, setSelectedTargetPlaylist] = useState<string | null>(null);
  const [showNewPlaylistInput, setShowNewPlaylistInput] = useState(false);
  const [newPlaylistName, setNewPlaylistName] = useState('');
  const [userPlaylists, setUserPlaylists] = useState<any[]>([]);
  const searchRef = useRef<HTMLDivElement>(null);
  const { addTask, pollTaskStatus, addNotification, triggerRefresh, setStagedTracks, localDirectorySelected, setLocalDirectorySelected } = useTaskStore();
  const { providerStatus, accessToken } = useAuthStore();

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

  const AUDIO_FORMATS = [
    { value: 'AUDIO', label: 'MP3', desc: 'Standard (320kbps)' },
    { value: 'WAV', label: 'WAV', desc: 'Pro Lossless' },
    { value: 'FLAC', label: 'FLAC', desc: 'Pro Studio' },
    { value: 'ALAC', label: 'ALAC', desc: 'Apple Pro' },
    { value: 'OPUS', label: 'OPUS', desc: 'WebRadio (Low Latency)' },
    { value: 'AAC', label: 'AAC', desc: 'WebRadio/TV' },
  ];

  const VIDEO_FORMATS = [
    { value: 'VIDEO', label: 'MP4', desc: 'Standard HD' },
    { value: 'MKV', label: 'MKV', desc: 'High Quality' },
  ];

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
        } finally {
          setIsSearching(false);
        }
      } else {
        setSearchResults(null);
        setShowResults(false);
      }
    }, 500);

    return () => clearTimeout(delayDebounceFn);
  }, [url, isUrl, explicitFilter]);

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
    if (!url) return null;
    
    if (isUrl) {
      for (const [domain, config] of Object.entries(PROVIDER_CONFIG)) {
        if (url.includes(domain)) return { ...config, domain };
      }
    }
    
    return { ...PROVIDER_CONFIG['apple.com'], domain: 'apple.com', isSearch: true };
  }, [url, isUrl]);

  const providerBadge = useMemo(() => {
    if (!detectedProvider || !url) return null;
    const Icon = detectedProvider.icon;
    const isAuth = providerStatus[detectedProvider.key as keyof typeof providerStatus];
    
    return (
      <motion.div 
        initial={{ opacity: 0, x: -10, scale: 0.8 }}
        animate={{ opacity: 1, x: 0, scale: 1 }}
        exit={{ opacity: 0, scale: 0.5 }}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-full border shadow-sm transition-all duration-300 ${
          isAuth 
            ? 'bg-white dark:bg-slate-800 border-gray-100 dark:border-slate-700' 
            : 'bg-amber-50 dark:bg-amber-900/20 border-amber-100 dark:border-amber-900/30'
        }`}
      >
        <Icon size={14} className={detectedProvider.color} />
        <span className="text-[10px] font-black uppercase tracking-wider text-gray-500 dark:text-gray-400">
          {detectedProvider.label}
        </span>
        {!isAuth && (
          <div className="flex items-center gap-1 ml-1 px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/40 rounded-md">
            <ShieldAlert size={10} className="text-amber-600 dark:text-amber-500" />
            <span className="text-[8px] font-bold text-amber-700 dark:text-amber-500 uppercase">Offline</span>
          </div>
        )}
      </motion.div>
    );
  }, [detectedProvider, url, providerStatus]);

  const authRequired = useMemo(() => {
    if (detectedProvider && !providerStatus[detectedProvider.key as keyof typeof providerStatus]) {
      return detectedProvider.key;
    }
    return null;
  }, [detectedProvider, providerStatus]);

  useEffect(() => {
    if (downloadTarget === 'playlist' && detectedProvider && accessToken) {
      fetchUserPlaylists(detectedProvider.key);
    }
  }, [downloadTarget, detectedProvider, accessToken]);

  const handleCreateAndSelectPlaylist = async () => {
    if (!newPlaylistName.trim() || !detectedProvider) return;
    
    let providerUrl = `https://${detectedProvider.key}.com`;
    if (detectedProvider.key === 'apple_music') providerUrl = 'https://music.apple.com';
    if (detectedProvider.key === 'youtube_music') providerUrl = 'https://music.youtube.com';

    try {
      const res = await axios.post('/api/playlist/manage/', {
        action: 'CREATE',
        provider: detectedProvider.key,
        provider_url: providerUrl,
        name: newPlaylistName
      });
      addNotification('success', `Playlist "${newPlaylistName}" créée !`);
      await fetchUserPlaylists(detectedProvider.key);
      setSelectedTargetPlaylist(res.data.playlist_id);
      setShowNewPlaylistInput(false);
      setNewPlaylistName('');
    } catch (err) {
      addNotification('error', "Erreur lors de la création");
    }
  };

  const fetchUserPlaylists = async (provider: string) => {
    // Détermination de l'URL de base correcte pour le provider
    let providerUrl = `https://${provider}.com`;
    if (provider === 'apple_music') providerUrl = 'https://music.apple.com';
    if (provider === 'youtube_music') providerUrl = 'https://music.youtube.com';

    try {
      const res = await axios.post('/api/playlist/manage/', {
        action: 'GET_LIST', 
        provider: provider,
        provider_url: providerUrl
      });
      setUserPlaylists(res.data.playlists || []);
    } catch (err) {}
  };

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

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!url) return;

    if (downloadTarget === 'playlist' && !selectedTargetPlaylist) {
      addNotification('error', "Veuillez choisir une playlist de destination");
      return;
    }

    setLoading(true);
    try {
      // Si on est en local et qu'aucun dossier n'est sélectionné, on demande d'abord
      if (downloadTarget === 'local' && !LocalFileSystemService.getHandle()) {
        const success = await LocalFileSystemService.selectDirectory();
        if (!success) {
          setLoading(false);
          return;
        }
        setLocalDirectorySelected(true);
      }

      const response = await axios.post('/api/download/', { 
        url,
        media_type: mediaType,
        quality,
        prefer_video: preferVideoIfAvailable,
        explicit_filter: explicitFilter
      });
      const data = response.data;

      if (data.type === 'staged_playlist') {
        addNotification('success', data.message);
        if (data.tracks) {
          const saveDir = downloadTarget === 'local' ? data.message.split(' : ')[1] || 'MNLV_Playlist' : undefined;
          
          setStagedTracks(data.tracks.map((t: any) => ({
            ...t,
            save_to_dir: saveDir
          })));
        }
        triggerRefresh();
        setUrl('');
      } else if (data.type === 'playlist') {
        const saveDir = downloadTarget === 'local' ? data.title || 'MNLV_Playlist' : undefined;
        
        data.tasks.forEach((t: any) => {
          addTask({ 
            id: t.task_id, 
            status: 'PENDING', 
            progress: 0, 
            original_url: url, 
            provider: t.provider || detectedProvider?.key || 'URL',
            save_to_dir: saveDir
          });
          pollTaskStatus(t.task_id);
        });
        addNotification('success', `${data.tasks.length} ${t('processing')}`);
        setUrl('');
      } else {
        // Single track handling
        if (downloadTarget === 'playlist' && selectedTargetPlaylist) {
          await axios.post('/api/playlist/manage/', {
            action: 'ADD_TRACKS',
            playlist_id: selectedTargetPlaylist,
            track_urls: [url],
            provider_url: `https://${detectedProvider?.key || 'spotify'}.com`
          });
          addNotification('success', "Titre ajouté à votre playlist !");
        }

        addTask({ 
          id: data.task_id, 
          status: 'PENDING', 
          progress: 0, 
          original_url: url, 
          provider: data.provider || detectedProvider?.key || 'URL',
          save_to_dir: downloadTarget === 'local' ? 'MNLV_Downloads' : undefined
        });
        pollTaskStatus(data.task_id);
        addNotification('info', t('processing'));
        setUrl('');
      }
    } catch (error: any) {
      addNotification('error', error.response?.data?.error || t('failed'));
    } finally {
      setLoading(false);
    }
  };

  const ProviderIcon = detectedProvider?.icon || (isUrl ? LinkIcon : Search);

  const isSoundCloud = detectedProvider?.key === 'soundcloud';
  const isAudiobook = isUrl && (url.includes('/audiobook/') || url.includes('/chapter/'));

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
        {isAudiobook && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="flex justify-center"
          >
            <div className="px-4 py-1.5 bg-blue-500/10 border border-blue-500/20 rounded-full flex items-center gap-2">
              <Sparkles size={12} className="text-blue-500" />
              <span className="text-[10px] font-black text-blue-600 uppercase tracking-tighter">Mode Livre Audio Détecté</span>
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

      <form onSubmit={handleSubmit} className="relative bg-white dark:bg-slate-900 border-2 border-transparent dark:border-slate-800 rounded-[2.5rem] shadow-2xl shadow-gray-200/40 dark:shadow-none overflow-hidden focus-within:border-blue-500 focus-within:ring-[12px] focus-within:ring-blue-500/5 transition-all">
        <div className="relative">
          <div className="absolute inset-y-0 left-6 flex items-center gap-3 z-10">
            <AnimatePresence mode="wait">
              {providerBadge}
            </AnimatePresence>
            {!detectedProvider && (
              <div className={isUrl ? "text-blue-500" : "text-gray-400"}>
                {isUrl ? <LinkIcon size={24} strokeWidth={2.5} /> : <Search size={24} strokeWidth={2.5} />}
              </div>
            )}
          </div>
          
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onFocus={() => url && !isUrl && setShowResults(true)}
            placeholder={t('search_placeholder')}
            className={`w-full pl-${detectedProvider ? '44' : '16'} pr-44 py-7 bg-transparent outline-none font-bold text-gray-700 dark:text-white text-lg placeholder:text-gray-300 dark:placeholder:text-gray-600 transition-all duration-300`}
          />
        </div>

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
            <div className="relative group/format">
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className={`flex items-center gap-2 px-3 py-2 rounded-xl transition-all ${mediaType !== 'VIDEO' && mediaType !== 'MKV' ? 'bg-white dark:bg-slate-700 text-blue-600 shadow-md ring-1 ring-black/5' : 'text-gray-400 hover:text-gray-600'}`}
                title="Format Audio"
              >
                <Music size={18} strokeWidth={2.5} />
                <span className="text-[10px] font-black tracking-widest uppercase hidden md:inline">
                  {AUDIO_FORMATS.find(f => f.value === mediaType)?.label || 'AUDIO'}
                </span>
              </button>
              
              <AnimatePresence>
                {showAdvanced && (
                  <motion.div 
                    initial={{ opacity: 0, scale: 0.9, y: 10 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.9, y: 10 }}
                    className="absolute bottom-full left-0 mb-4 bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-3xl shadow-2xl p-2 z-[60] min-w-[200px]"
                  >
                    <div className="p-3 border-b border-gray-50 dark:border-slate-800 mb-2">
                      <span className="text-[10px] font-black uppercase tracking-widest text-gray-400">Formats Audio Pro</span>
                    </div>
                    {AUDIO_FORMATS.map((f) => (
                      <button
                        key={f.value}
                        type="button"
                        onClick={() => {
                          setMediaType(f.value);
                          setShowAdvanced(false);
                        }}
                        className={`w-full flex flex-col items-start p-3 rounded-2xl transition-all text-left ${mediaType === f.value ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600' : 'hover:bg-gray-50 dark:hover:bg-slate-800 text-gray-600 dark:text-gray-400'}`}
                      >
                        <span className="text-xs font-black">{f.label}</span>
                        <span className="text-[9px] font-bold opacity-60 uppercase">{f.desc}</span>
                      </button>
                    ))}
                    <div className="p-3 border-t border-gray-50 dark:border-slate-800 mt-2">
                      <span className="text-[10px] font-black uppercase tracking-widest text-gray-400">Formats Vidéo</span>
                    </div>
                    {VIDEO_FORMATS.map((f) => (
                      <button
                        key={f.value}
                        type="button"
                        onClick={() => {
                          setMediaType(f.value);
                          setShowAdvanced(false);
                        }}
                        className={`w-full flex flex-col items-start p-3 rounded-2xl transition-all text-left ${mediaType === f.value ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600' : 'hover:bg-gray-50 dark:hover:bg-slate-800 text-gray-600 dark:text-gray-400'}`}
                      >
                        <span className="text-xs font-black">{f.label}</span>
                        <span className="text-[9px] font-bold opacity-60 uppercase">{f.desc}</span>
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
            
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

          {(mediaType === 'AUDIO' || mediaType === 'WAV' || mediaType === 'FLAC') && (
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
              <Download size="20" className="group-hover/btn:translate-y-0.5 transition-transform" />
            )}
            <span className="hidden sm:inline uppercase tracking-tighter">{t('download')}</span>
          </button>
        </div>

        <AnimatePresence>
          {showAdvanced && (
            <motion.div 
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="p-4 pt-0 border-t border-gray-100 dark:border-slate-800 space-y-4"
            >
              {/* Destination Toggle */}
              <div className="flex items-center gap-4 p-2 bg-gray-50/50 dark:bg-slate-800/50 rounded-2xl">
                <button
                  type="button"
                  onClick={() => setDownloadTarget('local')}
                  className={`flex-1 py-3 px-4 rounded-xl font-black text-[10px] uppercase tracking-widest transition-all flex items-center justify-center gap-2 ${
                    downloadTarget === 'local' 
                      ? 'bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-sm' 
                      : 'text-gray-400 hover:text-gray-600'
                  }`}
                >
                  <FolderOpen size={14} /> Local
                  {localDirectorySelected && <Check size={12} className="text-green-500" />}
                </button>
                <button
                  type="button"
                  disabled={!accessToken}
                  onClick={() => setDownloadTarget('playlist')}
                  className={`flex-1 py-3 px-4 rounded-xl font-black text-[10px] uppercase tracking-widest transition-all flex items-center justify-center gap-2 ${
                    downloadTarget === 'playlist' 
                      ? 'bg-white dark:bg-slate-700 text-emerald-600 dark:text-emerald-400 shadow-sm' 
                      : 'text-gray-400 hover:text-gray-600'
                  } ${!accessToken ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <LayoutGrid size={14} /> Playlist
                </button>
              </div>

              {/* Local Directory Selector */}
              {downloadTarget === 'local' && (
                <div className="px-2 py-2">
                  <button
                    type="button"
                    onClick={handleSelectLocalDir}
                    className={`w-full py-4 px-6 rounded-2xl border-2 border-dashed flex items-center justify-center gap-4 transition-all cursor-pointer shadow-sm hover:shadow-md ${
                      localDirectorySelected 
                        ? 'bg-green-50 border-green-300 text-green-700 dark:bg-green-900/20 dark:border-green-800' 
                        : 'bg-blue-50 border-blue-300 text-blue-700 dark:bg-blue-900/20 dark:border-blue-800 hover:bg-blue-100 dark:hover:bg-blue-900/30'
                    }`}
                  >
                    <div className={`p-2 rounded-xl ${localDirectorySelected ? 'bg-green-500 text-white' : 'bg-blue-500 text-white'}`}>
                      <FolderOpen size={20} />
                    </div>
                    <div className="text-left">
                      <span className="text-xs font-black uppercase tracking-widest block">
                        {localDirectorySelected ? 'Dossier configuré' : 'Choisir un dossier de destination'}
                      </span>
                      <span className="text-[10px] font-bold opacity-60 block">
                        {localDirectorySelected ? 'Cliquez pour changer l\'emplacement' : 'Emplacement local sur votre appareil'}
                      </span>
                    </div>
                  </button>
                  {localDirectorySelected && (
                    <motion.p 
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="text-[9px] text-green-600 font-black mt-3 text-center uppercase tracking-[0.1em]"
                    >
                      <Check size={10} className="inline mr-1" />
                      Enregistrement automatique activé
                    </motion.p>
                  )}
                </div>
              )}

              {/* Playlist Selector */}
              {downloadTarget === 'playlist' && (
                <motion.div 
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="space-y-2"
                >
                  <div className="flex items-center justify-between px-1">
                    <label className="text-[9px] font-black text-gray-400 uppercase tracking-widest">Playlist de destination</label>
                    <button 
                      type="button"
                      onClick={() => setShowNewPlaylistInput(!showNewPlaylistInput)}
                      className="text-[9px] font-black text-emerald-500 hover:underline flex items-center gap-1"
                    >
                      <Plus size={10} /> {showNewPlaylistInput ? 'Annuler' : 'Nouvelle'}
                    </button>
                  </div>

                  {showNewPlaylistInput ? (
                    <div className="flex gap-2">
                      <input 
                        type="text"
                        value={newPlaylistName}
                        onChange={(e) => setNewPlaylistName(e.target.value)}
                        placeholder="Nom..."
                        className="flex-1 bg-white dark:bg-slate-800 border border-emerald-100 dark:border-emerald-900/30 rounded-xl px-3 py-2 text-xs font-bold outline-none focus:border-emerald-500 transition-all text-gray-700 dark:text-white"
                      />
                      <button 
                        type="button"
                        onClick={handleCreateAndSelectPlaylist}
                        disabled={!newPlaylistName.trim()}
                        className="px-4 py-2 bg-emerald-500 text-white rounded-xl font-black text-[10px] uppercase hover:bg-emerald-600 transition-all"
                      >
                        Créer
                      </button>
                    </div>
                  ) : (
                    <select 
                      value={selectedTargetPlaylist || ''}
                      onChange={(e) => setSelectedTargetPlaylist(e.target.value)}
                      className="w-full bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl px-4 py-3 text-xs font-bold outline-none focus:border-emerald-500 transition-all text-gray-700 dark:text-white"
                    >
                      <option value="">Sélectionner une playlist...</option>
                      {userPlaylists.map(pl => (
                        <option key={pl.id} value={pl.id}>{pl.name}</option>
                      ))}
                    </select>
                  )}
                  {!accessToken && (
                    <p className="text-[9px] text-orange-500 font-bold uppercase text-center">Connexion requise pour les playlists</p>
                  )}
                </motion.div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
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