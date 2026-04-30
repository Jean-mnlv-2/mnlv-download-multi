from ..base import MusicProvider, ProviderTrackMetadata
import re
import logging
try:
    from ytmusicapi import YTMusic
except ImportError:
    YTMusic = None
from typing import List, Optional

logger = logging.getLogger(__name__)

class YouTubeMusicProvider(MusicProvider):
    """
    Adapteur pour YouTube Music utilisant ytmusicapi.
    Sert également de base pour le matching ISRC.
    """
    def __init__(self, auth_token: str = None):
        """
        Initialise le provider YouTube Music.
        auth_token peut être le contenu d'un fichier browser.json ou des headers.
        """
        self._yt = None
        self.auth_token = auth_token

    @property
    def yt(self):
        if self._yt is None:
            if self.auth_token:
                import json
                try:
                    cleaned_token = self.auth_token.strip()
                    if cleaned_token.startswith('{') and cleaned_token.endswith('}'):
                        auth_headers = json.loads(cleaned_token)
                        self._yt = YTMusic(auth=auth_headers)
                    else:
                        if cleaned_token.startswith('AIza'):
                            logger.warning("Clé API YouTube v3 fournie au lieu des headers YouTube Music. Utilisation anonyme.")
                            self._yt = YTMusic()
                        elif os.path.exists(cleaned_token):
                            self._yt = YTMusic(auth=cleaned_token)
                        else:
                            logger.warning(f"Token YouTube Music non reconnu : {cleaned_token[:10]}...")
                            self._yt = YTMusic()
                except Exception as e:
                    logger.error(f"Erreur d'initialisation YTMusic avec token: {e}")
                    self._yt = YTMusic()
            else:
                self._yt = YTMusic()
        return self._yt

    def create_playlist(self, name: str, description: str = "", public: bool = False) -> str:
        """Crée une nouvelle playlist sur YouTube Music"""
        if not self.auth_token or self.auth_token.startswith('AIza'):
            raise Exception("Authentification YouTube Music requise. Veuillez fournir vos headers JSON (cookies) et non une clé API v3 pour les opérations de bibliothèque.")
            
        try:
            privacy_status = "PUBLIC" if public else "PRIVATE"
            playlist_id = self.yt.create_playlist(name, description, privacy_status=privacy_status)
            return playlist_id
        except Exception as e:
            if "authentication" in str(e).lower():
                raise Exception("Session YouTube Music expirée ou headers invalides. Veuillez reconnecter votre compte.")
            raise e

    def delete_playlist(self, playlist_id: str):
        """Supprime une playlist sur YouTube Music"""
        if not self.auth_token or self.auth_token.startswith('AIza'):
            raise Exception("Authentification requise pour supprimer une playlist.")
        self.yt.delete_playlist(playlist_id)

    def add_tracks_to_playlist(self, playlist_id: str, track_urls: List[str]):
        """Ajoute des titres via leurs IDs de vidéo YouTube"""
        if not self.auth_token or self.auth_token.startswith('AIza'):
            raise Exception("Authentification requise pour modifier une playlist.")
        video_ids = []
        for url in track_urls:
            try:
                video_ids.append(self._extract_id(url, "watch?v="))
            except Exception:
                continue
        if video_ids:
            self.yt.add_playlist_items(playlist_id, video_ids)

    def remove_tracks_from_playlist(self, playlist_id: str, track_urls: List[str]):
        """Retire des titres d'une playlist"""
        playlist = self.yt.get_playlist(playlist_id)
        video_ids_to_remove = [self._extract_id(u, "watch?v=") for u in track_urls]
        
        items_to_remove = [
            item for item in playlist['tracks'] 
            if item['videoId'] in video_ids_to_remove
        ]
        
        if items_to_remove:
            self.yt.remove_playlist_items(playlist_id, items_to_remove)

    def supports_url(self, url: str) -> bool:
        """Vérifie si l'URL est de type music.youtube.com"""
        return bool(re.search(r"music\.youtube\.com", url))

    def get_track_info(self, url: str) -> ProviderTrackMetadata:
        """Extrait les métadonnées d'un titre YT Music via son ID"""
        video_id = self._extract_id(url, "watch?v=")
        track = self.yt.get_song(video_id)
        details = track.get('videoDetails', {})
        
        isrc = None
        try:
            microformat = track.get('microformat', {}).get('microformatDataRenderer', {})
            isrc = track.get('isrc')
        except:
            pass

        return ProviderTrackMetadata(
            title=details.get('title'),
            artist=details.get('author'),
            album=None,
            cover_url=details.get('thumbnail', {}).get('thumbnails', [{}])[-1].get('url'),
            duration_ms=int(details.get('lengthSeconds', 0)) * 1000,
            isrc=isrc,
            provider="youtube_music",
            original_url=url
        )

    def get_playlist_tracks(self, url: str) -> List[ProviderTrackMetadata]:
        """Extrait la liste des titres d'une playlist YT Music"""
        playlist_id = self._extract_id(url, "list=")
        data = self.yt.get_playlist(playlist_id)
        tracks = []
        for item in data.get('tracks', []):
            tracks.append(ProviderTrackMetadata(
                title=item['title'],
                artist=", ".join([a['name'] for a in item['artists']]),
                album=item.get('album', {}).get('name'),
                cover_url=item.get('thumbnails', [{}])[-1].get('url'),
                duration_ms=int(item.get('duration_seconds', 0)) * 1000,
                provider="youtube_music",
                original_url=f"https://music.youtube.com/watch?v={item['videoId']}"
            ))
        return tracks

    def get_user_playlists(self) -> List[dict]:
        """Récupère les playlists de l'utilisateur connecté sur YouTube Music"""
        if not self.auth_token:
            return []
            
        try:
            playlists = self.yt.get_library_playlists(limit=50)
            return [
                {
                    'id': p['playlistId'],
                    'name': p['title'],
                    'track_count': p.get('count', 0),
                    'provider': 'youtube_music'
                }
                for p in playlists
            ]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des playlists YT Music: {e}")
            return []

    def _extract_id(self, url: str, marker: str) -> str:
        """Extrait l'ID de la vidéo ou de la playlist"""
        if marker in url:
            return url.split(marker)[1].split("&")[0]
        raise ValueError(f"URL YouTube Music invalide : {url}")
