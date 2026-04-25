from ..base import MusicProvider, TrackMetadata
import re
import requests
import logging
from typing import List, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

class BoomplayProvider(MusicProvider):
    """
    Adapteur pour Boomplay utilisant l'Open API de Boomplay.
    Nécessite BOOMPLAY_APP_ID et BOOMPLAY_ACCESS_TOKEN dans les réglages.
    """
    API_BASE = getattr(settings, 'BOOMPLAY_API_BASE', 'https://openapi.boomplay.com')

    def __init__(self, auth_token: Optional[str] = None):
        """
        Initialise le provider Boomplay.
        Si un auth_token est fourni, il sera utilisé (User Access Token).
        Sinon, utilise le token global configuré.
        """
        self.auth_token = auth_token or getattr(settings, 'BOOMPLAY_ACCESS_TOKEN', None)
        self.app_id = getattr(settings, 'BOOMPLAY_APP_ID', None)
        self._session = requests.Session()

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Helper pour les requêtes GET avec authentification Boomplay"""
        if params is None:
            params = {}
        
        headers = {
            "Content-Type": "application/json",
            "Accept-Language": "en-US",
            "app_id": self.app_id,
            "Authorization": f"Bearer {self.auth_token}" if self.auth_token else ""
        }

        url = f"{self.API_BASE}/{endpoint.lstrip('/')}"
        response = self._session.get(url, headers=headers, params=params, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"Boomplay API error {response.status_code}: {response.text}")
            raise ValueError(f"Boomplay API error {response.status_code}")
            
        data = response.json()
        if data.get('code') != 0:
            error_msg = data.get('desc', 'Unknown error')
            logger.error(f"Boomplay API Error [{data.get('code')}]: {error_msg}")
            raise ValueError(f"Boomplay API Error: {error_msg}")
            
        return data.get('data', {})

    def supports_url(self, url: str) -> bool:
        """Vérifie si l'URL appartient à Boomplay"""
        return bool(re.search(r"boomplay(music)?\.com", url))

    def get_track_info(self, url: str) -> TrackMetadata:
        """Extrait les métadonnées d'un titre Boomplay"""
        track_id = self._extract_id(url, r"songs?")
        data = self._get(f"track/v1/id/{track_id}")
        
        if isinstance(data, list) and len(data) > 0:
            track_data = data[0]
        else:
            track_data = data

        return self._map_track(track_data, url)

    def get_playlist_tracks(self, url: str) -> List[TrackMetadata]:
        """Extrait les titres d'une playlist ou d'un album Boomplay"""
        tracks = []
        if "/playlist" in url:
            playlist_id = self._extract_id(url, r"playlists?")
            data = self._get(f"playlist/v1/tracks/{playlist_id}")
            track_list = data.get('tracks', []) if isinstance(data, dict) else data
            for item in track_list:
                tracks.append(self._map_track(item))
        elif "/album" in url:
            album_id = self._extract_id(url, r"albums?")
            data = self._get(f"album/v1/tracks/{album_id}")
            track_list = data.get('tracks', []) if isinstance(data, dict) else data
            for item in track_list:
                tracks.append(self._map_track(item))
        
        return tracks

    def create_playlist(self, name: str, description: str = "", public: bool = False) -> str:
        """
        Crée une nouvelle playlist sur Boomplay.
        Nécessite des permissions d'écriture et un User Access Token.
        """
        if not self.auth_token:
            raise ValueError("Token utilisateur requis pour créer une playlist sur Boomplay.")
            
        payload = {
            "playlist_name": name,
            "description": description,
            "is_public": public
        }
        # Note: L'endpoint exact peut varier selon la version de l'API Open
        data = self._post("playlist/v1/create", json=payload)
        return data.get('playlist_id')

    def add_tracks_to_playlist(self, playlist_id: str, track_urls: List[str]):
        """
        Ajoute des titres à une playlist Boomplay.
        """
        if not self.auth_token:
            raise ValueError("Token utilisateur requis pour modifier une playlist.")
            
        track_ids = [self._extract_id(u, r"songs?") for u in track_urls]
        payload = {
            "playlist_id": playlist_id,
            "track_ids": track_ids
        }
        self._post("playlist/v1/add_tracks", json=payload)

    def _post(self, endpoint: str, json: dict = None) -> dict:
        """Helper pour les requêtes POST avec authentification Boomplay"""
        headers = {
            "Content-Type": "application/json",
            "app_id": self.app_id,
            "Authorization": f"Bearer {self.auth_token}" if self.auth_token else ""
        }

        url = f"{self.API_BASE}/{endpoint.lstrip('/')}"
        response = self._session.post(url, headers=headers, json=json, timeout=15)
        
        if response.status_code not in [200, 201]:
            logger.error(f"Boomplay API error {response.status_code}: {response.text}")
            raise ValueError(f"Boomplay API error {response.status_code}")
            
        data = response.json()
        if data.get('code') != 0:
            error_msg = data.get('desc', 'Unknown error')
            logger.error(f"Boomplay API Error [{data.get('code')}]: {error_msg}")
            raise ValueError(f"Boomplay API Error: {error_msg}")
            
        return data.get('data', {})

    def _extract_id(self, url: str, type_name: str) -> str:
        """Extrait l'ID numérique de l'URL Boomplay"""
        match = re.search(rf"{type_name}/(\d+)", url)
        if match:
            return match.group(1)
        raise ValueError(f"ID Boomplay non trouvé pour le type {type_name} dans l'URL : {url}")

    def _map_track(self, data: dict, original_url: Optional[str] = None) -> TrackMetadata:
        """Mappe les données JSON de Boomplay vers TrackMetadata"""
        artists = data.get('artists', [])
        artist_name = ", ".join([a.get('artist_name', '') for a in artists]) if artists else "Unknown Artist"
        
        artwork = data.get('artwork', {})
        cover_url = artwork.get('url') if isinstance(artwork, dict) else None

        # Boomplay duration is often "MM:SS"
        duration_str = data.get('duration', '00:00')
        duration_ms = 0
        try:
            parts = duration_str.split(':')
            if len(parts) == 2:
                duration_ms = (int(parts[0]) * 60 + int(parts[1])) * 1000
            elif len(parts) == 3:
                duration_ms = (int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])) * 1000
        except (ValueError, IndexError):
            pass

        return TrackMetadata(
            title=data.get('track_title', 'Unknown Title'),
            artist=artist_name,
            album=data.get('album_title'),
            release_year=None,
            cover_url=cover_url,
            duration_ms=duration_ms,
            isrc=data.get('isrc'),
            provider="boomplay",
            original_url=original_url or data.get('web_url')
        )
