from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from api.models import ProviderAuth
from api.mixins import StandardizedErrorMixin
from .services import SpotifyAdsService
from core.logger_utils import get_mnlv_logger

logger = get_mnlv_logger("spotify_ads")

class SpotifyAdsBaseView(StandardizedErrorMixin, APIView):
    """
    Classe de base pour les vues Spotify Ads.
    Gère l'initialisation du service avec le token d'authentification de l'utilisateur.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_ads_service(self, user):
        auth = ProviderAuth.objects.filter(user=user, provider='spotify').first()
        if not auth:
            return None
        return SpotifyAdsService(access_token=auth.access_token)

class AdAccountsView(SpotifyAdsBaseView):
    """
    Endpoint GET /api/spotify_ads/ad_accounts/
    """
    def get(self, request):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            accounts = service.get_ad_accounts()
            return Response(accounts)
        except Exception as e:
            logger.exception(f"Error fetching ad accounts: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BusinessesView(SpotifyAdsBaseView):
    """
    Endpoint GET /api/spotify_ads/businesses/
    """
    def get(self, request):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            businesses = service.get_businesses()
            return Response(businesses)
        except Exception as e:
            logger.exception(f"Error fetching businesses: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CampaignsView(SpotifyAdsBaseView):
    """
    Endpoint GET /api/spotify_ads/ad_accounts/{ad_account_id}/campaigns/
    Endpoint POST /api/spotify_ads/ad_accounts/{ad_account_id}/campaigns/
    """
    def get(self, request, ad_account_id):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            campaigns = service.get_campaigns(ad_account_id)
            return Response(campaigns)
        except Exception as e:
            logger.exception(f"Error fetching campaigns: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, ad_account_id):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            campaign = service.create_campaign(ad_account_id, request.data)
            return Response(campaign, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception(f"Error creating campaign: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AdSetsView(SpotifyAdsBaseView):
    """
    Endpoint GET /api/spotify_ads/ad_accounts/{ad_account_id}/ad_sets/
    Endpoint POST /api/spotify_ads/ad_accounts/{ad_account_id}/ad_sets/
    """
    def get(self, request, ad_account_id):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            ad_sets = service.get_ad_sets(ad_account_id)
            return Response(ad_sets)
        except Exception as e:
            logger.exception(f"Error fetching ad sets: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, ad_account_id):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            ad_set = service.create_ad_set(ad_account_id, request.data)
            return Response(ad_set, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception(f"Error creating ad set: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AdsView(SpotifyAdsBaseView):
    """
    Endpoint GET /api/spotify_ads/ad_accounts/{ad_account_id}/ads/
    Endpoint POST /api/spotify_ads/ad_accounts/{ad_account_id}/ads/
    """
    def get(self, request, ad_account_id):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            ads = service.get_ads(ad_account_id)
            return Response(ads)
        except Exception as e:
            logger.exception(f"Error fetching ads: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, ad_account_id):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            ad = service.create_ad(ad_account_id, request.data)
            return Response(ad, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception(f"Error creating ad: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AssetsView(SpotifyAdsBaseView):
    """
    Endpoint GET /api/spotify_ads/ad_accounts/{ad_account_id}/assets/
    Endpoint POST /api/spotify_ads/ad_accounts/{ad_account_id}/assets/
    """
    def get(self, request, ad_account_id):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            assets = service.get_assets(ad_account_id)
            return Response(assets)
        except Exception as e:
            logger.exception(f"Error fetching assets: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, ad_account_id):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            asset = service.create_asset(ad_account_id, request.data)
            return Response(asset, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception(f"Error creating asset: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReportsView(SpotifyAdsBaseView):
    """
    Endpoint GET /api/spotify_ads/ad_accounts/{ad_account_id}/reports/aggregate/
    Endpoint GET /api/spotify_ads/ad_accounts/{ad_account_id}/reports/insights/
    Endpoint GET /api/spotify_ads/ad_accounts/{ad_account_id}/reports/recent_activity/
    """
    def get(self, request, ad_account_id, report_type='aggregate'):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            if report_type == 'aggregate':
                report = service.get_aggregate_report(ad_account_id, request.query_params)
            elif report_type == 'insights':
                report = service.get_insight_report(ad_account_id, request.query_params)
            elif report_type == 'recent_activity':
                report = service.get_recent_activity(ad_account_id)
            else:
                return Response({"error": "Type de rapport inconnu"}, status=status.HTTP_400_BAD_REQUEST)
            return Response(report)
        except Exception as e:
            logger.exception(f"Error fetching report: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AsyncReportsView(SpotifyAdsBaseView):
    """
    Endpoint POST /api/spotify_ads/ad_accounts/{ad_account_id}/async_reports/
    Endpoint GET /api/spotify_ads/ad_accounts/{ad_account_id}/async_reports/{report_id}/
    """
    def post(self, request, ad_account_id):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            report = service.create_async_report(ad_account_id, request.data)
            return Response(report, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception(f"Error creating async report: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, ad_account_id, report_id):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            status_data = service.get_async_report_status(ad_account_id, report_id)
            return Response(status_data)
        except Exception as e:
            logger.exception(f"Error fetching async report status: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TargetingView(SpotifyAdsBaseView):
    """
    Endpoint GET /api/spotify_ads/targeting/{target_type}/
    Supporte: geo, interests, genres, artists, playlists, languages, podcast_topics, sensitive_topics, podcast_shows
    """
    def get(self, request, target_type):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            if target_type == 'geo':
                data = service.get_geo_targets(request.query_params)
            elif target_type == 'interests':
                data = service.get_interest_targets()
            elif target_type == 'genres':
                data = service.get_genre_targets()
            elif target_type == 'artists':
                data = service.get_artist_targets(request.query_params)
            elif target_type == 'playlists':
                data = service.get_playlist_targets(request.query_params)
            elif target_type == 'languages':
                data = service.get_language_targets()
            elif target_type == 'podcast_topics':
                data = service.get_podcast_topic_targets()
            elif target_type == 'sensitive_topics':
                data = service.get_sensitive_topic_targets()
            elif target_type == 'podcast_shows':
                data = service.get_podcast_shows(request.query_params)
            else:
                return Response({"error": "Type de ciblage inconnu"}, status=status.HTTP_400_BAD_REQUEST)
            
            return Response(data)
        except Exception as e:
            logger.exception(f"Error fetching targeting data: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AssetUploadView(SpotifyAdsBaseView):
    """
    Endpoint POST /api/spotify_ads/ad_accounts/{ad_account_id}/assets/upload/
    """
    def post(self, request, ad_account_id):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        if 'file' not in request.FILES:
            return Response({"error": "Aucun fichier fourni"}, status=status.HTTP_400_BAD_REQUEST)
        
        file_obj = request.FILES['file']
        try:
            result = service.upload_asset_file(
                ad_account_id, 
                file_obj.read(), 
                file_obj.content_type
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception(f"Error uploading asset: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PixelsView(SpotifyAdsBaseView):
    """
    Endpoint GET /api/spotify_ads/businesses/{business_id}/pixels/
    Endpoint POST /api/spotify_ads/businesses/{business_id}/pixels/
    """
    def get(self, request, business_id):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            pixels = service.get_pixels(business_id)
            return Response(pixels)
        except Exception as e:
            logger.exception(f"Error fetching pixels: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, business_id):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            pixel = service.create_pixel(business_id, request.data)
            return Response(pixel, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception(f"Error creating pixel: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AudiencesView(SpotifyAdsBaseView):
    """
    Endpoint GET /api/spotify_ads/ad_accounts/{ad_account_id}/audiences/
    Endpoint POST /api/spotify_ads/ad_accounts/{ad_account_id}/audiences/
    """
    def get(self, request, ad_account_id):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            audiences = service.get_audiences(ad_account_id)
            return Response(audiences)
        except Exception as e:
            logger.exception(f"Error fetching audiences: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, ad_account_id):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            audience = service.create_audience(ad_account_id, request.data)
            return Response(audience, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception(f"Error creating audience: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CapiView(SpotifyAdsBaseView):
    """
    Endpoint GET /api/spotify_ads/businesses/{business_id}/capi_integrations/
    Endpoint POST /api/spotify_ads/businesses/{business_id}/capi_integrations/
    """
    def get(self, request, business_id):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            capi = service.get_capi_integrations(business_id)
            return Response(capi)
        except Exception as e:
            logger.exception(f"Error fetching CAPI integrations: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, business_id):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            capi = service.create_capi_integration(business_id, request.data)
            return Response(capi, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception(f"Error creating CAPI integration: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class EstimationsView(SpotifyAdsBaseView):
    """
    Endpoint POST /api/spotify_ads/ad_accounts/{ad_account_id}/estimations/{est_type}/
    """
    def post(self, request, ad_account_id, est_type):
        service = self.get_ads_service(request.user)
        if not service:
            return Response({"error": "Connexion Spotify requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            if est_type == 'audience':
                data = service.get_audience_estimation(ad_account_id, request.data)
            elif est_type == 'bid':
                data = service.get_bid_estimation(ad_account_id, request.data)
            else:
                return Response({"error": "Type d'estimation inconnu"}, status=status.HTTP_400_BAD_REQUEST)
            
            return Response(data)
        except Exception as e:
            logger.exception(f"Error fetching estimation: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
