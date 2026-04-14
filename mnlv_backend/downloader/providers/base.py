from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class TrackMetadata:
    title: str
    artist: str
    album: Optional[str] = None
    release_year: Optional[int] = None
    cover_url: Optional[str] = None
    duration_ms: Optional[int] = None
    isrc: Optional[str] = None
    provider: Optional[str] = None
    original_url: Optional[str] = None

class MusicProvider(ABC):
    @abstractmethod
    def get_track_info(self, url: str) -> TrackMetadata:
        """Extrait titre, artiste, album, ISRC, cover_url depuis l'URL fournie (track)"""
        pass

    @abstractmethod
    def get_playlist_tracks(self, url: str) -> List[TrackMetadata]:
        """Extrait la liste des tracks d'une playlist/album"""
        pass

    @abstractmethod
    def supports_url(self, url: str) -> bool:
        """Retourne True si l'URL appartient à ce provider"""
        pass

    def create_playlist(self, name: str, description: str = "", public: bool = False) -> str:
        """Crée une nouvelle playlist (Nécessite user_token)"""
        raise NotImplementedError("Ce provider ne supporte pas la création de playlists.")

    def delete_playlist(self, playlist_id: str):
        """Supprime une playlist (Nécessite user_token)"""
        raise NotImplementedError("Ce provider ne supporte pas la suppression de playlists.")

    def add_tracks_to_playlist(self, playlist_id: str, track_urls: List[str]):
        """Ajoute une liste de titres à une playlist (Nécessite user_token)"""
        raise NotImplementedError("Ce provider ne supporte pas l'ajout de titres.")

    def remove_tracks_from_playlist(self, playlist_id: str, track_urls: List[str]):
        """Retire une liste de titres d'une playlist (Nécessite user_token)"""
        raise NotImplementedError("Ce provider ne supporte pas la suppression de titres.")

    def get_user_playlists(self) -> List[dict]:
        """Récupère la liste des playlists de l'utilisateur (Nécessite auth_token)"""
        raise NotImplementedError("Ce provider ne supporte pas la récupération des playlists.")

    def get_playlist_details(self, url: str) -> dict:
        """Récupère les détails et statistiques d'une playlist (titre, nb titres, durée totale, etc.)"""
        raise NotImplementedError("Ce provider ne supporte pas la récupération des détails de playlist.")
