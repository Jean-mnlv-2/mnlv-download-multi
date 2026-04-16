from ..base import MusicProvider, TrackMetadata
import re
import yt_dlp
import requests
from typing import List, Optional
from django.conf import settings

class SoundCloudProvider(MusicProvider):
    """
    Adapteur pour SoundCloud utilisant l'API officielle (via Resolve/OAuth) 
    avec un fallback yt-dlp pour la robustesse.
    """
    
    def __init__(self, auth_token: Optional[str] = None):
        self.auth_token = auth_token
        self.api_base = getattr(settings, 'SOUNDCLOUD_API_BASE', 'https://api.soundcloud.com')
        self.client_id = getattr(settings, 'SOUNDCLOUD_CLIENT_ID', None)
        self._session = requests.Session()
        if self.auth_token:
            self._session.headers.update({"Authorization": f"OAuth {self.auth_token}"})

    def supports_url(self, url: str) -> bool:
        return bool(re.search(r"soundcloud\.com/.*?/.*?", url))

    def _resolve(self, url: str) -> dict:
        """Utilise l'endpoint /resolve pour obtenir l'ID et les infos de la ressource"""
        if not self.auth_token and not self.client_id:
            return self._resolve_fallback(url)
            
        params = {"url": url}
        if not self.auth_token:
            params["client_id"] = self.client_id
            
        response = self._session.get(f"{self.api_base}/resolve", params=params)
        if response.status_code == 200:
            return response.json()
        return self._resolve_fallback(url)

    def _resolve_fallback(self, url: str) -> dict:
        """Fallback via yt-dlp si l'API échoue ou pas de token"""
        ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    def get_track_info(self, url: str) -> TrackMetadata:
        info = self._resolve(url)
        return self._map_track(info)

    def get_playlist_tracks(self, url: str) -> List[TrackMetadata]:
        info = self._resolve(url)
        tracks = []
        
        if info.get('kind') == 'playlist' or 'entries' in info:
            items = info.get('tracks') or info.get('entries', [])
            
            next_href = info.get('next_href')
            while next_href:
                response = self._session.get(next_href)
                if response.status_code == 200:
                    data = response.json()
                    items.extend(data.get('collection', []))
                    next_href = data.get('next_href')
                else:
                    break
                    
            for item in items:
                # Filtrage access=playable
                if item.get('access') == 'blocked' or item.get('policy') == 'BLOCK':
                    continue
                tracks.append(self._map_track(item))
        else:
            tracks.append(self._map_track(info))
            
        return tracks

    def get_user_likes(self) -> List[TrackMetadata]:
        """Récupère les titres likés de l'utilisateur authentifié"""
        if not self.auth_token:
            raise ValueError("Authentification SoundCloud requise pour accéder aux Likes.")
            
        response = self._session.get(f"{self.api_base}/me/likes/tracks", params={"limit": 50, "linked_partitioning": 1})
        if response.status_code != 200:
            return []
            
        data = response.json()
        return [self._map_track(item) for item in data.get('collection', [])]

    def get_user_stream(self) -> List[TrackMetadata]:
        """Récupère le flux (Stream) de l'utilisateur"""
        if not self.auth_token:
            raise ValueError("Authentification SoundCloud requise pour accéder au Stream.")
            
        response = self._session.get(f"{self.api_base}/me/stream", params={"limit": 30, "linked_partitioning": 1})
        if response.status_code != 200:
            return []
            
        data = response.json()
        tracks = []
        for item in data.get('collection', []):
            origin = item.get('origin')
            if origin and origin.get('kind') == 'track':
                tracks.append(self._map_track(origin))
        return tracks

    def like_track(self, track_id: str):
        """Like un titre sur SoundCloud"""
        if self.auth_token:
            self._session.put(f"{self.api_base}/me/likes/tracks/{track_id}")

    def _map_track(self, info: dict) -> TrackMetadata:
        """Mappe les données SoundCloud (API ou yt-dlp) vers TrackMetadata"""
        title = info.get('title') or info.get('track', 'Titre inconnu')
        
        user = info.get('user', {})
        artist = user.get('username') or info.get('uploader') or info.get('artist', 'Artiste inconnu')
        
        cover_url = info.get('artwork_url') or info.get('thumbnail')
        if cover_url and '-large.' in cover_url:
            cover_url = cover_url.replace('-large.', '-t500x500.')
            
        created_at = info.get('created_at', '0000')
        release_year = int(created_at[:4]) if created_at and created_at[0].isdigit() else None
        if not release_year:
            upload_date = info.get('upload_date', '0000')
            release_year = int(upload_date[:4]) if upload_date else None

        return TrackMetadata(
            title=title,
            artist=artist,
            album=info.get('album'),
            release_year=release_year,
            cover_url=cover_url,
            duration_ms=int(info.get('duration', 0)) if 'duration' in info and info['duration'] > 5000 else int(info.get('duration', 0)) * 1000,
            explicit=info.get('explicit', False) or 'explicit' in title.lower(),
            provider="soundcloud",
            original_url=info.get('permalink_url') or info.get('webpage_url') or info.get('url')
        )
