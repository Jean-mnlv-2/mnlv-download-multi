import React, { useState, useRef } from 'react';
import axios from 'axios';
import { 
  Wrench, 
  Music, 
  Tags, 
  FileAudio, 
  Download, 
  Loader2, 
  CheckCircle2, 
  AlertCircle,
  FileUp,
  Settings2,
  ChevronRight,
  Info,
  Sparkles
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { useTaskStore } from '../../store/useTaskStore';

const MediaTools: React.FC = () => {
  const { t } = useTranslation();
  const { addNotification } = useTaskStore();
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [mode, setMode] = useState<'convert' | 'tags'>('convert');
  const [targetFormat, setTargetFormat] = useState('WAV');
  const [inputExt, setInputExt] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [metadata, setMetadata] = useState({
    title: '',
    artist: '',
    album: '',
    year: '',
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      const ext = selectedFile.name.split('.').pop()?.toUpperCase() || '';
      setInputExt(ext);
    }
  };

  const FORMATS = [
    { value: 'WAV', label: 'WAV Professionnel', desc: '44.1kHz / 16-bit PCM', longDesc: 'La conversion WAV transforme vos fichiers compressés en format PCM linéaire haute qualité. Idéal pour le mixage DJ ou la post-production audio.' },
    { value: 'FLAC', label: 'FLAC Studio', desc: 'Lossless Archive', longDesc: 'Le format FLAC permet une compression sans perte, préservant l\'intégralité des données audio originales tout en réduisant la taille du fichier.' },
    { value: 'ALAC', label: 'ALAC Apple', desc: 'Apple Lossless', longDesc: 'Format Apple Lossless, idéal pour les utilisateurs de l\'écosystème Apple souhaitant une qualité studio sans compromis.' },
    { value: 'OPUS', label: 'OPUS WebRadio', desc: 'Streaming Latence Basse', longDesc: 'Opus est le codec le plus efficace pour le streaming en temps réel, offrant une qualité exceptionnelle même à bas débit.' },
    { value: 'AAC', label: 'AAC WebTV', desc: 'Diffusion Standard', longDesc: 'Format standard pour la diffusion vidéo et WebTV, offrant un excellent compromis entre compatibilité et fidélité audio.' },
  ];

  const handleProcess = async () => {
    if (!file) return;
    setLoading(true);
    setResultUrl(null);

    const formData = new FormData();
    formData.append('file', file);
    
    if (mode === 'tags') {
      Object.entries(metadata).forEach(([key, value]) => formData.append(key, value));
    } else {
      formData.append('format', targetFormat);
    }

    const endpoint = mode === 'convert' ? '/api/media/convert/' : '/api/media/edit-tags/';

    try {
      const response = await axios.post(endpoint, formData);
      setResultUrl(response.data.download_url);
      addNotification('success', "Traitement terminé avec succès");
    } catch (error: any) {
      addNotification('error', error.response?.data?.error || "Échec du traitement");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto space-y-10">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400 font-black text-xs uppercase tracking-widest">
            <Sparkles size={14} />
            <span>Studio Média</span>
          </div>
          <h2 className="text-3xl font-black text-gray-900 dark:text-white tracking-tight">Outils de Traitement</h2>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
        {/* Left Column: Selection & Upload */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-white dark:bg-slate-900 rounded-[2.5rem] p-4 border border-gray-100 dark:border-slate-800 shadow-sm flex flex-col gap-2">
            <button
              onClick={() => { setMode('convert'); setFile(null); setResultUrl(null); }}
              className={`flex items-center justify-between p-4 rounded-2xl transition-all ${mode === 'convert' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20' : 'text-gray-500 hover:bg-gray-50 dark:hover:bg-slate-800'}`}
            >
              <div className="flex items-center gap-3">
                <FileAudio size={20} />
                <span className="font-black text-sm uppercase tracking-widest">Conversion WAV</span>
              </div>
              <ChevronRight size={16} />
            </button>
            <button
              onClick={() => { setMode('tags'); setFile(null); setResultUrl(null); }}
              className={`flex items-center justify-between p-4 rounded-2xl transition-all ${mode === 'tags' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20' : 'text-gray-500 hover:bg-gray-50 dark:hover:bg-slate-800'}`}
            >
              <div className="flex items-center gap-3">
                <Tags size={20} />
                <span className="font-black text-sm uppercase tracking-widest">Édition Tags</span>
              </div>
              <ChevronRight size={16} />
            </button>
          </div>

          <div 
            onClick={() => fileInputRef.current?.click()}
            className={`
              cursor-pointer group h-64 bg-white dark:bg-slate-900 rounded-[2.5rem] border-4 border-dashed transition-all flex flex-col items-center justify-center p-8 text-center
              ${file ? 'border-indigo-500 bg-indigo-50/10' : 'border-gray-100 dark:border-slate-800 hover:border-indigo-200 dark:hover:border-indigo-900/50'}
            `}
          >
            <input 
              ref={fileInputRef}
              type="file" 
              onChange={handleFileChange} 
              className="hidden"
              accept={mode === 'convert' ? 'audio/*,video/*' : '.mp3'}
            />
            <div className="w-16 h-16 bg-gray-50 dark:bg-slate-800 rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <FileUp className="text-indigo-600 dark:text-indigo-400" size={32} />
            </div>
            {file ? (
              <div className="space-y-1">
                <p className="text-gray-900 dark:text-white font-black text-sm truncate max-w-[200px]">{file.name}</p>
                <p className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
              </div>
            ) : (
              <div className="space-y-1">
                <p className="text-gray-900 dark:text-white font-black text-sm">Déposez votre fichier</p>
                <p className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">MP3, WAV, FLAC</p>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Configuration & Action */}
        <div className="lg:col-span-2">
          <AnimatePresence mode="wait">
            <motion.div
              key={mode}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              className="bg-white dark:bg-slate-900 rounded-[3rem] p-10 border border-gray-100 dark:border-slate-800 shadow-sm min-h-[400px] flex flex-col"
            >
              <div className="flex-grow space-y-8">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-indigo-50 dark:bg-indigo-900/20 rounded-2xl flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                    {mode === 'convert' ? <FileAudio size={24} /> : <Settings2 size={24} />}
                  </div>
                  <div>
                    <h3 className="text-xl font-black text-gray-900 dark:text-white tracking-tight">
                      {mode === 'convert' ? `Convertir en ${targetFormat} Professionnel` : 'Modifier les Métadonnées'}
                    </h3>
                    <p className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest">
                      {mode === 'convert' ? FORMATS.find(f => f.value === targetFormat)?.desc : 'Injection de tags ID3v2.4'}
                    </p>
                  </div>
                </div>

                {mode === 'convert' && (
                  <div className="space-y-6">
                    {file && (
                      <div className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-slate-800/50 rounded-2xl border border-gray-100 dark:border-slate-800">
                        <div className="w-10 h-10 bg-indigo-100 dark:bg-indigo-900/30 rounded-xl flex items-center justify-center text-indigo-600 dark:text-indigo-400 font-black text-xs">
                          {inputExt}
                        </div>
                        <ChevronRight size={16} className="text-gray-300" />
                        <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white font-black text-xs">
                          {targetFormat}
                        </div>
                        <div className="ml-2">
                          <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Configuration Flux</p>
                          <p className="text-xs font-bold text-gray-700 dark:text-white">Conversion {inputExt} vers {targetFormat}</p>
                        </div>
                      </div>
                    )}
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {FORMATS.map((f) => (
                        <button
                          key={f.value}
                          onClick={() => setTargetFormat(f.value)}
                          className={`flex flex-col items-start p-5 rounded-[2rem] border-2 transition-all ${targetFormat === f.value ? 'bg-indigo-50 border-indigo-500 dark:bg-indigo-900/20 dark:border-indigo-500' : 'bg-gray-50 border-transparent dark:bg-slate-800/50 hover:border-gray-200'}`}
                        >
                          <span className={`text-sm font-black ${targetFormat === f.value ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-900 dark:text-white'}`}>{f.label}</span>
                          <span className="text-[10px] font-bold text-gray-400 uppercase mt-1">{f.desc}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {mode === 'tags' && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Titre</label>
                      <input 
                        type="text" 
                        value={metadata.title}
                        onChange={(e) => setMetadata({...metadata, title: e.target.value})}
                        className="w-full bg-gray-50 dark:bg-slate-800/50 border-none rounded-2xl px-5 py-4 text-sm font-bold text-gray-700 dark:text-white outline-none focus:ring-4 focus:ring-indigo-500/10 transition-all"
                        placeholder="Ex: Moonlight Sonata"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Artiste</label>
                      <input 
                        type="text" 
                        value={metadata.artist}
                        onChange={(e) => setMetadata({...metadata, artist: e.target.value})}
                        className="w-full bg-gray-50 dark:bg-slate-800/50 border-none rounded-2xl px-5 py-4 text-sm font-bold text-gray-700 dark:text-white outline-none focus:ring-4 focus:ring-indigo-500/10 transition-all"
                        placeholder="Ex: Beethoven"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Album</label>
                      <input 
                        type="text" 
                        value={metadata.album}
                        onChange={(e) => setMetadata({...metadata, album: e.target.value})}
                        className="w-full bg-gray-50 dark:bg-slate-800/50 border-none rounded-2xl px-5 py-4 text-sm font-bold text-gray-700 dark:text-white outline-none focus:ring-4 focus:ring-indigo-500/10 transition-all"
                        placeholder="Ex: Classics Vol. 1"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Année</label>
                      <input 
                        type="text" 
                        value={metadata.year}
                        onChange={(e) => setMetadata({...metadata, year: e.target.value})}
                        className="w-full bg-gray-50 dark:bg-slate-800/50 border-none rounded-2xl px-5 py-4 text-sm font-bold text-gray-700 dark:text-white outline-none focus:ring-4 focus:ring-indigo-500/10 transition-all"
                        placeholder="Ex: 2024"
                      />
                    </div>
                  </div>
                )}

                {mode === 'convert' && (
                  <div className="p-8 bg-indigo-50 dark:bg-indigo-900/10 rounded-[2rem] border border-indigo-100 dark:border-indigo-900/30 flex items-start gap-4">
                    <Info className="text-indigo-600 dark:text-indigo-400 mt-1 flex-shrink-0" size={20} />
                    <p className="text-sm text-indigo-900 dark:text-indigo-300 font-medium leading-relaxed">
                      {FORMATS.find(f => f.value === targetFormat)?.longDesc}
                    </p>
                  </div>
                )}
              </div>

              <div className="mt-10 pt-8 border-t border-gray-50 dark:border-slate-800 flex items-center justify-between gap-6">
                {resultUrl ? (
                  <motion.a
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    href={resultUrl}
                    download
                    className="flex-1 py-5 bg-green-500 hover:bg-green-600 text-white rounded-3xl font-black text-center shadow-xl shadow-green-500/20 transition-all flex items-center justify-center gap-3"
                  >
                    <Download size={20} />
                    Télécharger le résultat
                  </motion.a>
                ) : (
                  <button
                    onClick={handleProcess}
                    disabled={loading || !file}
                    className="flex-1 py-5 bg-gray-900 dark:bg-indigo-600 hover:bg-black dark:hover:bg-indigo-500 text-white rounded-3xl font-black shadow-xl shadow-gray-200 dark:shadow-none transition-all flex items-center justify-center gap-3 active:scale-95 disabled:bg-gray-200 dark:disabled:bg-slate-800 disabled:text-gray-400 disabled:shadow-none"
                  >
                    {loading ? <Loader2 className="animate-spin" size={20} /> : <CheckCircle2 size={20} />}
                    Lancer le traitement
                  </button>
                )}
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default MediaTools;
