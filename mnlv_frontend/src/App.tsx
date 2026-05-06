import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useTaskStore } from './store/useTaskStore';
import { useAuthStore } from './store/useAuthStore';
import DownloadCard from './components/downloader/DownloadCard';
import TaskList from './components/downloader/TaskList';
import URLInput from './components/downloader/URLInput';
import CSVUpload from './components/downloader/CSVUpload';
import StagingArea from './components/downloader/StagingArea';
import PlaylistExplorer from './components/downloader/PlaylistExplorer';
import MediaTools from './components/media/MediaTools';
import Login from './components/auth/Login';
import Register from './components/auth/Register';
import ProviderManager from './components/auth/ProviderManager';
import HistoryView from './components/downloader/HistoryView';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { Toaster } from 'react-hot-toast';
import { 
  LayoutDashboard, 
  Download, 
  ListMusic, 
  Wrench, 
  Settings, 
  LogOut, 
  Moon, 
  Sun, 
  Globe, 
  Music2, 
  History,
  Menu,
  X,
  LayoutGrid,
  List as ListIcon,
  Search,
  Bell,
  ChevronRight
} from 'lucide-react';

const App: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [activeTab, setActiveTab] = useState<'dashboard' | 'downloader' | 'playlists' | 'ads' | 'media' | 'history' | 'settings'>('downloader');
  const [darkMode, setDarkMode] = useState(localStorage.getItem('theme') === 'dark');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list');

  const { tasks, connectWebSocket, fetchHistory, stagedTracks } = useTaskStore();
  const { isAuthenticated, isInitialized, user, logout, initialize, accessToken } = useAuthStore();

  useEffect(() => {
    initialize();
  }, [initialize]);

  useEffect(() => {
    if (isAuthenticated && accessToken) {
      connectWebSocket(accessToken);
      fetchHistory();
    }
  }, [isAuthenticated, accessToken, connectWebSocket, fetchHistory]);

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [darkMode]);

  if (!isInitialized) {
    return (
      <div className="min-h-screen bg-mnlv-slate-50 dark:bg-mnlv-slate-950 flex items-center justify-center">
        <motion.div 
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
          className="w-10 h-10 border-[3px] border-mnlv-blue border-t-transparent rounded-full"
        />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-mnlv-slate-50 dark:bg-mnlv-slate-950 flex items-center justify-center p-4">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
          {authMode === 'login' ? (
            <Login onSwitchToRegister={() => setAuthMode('register')} />
          ) : (
            <Register onSwitchToLogin={() => setAuthMode('login')} onSuccess={() => setAuthMode('login')} />
          )}
        </motion.div>
      </div>
    );
  }

  const NavItem = ({ id, icon, label }: { id: any, icon: any, label: string }) => {
    const Icon = icon;
    const active = activeTab === id;
    return (
      <button
        onClick={() => {
          setActiveTab(id);
          setIsSidebarOpen(false);
        }}
        className={`w-full flex items-center justify-between px-4 py-3 rounded-2xl transition-all duration-300 group ${
          active 
            ? 'bg-white dark:bg-mnlv-slate-800 shadow-pro border border-mnlv-slate-100 dark:border-mnlv-slate-700 text-mnlv-blue' 
            : 'text-mnlv-slate-500 hover:text-mnlv-slate-900 dark:hover:text-white'
        }`}
      >
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-xl transition-colors ${active ? 'bg-mnlv-blue/10' : 'bg-transparent group-hover:bg-mnlv-slate-100 dark:group-hover:bg-mnlv-slate-800'}`}>
            <Icon size={18} strokeWidth={active ? 2.5 : 2} />
          </div>
          <span className={`text-sm font-bold tracking-tight ${active ? 'opacity-100' : 'opacity-70 group-hover:opacity-100'}`}>{label}</span>
        </div>
        {active && (
          <motion.div layoutId="active-pill" className="w-1.5 h-1.5 rounded-full bg-mnlv-blue" />
        )}
      </button>
    );
  };

  return (
    <div className="min-h-screen bg-mnlv-slate-50 dark:bg-mnlv-slate-950 font-sans text-mnlv-slate-900 dark:text-mnlv-slate-50 flex overflow-hidden">
      <Toaster position="top-center" />

      {/* Sidebar */}
      <aside className={`
        fixed inset-y-0 left-0 w-72 bg-mnlv-slate-50/50 dark:bg-mnlv-slate-950/50 backdrop-blur-xl border-r border-mnlv-slate-200/50 dark:border-mnlv-slate-800/50
        transform transition-transform duration-500 ease-[cubic-bezier(0.23,1,0.32,1)] z-50 lg:relative lg:translate-x-0
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="h-full flex flex-col p-6">
          <div className="flex items-center gap-3 mb-10 px-2">
            <div className="w-10 h-10 bg-mnlv-blue rounded-2xl flex items-center justify-center shadow-pro-blue">
              <Music2 className="text-white" size={22} />
            </div>
            <span className="font-display font-black text-2xl tracking-tighter">MNLV</span>
          </div>

          <nav className="flex-1 space-y-2">
            <NavItem id="dashboard" icon={LayoutDashboard} label={t('dashboard')} />
            <NavItem id="downloader" icon={Download} label={t('downloader')} />
            <NavItem id="playlists" icon={ListMusic} label={t('playlists')} />
            <NavItem id="media" icon={Wrench} label={t('media_tools')} />
            <NavItem id="history" icon={History} label={t('history')} />
          </nav>

          <div className="mt-auto pt-6 space-y-6">
            <div className="px-2">
              <NavItem id="settings" icon={Settings} label={t('settings')} />
            </div>

            <div className="p-5 bg-white dark:bg-mnlv-slate-900 rounded-[2rem] border border-mnlv-slate-100 dark:border-mnlv-slate-800 shadow-pro">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-2xl bg-mnlv-red flex items-center justify-center text-white font-bold shadow-lg shadow-mnlv-red/20">
                  {user?.username?.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-black truncate">{user?.username}</p>
                  <div className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                    <p className="text-[10px] text-mnlv-slate-500 font-bold uppercase tracking-widest">Premium</p>
                  </div>
                </div>
              </div>
              <button 
                onClick={logout}
                className="w-full flex items-center justify-center gap-2 py-3 text-xs font-black text-mnlv-red hover:bg-mnlv-red/5 rounded-xl transition-all active:scale-95"
              >
                <LogOut size={14} />
                <span>Déconnexion</span>
              </button>
            </div>
            
            <div className="flex items-center justify-between px-4 pb-2">
              <button onClick={() => setDarkMode(!darkMode)} className="p-2.5 bg-white dark:bg-mnlv-slate-900 rounded-xl border border-mnlv-slate-100 dark:border-mnlv-slate-800 shadow-sm text-mnlv-slate-500 hover:text-mnlv-blue transition-all active:scale-90">
                {darkMode ? <Sun size={18} /> : <Moon size={18} />}
              </button>
              <button onClick={() => i18n.changeLanguage(i18n.language === 'fr' ? 'en' : 'fr')} className="p-2.5 bg-white dark:bg-mnlv-slate-900 rounded-xl border border-mnlv-slate-100 dark:border-mnlv-slate-800 shadow-sm text-mnlv-slate-500 hover:text-mnlv-blue transition-all active:scale-90">
                <Globe size={18} />
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        {/* Top Header */}
        <header className="h-20 flex items-center justify-between px-6 lg:px-10 border-b border-mnlv-slate-200/50 dark:border-mnlv-slate-800/50 bg-white/50 dark:bg-mnlv-slate-950/50 backdrop-blur-xl z-30">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setIsSidebarOpen(true)}
              className="lg:hidden p-2 text-mnlv-slate-600 dark:text-mnlv-slate-400 hover:bg-mnlv-slate-100 dark:hover:bg-mnlv-slate-800 rounded-xl transition-colors"
            >
              <Menu size={22} />
            </button>
            <div className="hidden md:flex items-center gap-2 px-4 py-2 bg-mnlv-slate-100 dark:bg-mnlv-slate-900 rounded-xl border border-mnlv-slate-200/50 dark:border-mnlv-slate-800/50 text-mnlv-slate-400 focus-within:text-mnlv-blue focus-within:border-mnlv-blue/30 transition-all w-64 lg:w-96">
              <Search size={16} />
              <input type="text" placeholder="Rechercher..." className="bg-transparent border-none outline-none text-xs font-bold w-full placeholder:text-mnlv-slate-500" />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button className="p-2.5 text-mnlv-slate-500 hover:text-mnlv-blue transition-colors relative">
              <Bell size={20} />
              <span className="absolute top-2 right-2 w-2 h-2 bg-mnlv-red rounded-full border-2 border-white dark:border-mnlv-slate-950" />
            </button>
            <div className="h-8 w-px bg-mnlv-slate-200 dark:bg-mnlv-slate-800 mx-2" />
            <div className="flex items-center gap-3 pl-2">
              <div className="text-right hidden sm:block">
                <p className="text-xs font-black leading-none mb-1">{user?.username}</p>
                <p className="text-[9px] text-mnlv-blue font-bold uppercase tracking-widest">Compte Pro</p>
              </div>
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-mnlv-blue to-indigo-600 shadow-pro-blue p-0.5">
                <div className="w-full h-full rounded-[14px] bg-white dark:bg-mnlv-slate-950 flex items-center justify-center font-black text-mnlv-blue text-sm">
                  {user?.username?.charAt(0).toUpperCase()}
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-6 lg:p-10 space-y-10 custom-scrollbar">
          <AnimatePresence mode="wait">
            {activeTab === 'downloader' && (
              <motion.div
                key="downloader"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] }}
                className="max-w-6xl mx-auto space-y-10"
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                  <div>
                    <h2 className="text-4xl font-display font-black tracking-tight">{t('downloader')}</h2>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="px-2 py-0.5 bg-mnlv-blue/10 text-mnlv-blue text-[10px] font-black uppercase tracking-widest rounded-md">High Speed</span>
                      <p className="text-mnlv-slate-500 text-sm font-medium">Téléchargez vos médias en un clic.</p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2 bg-white dark:bg-mnlv-slate-900 p-1.5 rounded-2xl border border-mnlv-slate-200/50 dark:border-mnlv-slate-800/50 shadow-sm">
                    <button 
                      onClick={() => setViewMode('list')}
                      className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-black transition-all ${viewMode === 'list' ? 'bg-mnlv-blue text-white shadow-pro-blue' : 'text-mnlv-slate-400 hover:bg-mnlv-slate-50 dark:hover:bg-mnlv-slate-800'}`}
                    >
                      <ListIcon size={16} />
                      <span>Liste</span>
                    </button>
                    <button 
                      onClick={() => setViewMode('grid')}
                      className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-black transition-all ${viewMode === 'grid' ? 'bg-mnlv-blue text-white shadow-pro-blue' : 'text-mnlv-slate-400 hover:bg-mnlv-slate-50 dark:hover:bg-mnlv-slate-800'}`}
                    >
                      <LayoutGrid size={16} />
                      <span>Grille</span>
                    </button>
                  </div>
                </div>

                <div className="relative group">
                  <div className="absolute -inset-1 bg-gradient-to-r from-mnlv-blue to-indigo-600 rounded-[2rem] blur opacity-20 group-hover:opacity-30 transition duration-1000 group-hover:duration-200" />
                  <URLInput />
                </div>

                {/* CSV/Excel Upload Section */}
                <div className="pt-4">
                  <CSVUpload />
                </div>

                <div className="space-y-6">
                  <div className="flex items-center justify-between px-2">
                    <div className="flex items-center gap-3">
                      <h3 className="font-black text-xl tracking-tight">File d'attente</h3>
                      <span className="w-6 h-6 rounded-lg bg-mnlv-slate-200 dark:bg-mnlv-slate-800 flex items-center justify-center text-[10px] font-black text-mnlv-slate-500">
                        {Object.keys(tasks).length + stagedTracks.length}
                      </span>
                    </div>
                  </div>

                  {stagedTracks.length > 0 && <StagingArea />}

                  {Object.keys(tasks).length > 0 && (
                    viewMode === 'grid' ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                        <AnimatePresence mode="popLayout">
                          {Object.values(tasks).map(task => (
                            <DownloadCard key={task.id} task={task} />
                          ))}
                        </AnimatePresence>
                      </div>
                    ) : (
                      <TaskList tasks={Object.values(tasks)} />
                    )
                  )}

                  {Object.keys(tasks).length === 0 && stagedTracks.length === 0 && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="py-24 text-center">
                      <div className="w-20 h-20 bg-mnlv-slate-100 dark:bg-mnlv-slate-900 rounded-[2.5rem] flex items-center justify-center mx-auto text-mnlv-slate-300 mb-6 border border-mnlv-slate-200/50 dark:border-mnlv-slate-800/50">
                        <Download size={32} />
                      </div>
                      <h4 className="text-lg font-black mb-1">Prêt à télécharger</h4>
                      <p className="text-mnlv-slate-500 text-sm font-medium">Vos téléchargements apparaîtront ici en temps réel.</p>
                    </motion.div>
                  )}
                </div>
              </motion.div>
            )}

            {activeTab === 'dashboard' && (
              <motion.div key="dashboard" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="max-w-6xl mx-auto space-y-10">
                <h2 className="text-4xl font-display font-black tracking-tight">Vue d'ensemble</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                  {[
                    { label: 'Téléchargements', val: '1,284', trend: '+12%', color: 'text-mnlv-blue' },
                    { label: 'Espace Économisé', val: '42.5 GB', trend: '+5%', color: 'text-mnlv-red' },
                    { label: 'Playlists Sync', val: '28', trend: '+2', color: 'text-indigo-500' }
                  ].map((stat, i) => (
                    <div key={i} className="p-8 bg-white dark:bg-mnlv-slate-900 rounded-[2.5rem] border border-mnlv-slate-100 dark:border-mnlv-slate-800 shadow-pro group hover:shadow-pro-hover transition-all duration-500">
                      <div className="flex justify-between items-start mb-4">
                        <p className="text-mnlv-slate-500 font-black text-[10px] uppercase tracking-widest">{stat.label}</p>
                        <span className="text-[10px] font-black text-green-500 px-2 py-1 bg-green-500/10 rounded-lg">{stat.trend}</span>
                      </div>
                      <p className={`text-4xl font-display font-black ${stat.color}`}>{stat.val}</p>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {activeTab === 'playlists' && <PlaylistExplorer key="playlists" />}
            {activeTab === 'media' && <MediaTools key="media" />}
            {activeTab === 'history' && <HistoryView key="history" />}
            {activeTab === 'settings' && <ProviderManager key="settings" />}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
};

export default App;
