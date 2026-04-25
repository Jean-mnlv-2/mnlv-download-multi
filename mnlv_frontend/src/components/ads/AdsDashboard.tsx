import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuthStore } from '../../store/useAuthStore';
import { 
  BarChart3, 
  Plus, 
  Settings, 
  Users, 
  Target, 
  FileText, 
  AlertCircle,
  LayoutDashboard,
  Megaphone,
  Briefcase,
  ChevronRight,
  Loader2,
  Upload,
  Image as ImageIcon,
  Music,
  Video
} from 'lucide-react';

const Sparkline = ({ color }: { color: string }) => (
  <svg className="w-20 h-8 opacity-50" viewBox="0 0 100 40">
    <path
      d="M0 35 Q 20 5, 40 25 T 80 15 T 100 30"
      fill="none"
      stroke={color === 'blue' ? '#3b82f6' : color === 'green' ? '#22c55e' : '#a855f7'}
      strokeWidth="3"
    />
  </svg>
);
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';

const AdsDashboard: React.FC = () => {
  const { providerStatus } = useAuthStore();
  const [activeTab, setActiveTab] = useState<'overview' | 'campaigns' | 'adsets' | 'ads' | 'reports' | 'audiences' | 'assets'>('overview');
  const [adAccounts, setAdAccounts] = useState<any[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [data, setData] = useState<any>({
    campaigns: [],
    adsets: [],
    ads: [],
    audiences: [],
    assets: [],
    overview: {
      impressions: 0,
      clicks: 0,
      spend: 0,
      ctr: 0,
      recentActivity: []
    }
  });

  useEffect(() => {
    if (providerStatus.spotify) {
      fetchAdAccounts();
    }
  }, [providerStatus.spotify]);

  useEffect(() => {
    if (selectedAccount) {
      if (activeTab === 'overview') {
        fetchOverviewData();
      } else {
        fetchTabData(activeTab);
      }
    }
  }, [selectedAccount, activeTab]);

  const fetchAdAccounts = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/spotify_ads/ad_accounts/');
      setAdAccounts(response.data);
      if (response.data.length > 0) {
        setSelectedAccount(response.data[0]);
      }
    } catch (err: any) {
      setError("Impossible de charger les comptes publicitaires. Vérifiez vos permissions Spotify Ads.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchOverviewData = async () => {
    if (!selectedAccount) return;
    try {
      const statsRes = await axios.get(`/api/spotify_ads/ad_accounts/${selectedAccount.id}/reports/aggregate/`, {
        params: {
          metrics: 'impressions,clicks,spend,ctr',
          granularity: 'LIFETIME'
        }
      });
      
      const activityRes = await axios.get(`/api/spotify_ads/ad_accounts/${selectedAccount.id}/reports/recent_activity/`);

      setData((prev: any) => ({
        ...prev,
        overview: {
          impressions: statsRes.data.metrics?.impressions || 0,
          clicks: statsRes.data.metrics?.clicks || 0,
          spend: statsRes.data.metrics?.spend || 0,
          ctr: statsRes.data.metrics?.ctr || 0,
          recentActivity: Array.isArray(activityRes.data) ? activityRes.data : []
        }
      }));
    } catch (err) {
      console.error("Error fetching overview data:", err);
    }
  };

  const fetchTabData = async (tab: string) => {
    if (!selectedAccount) return;
    setLoading(true);
    try {
      let endpoint = '';
      switch (tab) {
        case 'campaigns': endpoint = `/api/spotify_ads/ad_accounts/${selectedAccount.id}/campaigns/`; break;
        case 'adsets': endpoint = `/api/spotify_ads/ad_accounts/${selectedAccount.id}/ad_sets/`; break;
        case 'ads': endpoint = `/api/spotify_ads/ad_accounts/${selectedAccount.id}/ads/`; break;
        case 'audiences': endpoint = `/api/spotify_ads/ad_accounts/${selectedAccount.id}/audiences/`; break;
        case 'assets': endpoint = `/api/spotify_ads/ad_accounts/${selectedAccount.id}/assets/`; break;
        default: return;
      }
      const response = await axios.get(endpoint);
      setData((prev: any) => ({ ...prev, [tab]: response.data }));
    } catch (err) {
      console.error(`Error fetching ${tab}:`, err);
      toast.error(`Erreur lors du chargement des ${tab}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAccount) return;

    const formData = new FormData(e.target as HTMLFormElement);
    const payload = {
      name: formData.get('name'),
      objective: formData.get('objective'),
      status: formData.get('status'),
    };

    try {
      setLoading(true);
      await axios.post(`/api/spotify_ads/ad_accounts/${selectedAccount.id}/campaigns/`, payload);
      toast.success("Campagne créée avec succès !");
      setIsCreateModalOpen(false);
      fetchTabData('campaigns');
    } catch (err: any) {
      toast.error("Erreur lors de la création de la campagne.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedAccount) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      toast.loading("Téléversement de l'asset...", { id: 'upload' });
      await axios.post(`/api/spotify_ads/ad_accounts/${selectedAccount.id}/assets/upload/`, formData);
      toast.success("Asset téléversé avec succès !", { id: 'upload' });
      fetchTabData('assets');
    } catch (err) {
      toast.error("Erreur lors du téléversement.", { id: 'upload' });
      console.error(err);
    }
  };

  const CreateCampaignModal = () => (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <motion.div 
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="bg-white dark:bg-slate-900 rounded-3xl p-8 max-w-2xl w-full shadow-2xl border border-gray-100 dark:border-slate-800"
      >
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-2xl font-bold">Nouvelle Campagne</h3>
          <button onClick={() => setIsCreateModalOpen(false)} className="p-2 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-full transition-colors">
            <Plus className="w-6 h-6 rotate-45" />
          </button>
        </div>

        <form className="space-y-6" onSubmit={handleCreateCampaign}>
          <div>
            <label className="block text-sm font-bold mb-2">Nom de la campagne</label>
            <input name="name" required type="text" className="w-full bg-gray-50 dark:bg-slate-800 border-none rounded-xl px-4 py-3 outline-none" placeholder="ex: Promo Album Printemps" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-bold mb-2">Objectif</label>
              <select name="objective" className="w-full bg-gray-50 dark:bg-slate-800 border-none rounded-xl px-4 py-3 outline-none">
                <option value="AWARENESS">Notoriété</option>
                <option value="CLICKS">Clics</option>
                <option value="VIDEO_VIEWS">Vues Vidéo</option>
                <option value="WEB_TRAFFIC">Trafic Web</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-bold mb-2">Statut initial</label>
              <select name="status" className="w-full bg-gray-50 dark:bg-slate-800 border-none rounded-xl px-4 py-3 outline-none">
                <option value="ACTIVE">Actif</option>
                <option value="PAUSED">En pause</option>
              </select>
            </div>
          </div>

          <div className="flex gap-4 pt-4">
            <button type="button" onClick={() => setIsCreateModalOpen(false)} className="flex-1 py-3 rounded-xl font-bold border border-gray-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-800 transition-all">
              Annuler
            </button>
            <button type="submit" disabled={loading} className="flex-1 py-3 bg-green-500 hover:bg-green-600 text-white rounded-xl font-bold transition-all shadow-lg shadow-green-500/20 disabled:opacity-50">
              {loading ? <Loader2 className="w-5 h-5 animate-spin mx-auto" /> : "Créer la campagne"}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );

  if (!providerStatus.spotify) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] text-center px-4">
        <div className="w-20 h-20 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mb-6">
          <Megaphone className="w-10 h-10 text-green-600" />
        </div>
        <h2 className="text-2xl font-bold mb-2">Spotify Ads Manager</h2>
        <p className="text-gray-500 max-w-md mb-8">
          Connectez votre compte Spotify avec les permissions publicitaires pour gérer vos campagnes directement depuis MNLV.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Megaphone className="text-green-500" />
            Régie Publicitaire Spotify
          </h1>
          <p className="text-gray-500">Gérez vos campagnes, ciblages et rapports en temps réel.</p>
        </div>
        
        <div className="flex items-center gap-4">
          {selectedAccount && (
            <select 
              className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl px-4 py-2 outline-none"
              value={selectedAccount.id}
              onChange={(e) => setSelectedAccount(adAccounts.find(a => a.id === e.target.value))}
            >
              {adAccounts.map(account => (
                <option key={account.id} value={account.id}>{account.name}</option>
              ))}
            </select>
          )}
          <button 
            onClick={() => setIsCreateModalOpen(true)}
            className="bg-green-500 hover:bg-green-600 text-white px-6 py-2 rounded-xl font-bold flex items-center gap-2 transition-all shadow-lg shadow-green-500/20"
          >
            <Plus className="w-5 h-5" />
            Nouvelle Campagne
          </button>
        </div>
      </div>

      <AnimatePresence>
        {isCreateModalOpen && <CreateCampaignModal />}
      </AnimatePresence>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-10 h-10 animate-spin text-green-500" />
        </div>
      ) : error ? (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-800 p-6 rounded-2xl flex items-center gap-4 text-red-700 dark:text-red-400">
          <AlertCircle className="w-8 h-8 flex-shrink-0" />
          <div>
            <h3 className="font-bold">Erreur d'accès</h3>
            <p>{error}</p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-12 gap-8 flex-1">
          {/* Sidebar Tabs */}
          <div className="col-span-12 lg:col-span-2 flex flex-col gap-2">
            {[
              { id: 'overview', label: 'Aperçu', icon: LayoutDashboard },
              { id: 'campaigns', label: 'Campagnes', icon: Briefcase },
              { id: 'adsets', label: 'Ensembles', icon: Target },
              { id: 'ads', label: 'Annonces', icon: Megaphone },
              { id: 'assets', label: 'Actifs (Média)', icon: ImageIcon },
              { id: 'audiences', label: 'Audiences', icon: Users },
              { id: 'reports', label: 'Rapports', icon: BarChart3 },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition-all ${
                  activeTab === tab.id 
                    ? 'bg-green-500 text-white shadow-lg shadow-green-500/20' 
                    : 'hover:bg-gray-100 dark:hover:bg-slate-800 text-gray-500 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                <tab.icon className="w-5 h-5" />
                {tab.label}
              </button>
            ))}
          </div>

          {/* Main Content Area */}
          <div className="col-span-12 lg:col-span-10 bg-white dark:bg-slate-900 rounded-3xl border border-gray-100 dark:border-slate-800 p-8 shadow-sm overflow-y-auto">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
              >
                {activeTab === 'overview' && (
                  <div className="space-y-8">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                      {[
                        { label: 'Impressions', value: data.overview.impressions.toLocaleString(), delta: '+12%', color: 'blue' },
                        { label: 'Clics', value: data.overview.clicks.toLocaleString(), delta: '+8%', color: 'green' },
                        { label: 'Dépenses', value: `€${data.overview.spend.toFixed(2)}`, delta: '+5%', color: 'purple' },
                        { label: 'CTR', value: `${(data.overview.ctr * 100).toFixed(2)}%`, delta: '+2%', color: 'blue' },
                      ].map(stat => (
                        <div key={stat.label} className="p-6 rounded-2xl border border-gray-100 dark:border-slate-800 bg-gray-50/50 dark:bg-slate-800/50">
                          <p className="text-gray-500 text-sm mb-1">{stat.label}</p>
                          <div className="flex items-end justify-between">
                            <div>
                              <h3 className="text-2xl font-bold">{stat.value}</h3>
                              <span className="text-green-500 text-sm font-bold">{stat.delta}</span>
                            </div>
                            <Sparkline color={stat.color} />
                          </div>
                        </div>
                      ))}
                    </div>
                    
                    <div className="rounded-2xl border border-gray-100 dark:border-slate-800 p-6">
                      <h3 className="font-bold mb-6">Activité Récente</h3>
                      <div className="space-y-4">
                        {data.overview.recentActivity.length > 0 ? data.overview.recentActivity.map((activity: any) => (
                          <div key={activity.id} className="flex items-center justify-between p-4 rounded-xl hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors">
                            <div className="flex items-center gap-4">
                              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                                activity.type === 'CAMPAIGN' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600' :
                                activity.type === 'AD_SET' ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-600' :
                                'bg-green-100 dark:bg-green-900/30 text-green-600'
                              }`}>
                                {activity.type === 'CAMPAIGN' ? <Briefcase className="w-5 h-5" /> :
                                 activity.type === 'AD_SET' ? <Target className="w-5 h-5" /> :
                                 <Megaphone className="w-5 h-5" />}
                              </div>
                              <div>
                                <p className="font-bold">{activity.name}</p>
                                <p className="text-xs text-gray-500">{activity.type} • {activity.time}</p>
                              </div>
                            </div>
                            <div className="flex items-center gap-4">
                              <span className={`px-2 py-1 text-[10px] font-bold rounded-lg ${
                                activity.status === 'ACTIVE' || activity.status === 'APPROVED' ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-500'
                              }`}>
                                {activity.status}
                              </span>
                              <ChevronRight className="w-5 h-5 text-gray-300" />
                            </div>
                          </div>
                        )) : (
                          <div className="py-10 text-center text-gray-400 italic">
                            Aucune activité récente enregistrée.
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === 'campaigns' && (
                  <div className="space-y-6">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xl font-bold">Toutes les Campagnes</h3>
                      <div className="flex gap-2">
                        <input 
                          type="text" 
                          placeholder="Rechercher..." 
                          className="bg-gray-50 dark:bg-slate-800 border-none rounded-xl px-4 py-2 outline-none text-sm w-64"
                        />
                      </div>
                    </div>
                    
                    <div className="overflow-x-auto">
                      <table className="w-full text-left">
                        <thead>
                          <tr className="text-gray-400 text-sm border-b border-gray-100 dark:border-slate-800">
                            <th className="pb-4 font-medium">Nom</th>
                            <th className="pb-4 font-medium">Statut</th>
                            <th className="pb-4 font-medium">Objectif</th>
                            <th className="pb-4 font-medium">Budget</th>
                            <th className="pb-4"></th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 dark:divide-slate-800">
                          {data.campaigns.length > 0 ? data.campaigns.map((campaign: any) => (
                            <tr key={campaign.id} className="hover:bg-gray-50/50 dark:hover:bg-slate-800/50 transition-colors">
                              <td className="py-4 font-bold">{campaign.name}</td>
                              <td className="py-4">
                                <span className={`px-2 py-1 text-xs font-bold rounded-lg ${
                                  campaign.status === 'ACTIVE' ? 'bg-green-100 dark:bg-green-900/30 text-green-600' : 'bg-gray-100 dark:bg-gray-800 text-gray-500'
                                }`}>
                                  {campaign.status}
                                </span>
                              </td>
                              <td className="py-4 text-sm">{campaign.objective}</td>
                              <td className="py-4 text-sm">{campaign.budget?.micro_amount / 1000000} {campaign.currency}</td>
                              <td className="py-4 text-right">
                                <button className="p-2 hover:bg-gray-200 dark:hover:bg-slate-700 rounded-lg transition-colors">
                                  <Settings className="w-4 h-4 text-gray-400" />
                                </button>
                              </td>
                            </tr>
                          )) : (
                            <tr>
                              <td colSpan={5} className="py-12 text-center text-gray-500">Aucune campagne trouvée.</td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {activeTab === 'adsets' && (
                  <div className="space-y-6">
                    <h3 className="text-xl font-bold">Ensembles d'Annonces</h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left">
                        <thead>
                          <tr className="text-gray-400 text-sm border-b border-gray-100 dark:border-slate-800">
                            <th className="pb-4 font-medium">Nom</th>
                            <th className="pb-4 font-medium">Statut</th>
                            <th className="pb-4 font-medium">Format</th>
                            <th className="pb-4"></th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 dark:divide-slate-800">
                          {data.adsets.length > 0 ? data.adsets.map((adset: any) => (
                            <tr key={adset.id} className="hover:bg-gray-50/50 dark:hover:bg-slate-800/50 transition-colors">
                              <td className="py-4 font-bold">{adset.name}</td>
                              <td className="py-4">
                                <span className={`px-2 py-1 text-xs font-bold rounded-lg ${
                                  adset.status === 'ACTIVE' ? 'bg-green-100 dark:bg-green-900/30 text-green-600' : 'bg-gray-100 dark:bg-gray-800 text-gray-500'
                                }`}>
                                  {adset.status}
                                </span>
                              </td>
                              <td className="py-4 text-sm">{adset.asset_format}</td>
                              <td className="py-4 text-right">
                                <button className="p-2 hover:bg-gray-200 dark:hover:bg-slate-700 rounded-lg transition-colors">
                                  <Settings className="w-4 h-4 text-gray-400" />
                                </button>
                              </td>
                            </tr>
                          )) : (
                            <tr>
                              <td colSpan={4} className="py-12 text-center text-gray-500">Aucun ensemble d'annonces trouvé.</td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {activeTab === 'ads' && (
                  <div className="space-y-6">
                    <h3 className="text-xl font-bold">Annonces</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {data.ads.length > 0 ? data.ads.map((ad: any) => (
                        <div key={ad.id} className="p-6 rounded-2xl border border-gray-100 dark:border-slate-800 hover:border-green-500 transition-all">
                          <div className="flex justify-between items-start mb-4">
                            <div>
                              <h4 className="font-bold">{ad.name}</h4>
                              <p className="text-xs text-gray-500">ID: {ad.id}</p>
                            </div>
                            <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-600 text-[10px] font-bold rounded-lg">
                              {ad.status}
                            </span>
                          </div>
                          {ad.ad_preview_url && (
                            <a href={ad.ad_preview_url} target="_blank" rel="noopener noreferrer" className="text-green-500 text-sm font-bold hover:underline">
                              Prévisualiser l'annonce
                            </a>
                          )}
                        </div>
                      )) : (
                        <div className="col-span-2 py-12 text-center text-gray-500">Aucune annonce trouvée.</div>
                      )}
                    </div>
                  </div>
                )}

                {activeTab === 'audiences' && (
                   <div className="space-y-6">
                     <h3 className="text-xl font-bold">Audiences</h3>
                     <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                       {data.audiences.length > 0 ? data.audiences.map((audience: any) => (
                         <div key={audience.id} className="p-6 rounded-2xl border border-gray-100 dark:border-slate-800 bg-gray-50/30 dark:bg-slate-800/30">
                           <Users className="w-8 h-8 text-blue-500 mb-4" />
                           <h4 className="font-bold mb-1">{audience.name}</h4>
                           <p className="text-sm text-gray-500">{audience.type}</p>
                         </div>
                       )) : (
                         <div className="col-span-3 py-12 text-center text-gray-500">Aucune audience trouvée.</div>
                       )}
                     </div>
                   </div>
                 )}

                 {activeTab === 'assets' && (
                   <div className="space-y-6">
                     <div className="flex items-center justify-between">
                       <h3 className="text-xl font-bold">Médiathèque (Assets)</h3>
                       <label className="cursor-pointer bg-green-500 hover:bg-green-600 text-white px-6 py-2 rounded-xl font-bold flex items-center gap-2 transition-all shadow-lg shadow-green-500/20">
                         <Upload className="w-5 h-5" />
                         Téléverser
                         <input type="file" className="hidden" onChange={handleFileUpload} accept="audio/*,image/*,video/*" />
                       </label>
                     </div>
                     <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-6">
                       {data.assets.length > 0 ? data.assets.map((asset: any) => (
                         <div key={asset.id} className="group relative aspect-square rounded-2xl border border-gray-100 dark:border-slate-800 bg-gray-50 dark:bg-slate-800/50 overflow-hidden flex flex-col items-center justify-center p-4">
                           {asset.type === 'IMAGE' ? <ImageIcon className="w-10 h-10 text-blue-500" /> :
                            asset.type === 'AUDIO' ? <Music className="w-10 h-10 text-purple-500" /> :
                            <Video className="w-10 h-10 text-red-500" />}
                           <p className="mt-2 text-[10px] font-bold text-center truncate w-full">{asset.name}</p>
                           <p className="text-[8px] text-gray-500">{asset.type}</p>
                           
                           <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                             <button className="p-2 bg-white rounded-full text-black hover:scale-110 transition-transform">
                               <Settings className="w-4 h-4" />
                             </button>
                           </div>
                         </div>
                       )) : (
                         <div className="col-span-full py-20 text-center flex flex-col items-center">
                           <Upload className="w-12 h-12 text-gray-200 mb-4" />
                           <p className="text-gray-500">Aucun média disponible.</p>
                         </div>
                       )}
                     </div>
                   </div>
                 )}

                 {activeTab === 'reports' && (
                   <div className="space-y-6">
                     <h3 className="text-xl font-bold">Générer un Rapport</h3>
                     <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                       <div className="p-6 rounded-2xl border border-gray-100 dark:border-slate-800 bg-gray-50/50 dark:bg-slate-800/50">
                         <h4 className="font-bold mb-4 flex items-center gap-2">
                           <FileText className="w-5 h-5 text-blue-500" />
                           Rapport CSV Asynchrone
                         </h4>
                         <p className="text-sm text-gray-500 mb-6">Générez un rapport complet au format CSV pour toutes vos campagnes.</p>
                         <button 
                          onClick={async () => {
                            try {
                              toast.loading("Génération du rapport...", { id: 'report' });
                              const res = await axios.post(`/api/spotify_ads/ad_accounts/${selectedAccount.id}/async_reports/`, {
                                metrics: 'impressions,clicks,spend',
                                date_range: 'LAST_30_DAYS'
                              });
                              toast.success(`Rapport #${res.data.id} en cours...`, { id: 'report' });
                            } catch (err) {
                              toast.error("Erreur lors de la génération.");
                            }
                          }}
                          className="w-full py-3 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl font-bold hover:border-blue-500 hover:text-blue-500 transition-all"
                         >
                           Générer CSV
                         </button>
                       </div>
                       <div className="p-6 rounded-2xl border border-gray-100 dark:border-slate-800 bg-gray-50/50 dark:bg-slate-800/50">
                         <h4 className="font-bold mb-4 flex items-center gap-2">
                           <BarChart3 className="w-5 h-5 text-green-500" />
                           Analytics Avancés
                         </h4>
                         <p className="text-sm text-gray-500 mb-6">Visualisez les performances par plateforme, âge et genre.</p>
                         <button className="w-full py-3 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl font-bold hover:border-green-500 hover:text-green-500 transition-all">
                           Voir Graphiques
                         </button>
                       </div>
                     </div>
                   </div>
                 )}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdsDashboard;
