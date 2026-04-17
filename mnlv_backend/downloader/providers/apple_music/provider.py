from ..base import MusicProvider, TrackMetadata
import re
import requests
import logging
try:
    from applemusicpy import AppleMusic
except ImportError:
    AppleMusic = None
from django.conf import settings
from typing import List, Optional

logger = logging.getLogger(__name__)

class AppleMusicProvider(MusicProvider):
    """
    Adapteur pour Apple Music utilisant applemusicpy et des appels directs à l'API.
    Nécessite APPLE_MUSIC_KEY_ID, APPLE_MUSIC_TEAM_ID, APPLE_MUSIC_SECRET_KEY.
    """
    def __init__(self, auth_token: Optional[str] = None):
        self._am = None
        self.auth_token = auth_token
        self.base_url = settings.APPLE_MUSIC_API_BASE

    @property
    def am(self):
        if self._am is None:
            if not AppleMusic:
                raise ImportError("applemusicpy n'est pas installé.")
            
            secret_key = settings.APPLE_MUSIC_SECRET_KEY
            if secret_key and isinstance(secret_key, str):
                if "\\n" in secret_key:
                    secret_key = secret_key.replace("\\n", "\n")
                if "-----BEGIN PRIVATE KEY-----" not in secret_key:
                    secret_key = f"-----BEGIN PRIVATE KEY-----\n{secret_key}\n-----END PRIVATE KEY-----"
            
            self._am = AppleMusic(
                secret_key=secret_key,
                key_id=settings.APPLE_MUSIC_KEY_ID,
                team_id=settings.APPLE_MUSIC_TEAM_ID
            )
        return self._am

    def _get_headers(self) -> dict:
        """Génère les headers pour les requêtes directes à l'API Apple Music"""
        headers = {
            "Authorization": f"Bearer {self.am.token}",
            "Content-Type": "application/json"
        }
        if self.auth_token:
            headers["Music-User-Token"] = self.auth_token
        return headers

    def _handle_api_error(self, e: Exception):
        """Gère les erreurs API Apple Music de manière détaillée"""
        if isinstance(e, requests.exceptions.HTTPError):
            status_code = e.response.status_code
            try:
                error_data = e.response.json()
                error_msg = error_data.get('errors', [{}])[0].get('detail', str(e))
            except:
                error_msg = str(e)

            if status_code == 401:
                raise ValueError(f"Session Apple Music expirée ou invalide (401). Veuillez vous reconnecter. Détail: {error_msg}")
            elif status_code == 403:
                raise ValueError(f"Accès refusé par Apple Music (403). Vérifiez vos abonnements ou restrictions. Détail: {error_msg}")
            elif status_code == 404:
                raise ValueError(f"Contenu introuvable sur Apple Music (404). Il a peut-être été supprimé ou n'est pas disponible dans votre région. Détail: {error_msg}")
            else:
                raise ValueError(f"Erreur Apple Music ({status_code}): {error_msg}")
        
        logger.error(f"Erreur Apple Music non gérée: {str(e)}")
        raise ValueError(f"Erreur de communication avec Apple Music : {str(e)}")

    def supports_url(self, url: str) -> bool:
        """Vérifie si l'URL est de type music.apple.com"""
        return bool(re.search(r"music\.apple\.com/.*?/(album|song|playlist)/", url))
    def get_track_info(self, url: str) -> TrackMetadata:
        """Extrait les métadonnées d'un titre ou d'un clip Apple Music avec 'extend' pour plus de détails"""
        try:
            track_id = self._extract_id(url)
            storefront = self._extract_storefront(url)
            
            resource_type = "music-videos" if "/music-video/" in url else "songs"
            
            params = {"extend": "editorialVideo,trackCount,bornOn,isrc"}
            response = requests.get(
                f"{self.base_url}/catalog/{storefront}/{resource_type}/{track_id}", 
                headers=self._get_headers(),
                params=params
            )
            response.raise_for_status()
            results = response.json()

            if not results.get('data'):
                raise ValueError(f"Aucune donnée trouvée pour l'ID : {track_id}")
                
            track = results['data'][0]
            attrs = track['attributes']
            
            return self._map_track(attrs, url, is_video=(resource_type == "music-videos"))
        except Exception as e:
            self._handle_api_error(e)

    def get_playlist_tracks(self, url: str) -> List[TrackMetadata]:
        """Extrait la liste des titres et clips d'une playlist ou d'un album avec pagination optimisée (limit=100)"""
        tracks = []
        item_id = self._extract_id(url)
        storefront = self._extract_storefront(url)
        
        try:
            resource_type = "albums" if "/album/" in url else "playlists"
            params = {
                "include": "tracks",
                "limit[tracks]": 100,
                "extend": "trackCount,isrc"
            }
            
            response = requests.get(
                f"{self.base_url}/catalog/{storefront}/{resource_type}/{item_id}",
                headers=self._get_headers(),
                params=params
            )
            response.raise_for_status()
            results = response.json()
            
            if not results.get('data'):
                return []

            resource_data = results['data'][0]
            current_data = resource_data.get('relationships', {}).get('tracks', {})
            
            while current_data:
                for item in current_data.get('data', []):
                    is_video = item.get('type') == 'music-videos' or item.get('type') == 'library-music-videos'
                    tracks.append(self._map_track(item['attributes'], item['attributes'].get('url', ''), is_video=is_video))
                
                next_url = current_data.get('next')
                if next_url:
                    full_next_url = next_url if next_url.startswith('http') else f"{self.base_url}{next_url}"
                    if "limit=" not in full_next_url:
                        sep = "&" if "?" in full_next_url else "?"
                        full_next_url += f"{sep}limit=100"
                        
                    response = requests.get(full_next_url, headers=self._get_headers())
                    response.raise_for_status()
                    current_data = response.json()
                else:
                    current_data = None
                        
        except Exception as e:
            self._handle_api_error(e)
            
        return tracks

    def get_user_playlists(self) -> List[dict]:
        """Récupère toutes les playlists de la bibliothèque de l'utilisateur avec pagination optimisée (limit=100)"""
        if not self.auth_token:
            raise ValueError("Music-User-Token requis pour accéder à la bibliothèque.")

        playlists = []
        url = f"{self.base_url}/me/library/playlists"
        params = {"limit": 100}
        
        try:
            while url:
                response = requests.get(url, headers=self._get_headers(), params=params)
                response.raise_for_status()
                data = response.json()
                
                for item in data.get('data', []):
                    attrs = item['attributes']
                    artwork = attrs.get('artwork', {})
                    cover_url = artwork.get('url', '').replace('{w}', '300').replace('{h}', '300') if artwork else None
                    
                    # Détection si la playlist contient des vidéos via 'trackTypes' (attribut étendu)
                    track_types = attrs.get('trackTypes', [])
                    has_videos = 'library-music-videos' in track_types or 'music-videos' in track_types
                    
                    playlists.append({
                        'id': item['id'],
                        'name': attrs['name'],
                        'track_count': attrs.get('trackCount'),
                        'owner': "Moi",
                        'url': f"https://music.apple.com/library/playlist/{item['id']}",
                        'cover_url': cover_url,
                        'provider': 'apple_music',
                        'has_videos': has_videos
                    })
                
                next_page = data.get('next')
                if next_page:
                    url = f"{self.base_url}{next_page}" if not next_page.startswith('http') else next_page
                    params = {}
                else:
                    url = None
                
        except Exception as e:
            self._handle_api_error(e)
            
        return playlists

    def get_tracks_by_ids(self, ids: List[str], storefront: str = "us") -> List[TrackMetadata]:
        """Récupère plusieurs titres ou clips en une seule requête (Batch Request) - Max 25 IDs"""
        if not ids:
            return []
        
        batch_ids = ids[:25]
        url = f"{self.base_url}/catalog/{storefront}/songs" # Par défaut on cherche des songs
        params = {"ids": ",".join(batch_ids), "extend": "isrc"}
        
        try:
            response = requests.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            data = response.json()
            
            return [self._map_track(item['attributes'], item['attributes'].get('url', ''), is_video=False) for item in data.get('data', [])]
        except Exception as e:
            self._handle_api_error(e)
            return []

    def search(self, query: str, types: List[str] = None, storefront: str = "us", limit: int = 20) -> dict:
        """
        Recherche dans le catalogue Apple Music.
        Types possibles : songs, albums, playlists, music-videos, artists
        """
        if not query:
            return {}

        search_types = ",".join(types) if types else "songs,albums,playlists,music-videos"
        url = f"{self.base_url}/catalog/{storefront}/search"
        params = {
            "term": query.replace(" ", "+"),
            "types": search_types,
            "limit": limit,
            "extend": "trackCount,isrc"
        }

        try:
            response = requests.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            results = response.json().get('results', {})
            
            formatted_results = {}
            for res_type, data in results.items():
                formatted_results[res_type] = []
                for item in data.get('data', []):
                    attrs = item['attributes']
                    is_video = item.get('type') == 'music-videos'
                    
                    if item['type'] in ['songs', 'music-videos']:
                        formatted_results[res_type].append(self._map_track(attrs, attrs.get('url', ''), is_video=is_video).__dict__)
                    else:
                        artwork = attrs.get('artwork', {})
                        cover_url = artwork.get('url', '').replace('{w}', '300').replace('{h}', '300') if artwork else None
                        formatted_results[res_type].append({
                            "id": item['id'],
                            "type": item['type'],
                            "title": attrs.get('name'),
                            "artist": attrs.get('artistName', attrs.get('curatorName')),
                            "url": attrs.get('url'),
                            "cover_url": cover_url,
                            "track_count": attrs.get('trackCount')
                        })
            
            return formatted_results
        except Exception as e:
            self._handle_api_error(e)
            return {}

    def search_library(self, query: str, types: List[str] = None, limit: int = 20) -> dict:
        """
        Recherche dans la bibliothèque personnelle de l'utilisateur.
        Nécessite Music-User-Token.
        """
        if not self.auth_token or not query:
            return {}

        search_types = ",".join(types) if types else "library-songs,library-albums,library-playlists"
        url = f"{self.base_url}/me/library/search"
        params = {
            "term": query.replace(" ", "+"),
            "types": search_types,
            "limit": limit
        }

        try:
            response = requests.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            results = response.json().get('results', {})
            
            formatted_results = {}
            for res_type, data in results.items():
                formatted_results[res_type] = []
                for item in data.get('data', []):
                    attrs = item['attributes']
                    artwork = attrs.get('artwork', {})
                    cover_url = artwork.get('url', '').replace('{w}', '300').replace('{h}', '300') if artwork else None
                    
                    formatted_results[res_type].append({
                        "id": item['id'],
                        "type": item['type'],
                        "title": attrs.get('name'),
                        "artist": attrs.get('artistName'),
                        "url": f"https://music.apple.com/library/{item['type'].replace('library-', '')}/{item['id']}",
                        "cover_url": cover_url,
                        "track_count": attrs.get('trackCount')
                    })
            
            return formatted_results
        except Exception as e:
            self._handle_api_error(e)
            return {}

    def create_playlist(self, name: str, description: str = "", public: bool = False) -> str:
        """Crée une nouvelle playlist dans la bibliothèque (Nécessite Music-User-Token)"""
        if not self.auth_token:
            raise ValueError("Music-User-Token requis pour créer une playlist.")

        url = f"{self.base_url}/me/library/playlists"
        payload = {
            "attributes": {
                "name": name,
                "description": description
            }
        }
        
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            data = response.json()
            return data['data'][0]['id']
        except Exception as e:
            self._handle_api_error(e)

    def add_tracks_to_playlist(self, playlist_id: str, track_urls: List[str], position: Optional[int] = None) -> Optional[str]:
        """Ajoute des titres ou des clips à une playlist de bibliothèque"""
        if not self.auth_token:
            raise ValueError("Music-User-Token requis.")

        url = f"{self.base_url}/me/library/playlists/{playlist_id}/tracks"
        
        tracks_data = []
        for track_url in track_urls:
            try:
                t_id = self._extract_id(track_url)
                t_type = "music-videos" if "/music-video/" in track_url else "songs"
                tracks_data.append({"id": t_id, "type": t_type})
            except:
                continue

        payload = {"data": tracks_data}
        
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            return "success"
        except Exception as e:
            self._handle_api_error(e)

    def _extract_id(self, url: str) -> str:
        """Extrait l'ID de l'URL Apple Music (Song, Album, Playlist, Music Video)"""
        match = re.search(r"/(?:album|song|playlist|music-video)/.*?/(\d+|pl\..*|i\..*)", url)
        if match:
            return match.group(1)
        
        if re.match(r"^(\d+|pl\..*|i\..*)$", url):
            return url
            
        raise ValueError(f"ID Apple Music introuvable dans l'URL : {url}")

    def _extract_storefront(self, url: str) -> str:
        """Extrait le storefront (ex: fr, us) de l'URL"""
        match = re.search(r"apple\.com/([^/]+)/", url)
        return match.group(1) if match else "us"

    def _map_track(self, attrs: dict, url: str, is_video: bool = False) -> TrackMetadata:
        """Mappe les attributs Apple Music vers TrackMetadata avec enrichissement"""
        artwork_url = attrs.get('artwork', {}).get('url', '')
        if artwork_url:
            artwork_url = artwork_url.replace('{w}', '1000').replace('{h}', '1000')
        
        isrc = attrs.get('isrc')
        
        return TrackMetadata(
            title=attrs.get('name', 'Titre inconnu'),
            artist=attrs.get('artistName', 'Artiste inconnu'),
            album=attrs.get('albumName'),
            release_year=int(attrs.get('releaseDate', '0')[:4]) if attrs.get('releaseDate') else None,
            cover_url=artwork_url,
            duration_ms=attrs.get('durationInMillis', 0),
            isrc=isrc,
            explicit=attrs.get('contentRating') == 'explicit',
            is_video=is_video,
            provider="apple_music",
            original_url=url
        )
