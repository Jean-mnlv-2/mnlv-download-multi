import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useTaskStore, Notification } from './store/useTaskStore';
import { useAuthStore } from './store/useAuthStore';
import DownloadCard from './components/downloader/DownloadCard';
import URLInput from './components/downloader/URLInput';
import CSVUpload from './components/downloader/CSVUpload';
import PlaylistExplorer from './components/downloader/PlaylistExplorer';
import MediaTools from './components/media/MediaTools';
import Login from './components/auth/Login';
import Register from './components/auth/Register';
import ProviderManager from './components/auth/ProviderManager';
import HistoryView from './components/downloader/HistoryView';
import AdsDashboard from './components/ads/AdsDashboard';
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
  Disc, 
  Radio, 
  Cloud, 
  Youtube,
  Megaphone,
  TrendingUp,
  Library,
  History,
  XCircle
} from 'lucide-react';

const NotificationToast: React.FC<{ notification: Notification; onRemove: (id: string) => void }> = ({ notification, onRemove }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 50, scale: 0.3 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.5, transition: { duration: 0.2 } }}
      className={`flex items-center p-4 mb-4 text-sm font-bold rounded-2xl shadow-xl border ${
        notification.type === 'success' ? 'bg-green-50 text-green-800 border-green-100 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800' : 
        notification.type === 'error' ? 'bg-red-50 text-red-800 border-red-100 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800' : 
        'bg-blue-50 text-blue-800 border-blue-100 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800'
      }`}
    >
      <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center mr-3">
        {notification.type === 'success' ? (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
        ) : notification.type === 'error' ? (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" /></svg>
        ) : (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
        )}
      </div>
      <div className="flex-1 mr-4">{notification.message}</div>
      <button onClick={() => onRemove(notification.id)} className="text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
      </button>
    </motion.div>
  );
};

const App: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [previewVideo, setPreviewVideo] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'downloader' | 'playlists' | 'ads' | 'media' | 'history' | 'settings'>('downloader');
  const [darkMode, setDarkMode] = useState(localStorage.getItem('theme') === 'dark');

  const { 
    tasks, 
    clearCompleted, 
    notifications, 
    removeNotification, 
    addNotification, 
    connectWebSocket, 
    addTask, 
    pollTaskStatus, 
    fetchHistory,
    cancelAllTasks
  } = useTaskStore();
  const { isAuthenticated, isInitialized, user, logout, initialize, accessToken, providerStatus, fetchProviderStatus } = useAuthStore();

  const handleCancelAll = async (e: React.MouseEvent) => {
    e.stopPropagation(); // Empêcher la redirection vers l'onglet downloader
    if (window.confirm("Voulez-vous vraiment annuler toutes les tâches en cours ?")) {
      await cancelAllTasks();
    }
  };

  useEffect(() => {
    const initFS = async () => {
      const { LocalFileSystemService } = await import('./services/localFileSystem');
      const success = await LocalFileSystemService.initialize();
      if (success) {
        useTaskStore.getState().setLocalDirectorySelected(true);
      }
    };
    initFS();
  }, []);

  const handleQuickDownload = async (url: string) => {
    try {
      const response = await axios.post('/api/download/', { url });
      const data = response.data;
      if (data.type === 'playlist') {
        data.tasks.forEach((t: any) => {
          addTask({ id: t.task_id, status: 'PENDING', progress: 0, original_url: url, provider: data.provider || 'URL' });
          pollTaskStatus(t.task_id);
        });
        addNotification('success', `${data.tasks.length} titres ajoutés`);
        fetchHistory();
      } else {
        addTask({ id: data.task_id, status: 'PENDING', progress: 0, original_url: url, provider: data.provider || 'URL' });
        pollTaskStatus(data.task_id);
        addNotification('info', 'Téléchargement lancé');
        fetchHistory();
      }
    } catch (error) {
      addNotification('error', 'Erreur de téléchargement');
    }
  };

  useEffect(() => {
    initialize();
  }, [initialize]);

  useEffect(() => {
    if (isAuthenticated && accessToken) {
      connectWebSocket(accessToken);
      fetchHistory();
      
      const urlParams = new URLSearchParams(window.location.search);
      const authSuccess = urlParams.get('auth_success');
      const authError = urlParams.get('auth_error');
      const reason = urlParams.get('reason');

      if (authSuccess) {
        addNotification('success', `Compte ${authSuccess} connecté avec succès !`);
        fetchProviderStatus();
        window.history.replaceState({}, document.title, window.location.pathname);
      } else if (authError) {
        let message = `Erreur lors de la connexion ${authError}`;
        if (reason === 'access_denied') message = "Connexion refusée par l'utilisateur.";
        else if (reason === 'invalid_scope') message = "Permissions (scopes) invalides ou non autorisées.";
        else if (reason === 'invalid_request') message = "Requête invalide (vérifiez votre Redirect URI).";
        else if (reason === 'missing_parameters') message = "Paramètres de connexion manquants.";
        else if (reason) message = `Erreur : ${reason}`;
        
        addNotification('error', message);
        window.history.replaceState({}, document.title, window.location.pathname);
      }
    }
  }, [isAuthenticated, accessToken, connectWebSocket, fetchProviderStatus, addNotification]);

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [darkMode]);

  const toggleLanguage = () => {
    i18n.changeLanguage(i18n.language === 'fr' ? 'en' : 'fr');
  };

  if (!isInitialized) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-950 flex items-center justify-center p-4">
        {authMode === 'login' ? (
          <Login onSwitchToRegister={() => setAuthMode('register')} />
        ) : (
          <Register 
            onSwitchToLogin={() => setAuthMode('login')} 
            onSuccess={() => setAuthMode('login')} 
          />
        )}
      </div>
    );
  }

  const activeTasksCount = Object.values(tasks).filter(t => t.status !== 'COMPLETED' && t.status !== 'FAILED').length;

  const handleTaskCounterClick = () => {
    setActiveTab('downloader');
    // On pourrait ajouter un filtre ou scroller vers les tâches actives si nécessaire
  };

  const NavItem = ({ id, icon, label }: { id: any, icon: any, label: string }) => {
    const Icon = icon;
    return (
      <button
        onClick={() => setActiveTab(id as any)}
        className={`flex items-center gap-3 px-6 py-4 rounded-2xl font-black text-sm transition-all duration-300 ${
          activeTab === id 
            ? 'bg-blue-600 text-white shadow-xl shadow-blue-500/30 translate-x-1' 
            : 'text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-slate-800'
        }`}
      >
        <Icon size={20} strokeWidth={2.5} />
        <span className="tracking-tight">{label}</span>
      </button>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950 flex transition-colors duration-300">
      {/* Toast Notifications */}
      <Toaster 
        position="bottom-right"
        toastOptions={{
          duration: 4000,
          style: {
            borderRadius: '1rem',
            background: '#1e293b',
            color: '#fff',
            fontWeight: 'bold',
          },
        }}
      />

      {/* Sidebar */}
      <aside className="w-72 bg-white dark:bg-slate-900 border-r border-gray-100 dark:border-slate-800 flex flex-col fixed h-full z-20">
        <div className="p-8">
          <div className="flex items-center space-x-3 mb-10">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl flex items-center justify-center shadow-xl shadow-blue-500/20">
              <Music2 className="text-white" size={24} />
            </div>
            <h1 className="text-2xl font-black text-gray-900 dark:text-white tracking-tighter">MNLV</h1>
          </div>

          <nav className="space-y-2">
            <NavItem id="dashboard" icon={LayoutDashboard} label={t('dashboard')} />
            <NavItem id="downloader" icon={Download} label={t('downloader')} />
            <NavItem id="playlists" icon={ListMusic} label={t('playlists')} />
            {providerStatus.spotify && <NavItem id="ads" icon={Megaphone} label="Spotify Ads" />}
            <NavItem id="media" icon={Wrench} label={t('mediaTools')} />
            <NavItem id="history" icon={History} label={t('history')} />
            <NavItem id="settings" icon={Settings} label={t('settings')} />
          </nav>
        </div>

        <div className="mt-auto p-6 space-y-4">
          <div className="bg-gray-50 dark:bg-slate-800/50 p-4 rounded-3xl border border-gray-100 dark:border-slate-800">
            <div className="flex items-center space-x-3 mb-3">
              <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center text-blue-600 dark:text-blue-400 font-black">
                {user?.username?.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-black text-gray-900 dark:text-white truncate">{user?.username}</p>
                <p className="text-[10px] text-gray-400 font-bold uppercase truncate tracking-wider">{user?.email}</p>
              </div>
            </div>
            <button 
              onClick={logout}
              className="w-full flex items-center justify-center space-x-2 py-2 text-xs font-bold text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-colors"
            >
              <LogOut size={14} />
              <span>{t('logout')}</span>
            </button>
          </div>

          <div className="flex items-center justify-between px-2">
            <button 
              onClick={() => setDarkMode(!darkMode)}
              className="p-2 text-gray-400 hover:text-blue-500 transition-colors"
            >
              {darkMode ? <Sun size={20} /> : <Moon size={20} />}
            </button>
            <button 
              onClick={toggleLanguage}
              className="p-2 text-gray-400 hover:text-blue-500 transition-colors flex items-center space-x-1"
            >
              <Globe size={20} />
              <span className="text-[10px] font-black uppercase">{i18n.language}</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-72 min-h-screen">
        <header className="h-20 border-b border-gray-100 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md sticky top-0 z-10 flex items-center justify-between px-10">
          <h2 className="text-xl font-black text-gray-900 dark:text-white tracking-tight">
            {t(activeTab)}
          </h2>
          
          {activeTasksCount > 0 && (
            <div className="flex items-center gap-2">
              <button 
                onClick={handleTaskCounterClick}
                className="flex items-center space-x-2 bg-blue-50 dark:bg-blue-900/20 px-4 py-2 rounded-2xl border border-blue-100 dark:border-blue-800 hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-all active:scale-95"
              >
                <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
                <span className="text-xs font-black text-blue-600 dark:text-blue-400">
                  {activeTasksCount} {t('active_tasks')}
                </span>
              </button>
              
              <button
                onClick={handleCancelAll}
                className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-all"
                title="Tout annuler"
              >
                <XCircle size={18} />
              </button>
            </div>
          )}
        </header>

        <div className="p-10 max-w-6xl mx-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              {activeTab === 'dashboard' && (
                <div className="space-y-10">
                  {/* Stats / Welcome Header */}
                  <motion.div 
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="grid grid-cols-1 md:grid-cols-3 gap-6"
                  >
                    <div className="bg-gradient-to-br from-blue-600 to-indigo-700 p-8 rounded-[2.5rem] text-white shadow-2xl shadow-blue-500/20 col-span-1 md:col-span-2 relative overflow-hidden group">
                      <div className="absolute -right-10 -bottom-10 w-64 h-64 bg-white/10 rounded-full blur-3xl group-hover:bg-white/20 transition-all duration-700" />
                      <div className="relative z-10">
                        <h3 className="text-3xl font-black tracking-tighter mb-2">Hello, {user?.username}! 👋</h3>
                        <p className="text-blue-100 font-bold text-sm max-w-sm opacity-80 leading-relaxed">
                          Votre studio de téléchargement personnel est prêt. Collez un lien pour commencer.
                        </p>
                        <button 
                          onClick={() => setActiveTab('downloader')}
                          className="mt-6 px-8 py-3 bg-white text-blue-600 rounded-2xl font-black text-sm hover:shadow-xl hover:scale-105 transition-all active:scale-95"
                        >
                          Lancer un téléchargement
                        </button>
                      </div>
                    </div>
                    
                    <div className="bg-white dark:bg-slate-900 p-8 rounded-[2.5rem] border border-gray-100 dark:border-slate-800 shadow-sm flex flex-col justify-center items-center text-center group">
                      <div className="w-14 h-14 bg-blue-50 dark:bg-blue-900/20 rounded-2xl flex items-center justify-center text-blue-600 mb-4 group-hover:scale-110 transition-transform">
                        <Download size={28} strokeWidth={2.5} />
                      </div>
                      <p className="text-2xl font-black text-gray-900 dark:text-white tracking-tighter">{Object.values(tasks).length}</p>
                      <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mt-1">Titres traités</p>
                    </div>
                  </motion.div>

                  {/* Deezer Features Section */}
                  {providerStatus.deezer && (
                    <motion.div 
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="grid grid-cols-1 md:grid-cols-4 gap-6"
                    >
                      <div className="md:col-span-4 flex items-center gap-3">
                        <div className="w-1 h-6 bg-purple-600 rounded-full" />
                        <h3 className="text-sm font-black text-gray-900 dark:text-white uppercase tracking-widest">
                          Fonctionnalités Deezer
                        </h3>
                      </div>
                      
                      <button 
                        onClick={() => axios.get('/api/auth/providers/deezer/flow/').then(res => {
                          res.data.tasks.forEach((t: any) => {
                            addTask({ id: t.task_id, status: 'PENDING', progress: 0, original_url: 'Flow Deezer', provider: 'deezer' });
                            pollTaskStatus(t.task_id);
                          });
                          addNotification('success', 'Flow Deezer lancé');
                        })}
                        className="bg-white dark:bg-slate-900 p-6 rounded-[2rem] border border-gray-100 dark:border-slate-800 shadow-sm hover:shadow-xl hover:border-purple-200 transition-all flex flex-col items-center text-center gap-3 group"
                      >
                        <div className="w-12 h-12 bg-purple-50 dark:bg-purple-900/20 rounded-2xl flex items-center justify-center text-purple-600 group-hover:scale-110 transition-transform">
                          <Radio size={24} />
                        </div>
                        <div>
                          <p className="text-xs font-black text-gray-900 dark:text-white uppercase">Mon Flow</p>
                          <p className="text-[10px] text-gray-400 font-bold uppercase tracking-tighter">Radio Personnelle</p>
                        </div>
                      </button>

                      <button 
                        onClick={() => setActiveTab('playlists')}
                        className="bg-white dark:bg-slate-900 p-6 rounded-[2rem] border border-gray-100 dark:border-slate-800 shadow-sm hover:shadow-xl hover:border-pink-200 transition-all flex flex-col items-center text-center gap-3 group"
                      >
                        <div className="w-12 h-12 bg-pink-50 dark:bg-pink-900/20 rounded-2xl flex items-center justify-center text-pink-600 group-hover:scale-110 transition-transform">
                          <Library size={24} />
                        </div>
                        <div>
                          <p className="text-xs font-black text-gray-900 dark:text-white uppercase">Mes Favoris</p>
                          <p className="text-[10px] text-gray-400 font-bold uppercase tracking-tighter">Coups de Cœur</p>
                        </div>
                      </button>

                      <div className="md:col-span-2 bg-white dark:bg-slate-900 p-6 rounded-[2rem] border border-gray-100 dark:border-slate-800 shadow-sm">
                         <div className="flex items-center gap-3 mb-4">
                            <TrendingUp size={18} className="text-blue-500" />
                            <p className="text-xs font-black text-gray-900 dark:text-white uppercase tracking-widest">Tendances</p>
                         </div>
                         <div className="flex gap-2">
                            <button 
                              onClick={() => handleQuickDownload('https://www.deezer.com/playlist/3155776842')}
                              className="flex-1 py-2 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-xl text-[10px] font-black uppercase tracking-tighter hover:bg-blue-600 hover:text-white transition-all"
                            >
                              Top 50 Monde
                            </button>
                            <button 
                              onClick={() => handleQuickDownload('https://www.deezer.com/playlist/1109890291')}
                              className="flex-1 py-2 bg-gray-50 dark:bg-slate-800 text-gray-400 rounded-xl text-[10px] font-black uppercase tracking-tighter hover:bg-gray-200 dark:hover:bg-slate-700 transition-all"
                            >
                              Top France
                            </button>
                         </div>
                      </div>
                    </motion.div>
                  )}

                  <section>
                    <div className="flex justify-between items-center mb-6">
                      <div className="flex items-center gap-3">
                        <div className="w-1 h-6 bg-blue-600 rounded-full" />
                        <h3 className="text-sm font-black text-gray-900 dark:text-white uppercase tracking-widest">
                          {t('recent_history')}
                        </h3>
                      </div>
                      {Object.values(tasks).length > 0 && (
                        <button 
                          onClick={clearCompleted}
                          className="px-4 py-2 bg-gray-50 dark:bg-slate-800/50 hover:bg-red-50 dark:hover:bg-red-900/20 text-[10px] font-black text-gray-400 hover:text-red-500 uppercase tracking-widest rounded-xl transition-all"
                        >
                          {t('clear_list')}
                        </button>
                      )}
                    </div>
                    
                    {Object.values(tasks).length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <AnimatePresence mode="popLayout">
                          {Object.values(tasks).map(task => (
                            <DownloadCard key={task.id} task={task} onPreviewVideo={setPreviewVideo} />
                          ))}
                        </AnimatePresence>
                      </div>
                    ) : (
                      <div className="text-center py-20 bg-white dark:bg-slate-900 rounded-[2.5rem] border border-gray-100 dark:border-slate-800 shadow-sm border-dashed">
                        <div className="bg-blue-50 dark:bg-blue-900/20 w-20 h-20 rounded-3xl flex items-center justify-center mx-auto mb-6 transform rotate-3">
                          <Music2 className="text-blue-500 dark:text-blue-400" size={40} />
                        </div>
                        <h4 className="text-xl font-black text-gray-900 dark:text-white mb-2">{t('ready_for_music')}</h4>
                        <p className="text-gray-400 dark:text-gray-500 max-w-xs mx-auto text-sm font-medium leading-relaxed mb-8">
                          {t('paste_link')}
                        </p>
                        <div className="flex justify-center gap-3 opacity-30 grayscale">
                          <Disc size={20} /> <Radio size={20} /> <Cloud size={20} /> <Youtube size={20} />
                        </div>
                      </div>
                    )}
                  </section>
                </div>
              )}

              {activeTab === 'downloader' && (
                <div className="space-y-8">
                  <URLInput />
                  <div className="grid grid-cols-1 gap-8">
                    <CSVUpload />
                  </div>
                </div>
              )}

              {activeTab === 'playlists' && <PlaylistExplorer />}
              {activeTab === 'ads' && <AdsDashboard />}
              {activeTab === 'media' && <MediaTools />}

              {activeTab === 'history' && (
                <div className="bg-white dark:bg-slate-900 rounded-[2.5rem] p-10 border border-gray-100 dark:border-slate-800">
                  <HistoryView />
                </div>
              )}

              {activeTab === 'settings' && (
                <div className="space-y-8">
                  <div className="bg-white dark:bg-slate-900 rounded-[2.5rem] p-10 border border-gray-100 dark:border-slate-800">
                    <h3 className="text-xl font-black text-gray-900 dark:text-white tracking-tight mb-6">Préférences</h3>
                    <div className="space-y-6">
                      <div className="flex items-center justify-between p-6 bg-gray-50 dark:bg-slate-800/50 rounded-3xl">
                        <div>
                          <p className="font-black text-gray-900 dark:text-white">{t('dark_mode')}</p>
                          <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">Activer ou désactiver l'interface sombre</p>
                        </div>
                        <button 
                          onClick={() => setDarkMode(!darkMode)}
                          className={`w-14 h-8 rounded-full transition-all relative ${darkMode ? 'bg-blue-600' : 'bg-gray-300'}`}
                        >
                          <div className={`absolute top-1 w-6 h-6 bg-white rounded-full transition-all ${darkMode ? 'left-7' : 'left-1'}`} />
                        </button>
                      </div>

                      <div className="flex items-center justify-between p-6 bg-gray-50 dark:bg-slate-800/50 rounded-3xl">
                        <div>
                          <p className="font-black text-gray-900 dark:text-white">{t('language')}</p>
                          <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">Changer la langue de l'interface</p>
                        </div>
                        <button 
                          onClick={toggleLanguage}
                          className="px-6 py-2 bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-xl font-black text-sm uppercase shadow-sm"
                        >
                          {i18n.language === 'fr' ? 'English' : 'Français'}
                        </button>
                      </div>
                    </div>
                  </div>

                  <div className="bg-white dark:bg-slate-900 rounded-[2.5rem] p-10 border border-gray-100 dark:border-slate-800">
                    <ProviderManager />
                  </div>
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>

      {/* Notifications */}
      <div className="fixed bottom-10 right-10 z-50 flex flex-col items-end pointer-events-none">
        <div className="pointer-events-auto w-full max-w-sm">
          <AnimatePresence>
            {notifications.map(n => (
              <NotificationToast key={n.id} notification={n} onRemove={removeNotification} />
            ))}
          </AnimatePresence>
        </div>
      </div>

      {/* Video Preview Modal */}
      <AnimatePresence>
        {previewVideo && (
          <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
            <motion.div 
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setPreviewVideo(null)}
              className="absolute inset-0 bg-black/95 backdrop-blur-md"
            />
            <motion.div 
              initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
              className="relative w-full max-w-5xl bg-black rounded-[3rem] overflow-hidden shadow-2xl border border-white/10"
            >
              <button 
                onClick={() => setPreviewVideo(null)}
                className="absolute top-6 right-6 z-10 p-3 bg-white/10 hover:bg-white/20 rounded-full text-white transition-colors"
              >
                <LogOut size={24} className="rotate-90" />
              </button>
              <video 
                src={previewVideo} 
                controls 
                autoPlay 
                className="w-full aspect-video"
              />
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default App;
