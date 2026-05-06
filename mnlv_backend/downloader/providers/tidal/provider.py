from ..base import MusicProvider, ProviderTrackMetadata, ProviderAuthError, ProviderAPIError, ProviderResourceNotFoundError, ProviderError, monitor_provider, monitor_provider_async
import re
try:
    import tidalapi
except ImportError:
    tidalapi = None
from django.conf import settings
from typing import List, Optional
from asgiref.sync import sync_to_async

class TidalProvider(MusicProvider):
    """
    Adapteur pour Tidal utilisant tidalapi.
    Supporte l'exécution asynchrone via thread pooling.
    """
    def __init__(self, auth_token: str = None, refresh_token: str = None, user_id: str = None):
        """
        Initialise le provider Tidal.
        auth_token est requis pour les opérations d'écriture.
        """
        self._session = None
        self._user_obj = None  # Stockage local de l'objet User pour bypasser session.user
        self.auth_token = auth_token
        self.refresh_token = refresh_token
        self.user_id = user_id

    @property
    def session(self):
        if self._session is None:
            if tidalapi is None:
                raise ProviderAPIError("La bibliothèque 'tidalapi' n'est pas installée sur le serveur.", code="TIDAL_MISSING_LIB")
            
            import logging
            logger = logging.getLogger(__name__)

            config = tidalapi.Config()
            if settings.TIDAL_CLIENT_ID and "votre_client" not in settings.TIDAL_CLIENT_ID:
                config.client_id = settings.TIDAL_CLIENT_ID
            if settings.TIDAL_CLIENT_SECRET and "votre_secret" not in settings.TIDAL_CLIENT_SECRET:
                config.client_secret = settings.TIDAL_CLIENT_SECRET
            
            self._session = tidalapi.Session(config=config)
            
            if self.auth_token and "votre_token" not in self.auth_token:
                try:
                    masked_token = f"{self.auth_token[:6]}...{self.auth_token[-4:]}" if len(self.auth_token) > 10 else "***"
                    logger.debug(f"Initialisation manuelle session Tidal (Bypass /sessions) : token={masked_token}, user_id={self.user_id}")
                    
                    self._session.access_token = self.auth_token
                    self._session.refresh_token = self.refresh_token
                    self._session.token_type = settings.TIDAL_TOKEN_TYPE or 'Bearer'
                    
                    self._session.check_login = lambda: True
                    
                    if self.user_id:
                        try:
                            from tidalapi.user import User
                            uid = int(self.user_id) if str(self.user_id).isdigit() else self.user_id
                            self._session.user_id = uid
                            
                            # Injection et stockage local de l'objet User
                            logger.debug(f"Injection manuelle de l'objet User pour ID {uid}")
                            self._user_obj = User(self._session, uid)
                            self._session._user = self._user_obj
                            
                        except Exception as e_user:
                            logger.warning(f"Impossible d'instancier l'objet User manuellement : {e_user}")
                    
                    logger.info(f"Session Tidal initialisée avec succès (Mode Direct Bypass 403) pour {self.user_id}")
                        
                except Exception as e:
                    raise ProviderAuthError(f"Échec initialisation session Tidal : {str(e)}", code="TIDAL_AUTH_ERROR")
            
            else:
                global_access = settings.TIDAL_ACCESS_TOKEN
                global_refresh = settings.TIDAL_REFRESH_TOKEN
                
                if global_access and "votre_token" not in global_access:
                    try:
                        logger.debug("Tentative de fallback sur le token Tidal global (settings)")
                        self._session.load_oauth_session(
                            token_type=settings.TIDAL_TOKEN_TYPE or 'Bearer',
                            access_token=global_access,
                            refresh_token=global_refresh if global_refresh and "votre_token" not in global_refresh else None
                        )
                    except Exception as e:
                        logger.error(f"Erreur lors du chargement du token Tidal global : {e}")
                    
        return self._session

    def _get_user(self):
        """Récupère l'utilisateur Tidal de manière robuste"""
        if self._user_obj:
            return self._user_obj
            
        s = self.session
        user = getattr(s, '_user', None)
        if user:
            return user
            
        try:
            return s.user
        except Exception:
            return None

    @monitor_provider_async
    async def get_track_info_async(self, url: str) -> ProviderTrackMetadata:
        """Version asynchrone de get_track_info pour Tidal"""
        try:
            track_id = self._extract_id(url, "track")
            track = await sync_to_async(self.session.track)(track_id)
            if not track:
                raise ProviderResourceNotFoundError(f"Titre Tidal {track_id} introuvable", code="TIDAL_NOT_FOUND")
            return self._map_track(track)
        except Exception as e:
            if isinstance(e, ProviderError): raise
            raise ProviderAPIError(f"Erreur Tidal get_track_info : {str(e)}", code="TIDAL_API_ERROR")

    @monitor_provider_async
    async def get_playlist_tracks_async(self, url: str) -> List[ProviderTrackMetadata]:
        """Version asynchrone de get_playlist_tracks pour Tidal"""
        tracks = []
        try:
            if "/playlist/" in url:
                playlist_id = self._extract_id(url, "playlist")
                playlist = await sync_to_async(self.session.playlist)(playlist_id)
                tidal_tracks = await sync_to_async(playlist.tracks)()
                for track in tidal_tracks:
                    tracks.append(self._map_track(track))
            
            elif "/album/" in url:
                album_id = self._extract_id(url, "album")
                album = await sync_to_async(self.session.album)(album_id)
                tidal_tracks = await sync_to_async(album.tracks)()
                for track in tidal_tracks:
                    tracks.append(self._map_track(track))
                    
            return tracks
        except Exception as e:
            raise ProviderAPIError(f"Erreur Tidal get_playlist_tracks : {str(e)}", code="TIDAL_API_ERROR")

    @monitor_provider
    def create_playlist(self, name: str, description: str = "", public: bool = False) -> str:
        """Crée une nouvelle playlist sur Tidal"""
        user = self._get_user()
        if not user:
            raise ProviderAuthError("La session Tidal n'est pas authentifiée ou utilisateur introuvable.", code="TIDAL_AUTH_REQUIRED")
            
        try:
            playlist = user.create_playlist(name, description)
            return playlist.id
        except Exception as e:
            if "401" in str(e) or "403" in str(e):
                raise ProviderAuthError("Session Tidal expirée ou accès refusé.", code="TIDAL_AUTH_ERROR")
            raise ProviderAPIError(f"Erreur création playlist Tidal : {str(e)}", code="TIDAL_API_ERROR")

    def delete_playlist(self, playlist_id: str):
        """Supprime une playlist sur Tidal (unfollow)"""
        user = self._get_user()
        if not user:
            raise ValueError("La session Tidal n'est pas authentifiée.")
            
        try:
            playlist = self.session.playlist(playlist_id)
            playlist.delete()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Erreur lors de la suppression de la playlist Tidal: {e}")
            if "401" in str(e) or "403" in str(e):
                raise ValueError("Votre session Tidal est invalide ou a expiré. Veuillez vous reconnecter.")
            raise

    def add_tracks_to_playlist(self, playlist_id: str, track_urls: List[str], position: Optional[int] = None) -> Optional[str]:
        """Ajoute des titres via leurs IDs Tidal avec découpage par lots (max 50)"""
        user = self._get_user()
        if not user:
            raise ValueError("La session Tidal n'est pas authentifiée.")
            
        try:
            playlist = self.session.playlist(playlist_id)
            track_ids = [self._extract_id(u, "track") for u in track_urls]
            
            chunk_size = 50
            for i in range(0, len(track_ids), chunk_size):
                chunk = track_ids[i:i + chunk_size]
                playlist.add(chunk)
                
            return None
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Erreur lors de l'ajout de titres Tidal: {e}")
            if "401" in str(e) or "403" in str(e):
                raise ValueError("Votre session Tidal est invalide ou a expiré. Veuillez vous reconnecter.")
            raise

    def remove_tracks_from_playlist(self, playlist_id: str, track_urls: List[str], snapshot_id: Optional[str] = None) -> Optional[str]:
        """Retire des titres d'une playlist Tidal"""
        user = self._get_user()
        if not user:
            raise ValueError("La session Tidal a expiré ou n'est pas authentifiée.")
            
        playlist = self.session.playlist(playlist_id)
        track_ids = [self._extract_id(u, "track") for u in track_urls]
        for t_id in track_ids:
            playlist.remove(t_id)
        return None

    def supports_url(self, url: str) -> bool:
        """Vérifie si l'URL est de type tidal.com"""
        return bool(re.search(r"tidal\.com", url))

    @monitor_provider
    def get_track_info(self, url: str) -> ProviderTrackMetadata:
        """Extrait les métadonnées d'un titre Tidal"""
        try:
            track_id = self._extract_id(url, "track")
            track = self.session.track(track_id)
            if not track:
                raise ProviderResourceNotFoundError(f"Titre Tidal {track_id} introuvable", code="TIDAL_NOT_FOUND")
            return self._map_track(track)
        except Exception as e:
            if isinstance(e, ProviderError): raise
            raise ProviderAPIError(f"Erreur Tidal get_track_info : {str(e)}", code="TIDAL_API_ERROR")

    @monitor_provider
    def get_playlist_tracks(self, url: str) -> List[ProviderTrackMetadata]:
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

    def get_user_playlists(self) -> List[dict]:
        """Récupère les playlists de l'utilisateur connecté sur Tidal"""
        user = self._get_user()
        if not user:
            import logging
            logging.getLogger(__name__).warning(f"Tentative de récupération des playlists Tidal sans utilisateur connecté. UserID: {self.user_id}")
            return []
            
        try:
            playlists = user.playlists()
            return [
                {
                    'id': p.id,
                    'name': p.name,
                    'track_count': getattr(p, 'num_tracks', 0),
                    'provider': 'tidal'
                }
                for p in playlists
            ]
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Erreur lors de la récupération des playlists Tidal: {e}")
            if "401" in str(e) or "403" in str(e):
                raise ValueError("Votre session Tidal est invalide ou a expiré. Veuillez vous reconnecter.")
            return []

    def _extract_id(self, url: str, type_name: str) -> str:
        """Extrait l'ID de l'URL Tidal ou retourne l'ID s'il est déjà au format numérique"""
        url = str(url).strip()
        if url.isdigit():
            return url
            
        match = re.search(rf"{type_name}/(\d+)", url)
        if match:
            return match.group(1)
        raise ValueError(f"ID Tidal introuvable ou format invalide : {url}")

    def _map_track(self, track) -> ProviderTrackMetadata:
        """Mappe un objet tidalapi.Track vers TrackMetadata"""
        return ProviderTrackMetadata(
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