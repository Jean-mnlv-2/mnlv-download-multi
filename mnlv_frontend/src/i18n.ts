import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

const resources = {
  en: {
    translation: {
      "dashboard": "Dashboard",
      "downloader": "Downloader",
      "playlists": "Playlists",
      "media_tools": "Media Tools",
      "settings": "Settings",
      "logout": "Logout",
      "welcome": "Welcome back",
      "ready_for_music": "Ready for your music?",
      "paste_link": "Paste a link from Spotify, Deezer, Apple Music, Tidal, SoundCloud, Amazon or YouTube Music.",
      "active_tasks": "Active Tasks",
      "recent_history": "Recent History",
      "clear_list": "Clear List",
      "download": "Download",
      "add_to_playlist": "Add to Playlist",
      "processing": "Processing",
      "completed": "Completed",
      "failed": "Failed",
      "search_placeholder": "Enter track or playlist URL...",
      "dark_mode": "Dark Mode",
      "language": "Language"
    }
  },
  fr: {
    translation: {
      "dashboard": "Tableau de bord",
      "downloader": "Téléchargeur",
      "playlists": "Playlists",
      "media_tools": "Outils Média",
      "settings": "Paramètres",
      "logout": "Déconnexion",
      "welcome": "Heureux de vous revoir",
      "ready_for_music": "Prêt pour votre musique ?",
      "paste_link": "Collez un lien Spotify, Deezer, Apple Music, Tidal, SoundCloud, Amazon ou YouTube Music.",
      "active_tasks": "Tâches en cours",
      "recent_history": "Historique récent",
      "clear_list": "Vider la liste",
      "download": "Télécharger",
      "add_to_playlist": "Ajouter à la playlist",
      "processing": "Traitement",
      "completed": "Terminé",
      "failed": "Échoué",
      "search_placeholder": "Entrez l'URL du morceau ou de la playlist...",
      "dark_mode": "Mode Sombre",
      "language": "Langue"
    }
  }
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'fr',
    interpolation: {
      escapeValue: false
    }
  });

export default i18n;
