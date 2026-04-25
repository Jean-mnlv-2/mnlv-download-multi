import React, { useState, useMemo } from 'react';
import { useTaskStore, Task } from '../../store/useTaskStore';
import { 
  History as HistoryIcon, 
  Search, 
  Calendar, 
  Clock, 
  Filter, 
  Trash2, 
  Download, 
  CheckCircle2, 
  AlertCircle, 
  ChevronRight,
  Music,
  Video,
  FileText
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ProviderIcon from './ProviderIcon';

const HistoryView: React.FC = () => {
  const { history, clearCompleted } = useTaskStore();
  const [searchTerm, setSearchUrl] = useState('');
  const [dateFilter, setDateFilter] = useState<'all' | 'today' | 'week' | 'month'>('all');
  const [typeFilter, setTypeFilter] = useState<'all' | 'audio' | 'video'>('all');

  const filteredHistory = useMemo(() => {
    return (history as Task[]).filter(item => {
      // Filtre recherche
      const matchesSearch = (item.track?.title?.toLowerCase() || "").includes(searchTerm.toLowerCase()) || 
                           (item.track?.artist?.toLowerCase() || "").includes(searchTerm.toLowerCase()) ||
                           (item.original_url?.toLowerCase() || "").includes(searchTerm.toLowerCase());
      
      // Filtre date
      const date = new Date(item.created_at || Date.now());
      const now = new Date();
      let matchesDate = true;
      
      if (dateFilter === 'today') {
        matchesDate = date.toDateString() === now.toDateString();
      } else if (dateFilter === 'week') {
        const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        matchesDate = date >= weekAgo;
      } else if (dateFilter === 'month') {
        matchesDate = date.getMonth() === now.getMonth() && date.getFullYear() === now.getFullYear();
      }

      // Filtre type
      const isVideo = item.media_type === 'VIDEO' || item.media_type === 'MKV';
      const matchesType = typeFilter === 'all' || 
                         (typeFilter === 'video' && isVideo) || 
                         (typeFilter === 'audio' && !isVideo);

      return matchesSearch && matchesDate && matchesType;
    }).sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime());
  }, [history, searchTerm, dateFilter, typeFilter]);

  return (
    <div className="space-y-8">
      {/* Header & Stats */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h3 className="text-2xl font-black text-gray-900 dark:text-white tracking-tight flex items-center gap-3">
            <HistoryIcon className="text-blue-500" size={28} />
            Historique des activités
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 font-medium mt-1">
            Retrouvez tous vos téléchargements et manipulations passés
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="px-6 py-3 bg-gray-50 dark:bg-slate-800/50 rounded-2xl border border-gray-100 dark:border-slate-800">
            <span className="text-[10px] font-black uppercase tracking-widest text-gray-400 block">Total actions</span>
            <span className="text-xl font-black text-blue-500">{history.length}</span>
          </div>
          <button 
            onClick={() => {
              if (window.confirm("Voulez-vous vraiment vider l'historique ? (Note: Cela ne supprimera pas les fichiers sur le serveur)")) {
                clearCompleted();
              }
            }}
            className="p-4 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-2xl transition-all"
            title="Vider l'affichage local"
          >
            <Trash2 size={20} />
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-white dark:bg-slate-900 p-6 rounded-[2rem] border border-gray-100 dark:border-slate-800 shadow-sm space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
            <input 
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchUrl(e.target.value)}
              placeholder="Rechercher un titre ou un lien..."
              className="w-full pl-12 pr-6 py-4 bg-gray-50 dark:bg-slate-800 border-2 border-transparent focus:border-blue-500 rounded-2xl outline-none transition-all font-bold text-sm"
            />
          </div>

          {/* Date Filter */}
          <div className="flex bg-gray-50 dark:bg-slate-800 p-1.5 rounded-2xl">
            {(['all', 'today', 'week', 'month'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setDateFilter(f)}
                className={`flex-1 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${dateFilter === f ? 'bg-white dark:bg-slate-700 text-blue-600 shadow-sm' : 'text-gray-400 hover:text-gray-600'}`}
              >
                {f === 'all' ? 'Tout' : f === 'today' ? 'Aujourd\'hui' : f === 'week' ? '7 jours' : 'Ce mois'}
              </button>
            ))}
          </div>

          {/* Type Filter */}
          <div className="flex bg-gray-50 dark:bg-slate-800 p-1.5 rounded-2xl">
            {(['all', 'audio', 'video'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setTypeFilter(f)}
                className={`flex-1 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${typeFilter === f ? 'bg-white dark:bg-slate-700 text-blue-600 shadow-sm' : 'text-gray-400 hover:text-gray-600'}`}
              >
                {f === 'all' ? 'Tous formats' : f === 'audio' ? 'Audio' : 'Vidéo'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* History List */}
      <div className="space-y-4">
        {filteredHistory.length === 0 ? (
          <div className="py-20 text-center bg-gray-50/50 dark:bg-slate-900/50 rounded-[3rem] border-2 border-dashed border-gray-100 dark:border-slate-800">
            <div className="w-16 h-16 bg-white dark:bg-slate-800 rounded-2xl flex items-center justify-center mx-auto mb-4 text-gray-300">
              <Calendar size={32} />
            </div>
            <p className="text-gray-400 font-black uppercase tracking-widest text-xs">Aucun historique trouvé pour ces filtres</p>
          </div>
        ) : (
          filteredHistory.map((item: any, idx: number) => {
            const date = new Date(item.created_at || Date.now());
            const isVideo = item.media_type === 'VIDEO' || item.media_type === 'MKV';

            return (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                key={item.id || idx}
                className="group bg-white dark:bg-slate-900 p-5 rounded-[2rem] border border-gray-100 dark:border-slate-800 flex items-center gap-6 hover:shadow-xl hover:shadow-blue-500/5 hover:border-blue-100 dark:hover:border-blue-900/30 transition-all"
              >
                <div className="w-14 h-14 bg-gray-50 dark:bg-slate-800 rounded-2xl flex items-center justify-center text-gray-400 group-hover:bg-blue-50 dark:group-hover:bg-blue-900/20 group-hover:text-blue-500 transition-all flex-shrink-0">
                  {isVideo ? <Video size={24} /> : <Music size={24} />}
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-3 mb-1">
                    <h4 className="font-black text-gray-900 dark:text-white truncate">
                      {item.track?.title || item.original_url || "Titre inconnu"}
                    </h4>
                    <span className={`text-[8px] font-black px-2 py-0.5 rounded-full uppercase tracking-tighter ${item.status === 'COMPLETED' ? 'bg-green-50 text-green-600 dark:bg-green-900/20' : 'bg-red-50 text-red-600 dark:bg-red-900/20'}`}>
                      {item.status}
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-4 text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                    <span className="flex items-center gap-1">
                      <Clock size={12} /> {date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    <span className="flex items-center gap-1">
                      <Calendar size={12} /> {date.toLocaleDateString()}
                    </span>
                    <span className="flex items-center gap-1 text-blue-500">
                      <ProviderIcon provider={item.provider} size={12} /> {item.track?.artist || item.provider || 'batch'}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity pr-2">
                  <button className="p-3 text-gray-300 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-xl transition-all">
                    <Download size={18} />
                  </button>
                  <button className="p-3 text-gray-300 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-all">
                    <Trash2 size={18} />
                  </button>
                </div>
                
                <div className="pr-2 text-gray-200 dark:text-slate-800">
                  <ChevronRight size={20} />
                </div>
              </motion.div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default HistoryView;
