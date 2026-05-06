from typing import Optional
import yt_dlp
from django.core.cache import cache
from ..providers.base import ProviderTrackMetadata

class ISRCMatcher:
    """
    Module de matching intelligent Spotify -> YouTube Music.
    Priorise le code ISRC pour une précision de 100%.
    Inclut un système de cache pour réduire les appels yt-dlp.
    """
    
    def __init__(self, logger=None):
        self.logger = logger

    def find_best_match(self, metadata: ProviderTrackMetadata) -> str:
        """
        Trouve l'URL YouTube la plus pertinente.
        """
        # Système de cache par ISRC
        if metadata.isrc:
            cache_key = f"isrc_match:{metadata.isrc}"
            cached_url = cache.get(cache_key)
            if cached_url:
                if self.logger:
                    self.logger.info(f"Cache HIT pour ISRC {metadata.isrc} -> {cached_url}")
                return cached_url

        # Stratégie 1: ISRC (La plus précise)
        if metadata.isrc:
            isrc_query = f"isrc:{metadata.isrc}"
            match = self._try_search(isrc_query, metadata, "ISRC")
            if match:
                cache.set(f"isrc_match:{metadata.isrc}", match, timeout=86400 * 30)
                return match

        for id_type, id_val in [("UPC", metadata.upc), ("EAN", metadata.ean)]:
            if id_val:
                query = f"{id_type}:{id_val}"
                match = self._try_search(query, metadata, id_type)
                if match: return match

        suffix = " (Podcast Episode)" if metadata.is_episode else " (Official Audio)"
        year = f" {metadata.release_year}" if metadata.release_year else ""
        album = f" {metadata.album}" if metadata.album else ""
        search_query = f"{metadata.artist} - {metadata.title}{album}{year}{suffix}"
        if self.logger:
            self.logger.info(f"Fallback matching textuel: {search_query}")
        
        return f"ytsearch1:{search_query}"

    def _try_search(self, query: str, metadata: ProviderTrackMetadata, label: str) -> Optional[str]:
        """Helper pour tenter une recherche yt-dlp"""
        if self.logger:
            self.logger.info(f"Tentative de matching {label}: {query}")
        
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            try:
                info = ydl.extract_info(f"ytsearch5:{query}", download=False)
                entries = info.get('entries') or []
                best = None
                best_score = -1
                for e in entries[:5]:
                    if not e:
                        continue
                    score = self._score_entry(e, metadata)
                    if score > best_score:
                        best_score = score
                        best = e
                if best and self.verify_match(best, metadata):
                    return best.get('webpage_url')
            except Exception:
                pass
        return None

    def _score_entry(self, info_dict: dict, metadata: ProviderTrackMetadata) -> int:
        """
        Score simple (pas parfait mais nettement meilleur que ytsearch1):
        - proximité durée
        - présence artiste/titre dans le titre YouTube
        """
        title = (info_dict.get('title') or "").lower()
        artist = (metadata.artist or "").lower()
        track = (metadata.title or "").lower()
        score = 0
        if artist and artist.split(",")[0].strip() and artist.split(",")[0].strip() in title:
            score += 3
        if track and track.strip() and track.strip() in title:
            score += 3
        if "official audio" in title or "official video" in title:
            score += 1
        if metadata.duration_ms and info_dict.get('duration'):
            diff = abs((metadata.duration_ms / 1000) - info_dict.get('duration', 0))
            if diff <= 3:
                score += 3
            elif diff <= 8:
                score += 2
            elif diff <= 15:
                score += 1
        return score

    def verify_match(self, info_dict: dict, metadata: ProviderTrackMetadata) -> bool:
        """
        Vérifie si le résultat yt-dlp correspond aux métadonnées (durée, etc.)
        """
        if not info_dict:
            return False
            
        # Vérification de la durée (tolérance de 10 secondes)
        if metadata.duration_ms and info_dict.get('duration'):
            duration_diff = abs((metadata.duration_ms / 1000) - info_dict['duration'])
            if duration_diff > 15:
                if self.logger:
                    self.logger.warning(f"Écart de durée trop important: {duration_diff}s")
                return False
                
        return True
