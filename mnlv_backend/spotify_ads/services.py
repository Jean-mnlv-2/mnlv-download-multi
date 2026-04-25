import requests
from django.conf import settings
from typing import List, Dict, Optional
from core.logger_utils import get_mnlv_logger

logger = get_mnlv_logger("spotify_ads")

class SpotifyAdsService:
    """
    Service pour interagir avec l'API Spotify Ads v3.
    Gère les comptes publicitaires, campagnes, ensembles d'annonces, annonces et rapports.
    """
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = settings.SPOTIFY_ADS_API_BASE
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        if method == "PUT":
            method = "PATCH"
        try:
            response = self.session.request(method, url, **kwargs)
            
            remaining = response.headers.get('X-RateLimit-Remaining')
            if remaining and int(remaining) < 50:
                logger.warning(f"Spotify Ads API Rate Limit Warning: {remaining} requests left")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"Spotify Ads API Error ({method} {endpoint}): {e.response.text}")
            raise e

    # --- Ad Accounts ---
    def get_ad_accounts(self) -> List[Dict]:
        """Récupère tous les comptes publicitaires de l'utilisateur"""
        return self._request("GET", "/ad_accounts")

    def get_ad_account(self, ad_account_id: str) -> Dict:
        """Récupère les détails d'un compte publicitaire spécifique"""
        return self._request("GET", f"/ad_accounts/{ad_account_id}")

    def update_ad_account(self, ad_account_id: str, data: Dict) -> Dict:
        """Met à jour un compte publicitaire"""
        return self._request("PATCH", f"/ad_accounts/{ad_account_id}", json=data)

    # --- Businesses ---
    def get_businesses(self) -> List[Dict]:
        """Récupère toutes les entreprises de l'utilisateur"""
        return self._request("GET", "/businesses")

    def update_business(self, business_id: str, data: Dict) -> Dict:
        """Met à jour les informations d'une entreprise"""
        return self._request("PATCH", f"/businesses/{business_id}", json=data)

    # --- Campaigns ---
    def get_campaigns(self, ad_account_id: str, params: Optional[Dict] = None) -> List[Dict]:
        """Récupère toutes les campagnes d'un compte publicitaire"""
        return self._request("GET", f"/ad_accounts/{ad_account_id}/campaigns", params=params)

    def create_campaign(self, ad_account_id: str, data: Dict) -> Dict:
        """Crée une nouvelle campagne"""
        return self._request("POST", f"/ad_accounts/{ad_account_id}/campaigns", json=data)

    def update_campaign(self, ad_account_id: str, campaign_id: str, data: Dict) -> Dict:
        """Met à jour une campagne existante (Partial update via PATCH)"""
        return self._request("PATCH", f"/ad_accounts/{ad_account_id}/campaigns/{campaign_id}", json=data)

    # --- Ad Sets ---
    def get_ad_sets(self, ad_account_id: str, params: Optional[Dict] = None) -> List[Dict]:
        """Récupère tous les ensembles d'annonces d'un compte publicitaire"""
        return self._request("GET", f"/ad_accounts/{ad_account_id}/ad_sets", params=params)

    def create_ad_set(self, ad_account_id: str, data: Dict) -> Dict:
        """Crée un nouvel ensemble d'annonces"""
        return self._request("POST", f"/ad_accounts/{ad_account_id}/ad_sets", json=data)

    def update_ad_set(self, ad_account_id: str, ad_set_id: str, data: Dict) -> Dict:
        """Met à jour un ensemble d'annonces existant"""
        return self._request("PATCH", f"/ad_accounts/{ad_account_id}/ad_sets/{ad_set_id}", json=data)

    # --- Ads ---
    def get_ads(self, ad_account_id: str, params: Optional[Dict] = None) -> List[Dict]:
        """Récupère toutes les annonces d'un compte publicitaire"""
        return self._request("GET", f"/ad_accounts/{ad_account_id}/ads", params=params)

    def create_ad(self, ad_account_id: str, data: Dict) -> Dict:
        """Crée une nouvelle annonce"""
        return self._request("POST", f"/ad_accounts/{ad_account_id}/ads", json=data)

    def update_ad(self, ad_account_id: str, ad_id: str, data: Dict) -> Dict:
        """Met à jour une annonce existante"""
        return self._request("PATCH", f"/ad_accounts/{ad_account_id}/ads/{ad_id}", json=data)

    # --- Assets ---
    def get_assets(self, ad_account_id: str, params: Optional[Dict] = None) -> List[Dict]:
        """Récupère tous les actifs d'un compte publicitaire"""
        return self._request("GET", f"/ad_accounts/{ad_account_id}/assets", params=params)

    def create_asset(self, ad_account_id: str, data: Dict) -> Dict:
        """Crée un nouvel actif (Métadonnées)"""
        return self._request("POST", f"/ad_accounts/{ad_account_id}/assets", json=data)

    def update_asset(self, ad_account_id: str, asset_id: str, data: Dict) -> Dict:
        """Met à jour un actif"""
        return self._request("PATCH", f"/ad_accounts/{ad_account_id}/assets/{asset_id}", json=data)

    def upload_asset_file(self, ad_account_id: str, file_data: bytes, content_type: str) -> Dict:
        """Téléverse un fichier média (<25MB)"""
        url = f"{self.base_url.rstrip('/')}/ad_accounts/{ad_account_id}/assets/upload"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": content_type
        }
        response = self.session.post(url, data=file_data, headers=headers)
        
        remaining = response.headers.get('X-RateLimit-Remaining')
        if remaining:
            logger.debug(f"Spotify Ads Rate Limit Remaining: {remaining}")
            
        response.raise_for_status()
        return response.json()

    # --- Reports ---
    def get_aggregate_report(self, ad_account_id: str, params: Dict) -> Dict:
        """Récupère un rapport agrégé"""
        return self._request("GET", f"/ad_accounts/{ad_account_id}/reports/aggregate", params=params)

    def get_insight_report(self, ad_account_id: str, params: Dict) -> Dict:
        """Récupère un rapport d'analyse (Insight Report)"""
        return self._request("GET", f"/ad_accounts/{ad_account_id}/reports/insights", params=params)

    def create_async_report(self, ad_account_id: str, data: Dict) -> Dict:
        """Crée une demande de rapport asynchrone (CSV)"""
        return self._request("POST", f"/ad_accounts/{ad_account_id}/async_reports", json=data)

    def get_async_report_status(self, ad_account_id: str, report_id: str) -> Dict:
        """Récupère le statut d'un rapport asynchrone"""
        return self._request("GET", f"/ad_accounts/{ad_account_id}/async_reports/{report_id}")

    # --- Targeting ---
    def get_geo_targets(self, params: Dict) -> List[Dict]:
        """Récupère les cibles géographiques (Pays, Villes, Métros, Codes Postaux)"""
        return self._request("GET", "/targeting/geo", params=params)

    def get_interest_targets(self) -> List[Dict]:
        """Récupère les cibles par centres d'intérêt"""
        return self._request("GET", "/targeting/interests")

    def get_genre_targets(self) -> List[Dict]:
        """Récupère les cibles par genres musicaux"""
        return self._request("GET", "/targeting/genres")

    def get_artist_targets(self, params: Dict) -> List[Dict]:
        """Récupère les cibles par artistes"""
        return self._request("GET", "/targeting/artists", params=params)

    def get_playlist_targets(self, params: Dict) -> List[Dict]:
        """Récupère les cibles par playlists"""
        return self._request("GET", "/targeting/playlists", params=params)

    def get_language_targets(self) -> List[Dict]:
        """Récupère les cibles linguistiques"""
        return self._request("GET", "/targeting/languages")

    def get_podcast_topic_targets(self) -> List[Dict]:
        """Récupère les cibles par sujets de podcasts"""
        return self._request("GET", "/targeting/podcast_topics")

    def get_sensitive_topic_targets(self) -> List[Dict]:
        """Récupère les cibles d'exclusion de sujets sensibles"""
        return self._request("GET", "/targeting/sensitive_topics")

    def get_podcast_shows(self, params: Dict) -> List[Dict]:
        """Récupère les shows de podcasts pour le ciblage"""
        return self._request("GET", "/targeting/podcast_shows", params=params)

    # --- Pixels ---
    def get_pixels(self, business_id: str) -> List[Dict]:
        """Récupère les pixels d'une entreprise"""
        return self._request("GET", f"/businesses/{business_id}/pixels")

    def create_pixel(self, business_id: str, data: Dict) -> Dict:
        """Crée un nouveau pixel"""
        return self._request("POST", f"/businesses/{business_id}/pixels", json=data)

    # --- Audiences ---
    def get_audiences(self, ad_account_id: str) -> List[Dict]:
        """Récupère les audiences d'un compte publicitaire"""
        return self._request("GET", f"/ad_accounts/{ad_account_id}/audiences")

    def create_audience(self, ad_account_id: str, data: Dict) -> Dict:
        """Crée une nouvelle audience"""
        return self._request("POST", f"/ad_accounts/{ad_account_id}/audiences", json=data)

    # --- CAPI (Conversions API) ---
    def get_capi_integrations(self, business_id: str) -> List[Dict]:
        """Récupère les intégrations CAPI d'une entreprise"""
        return self._request("GET", f"/businesses/{business_id}/capi_integrations")

    def create_capi_integration(self, business_id: str, data: Dict) -> Dict:
        """Crée une nouvelle intégration CAPI"""
        return self._request("POST", f"/businesses/{business_id}/capi_integrations", json=data)

    # --- Estimations ---
    def get_audience_estimation(self, ad_account_id: str, data: Dict) -> Dict:
        """Récupère une estimation d'audience"""
        return self._request("POST", f"/ad_accounts/{ad_account_id}/audience_estimations", json=data)

    def get_bid_estimation(self, ad_account_id: str, data: Dict) -> Dict:
        """Récupère une estimation d'enchère"""
        return self._request("POST", f"/ad_accounts/{ad_account_id}/bid_estimations", json=data)

    # --- Activity / Logs ---
    def get_recent_activity(self, ad_account_id: str) -> List[Dict]:
        """Récupère les événements récents (Audit Logs) du compte"""
        try:
            return self._request("GET", f"/ad_accounts/{ad_account_id}/audit_logs")
        except:
            return []
