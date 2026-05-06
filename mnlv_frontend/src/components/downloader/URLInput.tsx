import React, { useState, useMemo } from 'react';
import { useTaskStore } from '../../store/useTaskStore';
import axios from 'axios';
import { 
  Loader2, 
  Link as LinkIcon, 
  Settings2,
  Disc,
  Radio,
  Youtube,
  Cloud,
  Music,
  FileUp
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ProviderIcon from './ProviderIcon';

const PROVIDER_CONFIG: { [key: string]: { key: string, label: string, color: string, icon: any } } = {
  'spotify.com': { key: 'spotify', label: 'Spotify', color: 'text-green-500', icon: Disc },
  'deezer.com': { key: 'deezer', label: 'Deezer', color: 'text-mnlv-red', icon: Radio },
  'apple.com': { key: 'apple_music', label: 'Apple Music', color: 'text-mnlv-red', icon: Music },
  'tidal.com': { key: 'tidal', label: 'Tidal', color: 'text-cyan-400', icon: Disc },
  'soundcloud.com': { key: 'soundcloud', label: 'SoundCloud', color: 'text-orange-500', icon: Cloud },
  'music.youtube.com': { key: 'youtube_music', label: 'YouTube Music', color: 'text-red-600', icon: Youtube },
};

const URLInput: React.FC = () => {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [mediaType, setMediaType] = useState<string>('AUDIO');
  const [quality, setQuality] = useState('320');
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  const { addTask, pollTaskStatus, addNotification, setStagedTracks } = useTaskStore();

  const isUrl = useMemo(() => {
    return url.startsWith('http://') || url.startsWith('https://');
  }, [url]);

  const detectedProvider = useMemo(() => {
    if (!url || !isUrl) return null;
    for (const [domain, config] of Object.entries(PROVIDER_CONFIG)) {
      if (url.includes(domain)) return { ...config, domain };
    }
    return null;
  }, [url, isUrl]);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!url) return;

    setLoading(true);
    try {
      const response = await axios.post('/api/download/', { 
        url,
        media_type: mediaType,
        quality
      });
      
      const data = response.data;

      if (data.type === 'staged_playlist') {
        setStagedTracks(data.tracks.map((t: any) => ({ ...t, provider: data.provider })));
        addNotification('info', `${data.count} morceaux prêts à être téléchargés`);
        setUrl('');
      } else if (data.task_id) {
        addTask({ 
          id: data.task_id, 
          status: 'PENDING', 
          progress: 0, 
          original_url: url, 
          provider: data.provider || 'URL', 
          title: data.title 
        });
        pollTaskStatus(data.task_id);
        addNotification('info', 'Téléchargement lancé');
        setUrl('');
      }
    } catch (error: any) {
      const msg = error.response?.data?.error || 'Erreur de téléchargement';
      addNotification('error', msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full space-y-4">
      <form onSubmit={handleSubmit} className="relative group">
        <div className="absolute inset-y-0 left-5 flex items-center pointer-events-none text-mnlv-slate-400 group-focus-within:text-mnlv-blue transition-colors">
          <LinkIcon size={20} />
        </div>
        
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Collez un lien Spotify, Apple Music, Deezer..."
          className="w-full pl-14 pr-32 py-5 bg-white dark:bg-mnlv-slate-900 border border-mnlv-slate-200 dark:border-mnlv-slate-800 rounded-2xl shadow-pro focus:ring-4 focus:ring-mnlv-blue/10 focus:border-mnlv-blue transition-all font-medium text-mnlv-slate-900 dark:text-white outline-none"
        />

        <div className="absolute inset-y-2 right-2 flex items-center gap-2">
          <input
            type="file"
            id="csv-upload-input"
            className="hidden"
            accept=".csv,.txt"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              const formData = new FormData();
              formData.append('file', file);
              setLoading(true);
              try {
                const res = await axios.post('/api/csv/upload/', formData);
                if (res.data.tracks) {
                  setStagedTracks(res.data.tracks);
                  addNotification('success', `${res.data.tracks.length} morceaux analysés`);
                }
              } catch (err: any) {
                const msg = err.response?.data?.error || "Erreur lors de l'upload";
                addNotification('error', msg);
              } finally {
                setLoading(false);
                if (e.target) e.target.value = '';
              }
            }}
          />
          <button
            type="button"
            onClick={() => document.getElementById('csv-upload-input')?.click()}
            className="p-3 text-mnlv-slate-400 hover:text-mnlv-blue hover:bg-mnlv-slate-50 dark:hover:bg-mnlv-slate-800 rounded-xl transition-all"
            title="Importer CSV/Excel"
          >
            <FileUp size={20} />
          </button>
          
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className={`p-3 rounded-xl transition-all ${showAdvanced ? 'bg-mnlv-slate-100 dark:bg-mnlv-slate-800 text-mnlv-blue' : 'text-mnlv-slate-400 hover:bg-mnlv-slate-50'}`}
          >
            <Settings2 size={20} />
          </button>
          
          <button
            type="submit"
            disabled={!url || loading}
            className="px-6 py-3 bg-mnlv-blue text-white rounded-xl font-bold shadow-pro-blue hover:bg-mnlv-blue-dark disabled:opacity-50 disabled:shadow-none transition-all flex items-center gap-2 active:scale-95"
          >
            {loading ? <Loader2 size={18} className="animate-spin" /> : <LinkIcon size={18} />}
            <span className="hidden md:inline">Analyser</span>
          </button>
        </div>

        {/* Provider Indicator */}
        <AnimatePresence>
          {detectedProvider && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className="absolute -top-3 left-14 px-3 py-1 bg-white dark:bg-mnlv-slate-800 border border-mnlv-slate-100 dark:border-mnlv-slate-700 rounded-full shadow-sm flex items-center gap-2"
            >
              <ProviderIcon provider={detectedProvider.key} size={12} />
              <span className="text-[10px] font-black uppercase tracking-widest text-mnlv-slate-500">{detectedProvider.label}</span>
            </motion.div>
          )}
        </AnimatePresence>
      </form>

      {/* Advanced Options */}
      <AnimatePresence>
        {showAdvanced && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-6 bg-white dark:bg-mnlv-slate-900 border border-mnlv-slate-200 dark:border-mnlv-slate-800 rounded-2xl shadow-pro">
              <div className="space-y-2">
                <label className="text-[10px] font-black uppercase tracking-widest text-mnlv-slate-400 px-1">Format</label>
                <div className="grid grid-cols-2 gap-2">
                  <button 
                    onClick={() => setMediaType('AUDIO')}
                    className={`px-4 py-2 rounded-xl border text-xs font-bold transition-all ${mediaType === 'AUDIO' ? 'bg-mnlv-blue/10 border-mnlv-blue text-mnlv-blue' : 'border-mnlv-slate-100 dark:border-mnlv-slate-800 hover:bg-mnlv-slate-50'}`}
                  >
                    Audio (MP3)
                  </button>
                  <button 
                    onClick={() => setMediaType('VIDEO')}
                    className={`px-4 py-2 rounded-xl border text-xs font-bold transition-all ${mediaType === 'VIDEO' ? 'bg-mnlv-blue/10 border-mnlv-blue text-mnlv-blue' : 'border-mnlv-slate-100 dark:border-mnlv-slate-800 hover:bg-mnlv-slate-50'}`}
                  >
                    Vidéo (MP4)
                  </button>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-black uppercase tracking-widest text-mnlv-slate-400 px-1">Qualité</label>
                <select 
                  value={quality}
                  onChange={(e) => setQuality(e.target.value)}
                  className="w-full px-4 py-2.5 bg-mnlv-slate-50 dark:bg-mnlv-slate-800 border border-mnlv-slate-100 dark:border-mnlv-slate-700 rounded-xl text-xs font-bold outline-none focus:border-mnlv-blue transition-all"
                >
                  <option value="320">320kbps (Standard)</option>
                  <option value="wav">Lossless (WAV)</option>
                  <option value="flac">Studio (FLAC)</option>
                </select>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default URLInput;
