from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView, CreateAPIView, ListAPIView
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.models import User
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from downloader.models import DownloadTask
from downloader.tasks import process_single_track, process_playlist_item
from downloader.providers.factory import ProviderFactory
from downloader.providers.apple_music.provider import AppleMusicProvider
from downloader.providers.deezer.provider import DeezerProvider
from .models import ProviderAuth
from .tasks import refresh_spotify_token, refresh_deezer_token, refresh_tidal_token
from .serializers import (
    DownloadTaskSerializer,
    CreateDownloadTaskSerializer,
    UserSerializer,
    PlaylistManagementSerializer
)
from .mixins import StandardizedErrorMixin
from core.logger_utils import get_mnlv_logger
import os
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from django.utils import timezone
from dataclasses import asdict
from datetime import timedelta
import logging

logger = get_mnlv_logger("api")

MAX_PLAYLIST_TRACKS = int(os.getenv("MAX_PLAYLIST_TRACKS", "500"))

def get_provider_auth(user, provider_name):
    return ProviderAuth.objects.filter(user=user, provider=provider_name).first()

class ProviderAuthStatusView(APIView):
    """
    Endpoint GET /api/auth/providers/status/
    Vérifie quels providers sont connectés pour l'utilisateur.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        auths = ProviderAuth.objects.filter(user=request.user).values_list('provider', flat=True)
        connected_providers = set(auths)
        status_dict = {
            'spotify': 'spotify' in connected_providers,
            'deezer': 'deezer' in connected_providers,
            'apple_music': 'apple_music' in connected_providers,
            'boomplay': 'boomplay' in connected_providers,
            'soundcloud': 'soundcloud' in connected_providers,
            'tidal': 'tidal' in connected_providers,
            'amazon_music': 'amazon_music' in connected_providers,
            'youtube_music': 'youtube_music' in connected_providers,
        }
        logger.info(f"Auth status check for user {request.user.id}: {status_dict}")
        return Response(status_dict)

class SpotifyLoginView(APIView):
    """
    Endpoint GET /api/auth/providers/spotify/login/
    Génère l'URL d'autorisation Spotify.
    Supporte l'authentification via Header Authorization ou paramètre ?token=
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        user = request.user

        if user.is_anonymous:
            token = request.GET.get('token')
            if token:
                try:
                    validated_token = AccessToken(token)
                    user_id = validated_token['user_id']
                    user = User.objects.get(id=user_id)
                    logger.info(f"User {user_id} authenticated via JWT for Spotify login")
                except (TokenError, User.DoesNotExist) as e:
                    logger.warning(f"Invalid JWT token attempt: {e}")
                    return Response({"error": "Token invalide ou expiré"}, status=status.HTTP_401_UNAUTHORIZED)

        if user.is_anonymous:
            return Response({"error": "Authentification requise"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            sp_oauth = SpotifyOAuth(
                client_id=settings.SPOTIFY_CLIENT_ID,
                client_secret=settings.SPOTIFY_CLIENT_SECRET,
                redirect_uri=settings.SPOTIFY_REDIRECT_URI,
                scope=settings.SPOTIFY_ADS_SCOPE,
                state=str(user.id)
            )
            auth_url = sp_oauth.get_authorize_url()
            logger.info(f"Spotify auth URL generated for user {user.id} with redirect: {settings.SPOTIFY_REDIRECT_URI}")

            if "text/html" in request.accepted_media_type:
                return redirect(auth_url)

            return Response({"auth_url": auth_url}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(f"Error generating Spotify auth URL: {e}")
            return Response({"error": "Erreur lors de la génération de l'URL d'autorisation"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SpotifyCallbackView(APIView):
    """
    Endpoint GET /api/auth/providers/spotify/callback/
    Gère le retour de Spotify et stocke le token.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        error = request.GET.get('error')
        code = request.GET.get('code')
        user_id = request.GET.get('state')

        if error:
            logger.warning(f"Spotify callback error: {error}")
            return redirect(f'{settings.FRONTEND_URL}/?auth_error=spotify&reason={error}')

        if not code or not user_id:
            logger.warning(f"Spotify callback missing code or state: code={code}, state={user_id}")
            return redirect(f'{settings.FRONTEND_URL}/?auth_error=spotify&reason=missing_parameters')

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.warning(f"Spotify callback invalid user_id: {user_id}")
            return redirect(f'{settings.FRONTEND_URL}/?auth_error=spotify&reason=invalid_user')

        backend_callback = settings.SPOTIFY_REDIRECT_URI
        sp_oauth = SpotifyOAuth(
            client_id=settings.SPOTIFY_CLIENT_ID,
            client_secret=settings.SPOTIFY_CLIENT_SECRET,
            redirect_uri=backend_callback
        )

        try:
            token_info = sp_oauth.get_access_token(code)
            if not token_info or 'access_token' not in token_info:
                logger.error(f"Spotify token exchange failed for user {user_id}")
                return Response({"error": "Échec de l'obtention du token Spotify"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            with transaction.atomic():
                ProviderAuth.objects.update_or_create(
                    user=user,
                    provider='spotify',
                    defaults={
                        'access_token': token_info['access_token'],
                        'refresh_token': token_info.get('refresh_token'),
                        'expires_at': timezone.now() + timedelta(seconds=token_info.get('expires_in', 3600))
                    }
                )
            logger.info(f"Spotify auth successful for user {user_id}")
            return redirect(f'{settings.FRONTEND_URL}/?auth_success=spotify')
        except Exception as e:
            logger.exception(f"Spotify callback error for user {user_id}: {e}")
            return Response({"error": "Erreur lors de l'authentification Spotify"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeezerLoginView(APIView):
    """
    Endpoint GET /api/auth/providers/deezer/login/
    Génère l'URL d'autorisation Deezer.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        app_id = settings.DEEZER_APP_ID
        backend_callback = f"{settings.BACKEND_URL.rstrip('/')}/api/auth/providers/deezer/callback/"
        
        perms = "basic_access,offline_access,manage_library,delete_library"
        auth_url = f"https://connect.deezer.com/oauth/auth.php?app_id={app_id}&redirect_uri={backend_callback}&perms={perms}&state={request.user.id}"
        
        logger.info(f"Deezer auth URL generated for user {request.user.id} with redirect: {backend_callback}")
        return Response({"auth_url": auth_url}, status=status.HTTP_200_OK)

class DeezerCallbackView(APIView):
    """
    Endpoint GET /api/auth/providers/deezer/callback/
    Gère le retour de Deezer et stocke le token.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        error = request.GET.get('error')
        code = request.GET.get('code')
        user_id = request.GET.get('state')

        if error:
            logger.warning(f"Deezer callback error: {error}")
            return redirect(f'{settings.FRONTEND_URL}/?auth_error=deezer&reason={error}')

        if not code or not user_id:
            logger.warning(f"Deezer callback missing code or state: code={code}, state={user_id}")
            return redirect(f'{settings.FRONTEND_URL}/?auth_error=deezer&reason=missing_parameters')

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.warning(f"Deezer callback invalid user_id: {user_id}")
            return redirect(f'{settings.FRONTEND_URL}/?auth_error=deezer&reason=invalid_user')

        try:
            app_id = settings.DEEZER_APP_ID
            secret = settings.DEEZER_SECRET_KEY
            
            token_url = f"https://connect.deezer.com/oauth/access_token.php?app_id={app_id}&secret={secret}&code={code}&output=json"
            response = requests.get(token_url)
            token_data = response.json()
            
            if 'access_token' not in token_data:
                logger.error(f"Deezer token exchange failed for user {user_id}: {token_data}")
                return redirect(f'{settings.FRONTEND_URL}/?auth_error=deezer&reason=token_exchange_failed')

            with transaction.atomic():
                ProviderAuth.objects.update_or_create(
                    user=user,
                    provider='deezer',
                    defaults={
                        'access_token': token_data['access_token'],
                        'expires_at': timezone.now() + timedelta(seconds=int(token_data.get('expires', 3600))) if token_data.get('expires') else None
                    }
                )
            
            logger.info(f"Deezer auth successful for user {user_id}")
            return redirect(f'{settings.FRONTEND_URL}/?auth_success=deezer')
        except Exception as e:
            logger.exception(f"Deezer callback error: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SoundCloudLoginView(APIView):
    """
    Endpoint GET /api/auth/providers/soundcloud/login/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        client_id = settings.SOUNDCLOUD_CLIENT_ID
        backend_callback = f"{settings.BACKEND_URL.rstrip('/')}/api/auth/providers/soundcloud/callback/"
        auth_url = f"https://soundcloud.com/connect?client_id={client_id}&redirect_uri={backend_callback}&response_type=code&state={request.user.id}"
        
        return Response({"auth_url": auth_url}, status=status.HTTP_200_OK)

class SoundCloudCallbackView(APIView):
    """
    Endpoint GET /api/auth/providers/soundcloud/callback/
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        error = request.GET.get('error')
        code = request.GET.get('code')
        user_id = request.GET.get('state')
        
        if error:
            logger.warning(f"SoundCloud callback error: {error}")
            return redirect(f'{settings.FRONTEND_URL}/?auth_error=soundcloud&reason={error}')

        if not code or not user_id:
            logger.warning(f"SoundCloud callback missing code or state: code={code}, state={user_id}")
            return redirect(f'{settings.FRONTEND_URL}/?auth_error=soundcloud&reason=missing_parameters')
            
        try:
            user = User.objects.get(id=user_id)
            return redirect(f'{settings.FRONTEND_URL}/?auth_success=soundcloud')
        except User.DoesNotExist:
            logger.warning(f"SoundCloud callback invalid user_id: {user_id}")
            return redirect(f'{settings.FRONTEND_URL}/?auth_error=soundcloud&reason=invalid_user')
        except Exception as e:
            logger.exception(f"SoundCloud callback error: {e}")
            return redirect(f'{settings.FRONTEND_URL}/?auth_error=soundcloud&reason=unknown')

class AmazonMusicLoginView(APIView):
    """
    Endpoint GET /api/auth/providers/amazon-music/login/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({"message": "Amazon Music login non encore implémenté"}, status=status.HTTP_501_NOT_IMPLEMENTED)

class TidalLoginView(APIView):
    """
    Endpoint GET /api/auth/providers/tidal/login/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        client_id = getattr(settings, 'TIDAL_CLIENT_ID', None)
        if not client_id:
            return Response({"error": "Tidal Client ID non configuré"}, status=status.HTTP_400_BAD_REQUEST)
            
        backend_callback = f"{settings.BACKEND_URL.rstrip('/')}/api/auth/providers/tidal/callback/"
        auth_url = f"https://login.tidal.com/authorize?client_id={client_id}&redirect_uri={backend_callback}&response_type=code&scope=playlists.edit&state={request.user.id}"
        
        return Response({"auth_url": auth_url}, status=status.HTTP_200_OK)

class TidalCallbackView(APIView):
    """
    Endpoint GET /api/auth/providers/tidal/callback/
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        error = request.GET.get('error')
        code = request.GET.get('code')
        user_id = request.GET.get('state')
        
        if error:
            logger.warning(f"Tidal callback error: {error}")
            return redirect(f'{settings.FRONTEND_URL}/?auth_error=tidal&reason={error}')

        if not code or not user_id:
            logger.warning(f"Tidal callback missing code or state: code={code}, state={user_id}")
            return redirect(f'{settings.FRONTEND_URL}/?auth_error=tidal&reason=missing_parameters')
            
        try:
            user = User.objects.get(id=user_id)
            return redirect(f'{settings.FRONTEND_URL}/?auth_success=tidal')
        except User.DoesNotExist:
            logger.warning(f"Tidal callback invalid user_id: {user_id}")
            return redirect(f'{settings.FRONTEND_URL}/?auth_error=tidal&reason=invalid_user')
        except Exception as e:
            logger.exception(f"Tidal callback error: {e}")
            return redirect(f'{settings.FRONTEND_URL}/?auth_error=tidal&reason=unknown')

class AppleMusicTokenView(APIView):
    """
    Endpoint GET /api/auth/providers/apple-music/token/
    Retourne le Developer Token (JWT) pour MusicKit JS.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not settings.APPLE_MUSIC_SECRET_KEY or "votre_cle" in settings.APPLE_MUSIC_SECRET_KEY:
            logger.warning(f"Apple Music secret key not configured correctly")
            return Response({"error": "Configuration Apple Music manquante ou invalide (Secret Key)"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            provider = AppleMusicProvider()
            token = provider.am.token
            logger.info(f"Apple Music token generated for user {request.user.id}")
            return Response({"token": token})
        except Exception as e:
            logger.exception(f"Apple Music token generation error: {e}")
            if "load PEM file" in str(e):
                return Response({"error": "La clé secrète Apple Music est malformée. Assurez-vous qu'il s'agit d'un fichier .p8 valide."}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"error": "Erreur lors de la génération du token Apple Music"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AppleMusicLoginView(APIView):
    """
    Endpoint POST /api/auth/providers/apple-music/login/
    Reçoit le Music-User-Token généré côté client (via MusicKit JS).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        music_user_token = request.data.get('music_user_token')
        if not music_user_token:
            return Response({"error": "Music-User-Token manquant"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                ProviderAuth.objects.update_or_create(
                    user=request.user,
                    provider='apple_music',
                    defaults={
                        'access_token': music_user_token,
                    }
                )
            logger.info(f"Apple Music login successful for user {request.user.id}")
            return Response({"message": "Connexion Apple Music réussie"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(f"Apple Music login error for user {request.user.id}: {e}")
            return Response({"error": "Erreur lors de la connexion Apple Music"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AppleMusicPlaylistsView(APIView):
    """
    Endpoint GET /api/auth/providers/apple-music/playlists/
    Récupère les playlists de l'utilisateur.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        auth = get_provider_auth(request.user, 'apple_music')
        if not auth:
            logger.warning(f"Apple Music auth required for user {request.user.id}")
            return Response({"error": "Connexion Apple Music requise"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            provider = AppleMusicProvider(auth_token=auth.access_token)
            playlists = provider.get_user_playlists()
            logger.info(f"Apple Music playlists retrieved for user {request.user.id}")
            return Response(playlists)
        except Exception as e:
            logger.exception(f"Apple Music playlists error for user {request.user.id}: {e}")
            return Response({"error": "Erreur lors de la récupération des playlists"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AppleMusicSearchView(APIView):
    """
    Endpoint GET /api/auth/providers/apple-music/search/
    Recherche dans le catalogue ou la bibliothèque Apple Music.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q')
        storefront = request.query_params.get('storefront', 'us')
        scope = request.query_params.get('scope', 'catalog')

        if not query:
            return Response({"error": "Requête de recherche manquante"}, status=status.HTTP_400_BAD_REQUEST)

        auth = get_provider_auth(request.user, 'apple_music')
        auth_token = auth.access_token if auth else None

        try:
            provider = AppleMusicProvider(auth_token=auth_token)
            if scope == 'library':
                if not auth_token:
                    logger.warning(f"Apple Music library search requires auth for user {request.user.id}")
                    return Response({"error": "Connexion Apple Music requise pour la recherche bibliothèque"}, status=status.HTTP_401_UNAUTHORIZED)
                results = provider.search_library(query)
            else:
                results = provider.search(query, storefront=storefront)

            logger.info(f"Apple Music search '{query}' (scope={scope}) for user {request.user.id}")
            return Response(results)
        except Exception as e:
            logger.exception(f"Apple Music search error for user {request.user.id}: {e}")
            return Response({"error": "Erreur lors de la recherche Apple Music"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeezerFlowView(APIView):
    """Récupère et lance le téléchargement du Flow Deezer"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        auth = get_provider_auth(request.user, 'deezer')
        if not auth:
            logger.warning(f"Deezer auth required for user {request.user.id}")
            return Response({"error": "Connexion Deezer requise"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            provider = DeezerProvider(auth_token=auth.access_token)
            tracks = provider.get_user_flow()

            tasks_to_create = []
            for track in tracks[:MAX_PLAYLIST_TRACKS]:
                tasks_to_create.append(DownloadTask(
                    user=request.user,
                    original_url=track.original_url,
                    provider='deezer',
                    media_type=DownloadTask.MediaType.AUDIO
                ))

            created_tasks = DownloadTask.objects.bulk_create(tasks_to_create)

            for task in created_tasks:
                process_playlist_item.delay(str(task.id))

            tasks_info = [{"task_id": str(task.id), "title": task.original_url} for task in created_tasks]
            logger.info(f"Deezer Flow: {len(created_tasks)} tasks created for user {request.user.id}")
            return Response({"type": "flow", "tasks": tasks_info}, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception(f"Deezer Flow error for user {request.user.id}: {e}")
            return Response({"error": "Erreur lors de la récupération du Flow Deezer"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeezerFavoritesView(APIView):
    """Récupère les favoris Deezer"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        auth = get_provider_auth(request.user, 'deezer')
        if not auth:
            logger.warning(f"Deezer auth required for user {request.user.id}")
            return Response({"error": "Connexion Deezer requise"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            provider = DeezerProvider(auth_token=auth.access_token)
            tracks = provider.get_user_favorites()
            logger.info(f"Deezer favorites: {len(tracks)} tracks retrieved for user {request.user.id}")
            return Response([asdict(t) if hasattr(t, '__dataclass_fields__') else t.__dict__ for t in tracks])
        except Exception as e:
            logger.exception(f"Deezer favorites error for user {request.user.id}: {e}")
            return Response({"error": "Erreur lors de la récupération des favoris Deezer"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeezerSearchView(APIView):
    """Recherche Smart Search Deezer"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.GET.get('q')
        if not query:
            return Response({"error": "Requête manquante"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            provider = DeezerProvider()
            results = provider.search(query)
            logger.info(f"Deezer search '{query}' for user {request.user.id}")
            return Response(results)
        except Exception as e:
            logger.exception(f"Deezer search error for user {request.user.id}: {e}")
            return Response({"error": "Erreur lors de la recherche Deezer"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeezerChartsView(APIView):
    """Récupère les tendances Deezer"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            provider = DeezerProvider()
            charts = provider.get_charts()
            logger.info(f"Deezer charts retrieved")
            return Response(charts)
        except Exception as e:
            logger.exception(f"Deezer charts error: {e}")
            return Response({"error": "Erreur lors de la récupération des charts Deezer"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RegisterView(CreateAPIView):
    """
    Endpoint POST /api/auth/register/
    Création d'un nouvel utilisateur.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

class UserProfileView(StandardizedErrorMixin, APIView):
    """
    Endpoint GET /api/auth/profile/
    Récupère les informations de l'utilisateur connecté.
    """
    def get(self, request):
        try:
            logger.info(f"Fetching profile for user: {request.user}")
            if not request.user or request.user.is_anonymous:
                return self.error_response("Utilisateur non authentifié", status_code=status.HTTP_401_UNAUTHORIZED)
            
            serializer = UserSerializer(request.user)
            return Response(serializer.data)
        except Exception as e:
            logger.exception(f"Error in UserProfileView: {e}")
            return self.handle_exception(e)

from rest_framework.throttling import UserRateThrottle

class DownloadRateThrottle(UserRateThrottle):
    scope = 'downloads'

class SubmitDownloadView(StandardizedErrorMixin, APIView):
    """
    Endpoint POST /api/download/
    Reçoit l'URL, valide, crée une ou plusieurs DownloadTask et lance Celery.
    """
    throttle_classes = [DownloadRateThrottle]

    def post(self, request):
        serializer = CreateDownloadTaskSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response("Données invalides", data=serializer.errors)

        url = serializer.validated_data['url']
        
        if any(url.lower().endswith(ext) for ext in ['.csv', '.txt']):
            try:
                import requests
                content = requests.get(url, timeout=10).text
                urls = [line.strip() for line in content.splitlines() if line.strip().startswith('http')]
                if urls:
                    from csv_handler.models import PendingFileUpload
                    resolved_tracks = []
                    for t_url in urls[:MAX_PLAYLIST_TRACKS]:
                        resolved_tracks.append({
                            "title": t_url.split('/')[-1] if '/' in t_url else t_url,
                            "artist": "Source externe",
                            "url": t_url,
                            "provider": "batch",
                            "status": "ready"
                        })
                    
                    PendingFileUpload.objects.create(
                        user=request.user,
                        filename=f"Batch : {url.split('/')[-1]}",
                        data=resolved_tracks
                    )
                    
                    return Response({
                        "status": "success",
                        "type": "staged_playlist",
                        "message": f"Fichier batch analysé : {len(resolved_tracks)} morceaux trouvés.",
                        "tracks": resolved_tracks,
                        "count": len(resolved_tracks)
                    }, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"Failed to parse batch file from URL: {e}")

        media_type = serializer.validated_data.get('media_type', DownloadTask.MediaType.AUDIO)
        prefer_video = serializer.validated_data.get('prefer_video', False)
        quality = serializer.validated_data.get('quality')
        explicit_filter = serializer.validated_data.get('explicit_filter', False)

        try:
            provider = ProviderFactory.get_provider(url)
            provider_name = provider.__class__.__name__.lower().replace("provider", "")

            if "/playlist/" in url or "/album/" in url:
                tracks = provider.get_playlist_tracks(url)
                
                from csv_handler.models import PendingFileUpload
                
                resolved_tracks = []
                for track in tracks[:MAX_PLAYLIST_TRACKS]:
                    if explicit_filter and getattr(track, 'explicit', False):
                        continue
                    resolved_tracks.append({
                        "title": track.title,
                        "artist": track.artist,
                        "url": track.original_url,
                        "provider": provider_name,
                        "cover_url": getattr(track, 'cover_url', None),
                        "status": "ready"
                    })

                PendingFileUpload.objects.create(
                    user=request.user,
                    filename=f"Playlist {provider_name.title()} : {url.split('/')[-1]}",
                    data=resolved_tracks
                )

                logger.info(f"Playlist staged for preview: {len(resolved_tracks)} tracks for user {request.user.id}")
                return Response({
                    "status": "success",
                    "type": "staged_playlist",
                    "message": f"Playlist analysée : {len(resolved_tracks)} morceaux trouvés.",
                    "tracks": resolved_tracks,
                    "count": len(resolved_tracks),
                    "provider": provider_name
                }, status=status.HTTP_201_CREATED)

            else:
                track_info = provider.get_track_info_cached(url)
                if explicit_filter and getattr(track_info, 'explicit', False):
                    return self.error_response("Ce titre est explicite et votre filtre est activé.")

                task = DownloadTask.objects.create(
                    user=request.user,
                    original_url=url,
                    provider=provider_name,
                    media_type=media_type,
                    prefer_video=prefer_video,
                    quality=quality,
                    explicit_filter=explicit_filter
                )
                process_single_track.delay(str(task.id))
                logger.info(f"Track download: task {task.id} created for user {request.user.id}")
                
                return Response({
                    "status": "success",
                    "type": "track",
                    "task_id": str(task.id),
                    "task_status": task.status,
                    "provider": task.provider,
                    "title": track_info.title
                }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return self.error_response(str(e))
        except Exception as e:
            return self.handle_exception(e)

class DownloadTaskListView(ListAPIView):
    """
    Endpoint GET /api/tasks/history/
    Récupère l'historique complet des téléchargements de l'utilisateur.
    """
    serializer_class = DownloadTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DownloadTask.objects.filter(user=self.request.user).order_by('-created_at')

class DownloadTaskStatusView(RetrieveAPIView):
    """
    Endpoint GET /api/task/{task_id}/status/
    Récupère l'état d'avancement d'une tâche (polling).
    """
    queryset = DownloadTask.objects.all()
    serializer_class = DownloadTaskSerializer
    lookup_field = 'id'

class BulkCancelTasksView(APIView):
    """
    Endpoint POST /api/tasks/cancel-all/
    Annule toutes les tâches en cours ou en attente de l'utilisateur.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            updated_count = DownloadTask.objects.filter(
                user=request.user,
                status__in=[DownloadTask.Status.PENDING, DownloadTask.Status.PROCESSING]
            ).update(
                status=DownloadTask.Status.FAILED,
                error_message="Annulé par l'utilisateur"
            )
            
            logger.info(f"Bulk cancel: {updated_count} tasks cancelled for user {request.user.id}")
            return Response({
                "status": "success",
                "message": f"{updated_count} tâches ont été annulées.",
                "cancelled_count": updated_count
            })
        except Exception as e:
            logger.exception(f"Error in BulkCancelTasksView: {e}")
            return Response({"error": "Erreur lors de l'annulation des tâches"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BulkDownloadView(StandardizedErrorMixin, APIView):
    """
    Endpoint POST /api/download/bulk/
    Reçoit une liste d'URLs et crée des tâches en masse.
    Optimisé pour l'import CSV/Playlists.
    """
    throttle_classes = [DownloadRateThrottle]

    def post(self, request):
        urls = request.data.get('urls', [])
        media_type = request.data.get('media_type', DownloadTask.MediaType.AUDIO)
        quality = request.data.get('quality')
        
        if not urls:
            return self.error_response("Aucune URL fournie")

        tasks_to_create = []
        for url in urls[:500]:
            provider_name = 'unknown'
            if 'spotify.com' in url: provider_name = 'spotify'
            elif 'deezer.com' in url: provider_name = 'deezer'
            elif 'apple.com' in url: provider_name = 'apple_music'
            
            tasks_to_create.append(DownloadTask(
                user=request.user,
                original_url=url,
                provider=provider_name,
                media_type=media_type,
                quality=quality
            ))

        try:
            with transaction.atomic():
                created_tasks = DownloadTask.objects.bulk_create(tasks_to_create)

            for task in created_tasks:
                process_playlist_item.delay(str(task.id))

            tasks_info = [
                {
                    "task_id": str(task.id), 
                    "url": task.original_url,
                    "title": "Téléchargement en cours...", # Titre temporaire plus propre
                    "provider": task.provider,
                    "status": task.status
                } 
                for task in created_tasks
            ]
            logger.info(f"Bulk download: {len(created_tasks)} tasks created for user {request.user.id}")
            
            return Response({
                "status": "success",
                "count": len(tasks_info),
                "tasks": tasks_info
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return self.handle_exception(e)

from django.db import connections
from django.core.cache import cache
from celery.result import AsyncResult

class HealthCheckView(APIView):
    """
    Endpoint GET /api/health/
    Vérifie l'état de santé des composants (DB, Redis, Celery).
    """
    permission_classes = []
    
    def get(self, request):
        status_info = {
            "database": "ok",
            "redis": "ok",
            "celery": "ok"
        }
        
        # Check DB
        try:
            connections['default'].cursor()
        except Exception:
            status_info["database"] = "error"
            
        # Check Redis (Cache)
        try:
            cache.set("health_check", "ok", timeout=5)
            if cache.get("health_check") != "ok":
                status_info["redis"] = "error"
        except Exception:
            status_info["redis"] = "error"
            
        # Check Celery (Worker status)
        try:
            from core.celery import app
            insp = app.control.inspect()
            stats = insp.stats()
            if not stats:
                status_info["celery"] = "no_workers"
        except Exception:
            status_info["celery"] = "error"
            
        overall_status = status.HTTP_200_OK if all(v == "ok" for v in status_info.values()) else status.HTTP_503_SERVICE_UNAVAILABLE
        
        return Response(status_info, status=overall_status)

from django.http import FileResponse

class DownloadFileView(APIView):
    """
    Endpoint GET /api/task/{task_id}/download/
    Sert le fichier final pour le téléchargement local.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, task_id):
        task = get_object_or_404(DownloadTask, id=task_id)
        
        if task.status != DownloadTask.Status.COMPLETED or not task.result_file:
            return Response({"error": "Le fichier n'est pas encore prêt."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            file_path = task.result_file.path
            if not os.path.exists(file_path):
                return Response({"error": "Fichier physique introuvable sur le serveur."}, status=status.HTTP_404_NOT_FOUND)
            
            filename = os.path.basename(file_path)
            response = FileResponse(open(file_path, 'rb'))
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            logger.error(f"Error serving file for task {task_id}: {e}")
            return Response({"error": "Erreur lors de la récupération du fichier."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PlaylistActionView(StandardizedErrorMixin, APIView):
    """
    Endpoint POST /api/playlist/manage/
    Permet de créer, supprimer ou modifier des playlists sur un provider tiers.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PlaylistManagementSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response("Données invalides", data=serializer.errors)

        data = serializer.validated_data
        action = data['action']
        provider_url = data['provider_url']

        auth_token = data.get('auth_token')
        provider_name = data.get('provider') or (
            'spotify' if 'spotify.com' in provider_url else
            'deezer' if 'deezer.com' in provider_url else
            'apple_music' if 'apple.com' in provider_url else
            'boomplay' if 'boomplay.com' in provider_url or 'boomplaymusic.com' in provider_url else
            None
        )

        if not auth_token:
            if provider_name:
                auth_obj = get_provider_auth(request.user, provider_name)
                if auth_obj:
                    if auth_obj.expires_at and auth_obj.expires_at <= timezone.now() + timedelta(minutes=1):
                        logger.info(f"Token {provider_name} expiré pour {request.user.id}, rafraîchissement...")
                        try:
                            if provider_name == 'spotify':
                                refresh_spotify_token(auth_obj)
                            elif provider_name == 'deezer':
                                refresh_deezer_token(auth_obj)
                            elif provider_name == 'tidal':
                                refresh_tidal_token(auth_obj)
                            auth_obj.refresh_from_db()
                        except Exception as e:
                            logger.error(f"Échec du refresh automatique {provider_name}: {e}")
                    
                    auth_token = auth_obj.access_token

        if not auth_token:
            logger.warning(f"Playlist action {action} requires auth for user {request.user.id}")
            return self.error_response("Veuillez connecter votre compte pour cette action.", status_code=status.HTTP_401_UNAUTHORIZED)

        try:
            effective_url = provider_url.strip()
            
            if not effective_url.startswith(('http://', 'https://')):
                effective_url = 'https://' + effective_url

            lower_url = effective_url.lower()
            provider_domain_map = {
                'spotify.com': 'https://open.spotify.com',
                'deezer.com': 'https://www.deezer.com',
                'apple.com': 'https://music.apple.com',
                'tidal.com': 'https://tidal.com',
                'soundcloud.com': 'https://soundcloud.com',
                'youtube.com': 'https://music.youtube.com',
                'amazon.com': 'https://music.amazon.com',
                'boomplay.com': 'https://www.boomplay.com',
                'boomplaymusic.com': 'https://www.boomplay.com',
            }
            
            for domain, canonical in provider_domain_map.items():
                if domain in lower_url and not any(x in lower_url for x in ['/track/', '/playlist/', '/album/', '/song/']):
                    effective_url = canonical
                    break
                
            try:
                provider = ProviderFactory.get_provider(effective_url, auth_token=auth_token)
            except ValueError:
                explicit_provider = data.get('provider')
                if explicit_provider:
                    try:
                        if explicit_provider == 'spotify':
                            from downloader.providers.spotify import SpotifyProvider
                            provider = SpotifyProvider(auth_token=auth_token)
                        elif explicit_provider == 'deezer':
                            from downloader.providers.deezer import DeezerProvider
                            provider = DeezerProvider(auth_token=auth_token)
                        elif explicit_provider == 'apple_music':
                            from downloader.providers.apple_music import AppleMusicProvider
                            provider = AppleMusicProvider(auth_token=auth_token)
                        elif explicit_provider == 'tidal':
                            from downloader.providers.tidal import TidalProvider
                            provider = TidalProvider(auth_token=auth_token)
                        elif explicit_provider == 'soundcloud':
                            from downloader.providers.soundcloud import SoundCloudProvider
                            provider = SoundCloudProvider(auth_token=auth_token)
                        elif explicit_provider == 'youtube_music':
                            from downloader.providers.youtube_music import YouTubeMusicProvider
                            provider = YouTubeMusicProvider(auth_token=auth_token)
                        elif explicit_provider == 'amazon_music':
                            from downloader.providers.amazon_music import AmazonMusicProvider
                            provider = AmazonMusicProvider(auth_token=auth_token)
                        elif explicit_provider == 'boomplay':
                            from downloader.providers.boomplay import BoomplayProvider
                            provider = BoomplayProvider(auth_token=auth_token)
                        else:
                            raise ValueError(f"Provider explicite non reconnu : {explicit_provider}")
                    except (ImportError, AttributeError):
                        raise ValueError(f"Impossible de charger le provider : {explicit_provider}")
                else:
                    raise

            if action == 'CREATE':
                if not data.get('name'):
                    return self.error_response("Nom requis pour la création")
                p_id = provider.create_playlist(data['name'], description=data.get('description', ''))
                logger.info(f"Playlist created: {p_id} by user {request.user.id}")
                return Response({"status": "created", "playlist_id": p_id}, status=status.HTTP_201_CREATED)

            elif action == 'DELETE':
                if not data.get('playlist_id'):
                    return self.error_response("ID requis pour la suppression")
                
                is_audiobook = data.get('item_type') == 'audiobook' or '/audiobook/' in provider_url
                
                if is_audiobook and hasattr(provider, 'remove_audiobook'):
                    provider.remove_audiobook(data['playlist_id'])
                    logger.info(f"Audiobook {data['playlist_id']} removed by user {request.user.id}")
                else:
                    provider.delete_playlist(data['playlist_id'])
                    logger.info(f"Playlist {data['playlist_id']} deleted by user {request.user.id}")
                
                return Response({"status": "deleted"}, status=status.HTTP_200_OK)

            elif action == 'SAVE_AUDIOBOOK':
                if not data.get('playlist_id'):
                    return self.error_response("ID du livre audio requis")
                if hasattr(provider, 'save_audiobook'):
                    provider.save_audiobook(data['playlist_id'])
                    logger.info(f"Audiobook {data['playlist_id']} saved by user {request.user.id}")
                    return Response({"status": "saved"}, status=status.HTTP_200_OK)
                return self.error_response("Ce provider ne supporte pas l'enregistrement de livres audio.", status_code=status.HTTP_405_METHOD_NOT_ALLOWED)

            elif action == 'ADD_TRACKS':
                if not data.get('playlist_id') or not data.get('track_urls'):
                    return self.error_response("ID et URLs requis")
                new_snapshot = provider.add_tracks_to_playlist(
                    data['playlist_id'],
                    data['track_urls'],
                    position=data.get('position')
                )
                logger.info(f"Tracks added to playlist {data['playlist_id']} by user {request.user.id}")
                return Response({"status": "tracks_added", "snapshot_id": new_snapshot}, status=status.HTTP_200_OK)

            elif action == 'REMOVE_TRACKS':
                if not data.get('playlist_id') or not data.get('track_urls'):
                    return self.error_response("ID et URLs requis")
                new_snapshot = provider.remove_tracks_from_playlist(
                    data['playlist_id'],
                    data['track_urls'],
                    snapshot_id=data.get('snapshot_id')
                )
                logger.info(f"Tracks removed from playlist {data['playlist_id']} by user {request.user.id}")
                return Response({"status": "tracks_removed", "snapshot_id": new_snapshot}, status=status.HTTP_200_OK)

            elif action == 'REORDER':
                if not data.get('playlist_id') or data.get('range_start') is None or data.get('insert_before') is None:
                    return self.error_response("ID, range_start et insert_before requis")
                new_snapshot = provider.reorder_playlist_tracks(
                    data['playlist_id'],
                    range_start=data['range_start'],
                    insert_before=data['insert_before'],
                    range_length=data.get('range_length', 1),
                    snapshot_id=data.get('snapshot_id')
                )
                logger.info(f"Playlist {data['playlist_id']} reordered by user {request.user.id}")
                return Response({"status": "reordered", "snapshot_id": new_snapshot}, status=status.HTTP_200_OK)

            elif action == 'GET_LIST':
                try:
                    items = provider.get_user_playlists()
                    
                    if provider_name == 'spotify' or 'spotify.com' in provider_url:
                        if hasattr(provider, 'get_user_audiobooks'):
                            audiobooks = provider.get_user_audiobooks()
                            items.extend(audiobooks)
                            
                    logger.info(f"Library items (playlists/audiobooks) retrieved for user {request.user.id}")
                    return Response({"status": "success", "playlists": items}, status=status.HTTP_200_OK)
                except Exception as e:
                    if "403" in str(e) and "not registered" in str(e):
                        return self.error_response(
                            "Votre compte Spotify n'est pas autorisé. Ajoutez votre email dans 'Users and Access' sur le Dashboard Spotify.",
                            status_code=status.HTTP_403_FORBIDDEN
                        )
                    raise

            elif action == 'GET_DETAILS':
                details = provider.get_playlist_details(provider_url)
                logger.info(f"Playlist details retrieved: {provider_url}")
                return Response({"status": "success", "details": details}, status=status.HTTP_200_OK)

            elif action == 'GET_LIKES':
                if hasattr(provider, 'get_user_likes'):
                    tracks = provider.get_user_likes()
                    logger.info(f"Likes retrieved for user {request.user.id}")
                    return Response({"status": "success", "tracks": [asdict(t) for t in tracks]}, status=status.HTTP_200_OK)
                return self.error_response("Ce provider ne supporte pas les Likes.", status_code=status.HTTP_405_METHOD_NOT_ALLOWED)

            elif action == 'GET_STREAM':
                if hasattr(provider, 'get_user_stream'):
                    tracks = provider.get_user_stream()
                    logger.info(f"Stream retrieved for user {request.user.id}")
                    return Response({"status": "success", "tracks": [asdict(t) for t in tracks]}, status=status.HTTP_200_OK)
                return self.error_response("Ce provider ne supporte pas le Stream.", status_code=status.HTTP_405_METHOD_NOT_ALLOWED)

            elif action == 'LIKE_TRACK':
                if not data.get('playlist_id'):
                    return self.error_response("ID du titre requis")
                if hasattr(provider, 'like_track'):
                    provider.like_track(data['playlist_id'])
                    logger.info(f"Track liked by user {request.user.id}")
                    return Response({"status": "success"}, status=status.HTTP_200_OK)
                return self.error_response("Ce provider ne supporte pas le Like direct.", status_code=status.HTTP_405_METHOD_NOT_ALLOWED)

        except NotImplementedError as e:
            logger.warning(f"Not implemented action {action}: {e}")
            return self.error_response(str(e), status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
        except Exception as e:
            logger.exception(f"Playlist action {action} error for user {request.user.id}: {e}")
            return self.handle_exception(e)
