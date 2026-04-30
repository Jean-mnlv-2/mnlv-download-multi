from typing import List, Optional
from ..base import MusicProvider, ProviderTrackMetadata
import re
import requests
from typing import List

class AmazonMusicProvider(MusicProvider):
    """
    Adapteur pour Amazon Music utilisant le scraping HTML des métadonnées.
    Suit le blueprint fonctionnel de SpotifyProvider.
    """
    def __init__(self, auth_token: Optional[str] = None):
        self.auth_token = auth_token

    def supports_url(self, url: str) -> bool:
        """Vérifie si l'URL est de type music.amazon.com"""
        return bool(re.search(r"music\.amazon", url))

    def get_track_info(self, url: str) -> ProviderTrackMetadata:
        """Extrait les métadonnées d'un titre Amazon Music via scraping"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        html = response.text

        # Scraping basique via Regex (Amazon utilise souvent du JSON dans le HTML)
        title = re.search(r'"title":"(.*?)"', html)
        artist = re.search(r'"artistName":"(.*?)"', html)
        album = re.search(r'"albumName":"(.*?)"', html)
        cover = re.search(r'"image":"(.*?)"', html)

        return ProviderTrackMetadata(
            title=title.group(1) if title else "Titre inconnu",
            artist=artist.group(1) if artist else "Artiste inconnu",
            album=album.group(1) if album else None,
            cover_url=cover.group(1).replace('\u002F', '/') if cover else None,
            provider="amazon_music",
            original_url=url
        )

    def get_playlist_tracks(self, url: str) -> List[ProviderTrackMetadata]:
        """Extrait la liste des titres d'une playlist Amazon Music (MVP: limité au track principal)"""
        # Le scraping de playlist Amazon est complexe sans API. 
        # Pour le MVP, on traite comme un titre unique ou on lève une erreur.
        return [self.get_track_info(url)]
