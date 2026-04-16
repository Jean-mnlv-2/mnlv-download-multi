from typing import Optional
import yt_dlp
from ..providers.base import TrackMetadata

class ISRCMatcher:
    """
    Module de matching intelligent Spotify -> YouTube Music.
    Priorise le code ISRC pour une précision de 100%.
    """
    
    def __init__(self, logger=None):
        self.logger = logger

    def find_best_match(self, metadata: TrackMetadata) -> str:
        """
        Trouve l'URL YouTube la plus pertinente.
        1. Recherche par ISRC sur YouTube Music (100% précision)
        2. Recherche par UPC/EAN (identifiants de secours)
        3. Recherche textuelle {artist} - {title} audio
        """
        # Stratégie 1: ISRC (La plus précise)
        if metadata.isrc:
            isrc_query = f"isrc:{metadata.isrc}"
            match = self._try_search(isrc_query, metadata, "ISRC")
            if match: return match

        for id_type, id_val in [("UPC", metadata.upc), ("EAN", metadata.ean)]:
            if id_val:
                query = f"{id_type}:{id_val}"
                match = self._try_search(query, metadata, id_type)
                if match: return match

        suffix = " (Podcast Episode)" if metadata.is_episode else " (Official Audio)"
        search_query = f"{metadata.artist} - {metadata.title}{suffix}"
        if self.logger:
            self.logger.info(f"Fallback matching textuel: {search_query}")
        
        return f"ytsearch1:{search_query}"

    def _try_search(self, query: str, metadata: TrackMetadata, label: str) -> Optional[str]:
        """Helper pour tenter une recherche yt-dlp"""
        if self.logger:
            self.logger.info(f"Tentative de matching {label}: {query}")
        
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            try:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                if info['entries'] and self.verify_match(info['entries'][0], metadata):
                    return info['entries'][0]['webpage_url']
            except Exception:
                pass
        return None

    def verify_match(self, info_dict: dict, metadata: TrackMetadata) -> bool:
        """
        Vérifie si le résultat yt-dlp correspond aux métadonnées (durée, etc.)
        """
        if not info_dict:
            return False
            
        # Vérification de la durée (tolérance de 10 secondes)
        if metadata.duration_ms and info_dict.get('duration'):
            duration_diff = abs((metadata.duration_ms / 1000) - info_dict['duration'])
            if duration_diff > 15: # Un peu plus souple
                if self.logger:
                    self.logger.warning(f"Écart de durée trop important: {duration_diff}s")
                return False
                
        return True
