from .base import MusicProvider, TrackMetadata
import re
from ytmusicapi import YTMusic
from typing import List

class YTMusicProvider(MusicProvider):
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
            self._yt = YTMusic(auth=self.auth_token) if self.auth_token else YTMusic()
        return self._yt

    def create_playlist(self, name: str, description: str = "", public: bool = False) -> str:
        """Crée une nouvelle playlist sur YouTube Music"""
        privacy_status = "PUBLIC" if public else "PRIVATE"
        playlist_id = self.yt.create_playlist(name, description, privacy_status=privacy_status)
        return playlist_id

    def delete_playlist(self, playlist_id: str):
        """Supprime une playlist sur YouTube Music"""
        self.yt.delete_playlist(playlist_id)

    def add_tracks_to_playlist(self, playlist_id: str, track_urls: List[str]):
        """Ajoute des titres via leurs IDs de vidéo YouTube"""
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
        # YTMusicAPI nécessite les setVideoIds (IDs internes à la playlist) pour supprimer, 
        # ou l'on peut supprimer via videoIds si on récupère la playlist d'abord.
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
        return bool(re.search(r"music\.youtube\.com/(watch\?v=|playlist\?list=)", url))

    def get_track_info(self, url: str) -> TrackMetadata:
        """Extrait les métadonnées d'un titre YT Music via son ID"""
        video_id = self._extract_id(url, "watch?v=")
        track = self.yt.get_song(video_id)
        details = track.get('videoDetails', {})
        
        return TrackMetadata(
            title=details.get('title'),
            artist=details.get('author'),
            album=None,
            cover_url=details.get('thumbnail', {}).get('thumbnails', [{}])[-1].get('url'),
            duration_ms=int(details.get('lengthSeconds', 0)) * 1000,
            provider="youtube_music",
            original_url=url
        )

    def get_playlist_tracks(self, url: str) -> List[TrackMetadata]:
        """Extrait la liste des titres d'une playlist YT Music"""
        playlist_id = self._extract_id(url, "list=")
        data = self.yt.get_playlist(playlist_id)
        tracks = []
        for item in data.get('tracks', []):
            tracks.append(TrackMetadata(
                title=item['title'],
                artist=", ".join([a['name'] for a in item['artists']]),
                album=item.get('album', {}).get('name'),
                cover_url=item.get('thumbnails', [{}])[-1].get('url'),
                duration_ms=int(item.get('duration_seconds', 0)) * 1000,
                provider="youtube_music",
                original_url=f"https://music.youtube.com/watch?v={item['videoId']}"
            ))
        return tracks

    def _extract_id(self, url: str, marker: str) -> str:
        """Extrait l'ID de la vidéo ou de la playlist"""
        if marker in url:
            return url.split(marker)[1].split("&")[0]
        raise ValueError(f"URL YouTube Music invalide : {url}")
