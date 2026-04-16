from ..base import MusicProvider, TrackMetadata
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

    def add_tracks_to_playlist(self, playlist_id: str, track_urls: List[str], position: Optional[int] = None) -> Optional[str]:
        """Ajoute une liste de titres à une playlist avec support de la position"""
        result = self.client.playlist_add_items(playlist_id, track_urls, position=position)
        return result.get('snapshot_id')

    def remove_tracks_from_playlist(self, playlist_id: str, track_urls: List[str], snapshot_id: Optional[str] = None) -> Optional[str]:
        """Retire une liste de titres d'une playlist avec snapshot_id pour la cohérence"""
        result = self.client.playlist_remove_all_occurrences_of_items(playlist_id, track_urls, snapshot_id=snapshot_id)
        return result.get('snapshot_id')

    def reorder_playlist_tracks(self, playlist_id: str, range_start: int, insert_before: int, range_length: int = 1, snapshot_id: Optional[str] = None) -> Optional[str]:
        """Réorganise les titres d'une playlist"""
        result = self.client.playlist_reorder_items(
            playlist_id, 
            range_start=range_start, 
            insert_before=insert_before, 
            range_length=range_length, 
            snapshot_id=snapshot_id
        )
        return result.get('snapshot_id')

    def get_user_playlists(self) -> List[dict]:
        """Récupère toutes les playlists de l'utilisateur avec pagination complète"""
        playlists = []
        results = self.client.current_user_playlists()
        
        while results:
            for item in results['items']:
                playlists.append({
                    'id': item['id'],
                    'name': item['name'],
                    'track_count': item['tracks']['total'],
                    'owner': item['owner']['display_name'],
                    'url': item['external_urls']['spotify'],
                    'cover_url': item['images'][0]['url'] if item['images'] else None,
                })
            if results['next']:
                results = self.client.next(results)
            else:
                results = None
        return playlists

    def get_playlist_details(self, url: str) -> dict:
        """Détails complets et statistiques d'une playlist Spotify avec pagination pour la durée"""
        fields = 'id,name,description,tracks.total,followers.total,images,owner.display_name,tracks.items(track(duration_ms)),tracks.next'
        playlist = self.client.playlist(url, fields=fields)
        
        tracks_data = playlist['tracks']
        items = tracks_data['items']
        
        total_duration_ms = sum([t['track']['duration_ms'] for t in items if t.get('track')])
        
        current_page = tracks_data
        while current_page['next']:
            current_page = self.client.next(current_page)
            total_duration_ms += sum([t['track']['duration_ms'] for t in current_page['items'] if t.get('track')])
        
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
        """Extrait les métadonnées d'un titre ou d'un épisode Spotify"""
        if "/episode/" in url:
            episode = self.client.episode(url)
            return self._map_episode(episode)
        
        track = self.client.track(url)
        return self._map_track(track)

    def get_playlist_tracks(self, url: str) -> List[TrackMetadata]:
        """Extrait la liste des titres d'une playlist ou d'un album avec pagination complète"""
        tracks = []
        try:
            if "/playlist/" in url:
                fields = 'items(track(name,artists,album(name,release_date,images),duration_ms,external_ids,external_urls,explicit,type)),next'
                results = self.client.playlist_tracks(url, fields=fields, additional_types=('track', 'episode'))
                items = results['items']
                while results['next']:
                    results = self.client.next(results)
                    items.extend(results['items'])
                
                for item in items:
                    if item.get('track'):
                        t = item['track']
                        if t.get('type') == 'episode':
                            tracks.append(self._map_episode(t))
                        else:
                            tracks.append(self._map_track(t))
            
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
            
            elif "/show/" in url:
                results = self.client.show_episodes(url)
                items = results['items']
                while results['next']:
                    results = self.client.next(results)
                    items.extend(results['items'])
                for ep in items:
                    tracks.append(self._map_episode(ep))
                    
        except spotipy.SpotifyException as e:
            raise ValueError(f"Erreur API Spotify (Code {e.http_status}) : {e.msg}")
        except Exception as e:
            raise ValueError(f"Erreur lors de l'extraction Spotify : {str(e)}")
            
        return tracks

    def _map_track(self, track: dict) -> TrackMetadata:
        """Mappe le dictionnaire Spotify vers l'objet TrackMetadata standard"""
        album = track.get('album', {})
        images = album.get('images', [])
        cover_url = images[0]['url'] if images else None
        external_ids = track.get('external_ids', {})
        
        return TrackMetadata(
            title=track['name'],
            artist=", ".join([a['name'] for a in track['artists']]),
            album=album.get('name'),
            release_year=int(album.get('release_date', '0')[:4]) if album.get('release_date') else None,
            cover_url=cover_url,
            duration_ms=track.get('duration_ms'),
            isrc=external_ids.get('isrc'),
            ean=external_ids.get('ean'),
            upc=external_ids.get('upc'),
            explicit=track.get('explicit', False),
            is_episode=False,
            provider="spotify",
            original_url=track.get('external_urls', {}).get('spotify')
        )

    def _map_episode(self, ep: dict) -> TrackMetadata:
        """Mappe un épisode de podcast vers TrackMetadata"""
        images = ep.get('images', [])
        cover_url = images[0]['url'] if images else None
        
        return TrackMetadata(
            title=ep['name'],
            artist=ep.get('show', {}).get('name', 'Podcast'),
            album=ep.get('show', {}).get('name'),
            release_year=int(ep.get('release_date', '0')[:4]) if ep.get('release_date') else None,
            cover_url=cover_url,
            duration_ms=ep.get('duration_ms'),
            explicit=ep.get('explicit', False),
            is_episode=True,
            provider="spotify",
            original_url=ep.get('external_urls', {}).get('spotify')
        )
