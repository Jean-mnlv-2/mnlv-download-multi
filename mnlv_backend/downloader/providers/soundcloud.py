from .base import MusicProvider, TrackMetadata
import re
import yt_dlp
from typing import List, Optional

class SoundCloudProvider(MusicProvider):
    """
    Adapteur pour SoundCloud utilisant yt-dlp pour l'extraction des métadonnées.
    Suit le blueprint fonctionnel de SpotifyProvider.
    """
    
    def __init__(self, auth_token: Optional[str] = None):
        """
        Initialise le provider SoundCloud.
        auth_token (OAuth) peut être utilisé si nécessaire, bien que SoundCloud
        soit principalement géré via extraction publique.
        """
        self.auth_token = auth_token

    def supports_url(self, url: str) -> bool:
        """Vérifie si l'URL appartient à SoundCloud"""
        return bool(re.search(r"soundcloud\.com/.*?/.*?", url))

    def get_track_info(self, url: str) -> TrackMetadata:
        """Extrait les métadonnées d'un titre SoundCloud via yt-dlp"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
        return self._map_track(info)

    def get_playlist_tracks(self, url: str) -> List[TrackMetadata]:
        """Extrait la liste des titres d'une playlist ou d'un set SoundCloud"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        
        tracks = []
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if 'entries' in info:
                for entry in info['entries']:
                    tracks.append(self._map_track(entry))
            else:
                tracks.append(self._map_track(info))
                
        return tracks

    def _map_track(self, info: dict) -> TrackMetadata:
        """Mappe le dictionnaire yt-dlp vers l'objet TrackMetadata standard"""
        return TrackMetadata(
            title=info.get('title') or info.get('track', 'Titre inconnu'),
            artist=info.get('uploader') or info.get('artist', 'Artiste inconnu'),
            album=info.get('album'),
            release_year=int(info.get('upload_date', '0000')[:4]) if info.get('upload_date') else None,
            cover_url=info.get('thumbnail'),
            duration_ms=int(info.get('duration', 0)) * 1000,
            provider="soundcloud",
            original_url=info.get('webpage_url') or info.get('url')
        )
