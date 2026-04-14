from .base import MusicProvider, TrackMetadata
import re
from applemusicpy import AppleMusic
from django.conf import settings
from typing import List, Optional

class AppleMusicProvider(MusicProvider):
    """
    Adapteur pour Apple Music utilisant applemusicpy.
    Nécessite APPLE_MUSIC_KEY_ID, APPLE_MUSIC_TEAM_ID, APPLE_MUSIC_SECRET_KEY.
    """
    def __init__(self, auth_token: Optional[str] = None):
        self._am = None
        self.auth_token = auth_token

    @property
    def am(self):
        if self._am is None:
            self._am = AppleMusic(
                secret_key=settings.APPLE_MUSIC_SECRET_KEY,
                key_id=settings.APPLE_MUSIC_KEY_ID,
                team_id=settings.APPLE_MUSIC_TEAM_ID
            )
        return self._am

    def supports_url(self, url: str) -> bool:
        """Vérifie si l'URL est de type music.apple.com"""
        return bool(re.search(r"music\.apple\.com/.*?/(album|song|playlist)/", url))

    def get_track_info(self, url: str) -> TrackMetadata:
        """Extrait les métadonnées d'un titre Apple Music"""
        track_id = self._extract_id(url)
        storefront = self._extract_storefront(url)
        
        results = self.am.song(track_id, storefront=storefront)
        track = results['data'][0]
        attrs = track['attributes']
        
        return self._map_track(attrs, url)

    def get_playlist_tracks(self, url: str) -> List[TrackMetadata]:
        """Extrait la liste des titres d'une playlist ou d'un album Apple Music"""
        tracks = []
        item_id = self._extract_id(url)
        storefront = self._extract_storefront(url)
        
        if "/album/" in url:
            results = self.am.album(item_id, storefront=storefront)
            album_data = results['data'][0]
            for relationship in album_data.get('relationships', {}).get('tracks', {}).get('data', []):
                tracks.append(self._map_track(relationship['attributes'], relationship['attributes']['url']))
        
        elif "/playlist/" in url:
            results = self.am.playlist(item_id, storefront=storefront)
            playlist_data = results['data'][0]
            for relationship in playlist_data.get('relationships', {}).get('tracks', {}).get('data', []):
                tracks.append(self._map_track(relationship['attributes'], relationship['attributes']['url']))
                
        return tracks

    def _extract_id(self, url: str) -> str:
        """Extrait l'ID de l'URL Apple Music"""
        match = re.search(r"/(?:album|song|playlist)/.*?/(\d+|pl\..*)", url)
        if match:
            return match.group(1)
        raise ValueError(f"ID Apple Music introuvable dans l'URL : {url}")

    def _extract_storefront(self, url: str) -> str:
        """Extrait le storefront (ex: fr, us) de l'URL"""
        match = re.search(r"apple\.com/([^/]+)/", url)
        return match.group(1) if match else "us"

    def _map_track(self, attrs: dict, url: str) -> TrackMetadata:
        """Mappe les attributs Apple Music vers TrackMetadata"""
        artwork_url = attrs.get('artwork', {}).get('url', '')
        artwork_url = artwork_url.replace('{w}', '1000').replace('{h}', '1000')
        
        return TrackMetadata(
            title=attrs.get('name', 'Titre inconnu'),
            artist=attrs.get('artistName', 'Artiste inconnu'),
            album=attrs.get('albumName'),
            release_year=int(attrs.get('releaseDate', '0')[:4]) if attrs.get('releaseDate') else None,
            cover_url=artwork_url,
            duration_ms=attrs.get('durationInMillis', 0),
            isrc=attrs.get('isrc'),
            provider="apple_music",
            original_url=url
        )
