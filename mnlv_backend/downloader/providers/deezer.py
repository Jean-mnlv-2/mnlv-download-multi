from .base import MusicProvider, TrackMetadata
import re
import requests
from typing import List, Optional

class DeezerProvider(MusicProvider):
    """
    Adapteur pour Deezer utilisant son API publique REST.
    Suit le blueprint fonctionnel de SpotifyProvider.
    """
    API_BASE = "https://api.deezer.com"

    def __init__(self, auth_token: Optional[str] = None):
        """
        Initialise le provider Deezer.
        Si un auth_token est fourni, il sera utilisé pour les opérations d'écriture.
        """
        self.auth_token = auth_token

    def create_playlist(self, name: str, description: str = "", public: bool = False) -> str:
        """Crée une nouvelle playlist (Nécessite auth_token / access_token)"""
        if not self.auth_token:
            raise ValueError("Token Deezer requis pour créer une playlist.")
        
        url = f"{self.API_BASE}/user/me/playlists"
        params = {"access_token": self.auth_token, "title": name}
        response = requests.post(url, params=params)
        data = response.json()
        if "error" in data:
            raise ValueError(f"Erreur Deezer: {data['error']['message']}")
        return str(data['id'])

    def delete_playlist(self, playlist_id: str):
        """Supprime une playlist (Nécessite auth_token / access_token)"""
        if not self.auth_token:
            raise ValueError("Token Deezer requis pour supprimer une playlist.")
            
        url = f"{self.API_BASE}/playlist/{playlist_id}"
        params = {"access_token": self.auth_token}
        response = requests.delete(url, params=params)
        data = response.json()
        if data is not True and "error" in data:
             raise ValueError(f"Erreur Deezer: {data['error']['message']}")

    def add_tracks_to_playlist(self, playlist_id: str, track_urls: List[str]):
        """Ajoute des titres via leurs IDs Deezer"""
        if not self.auth_token:
            raise ValueError("Token Deezer requis pour modifier une playlist.")
            
        track_ids = [self._extract_id(u, "track") for u in track_urls]
        url = f"{self.API_BASE}/playlist/{playlist_id}/tracks"
        params = {"access_token": self.auth_token, "songs": ",".join(track_ids)}
        response = requests.post(url, params=params)
        data = response.json()
        if data is not True and "error" in data:
             raise ValueError(f"Erreur Deezer: {data['error']['message']}")

    def get_user_playlists(self) -> List[dict]:
        """Récupère les playlists de l'utilisateur Deezer"""
        if not self.auth_token:
            raise ValueError("Token Deezer requis.")
            
        url = f"{self.API_BASE}/user/me/playlists"
        params = {"access_token": self.auth_token}
        response = requests.get(url, params=params)
        data = response.json()
        
        playlists = []
        for item in data.get('data', []):
            playlists.append({
                'id': str(item['id']),
                'name': item['title'],
                'track_count': item['nb_tracks'],
                'owner': item['creator']['name'],
                'url': item['link'],
                'cover_url': item['picture_xl'] or item['picture_medium'],
            })
        return playlists

    def get_playlist_details(self, url: str) -> dict:
        """Détails complets d'une playlist Deezer"""
        playlist_id = self._extract_id(url, "playlist")
        response = requests.get(f"{self.API_BASE}/playlist/{playlist_id}")
        data = response.json()
        
        return {
            'id': str(data['id']),
            'name': data['title'],
            'description': data.get('description', ''),
            'track_count': data['nb_tracks'],
            'total_duration_ms': data['duration'] * 1000,
            'followers': data['fans'],
            'cover_url': data['picture_xl'] or data['picture_medium'],
            'owner': data['creator']['name'],
            'provider': 'deezer'
        }

    def supports_url(self, url: str) -> bool:
        """Vérifie si l'URL est de type deezer.com"""
        return bool(re.search(r"deezer\.com/.*?/(track|album|playlist)/", url))

    def get_track_info(self, url: str) -> TrackMetadata:
        """Extrait les métadonnées d'un titre Deezer unique"""
        track_id = self._extract_id(url, "track")
        response = requests.get(f"{self.API_BASE}/track/{track_id}")
        if response.status_code != 200:
            raise ValueError(f"Impossible de récupérer le titre Deezer : {track_id}")
        
        data = response.json()
        if "error" in data:
            raise ValueError(f"Erreur API Deezer : {data['error'].get('message')}")
            
        return self._map_track(data)

    def get_playlist_tracks(self, url: str) -> List[TrackMetadata]:
        """Extrait la liste des titres d'une playlist ou d'un album Deezer"""
        tracks = []
        if "/playlist/" in url:
            playlist_id = self._extract_id(url, "playlist")
            response = requests.get(f"{self.API_BASE}/playlist/{playlist_id}")
            data = response.json()
            for track in data.get('tracks', {}).get('data', []):
                tracks.append(self._map_track(track))
                
        elif "/album/" in url:
            album_id = self._extract_id(url, "album")
            response = requests.get(f"{self.API_BASE}/album/{album_id}")
            data = response.json()
            album_info = data
            for track in data.get('tracks', {}).get('data', []):
                if 'album' not in track:
                    track['album'] = album_info
                tracks.append(self._map_track(track))
                
        return tracks

    def _extract_id(self, url: str, type_name: str) -> str:
        """Extrait l'ID numérique de l'URL Deezer"""
        match = re.search(rf"{type_name}/(\d+)", url)
        if not match:
            raise ValueError(f"URL Deezer invalide pour le type {type_name}")
        return match.group(1)

    def _map_track(self, data: dict) -> TrackMetadata:
        """Mappe le dictionnaire Deezer vers l'objet TrackMetadata standard"""
        album = data.get('album', {})
        return TrackMetadata(
            title=data.get('title', 'Titre inconnu'),
            artist=data.get('artist', {}).get('name', 'Artiste inconnu'),
            album=album.get('title'),
            release_year=int(album.get('release_date', '0')[:4]) if album.get('release_date') else None,
            cover_url=album.get('cover_xl') or album.get('cover_big'),
            duration_ms=data.get('duration', 0) * 1000,
            isrc=data.get('isrc'),
            provider="deezer",
            original_url=data.get('link')
        )
