from ..base import MusicProvider, TrackMetadata
import re
try:
    import tidalapi
except ImportError:
    tidalapi = None
from django.conf import settings
from typing import List, Optional

class TidalProvider(MusicProvider):
    """
    Adapteur pour Tidal utilisant tidalapi.
    Nécessite TIDAL_ACCESS_TOKEN (ou processus de login OAuth).
    """
    def __init__(self, auth_token: str = None):
        """
        Initialise le provider Tidal.
        auth_token est requis pour les opérations d'écriture.
        """
        self._session = None
        self.auth_token = auth_token

    @property
    def session(self):
        if self._session is None:
            self._session = tidalapi.Session()
            if self.auth_token:
                self._session.load_oauth_session(
                    token_type=settings.TIDAL_TOKEN_TYPE,
                    access_token=self.auth_token,
                    refresh_token=settings.TIDAL_REFRESH_TOKEN,
                    expiry=settings.TIDAL_EXPIRY
                )
            else:
                self._session.load_oauth_session(
                    token_type=settings.TIDAL_TOKEN_TYPE,
                    access_token=settings.TIDAL_ACCESS_TOKEN,
                    refresh_token=settings.TIDAL_REFRESH_TOKEN,
                    expiry=settings.TIDAL_EXPIRY
                )
        return self._session

    def create_playlist(self, name: str, description: str = "", public: bool = False) -> str:
        """Crée une nouvelle playlist sur Tidal"""
        user_id = self.session.user.id
        playlist = self.session.user.create_playlist(name, description)
        return playlist.id

    def delete_playlist(self, playlist_id: str):
        """Supprime une playlist sur Tidal (unfollow)"""
        playlist = self.session.playlist(playlist_id)
        playlist.delete()

    def add_tracks_to_playlist(self, playlist_id: str, track_urls: List[str]):
        """Ajoute des titres via leurs IDs Tidal"""
        playlist = self.session.playlist(playlist_id)
        track_ids = [self._extract_id(u, "track") for u in track_urls]
        playlist.add(track_ids)

    def remove_tracks_from_playlist(self, playlist_id: str, track_urls: List[str]):
        """Retire des titres d'une playlist Tidal"""
        playlist = self.session.playlist(playlist_id)
        track_ids = [self._extract_id(u, "track") for u in track_urls]
        for t_id in track_ids:
            playlist.remove(t_id)

    def supports_url(self, url: str) -> bool:
        """Vérifie si l'URL est de type tidal.com"""
        return bool(re.search(r"tidal\.com", url))

    def get_track_info(self, url: str) -> TrackMetadata:
        """Extrait les métadonnées d'un titre Tidal"""
        track_id = self._extract_id(url, "track")
        track = self.session.track(track_id)
        return self._map_track(track)

    def get_playlist_tracks(self, url: str) -> List[TrackMetadata]:
        """Extrait la liste des titres d'une playlist ou d'un album Tidal"""
        tracks = []
        if "/playlist/" in url:
            playlist_id = self._extract_id(url, "playlist")
            playlist = self.session.playlist(playlist_id)
            for track in playlist.tracks():
                tracks.append(self._map_track(track))
        
        elif "/album/" in url:
            album_id = self._extract_id(url, "album")
            album = self.session.album(album_id)
            for track in album.tracks():
                tracks.append(self._map_track(track))
                
        return tracks

    def _extract_id(self, url: str, type_name: str) -> str:
        """Extrait l'ID de l'URL Tidal"""
        match = re.search(rf"{type_name}/(\d+)", url)
        if match:
            return match.group(1)
        raise ValueError(f"ID Tidal introuvable dans l'URL : {url}")

    def _map_track(self, track) -> TrackMetadata:
        """Mappe un objet tidalapi.Track vers TrackMetadata"""
        return TrackMetadata(
            title=track.name,
            artist=", ".join([a.name for a in track.artists]),
            album=track.album.name if track.album else None,
            release_year=track.album.year if track.album else None,
            cover_url=track.album.image(1280) if track.album else None,
            duration_ms=track.duration * 1000,
            isrc=getattr(track, 'isrc', None),
            provider="tidal",
            original_url=f"https://tidal.com/track/{track.id}"
        )
