import React, { useState } from 'react';
import { useAuthStore } from '../../store/useAuthStore';
import axios from 'axios';
import { LogIn, User, Lock, AlertCircle, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';

interface LoginProps {
  onSwitchToRegister: () => void;
}

const Login: React.FC<LoginProps> = ({ onSwitchToRegister }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuthStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await axios.post('/api/auth/login/', { username, password });
      const { access, refresh } = response.data;
      await login(access, refresh);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Identifiants invalides');
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white p-10 rounded-3xl shadow-2xl w-full max-w-md border border-gray-100 relative overflow-hidden"
    >
      {/* Background Accent */}
      <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500"></div>

      <div className="text-center mb-10">
        <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-4 text-blue-600 shadow-inner">
          <LogIn size={32} />
        </div>
        <h2 className="text-3xl font-black text-gray-900 tracking-tight">Connexion</h2>
        <p className="text-gray-500 font-medium mt-1">Accédez à votre bibliothèque musicale</p>
      </div>

      {error && (
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-red-50 border border-red-100 text-red-700 px-4 py-3 mb-6 rounded-2xl flex items-center gap-3"
        >
          <AlertCircle size={20} className="flex-shrink-0" />
          <p className="text-sm font-bold">{error}</p>
        </motion.div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-2">
          <label className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">Utilisateur</label>
          <div className="relative group">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-gray-400 group-focus-within:text-blue-500 transition-colors">
              <User size={18} />
            </div>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full pl-11 pr-4 py-4 bg-gray-50 border-2 border-transparent rounded-2xl focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 outline-none transition-all font-bold text-gray-700"
              placeholder="votre_nom"
            />
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">Mot de passe</label>
          <div className="relative group">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-gray-400 group-focus-within:text-blue-500 transition-colors">
              <Lock size={18} />
            </div>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full pl-11 pr-4 py-4 bg-gray-50 border-2 border-transparent rounded-2xl focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 outline-none transition-all font-bold text-gray-700"
              placeholder="••••••••"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-4 bg-gray-900 hover:bg-black text-white rounded-2xl font-black text-lg transition-all shadow-xl shadow-gray-200 active:scale-[0.98] disabled:bg-gray-400 disabled:shadow-none flex items-center justify-center gap-2 overflow-hidden relative"
        >
          {loading ? (
            <Loader2 className="animate-spin" size={24} />
          ) : (
            <>
              <span>Se connecter</span>
            </>
          )}
        </button>
      </form>

      <div className="mt-10 pt-8 border-t border-gray-100 text-center">
        <p className="text-gray-500 font-bold text-sm">
          Nouveau sur MNLV ?{' '}
          <button
            onClick={onSwitchToRegister}
            className="text-blue-600 hover:text-blue-700 transition-colors ml-1"
          >
            Créer un compte
          </button>
        </p>
      </div>
    </motion.div>
  );
};

export default Login;
