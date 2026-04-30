from ..base import MusicProvider, ProviderTrackMetadata
import re
import requests
from typing import List, Optional
from django.conf import settings

class DeezerProvider(MusicProvider):
    """
    Adapteur pour Deezer utilisant son API publique REST.
    Suit le blueprint fonctionnel de SpotifyProvider.
    Optimisé pour la pagination complète et le matching haute précision.
    """
    API_BASE = settings.DEEZER_API_BASE

    def __init__(self, auth_token: Optional[str] = None):
        """
        Initialise le provider Deezer.
        Si un auth_token est fourni, il sera utilisé pour les opérations d'écriture.
        """
        self.auth_token = auth_token
        self._session = requests.Session()

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Helper pour les requêtes GET avec gestion d'erreurs centralisée"""
        if params is None:
            params = {}
        if self.auth_token:
            params['access_token'] = self.auth_token

        url = f"{self.API_BASE}/{endpoint.lstrip('/')}"
        response = self._session.get(url, params=params, timeout=15)
        
        if response.status_code != 200:
            raise ValueError(f"Deezer API error {response.status_code}: {response.text}")
            
        data = response.json()
        if isinstance(data, dict) and "error" in data:
            error = data["error"]
            code = error.get("code")
            msg = error.get("message")
            if code == 4:
                raise RuntimeError(f"Deezer Rate Limit: {msg}")
            raise ValueError(f"Deezer API Error [{code}]: {msg}")
            
        return data

    def create_playlist(self, name: str, description: str = "", public: bool = False) -> str:
        """Crée une nouvelle playlist (Nécessite auth_token / access_token)"""
        if not self.auth_token:
            raise ValueError("Token Deezer requis pour créer une playlist.")
        
        params = {"title": name}
        data = self._post("user/me/playlists", params=params)
        return str(data['id'])

    def _post(self, endpoint: str, params: dict = None) -> dict:
        """Helper pour les requêtes POST"""
        if params is None:
            params = {}
        if self.auth_token:
            params['access_token'] = self.auth_token

        url = f"{self.API_BASE}/{endpoint.lstrip('/')}"
        response = self._session.post(url, params=params, timeout=15)
        data = response.json()
        if isinstance(data, dict) and "error" in data:
            raise ValueError(f"Deezer POST Error: {data['error'].get('message')}")
        return data

    def delete_playlist(self, playlist_id: str):
        """Supprime une playlist (Nécessite auth_token / access_token)"""
        if not self.auth_token:
            raise ValueError("Token Deezer requis pour supprimer une playlist.")
            
        params = {"access_token": self.auth_token}
        url = f"{self.API_BASE}/playlist/{playlist_id}"
        response = self._session.delete(url, params=params)
        data = response.json()
        if data is not True and isinstance(data, dict) and "error" in data:
             raise ValueError(f"Erreur Deezer: {data['error']['message']}")

    def add_tracks_to_playlist(self, playlist_id: str, track_urls: List[str], position: Optional[int] = None) -> Optional[str]:
        """Ajoute des titres via leurs IDs Deezer"""
        if not self.auth_token:
            raise ValueError("Token Deezer requis pour modifier une playlist.")
            
        track_ids = [self._extract_id(u, "track") for u in track_urls]
        params = {"songs": ",".join(track_ids)}
        self._post(f"playlist/{playlist_id}/tracks", params=params)
        return None

    def remove_tracks_from_playlist(self, playlist_id: str, track_urls: List[str], snapshot_id: Optional[str] = None) -> Optional[str]:
        """Retire une liste de titres d'une playlist"""
        if not self.auth_token:
            raise ValueError("Token Deezer requis pour supprimer des titres.")
            
        track_ids = [self._extract_id(u, "track") for u in track_urls]
        params = {"songs": ",".join(track_ids)}
        url = f"{self.API_BASE}/playlist/{playlist_id}/tracks"
        response = self._session.delete(url, params={**params, "access_token": self.auth_token})
        return None

    def reorder_playlist_tracks(self, playlist_id: str, range_start: int, insert_before: int, range_length: int = 1, snapshot_id: Optional[str] = None) -> Optional[str]:
        """Réorganise les titres d'une playlist sur Deezer"""
        if not self.auth_token:
            raise ValueError("Token Deezer requis pour réorganiser une playlist.")
        
        params = {"order": f"{range_start},{insert_before}"}
        self._post(f"playlist/{playlist_id}/tracks", params=params)
        return None

    def get_user_playlists(self) -> List[dict]:
        """Récupère les playlists de l'utilisateur Deezer"""
        if not self.auth_token:
            raise ValueError("Token Deezer requis.")
            
        data = self._get("user/me/playlists")
        
        playlists = []
        for item in data.get('data', []):
            playlists.append({
                'id': str(item['id']),
                'name': item['title'],
                'track_count': item['nb_tracks'],
                'owner': item['creator']['name'] if 'creator' in item else "Moi",
                'url': item['link'],
                'cover_url': item.get('picture_xl') or item.get('picture_big'),
            })
        return playlists

    def get_playlist_details(self, url: str) -> dict:
        """Détails complets d'une playlist Deezer"""
        playlist_id = self._extract_id(url, "playlist")
        data = self._get(f"playlist/{playlist_id}")
        
        return {
            'id': str(data['id']),
            'name': data['title'],
            'description': data.get('description', ''),
            'track_count': data['nb_tracks'],
            'total_duration_ms': data['duration'] * 1000,
            'followers': data.get('fans', 0),
            'cover_url': data.get('picture_xl') or data.get('picture_big'),
            'owner': data.get('creator', {}).get('name', 'Inconnu'),
            'provider': 'deezer'
        }

    def supports_url(self, url: str) -> bool:
        """Vérifie si l'URL est une URL Deezer valide"""
        return bool(re.search(r"(www)?\.?deezer\.com", url))

    def get_track_info(self, url: str) -> ProviderTrackMetadata:
        """Extrait les métadonnées d'un titre ou d'un épisode de podcast"""
        if "/podcast/" in url or "/show/" in url:
            episode_id = self._extract_id(url, "(?:podcast|show)")
            data = self._get(f"episode/{episode_id}")
            return self._map_episode(data)
            
        track_id = self._extract_id(url, "track")
        data = self._get(f"track/{track_id}")
        return self._map_track(data)

    def get_playlist_tracks(self, url: str) -> List[ProviderTrackMetadata]:
        """Extrait la liste des titres (playlist, album, flow, favoris, podcast, radio)"""
        tracks = []
        limit = 100
        index = 0
        
        if "/playlist/" in url:
            playlist_id = self._extract_id(url, "playlist")
            tracks = self._fetch_all(f"playlist/{playlist_id}/tracks")
        elif "/album/" in url:
            album_id = self._extract_id(url, "album")
            album_data = self._get(f"album/{album_id}")
            tracks = self._fetch_all(f"album/{album_id}/tracks", extra_meta={'album': album_data})
        elif "/podcast/" in url or "/show/" in url:
            show_id = self._extract_id(url, "(?:podcast|show)")
            tracks = self._fetch_all(f"podcast/{show_id}/episodes", mapper=self._map_episode)
        elif "/radio/" in url:
            radio_id = self._extract_id(url, "radio")
            tracks = self._fetch_all(f"radio/{radio_id}/tracks")
        return tracks

    def get_user_flow(self) -> List[ProviderTrackMetadata]:
        """Récupère le Flow personnalisé de l'utilisateur"""
        if not self.auth_token:
            raise ValueError("Connexion Deezer requise pour accéder au Flow.")
        data = self._get("user/me/flow")
        return [self._map_track(t) for t in data.get('data', [])]

    def get_user_favorites(self) -> List[ProviderTrackMetadata]:
        """Récupère tous les titres 'Coups de Cœur' de l'utilisateur"""
        if not self.auth_token:
            raise ValueError("Connexion Deezer requise pour accéder aux favoris.")
        return self._fetch_all("user/me/tracks")

    def search(self, query: str, type: str = "track", limit: int = 20) -> List[dict]:
        """Recherche globale sur Deezer (Smart Search)"""
        endpoint = f"search/{type}" if type != "track" else "search"
        data = self._get(endpoint, params={"q": query, "limit": limit})
        results = []
        for item in data.get('data', []):
            if type == "track":
                results.append(self._map_track(item).__dict__)
            else:
                results.append(item)
        return results

    def get_charts(self, country: str = "0") -> dict:
        """Récupère les tendances (Top 50)"""
        data = self._get(f"chart/{country}")
        return {
            'tracks': [self._map_track(t) for t in data.get('tracks', {}).get('data', [])],
            'albums': data.get('albums', {}).get('data', []),
            'playlists': data.get('playlists', {}).get('data', [])
        }

    def _fetch_all(self, endpoint: str, params: dict = None, extra_meta: dict = None, mapper=None) -> List[ProviderTrackMetadata]:
        """Helper générique pour la pagination complète"""
        tracks = []
        limit = 100
        index = 0
        if params is None: params = {}
        if mapper is None: mapper = self._map_track
        
        while True:
            current_params = {**params, "index": index, "limit": limit}
            data = self._get(endpoint, params=current_params)
            batch = data.get('data', [])
            for item in batch:
                if extra_meta:
                    for k, v in extra_meta.items():
                        if k not in item: item[k] = v
                tracks.append(mapper(item))
            
            if len(batch) < limit or "next" not in data:
                break
            index += limit
        return tracks

    def _map_episode(self, data: dict) -> ProviderTrackMetadata:
        """Mappe un épisode de podcast vers TrackMetadata"""
        return ProviderTrackMetadata(
            title=data.get('title', 'Épisode inconnu'),
            artist=data.get('show', {}).get('title', 'Podcast inconnu'),
            album="Podcast",
            release_year=int(data.get('release_date', '0')[:4]) if data.get('release_date') else None,
            cover_url=data.get('picture_xl') or data.get('picture_big'),
            duration_ms=data.get('duration', 0) * 1000,
            isrc=None, # Les podcasts n'ont pas d'ISRC
            provider="deezer",
            original_url=data.get('link')
        )

    def _extract_id(self, url: str, type_name: str) -> str:
        """Extrait l'ID de l'URL Deezer, supporte les locales et types multiples"""
        match = re.search(rf"{type_name}/(\d+)", url)
        if not match:
            if "deezer.page.link" in url:
                resp = self._session.head(url, allow_redirects=True)
                return self._extract_id(resp.url, type_name)
            raise ValueError(f"URL Deezer invalide pour le type {type_name}")
        return match.group(1)

    def _map_track(self, data: dict) -> ProviderTrackMetadata:
        """Mappe le dictionnaire Deezer vers l'objet TrackMetadata standard"""
        album = data.get('album', {})
        artist = data.get('artist', {})
        
        # Filtre de contenu explicite (Parental Control)
        explicit = data.get('explicit_lyrics', False)
        
        return ProviderTrackMetadata(
            title=data.get('title', 'Titre inconnu'),
            artist=artist.get('name', 'Artiste inconnu'),
            album=album.get('title'),
            release_year=int(album.get('release_date', '0')[:4]) if album.get('release_date') else None,
            cover_url=album.get('cover_xl') or album.get('cover_big'),
            duration_ms=data.get('duration', 0) * 1000,
            isrc=data.get('isrc'),
            provider="deezer",
            original_url=data.get('link'),
            explicit=explicit
        )
