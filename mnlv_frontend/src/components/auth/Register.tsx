import React, { useState } from 'react';
import axios from 'axios';
import { UserPlus, User, Mail, Lock, AlertCircle, Loader2, ArrowLeft } from 'lucide-react';
import { motion } from 'framer-motion';

interface RegisterProps {
  onSwitchToLogin: () => void;
  onSuccess: () => void;
}

const Register: React.FC<RegisterProps> = ({ onSwitchToLogin, onSuccess }) => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.password !== formData.confirmPassword) {
      setError('Les mots de passe ne correspondent pas');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await axios.post('/api/auth/register/', {
        username: formData.username,
        email: formData.email,
        password: formData.password
      });
      onSuccess();
    } catch (err: any) {
      const detail = err.response?.data;
      setError(detail ? (typeof detail === 'object' ? Object.values(detail).flat().join(' ') : detail) : 'Erreur lors de la création du compte');
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="bg-white p-10 rounded-3xl shadow-2xl w-full max-w-md border border-gray-100 relative overflow-hidden"
    >
      {/* Background Accent */}
      <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-purple-500 via-pink-500 to-red-500"></div>

      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-purple-50 rounded-2xl flex items-center justify-center mx-auto mb-4 text-purple-600 shadow-inner">
          <UserPlus size={32} />
        </div>
        <h2 className="text-3xl font-black text-gray-900 tracking-tight">Inscription</h2>
        <p className="text-gray-500 font-medium mt-1">Créez votre compte MNLV gratuitement</p>
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

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Utilisateur</label>
          <div className="relative group">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-gray-400 group-focus-within:text-purple-500 transition-colors">
              <User size={16} />
            </div>
            <input
              type="text"
              required
              value={formData.username}
              onChange={(e) => setFormData({...formData, username: e.target.value})}
              className="w-full pl-10 pr-4 py-3 bg-gray-50 border-2 border-transparent rounded-xl focus:bg-white focus:border-purple-500 focus:ring-4 focus:ring-purple-500/10 outline-none transition-all font-bold text-gray-700 text-sm"
              placeholder="votre_nom"
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Email</label>
          <div className="relative group">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-gray-400 group-focus-within:text-purple-500 transition-colors">
              <Mail size={16} />
            </div>
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              className="w-full pl-10 pr-4 py-3 bg-gray-50 border-2 border-transparent rounded-xl focus:bg-white focus:border-purple-500 focus:ring-4 focus:ring-purple-500/10 outline-none transition-all font-bold text-gray-700 text-sm"
              placeholder="nom@exemple.com"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Mot de passe</label>
            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-gray-400 group-focus-within:text-purple-500 transition-colors">
                <Lock size={16} />
              </div>
              <input
                type="password"
                required
                value={formData.password}
                onChange={(e) => setFormData({...formData, password: e.target.value})}
                className="w-full pl-10 pr-4 py-3 bg-gray-50 border-2 border-transparent rounded-xl focus:bg-white focus:border-purple-500 focus:ring-4 focus:ring-purple-500/10 outline-none transition-all font-bold text-gray-700 text-sm"
                placeholder="••••"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Confirmer</label>
            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-gray-400 group-focus-within:text-purple-500 transition-colors">
                <Lock size={16} />
              </div>
              <input
                type="password"
                required
                value={formData.confirmPassword}
                onChange={(e) => setFormData({...formData, confirmPassword: e.target.value})}
                className="w-full pl-10 pr-4 py-3 bg-gray-50 border-2 border-transparent rounded-xl focus:bg-white focus:border-purple-500 focus:ring-4 focus:ring-purple-500/10 outline-none transition-all font-bold text-gray-700 text-sm"
                placeholder="••••"
              />
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-4 bg-gray-900 hover:bg-black text-white rounded-2xl font-black text-lg transition-all shadow-xl shadow-gray-200 active:scale-[0.98] disabled:bg-gray-400 disabled:shadow-none flex items-center justify-center gap-2 mt-4"
        >
          {loading ? (
            <Loader2 className="animate-spin" size={24} />
          ) : (
            <span>Créer mon compte</span>
          )}
        </button>
      </form>

      <div className="mt-8 pt-6 border-t border-gray-100 text-center">
        <button
          onClick={onSwitchToLogin}
          className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-900 font-bold text-sm transition-colors"
        >
          <ArrowLeft size={16} />
          Retour à la connexion
        </button>
      </div>
    </motion.div>
  );
};

export default Register;
