from ..base import MusicProvider, ProviderTrackMetadata, ProviderAuthError, ProviderRateLimitError, ProviderResourceNotFoundError, ProviderAPIError, monitor_provider, monitor_provider_async
import re
import spotipy
import logging
import asyncio
from spotipy.oauth2 import SpotifyClientCredentials
from django.conf import settings
from typing import List, Optional
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

class SpotifyProvider(MusicProvider):
    """
    Adapteur pour la plateforme Spotify utilisant spotipy pour les métadonnées.
    Supporte l'exécution asynchrone via thread pooling pour les appels bloquants.
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
            try:
                if self.auth_token:
                    self._sp_client = spotipy.Spotify(auth=self.auth_token)
                else:
                    auth_manager = SpotifyClientCredentials(
                        client_id=settings.SPOTIFY_CLIENT_ID,
                        client_secret=settings.SPOTIFY_CLIENT_SECRET
                    )
                    self._sp_client = spotipy.Spotify(auth_manager=auth_manager)
            except Exception as e:
                raise ProviderAPIError(f"Erreur initialisation client Spotify : {str(e)}", code="SPOTIFY_INIT_ERROR")
        return self._sp_client

    def _handle_spotify_error(self, e: spotipy.SpotifyException):
        """Mappe les erreurs Spotipy vers les exceptions Provider."""
        status = e.http_status
        msg = e.msg
        if status == 401:
            raise ProviderAuthError(f"Session Spotify expirée ou invalide : {msg}", code="SPOTIFY_AUTH_ERROR")
        if status == 403:
            raise ProviderAuthError(f"Action Spotify interdite (Permissions ?) : {msg}", code="SPOTIFY_FORBIDDEN")
        if status == 404:
            raise ProviderResourceNotFoundError(f"Ressource Spotify introuvable : {msg}", code="SPOTIFY_NOT_FOUND")
        if status == 429:
            raise ProviderRateLimitError(f"Limite Spotify atteinte : {msg}", code="SPOTIFY_RATE_LIMIT")
        raise ProviderAPIError(f"Erreur API Spotify [{status}]: {msg}", code=f"SPOTIFY_ERROR_{status}")

    @monitor_provider_async
    async def get_track_info_async(self, url: str) -> ProviderTrackMetadata:
        """Version asynchrone optimisée pour Spotify"""
        market = getattr(settings, 'SPOTIFY_MARKET', 'FR')
        try:
            if "/episode/" in url:
                data = await sync_to_async(self.client.episode)(url, market=market)
                return self._map_episode(data)
            elif "/chapter/" in url:
                data = await sync_to_async(self.client.chapter)(url, market=market)
                return self._map_chapter(data)
            elif "/audiobook/" in url:
                data = await sync_to_async(self.client.audiobook)(url, market=market)
                return self._map_audiobook(data)
            
            data = await sync_to_async(self.client.track)(url, market=market)
            return self._map_track(data)
        except spotipy.SpotifyException as e:
            self._handle_spotify_error(e)

    @monitor_provider_async
    async def get_playlist_tracks_async(self, url: str) -> List[ProviderTrackMetadata]:
        """Version asynchrone optimisée pour Spotify avec pagination parallèle"""
        market = getattr(settings, 'SPOTIFY_MARKET', 'FR')
        tracks = []
        
        try:
            if "/playlist/" in url:
                fields = 'items(track(name,artists,album(name,release_date,images),duration_ms,external_ids,external_urls,explicit,type)),next,total'
                results = await sync_to_async(self.client.playlist_tracks)(url, fields=fields, market=market, additional_types=('track', 'episode'))
                
                # Première page
                for item in results['items']:
                    if item.get('track'):
                        t = item['track']
                        tracks.append(self._map_episode(t) if t.get('type') == 'episode' else self._map_track(t))
                
                while results['next']:
                    results = await sync_to_async(self.client.next)(results)
                    for item in results['items']:
                        if item.get('track'):
                            t = item['track']
                            tracks.append(self._map_episode(t) if t.get('type') == 'episode' else self._map_track(t))
            
            elif "/album/" in url:
                results = await sync_to_async(self.client.album_tracks)(url, market=market)
                album_info = await sync_to_async(self.client.album)(url, market=market)
                
                items = results['items']
                while results['next']:
                    results = await sync_to_async(self.client.next)(results)
                    items.extend(results['items'])
                
                for item in items:
                    item['album'] = album_info
                    tracks.append(self._map_track(item))
            
            else:
                return await super().get_playlist_tracks_async(url)
                
            return tracks
        except spotipy.SpotifyException as e:
            self._handle_spotify_error(e)

    @monitor_provider
    def create_playlist(self, name: str, description: str = "", public: bool = False) -> str:
        """Crée une nouvelle playlist (Nécessite user_token)"""
        try:
            user_id = self.client.current_user()['id']
            playlist = self.client.user_playlist_create(user_id, name, public=public, description=description)
            return playlist['id']
        except spotipy.SpotifyException as e:
            self._handle_spotify_error(e)

    def delete_playlist(self, playlist_id: str):
        """Supprime (unfollow) une playlist (Nécessite user_token)"""
        self.client.current_user_unfollow_playlist(playlist_id)

    def add_tracks_to_playlist(self, playlist_id: str, track_urls: List[str], position: Optional[int] = None) -> Optional[str]:
        """Ajoute une liste de titres à une playlist avec support de la position et découpage par lots (max 100)"""
        chunk_size = 100
        snapshot_id = None
        
        
        for i in range(0, len(track_urls), chunk_size):
            chunk = track_urls[i:i + chunk_size]
            current_position = position + i if position is not None else None
            
            try:
                result = self.client.playlist_add_items(playlist_id, chunk, position=current_position)
                snapshot_id = result.get('snapshot_id')
            except spotipy.SpotifyException as e:
                self._handle_spotify_error(e)
                
        return snapshot_id

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
                    'type': 'playlist'
                })
            if results['next']:
                results = self.client.next(results)
            else:
                results = None
        return playlists

    def get_user_audiobooks(self) -> List[dict]:
        """Récupère tous les livres audio sauvegardés par l'utilisateur"""
        audiobooks = []
        try:
            results = self.client._get("me/audiobooks")
            
            if not results or not isinstance(results, dict):
                return []

            while results:
                items = results.get('items', [])
                for item in items:
                    if not item:
                        continue
                        
                    ab = item.get('audiobook') if isinstance(item, dict) and 'audiobook' in item else item
                    
                    if not ab or not isinstance(ab, dict):
                        continue
                        
                    audiobooks.append({
                        'id': ab.get('id'),
                        'name': ab.get('name'),
                        'track_count': ab.get('total_chapters', 0),
                        'owner': ", ".join([a['name'] for a in ab.get('authors', [])]) if ab.get('authors') else "Auteur inconnu",
                        'url': ab.get('external_urls', {}).get('spotify'),
                        'cover_url': ab.get('images', [{}])[0].get('url') if ab.get('images') else None,
                        'type': 'audiobook'
                    })
                
                if results.get('next'):
                    results = self.client.next(results)
                else:
                    results = None
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Note: Impossible de récupérer les livres audio Spotify (v2.23.0 limitation or region): {e}")
        return audiobooks

    def save_audiobook(self, audiobook_id: str):
        """Enregistre un livre audio dans la bibliothèque de l'utilisateur"""
        try:
            self.client._put(f"me/audiobooks?ids={audiobook_id}")
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement du livre audio Spotify {audiobook_id} : {e}")

    def remove_audiobook(self, audiobook_id: str):
        """Retire un livre audio de la bibliothèque de l'utilisateur"""
        try:
            self.client._delete(f"me/audiobooks?ids={audiobook_id}")
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du livre audio Spotify {audiobook_id} : {e}")

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
        """Vérifie si l'URL est une URL Spotify valide"""
        return bool(re.search(r"(open|play|www)?\.?spotify\.com", url))

    @monitor_provider
    def get_track_info(self, url: str) -> ProviderTrackMetadata:
        """Extrait les métadonnées d'un titre, d'un épisode ou d'un chapitre Spotify"""
        market = getattr(settings, 'SPOTIFY_MARKET', 'FR')
        
        try:
            if "/episode/" in url:
                episode = self.client.episode(url, market=market)
                return self._map_episode(episode)
            elif "/chapter/" in url:
                chapter = self.client.chapter(url, market=market)
                return self._map_chapter(chapter)
            elif "/audiobook/" in url:
                audiobook = self.client.audiobook(url, market=market)
                return self._map_audiobook(audiobook)
            
            track = self.client.track(url, market=market)
            return self._map_track(track)
        except spotipy.SpotifyException as e:
            self._handle_spotify_error(e)

    @monitor_provider
    def get_playlist_tracks(self, url: str) -> List[ProviderTrackMetadata]:
        """Extrait la liste des titres d'une playlist, album, show ou livre audio"""
        tracks = []
        market = getattr(settings, 'SPOTIFY_MARKET', 'FR')
        
        try:
            if "/playlist/" in url:
                fields = 'items(track(name,artists,album(name,release_date,images),duration_ms,external_ids,external_urls,explicit,type)),next'
                results = self.client.playlist_tracks(url, fields=fields, market=market, additional_types=('track', 'episode'))
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
                results = self.client.album_tracks(url, market=market)
                items = results['items']
                album_info = self.client.album(url, market=market)
                while results['next']:
                    results = self.client.next(results)
                    items.extend(results['items'])
                
                for item in items:
                    # Inject album info for mapping
                    item['album'] = album_info
                    tracks.append(self._map_track(item))
            
            elif "/artist/" in url:
                results = self.client.artist_top_tracks(url, market=market)
                for track in results['tracks']:
                    tracks.append(self._map_track(track))
            
            elif "/show/" in url:
                results = self.client.show_episodes(url, market=market)
                items = results['items']
                while results['next']:
                    results = self.client.next(results)
                    items.extend(results['items'])
                for ep in items:
                    tracks.append(self._map_episode(ep))

            elif "/audiobook/" in url:
                results = self.client.audiobook_chapters(url, market=market)
                items = results['items']
                audiobook_info = self.client.audiobook(url, market=market)
                while results['next']:
                    results = self.client.next(results)
                    items.extend(results['items'])
                
                for item in items:
                    # Inject audiobook info for mapping
                    item['audiobook'] = audiobook_info
                    tracks.append(self._map_chapter(item))
                    
        except spotipy.SpotifyException as e:
            raise ValueError(f"Erreur API Spotify (Code {e.http_status}) : {e.msg}")
        except Exception as e:
            raise ValueError(f"Erreur lors de l'extraction Spotify : {str(e)}")
            
        return tracks

    def _map_track(self, track: dict) -> ProviderTrackMetadata:
        """Mappe le dictionnaire Spotify vers l'objet TrackMetadata standard"""
        album = track.get('album', {})
        images = album.get('images', [])
        cover_url = images[0]['url'] if images else None
        external_ids = track.get('external_ids', {})
        
        return ProviderTrackMetadata(
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

    def _map_episode(self, ep: dict) -> ProviderTrackMetadata:
        """Mappe un épisode de podcast vers TrackMetadata"""
        images = ep.get('images', [])
        cover_url = images[0]['url'] if images else None
        
        return ProviderTrackMetadata(
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

    def _map_audiobook(self, ab: dict) -> ProviderTrackMetadata:
        """Mappe un livre audio vers TrackMetadata (en tant qu'entité unique)"""
        images = ab.get('images', [])
        cover_url = images[0]['url'] if images else None
        
        authors = [a['name'] for a in ab.get('authors', [])]
        narrators = [n['name'] for n in ab.get('narrators', [])]
        artist_parts = authors + ([f"Lu par {', '.join(narrators)}"] if narrators else [])
        artist = " & ".join(artist_parts)
        
        edition = ab.get('edition')
        title = f"{ab['name']} ({edition})" if edition else ab['name']
        
        return ProviderTrackMetadata(
            title=title,
            artist=artist,
            album=ab['name'],
            release_year=None,
            cover_url=cover_url,
            duration_ms=None,
            explicit=ab.get('explicit', False),
            is_episode=True,
            provider="spotify",
            original_url=ab.get('external_urls', {}).get('spotify')
        )

    def _map_chapter(self, ch: dict) -> ProviderTrackMetadata:
        """Mappe un chapitre de livre audio vers TrackMetadata"""
        images = ch.get('images', [])
        cover_url = images[0]['url'] if images else None
        
        # Récupération des infos depuis l'audiobook parent si injecté
        audiobook = ch.get('audiobook', {})
        authors = [a['name'] for a in audiobook.get('authors', [])]
        narrators = [n['name'] for n in audiobook.get('narrators', [])]
        
        artist_parts = authors + ([f"Lu par {', '.join(narrators)}"] if narrators else [])
        artist = " & ".join(artist_parts) if artist_parts else "Auteur Inconnu"
        
        album = audiobook.get('name', 'Livre Audio')
        edition = audiobook.get('edition')
        if edition:
            album = f"{album} ({edition})"

        return ProviderTrackMetadata(
            title=ch['name'],
            artist=artist,
            album=album,
            release_year=int(ch.get('release_date', '0')[:4]) if ch.get('release_date') else None,
            cover_url=cover_url,
            duration_ms=ch.get('duration_ms'),
            explicit=ch.get('explicit', False),
            is_episode=True,
            provider="spotify",
            original_url=ch.get('external_urls', {}).get('spotify')
        )
