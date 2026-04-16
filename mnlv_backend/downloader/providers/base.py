from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Optional, List
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

@dataclass
class TrackMetadata:
    title: str
    artist: str
    album: Optional[str] = None
    release_year: Optional[int] = None
    cover_url: Optional[str] = None
    duration_ms: Optional[int] = None
    isrc: Optional[str] = None
    ean: Optional[str] = None
    upc: Optional[str] = None
    explicit: bool = False
    is_episode: bool = False
    is_video: bool = False
    provider: Optional[str] = None
    original_url: Optional[str] = None

class MusicProvider(ABC):
    def get_track_info_cached(self, url: str) -> TrackMetadata:
        """
        Version avec cache de get_track_info.
        Évite de solliciter inutilement les APIs externes pour les mêmes URLs.
        """
        cache_key = f"metadata:{url}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.debug(f"Cache HIT pour {url}")
            return TrackMetadata(**cached_data)
        
        logger.debug(f"Cache MISS pour {url}")
        metadata = self.get_track_info(url)
        
        # On met en cache pendant 24 heures
        cache.set(cache_key, asdict(metadata), timeout=86400)
        return metadata

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

    def add_tracks_to_playlist(self, playlist_id: str, track_urls: List[str], position: Optional[int] = None) -> Optional[str]:
        """Ajoute une liste de titres à une playlist (Nécessite user_token)"""
        raise NotImplementedError("Ce provider ne supporte pas l'ajout de titres.")

    def remove_tracks_from_playlist(self, playlist_id: str, track_urls: List[str], snapshot_id: Optional[str] = None) -> Optional[str]:
        """Retire une liste de titres d'une playlist (Nécessite user_token)"""
        raise NotImplementedError("Ce provider ne supporte pas la suppression de titres.")

    def reorder_playlist_tracks(self, playlist_id: str, range_start: int, insert_before: int, range_length: int = 1, snapshot_id: Optional[str] = None) -> Optional[str]:
        """Réorganise les titres d'une playlist (Nécessite user_token)"""
        raise NotImplementedError("Ce provider ne supporte pas la réorganisation des titres.")

    def get_user_playlists(self) -> List[dict]:
        """Récupère la liste des playlists de l'utilisateur (Nécessite auth_token)"""
        raise NotImplementedError("Ce provider ne supporte pas la récupération des playlists.")

    def get_playlist_details(self, url: str) -> dict:
        """Récupère les détails et statistiques d'une playlist (titre, nb titres, durée totale, etc.)"""
        raise NotImplementedError("Ce provider ne supporte pas la récupération des détails de playlist.")
