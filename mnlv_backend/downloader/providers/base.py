from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Optional, List, Any, Callable
from django.core.cache import cache
from asgiref.sync import sync_to_async
import logging
import time
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)

# --- Exceptions ---

class ProviderError(Exception):
    """Base exception for all provider-related errors."""
    def __init__(self, message: str, code: Optional[str] = None):
        super().__init__(message)
        self.code = code

class ProviderAuthError(ProviderError):
    """Raised when authentication fails or token is expired."""
    def __init__(self, message: str = "Erreur d'authentification provider", code: str = "AUTH_ERROR"):
        super().__init__(message, code)

class ProviderRateLimitError(ProviderError):
    """Raised when the provider API rate limit is reached."""
    def __init__(self, message: str = "Limite de requêtes atteinte", code: str = "RATE_LIMIT"):
        super().__init__(message, code)

class ProviderResourceNotFoundError(ProviderError):
    """Raised when a track, playlist, or album is not found."""
    def __init__(self, message: str = "Ressource introuvable", code: str = "NOT_FOUND"):
        super().__init__(message, code)

class ProviderAPIError(ProviderError):
    """Raised when the provider API returns an unexpected error."""
    def __init__(self, message: str = "Erreur API provider", code: str = "API_ERROR"):
        super().__init__(message, code)

# --- Decorators ---

def monitor_provider(method):
    """Décorateur pour mesurer les performances et logger les succès/échecs (Sync)."""
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        start_time = time.time()
        provider_name = self.__class__.__name__
        method_name = method.__name__
        try:
            result = method(self, *args, **kwargs)
            duration = (time.time() - start_time) * 1000
            logger.debug(f"[{provider_name}] {method_name} (Sync) réussi en {duration:.2f}ms")
            return result
        except ProviderError as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[{provider_name}] {method_name} échoué ({e.code}) en {duration:.2f}ms : {str(e)}")
            raise
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.exception(f"[{provider_name}] {method_name} erreur inattendue en {duration:.2f}ms : {str(e)}")
            raise ProviderAPIError(f"Erreur interne dans le provider {provider_name}: {str(e)}", code="INTERNAL_ERROR")
    return wrapper

def monitor_provider_async(method):
    """Décorateur pour mesurer les performances et logger les succès/échecs (Async)."""
    @wraps(method)
    async def wrapper(self, *args, **kwargs):
        start_time = time.time()
        provider_name = self.__class__.__name__
        method_name = method.__name__
        try:
            result = await method(self, *args, **kwargs)
            duration = (time.time() - start_time) * 1000
            logger.debug(f"[{provider_name}] {method_name} (Async) réussi en {duration:.2f}ms")
            return result
        except ProviderError as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[{provider_name}] {method_name} échoué ({e.code}) en {duration:.2f}ms : {str(e)}")
            raise
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.exception(f"[{provider_name}] {method_name} erreur inattendue en {duration:.2f}ms : {str(e)}")
            raise ProviderAPIError(f"Erreur interne dans le provider {provider_name}: {str(e)}", code="INTERNAL_ERROR")
    return wrapper

# --- Models ---

@dataclass
class ProviderTrackMetadata:
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

    def __post_init__(self):
        """Nettoyage et validation automatique après instanciation."""
        self.title = self._clean_string(self.title) or "Titre inconnu"
        self.artist = self._clean_string(self.artist) or "Artiste inconnu"
        self.album = self._clean_string(self.album)
        
        # Validation de l'année
        if self.release_year:
            try:
                year = int(self.release_year)
                if year < 1900 or year > 2100:
                    self.release_year = None
                else:
                    self.release_year = year
            except (ValueError, TypeError):
                self.release_year = None

    def _clean_string(self, s: Optional[str]) -> Optional[str]:
        if s is None:
            return None
        s = str(s).strip()
        return s if s else None

class MusicProvider(ABC):
    def paginate_items(self, fetch_func: Callable, limit: int = 100, max_items: Optional[int] = None):
        """
        Helper universel pour la pagination des ressources (playlists, albums) - Version Sync.
        """
        all_items = []
        offset = 0
        
        while True:
            batch, total = fetch_func(offset, limit)
            all_items.extend(batch)
            
            if max_items and len(all_items) >= max_items:
                all_items = all_items[:max_items]
                break
                
            if len(all_items) >= total or not batch or len(batch) < limit:
                break
                
            offset += limit
            
        return all_items

    async def paginate_items_async(self, fetch_func: Callable, limit: int = 100, max_items: Optional[int] = None):
        """
        Helper universel pour la pagination des ressources (playlists, albums) - Version Async.
        """
        all_items = []
        offset = 0
        
        while True:
            batch, total = await fetch_func(offset, limit)
            all_items.extend(batch)
            
            if max_items and len(all_items) >= max_items:
                all_items = all_items[:max_items]
                break
                
            if len(all_items) >= total or not batch or len(batch) < limit:
                break
                
            offset += limit
            
        return all_items

    @monitor_provider
    def get_track_info_cached(self, url: str) -> ProviderTrackMetadata:
        """Version avec cache de get_track_info (Sync)."""
        cache_key = f"metadata:{url}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.debug(f"Cache HIT pour {url}")
            return ProviderTrackMetadata(**cached_data)
        
        logger.debug(f"Cache MISS pour {url}")
        metadata = self.get_track_info(url)
        
        cache.set(cache_key, asdict(metadata), timeout=86400)
        return metadata

    @monitor_provider_async
    async def get_track_info_cached_async(self, url: str) -> ProviderTrackMetadata:
        """Version avec cache de get_track_info (Async)."""
        cache_key = f"metadata:{url}"
        cached_data = await sync_to_async(cache.get)(cache_key)
        
        if cached_data:
            logger.debug(f"Cache HIT (Async) pour {url}")
            return ProviderTrackMetadata(**cached_data)
        
        logger.debug(f"Cache MISS (Async) pour {url}")
        metadata = await self.get_track_info_async(url)
        
        await sync_to_async(cache.set)(cache_key, asdict(metadata), timeout=86400)
        return metadata

    @abstractmethod
    def get_track_info(self, url: str) -> ProviderTrackMetadata:
        pass

    async def get_track_info_async(self, url: str) -> ProviderTrackMetadata:
        """Fallback par défaut : exécute la version sync dans un thread."""
        return await sync_to_async(self.get_track_info)(url)

    @abstractmethod
    def get_playlist_tracks(self, url: str) -> List[ProviderTrackMetadata]:
        pass

    async def get_playlist_tracks_async(self, url: str) -> List[ProviderTrackMetadata]:
        """Fallback par défaut : exécute la version sync dans un thread."""
        return await sync_to_async(self.get_playlist_tracks)(url)

    @abstractmethod
    def supports_url(self, url: str) -> bool:
        pass

    def create_playlist(self, name: str, description: str = "", public: bool = False) -> str:
        raise NotImplementedError()

    async def create_playlist_async(self, name: str, description: str = "", public: bool = False) -> str:
        return await sync_to_async(self.create_playlist)(name, description, public)

    def delete_playlist(self, playlist_id: str):
        raise NotImplementedError()

    async def delete_playlist_async(self, playlist_id: str):
        return await sync_to_async(self.delete_playlist)(playlist_id)

    def add_tracks_to_playlist(self, playlist_id: str, track_urls: List[str], position: Optional[int] = None) -> Optional[str]:
        raise NotImplementedError()

    async def add_tracks_to_playlist_async(self, playlist_id: str, track_urls: List[str], position: Optional[int] = None) -> Optional[str]:
        return await sync_to_async(self.add_tracks_to_playlist)(playlist_id, track_urls, position)

    def get_user_playlists(self) -> List[dict]:
        raise NotImplementedError()

    async def get_user_playlists_async(self) -> List[dict]:
        return await sync_to_async(self.get_user_playlists)()

    def get_playlist_details(self, url: str) -> dict:
        raise NotImplementedError()

    async def get_playlist_details_async(self, url: str) -> dict:
        return await sync_to_async(self.get_playlist_details)(url)
