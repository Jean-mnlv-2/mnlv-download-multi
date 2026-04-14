from .base import MusicProvider, TrackMetadata
import re
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from django.conf import settings
from typing import List, Optional

class SpotifyProvider(MusicProvider):
    """
    Adapteur pour la plateforme Spotify utilisant spotipy pour les métadonnées.
    Sert de Blueprint de référence pour les autres providers.
    """
    def __init__(self, auth_token: Optional[str] = None):
        """
        Initialise le provider.
        Si un auth_token est fourni, il sera utilisé pour les opérations d'écriture (playlists).
        Sinon, on utilise les credentials clients par défaut (lecture seule).
        """
        self._sp_client = None
        self.auth_token = auth_token

    @property
    def client(self):
        if self._sp_client is None:
            if self.auth_token:
                self._sp_client = spotipy.Spotify(auth=self.auth_token)
            else:
                auth_manager = SpotifyClientCredentials(
                    client_id=settings.SPOTIFY_CLIENT_ID,
                    client_secret=settings.SPOTIFY_CLIENT_SECRET
                )
                self._sp_client = spotipy.Spotify(auth_manager=auth_manager)
        return self._sp_client

    def create_playlist(self, name: str, description: str = "", public: bool = False) -> str:
        """Crée une nouvelle playlist (Nécessite user_token)"""
        user_id = self.client.current_user()['id']
        playlist = self.client.user_playlist_create(user_id, name, public=public, description=description)
        return playlist['id']

    def delete_playlist(self, playlist_id: str):
        """Supprime (unfollow) une playlist (Nécessite user_token)"""
        self.client.current_user_unfollow_playlist(playlist_id)

    def add_tracks_to_playlist(self, playlist_id: str, track_urls: List[str]):
        """Ajoute une liste de titres à une playlist (Nécessite user_token)"""
        self.client.playlist_add_items(playlist_id, track_urls)

    def remove_tracks_from_playlist(self, playlist_id: str, track_urls: List[str]):
        """Retire une liste de titres d'une playlist (Nécessite auth_token)"""
        self.client.playlist_remove_all_occurrences_of_items(playlist_id, track_urls)

    def get_user_playlists(self) -> List[dict]:
        """Récupère les playlists de l'utilisateur avec statistiques de base"""
        results = self.client.current_user_playlists()
        playlists = []
        for item in results['items']:
            playlists.append({
                'id': item['id'],
                'name': item['name'],
                'track_count': item['tracks']['total'],
                'owner': item['owner']['display_name'],
                'url': item['external_urls']['spotify'],
                'cover_url': item['images'][0]['url'] if item['images'] else None,
            })
        return playlists

    def get_playlist_details(self, url: str) -> dict:
        """Détails complets et statistiques d'une playlist Spotify"""
        playlist = self.client.playlist(url)
        tracks = playlist['tracks']['items']
        total_duration_ms = sum([t['track']['duration_ms'] for t in tracks if t.get('track')])
        
        return {
            'id': playlist['id'],
            'name': playlist['name'],
            'description': playlist['description'],
            'track_count': playlist['tracks']['total'],
            'total_duration_ms': total_duration_ms,
            'followers': playlist['followers']['total'],
            'cover_url': playlist['images'][0]['url'] if playlist['images'] else None,
            'owner': playlist['owner']['display_name'],
            'provider': 'spotify'
        }

    def supports_url(self, url: str) -> bool:
        """Vérifie si l'URL est de type spotify.com"""
        return bool(re.search(r"open\.spotify\.com/(track|album|playlist)/", url))

    def get_track_info(self, url: str) -> TrackMetadata:
        """Extrait les métadonnées d'un titre Spotify unique"""
        track = self.client.track(url)
        return self._map_track(track)

    def get_playlist_tracks(self, url: str) -> List[TrackMetadata]:
        """Extrait la liste des titres d'une playlist ou d'un album avec pagination complète"""
        tracks = []
        try:
            if "/playlist/" in url:
                results = self.client.playlist_tracks(url)
                items = results['items']
                while results['next']:
                    results = self.client.next(results)
                    items.extend(results['items'])
                
                for item in items:
                    if item.get('track'):
                        tracks.append(self._map_track(item['track']))
            
            elif "/album/" in url:
                results = self.client.album_tracks(url)
                items = results['items']
                album_info = self.client.album(url)
                while results['next']:
                    results = self.client.next(results)
                    items.extend(results['items'])
                
                for item in items:
                    # Inject album info for mapping
                    item['album'] = album_info
                    tracks.append(self._map_track(item))
            
            elif "/artist/" in url:
                results = self.client.artist_top_tracks(url)
                for track in results['tracks']:
                    tracks.append(self._map_track(track))
                    
        except Exception as e:
            raise ValueError(f"Erreur lors de l'extraction Spotify : {str(e)}")
            
        return tracks

    def _map_track(self, track: dict) -> TrackMetadata:
        """Mappe le dictionnaire Spotify vers l'objet TrackMetadata standard"""
        album = track.get('album', {})
        images = album.get('images', [])
        cover_url = images[0]['url'] if images else None
        
        return TrackMetadata(
            title=track['name'],
            artist=", ".join([a['name'] for a in track['artists']]),
            album=album.get('name'),
            release_year=int(album.get('release_date', '0')[:4]) if album.get('release_date') else None,
            cover_url=cover_url,
            duration_ms=track.get('duration_ms'),
            isrc=track.get('external_ids', {}).get('isrc'),
            provider="spotify",
            original_url=track.get('external_urls', {}).get('spotify')
        )
