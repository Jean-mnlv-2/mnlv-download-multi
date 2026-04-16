from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView, CreateAPIView
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.models import User
from django.conf import settings
from downloader.models import DownloadTask
from downloader.tasks import process_single_track, process_playlist_item
from downloader.providers.factory import ProviderFactory
from .models import ProviderAuth
from .serializers import (
    DownloadTaskSerializer, 
    CreateDownloadTaskSerializer, 
    UserSerializer,
    PlaylistManagementSerializer
)
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os

class ProviderAuthStatusView(APIView):
    """
    Endpoint GET /api/auth/providers/status/
    Vérifie quels providers sont connectés pour l'utilisateur.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        auths = ProviderAuth.objects.filter(user=request.user)
        status_dict = {
            'spotify': auths.filter(provider='spotify').exists(),
            'deezer': auths.filter(provider='deezer').exists(),
            'apple_music': auths.filter(provider='apple_music').exists(),
        }
        return Response(status_dict)

from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import login as django_login

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
                    access_token = AccessToken(token)
                    user = User.objects.get(id=access_token['user_id'])
                except Exception:
                    return Response({"error": "Token invalide ou expiré"}, status=status.HTTP_401_UNAUTHORIZED)
        
        if user.is_anonymous:
            return Response({"error": "Authentification requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            sp_oauth = SpotifyOAuth(
                client_id=settings.SPOTIFY_CLIENT_ID,
                client_secret=settings.SPOTIFY_CLIENT_SECRET,
                redirect_uri=settings.SPOTIFY_REDIRECT_URI,
                scope="playlist-modify-public playlist-modify-private playlist-read-private user-library-read",
                state=str(user.id)
            )
            auth_url = sp_oauth.get_authorize_url()
            
            if "text/html" in request.accepted_media_type:
                return redirect(auth_url)
            
            return Response({"auth_url": auth_url}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Erreur lors de la génération de l'URL : {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SpotifyCallbackView(APIView):
    """
    Endpoint GET /api/auth/providers/spotify/callback/
    Gère le retour de Spotify et stocke le token.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        code = request.GET.get('code')
        user_id = request.GET.get('state')
        
        if not code or not user_id:
            return Response({"error": "Code ou State manquant"}, status=status.HTTP_400_BAD_REQUEST)

        sp_oauth = SpotifyOAuth(
            client_id=settings.SPOTIFY_CLIENT_ID,
            client_secret=settings.SPOTIFY_CLIENT_SECRET,
            redirect_uri=settings.SPOTIFY_REDIRECT_URI
        )
        
        try:
            token_info = sp_oauth.get_access_token(code)
            user = User.objects.get(id=user_id)

            ProviderAuth.objects.update_or_create(
                user=user,
                provider='spotify',
                defaults={
                    'access_token': token_info['access_token'],
                    'refresh_token': token_info.get('refresh_token'),
                }
            )
            return redirect('http://localhost:3003/?auth_success=spotify')
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeezerLoginView(APIView):
    """
    Placeholder pour le login Deezer
    """
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        return Response({"message": "Le flux OAuth Deezer sera bientôt disponible."}, status=status.HTTP_200_OK)

from downloader.providers.apple_music.provider import AppleMusicProvider
from downloader.providers.deezer.provider import DeezerProvider
from dataclasses import asdict

class AppleMusicTokenView(APIView):
    """
    Endpoint GET /api/auth/providers/apple-music/token/
    Retourne le Developer Token (JWT) pour MusicKit JS.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            provider = AppleMusicProvider()
            token = provider.am.token
            return Response({"token": token})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
            ProviderAuth.objects.update_or_create(
                user=request.user,
                provider='apple_music',
                defaults={
                    'access_token': music_user_token,
                }
            )
            return Response({"message": "Connexion Apple Music réussie"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AppleMusicPlaylistsView(APIView):
    """
    Endpoint GET /api/auth/providers/apple-music/playlists/
    Récupère les playlists de l'utilisateur.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        auth = ProviderAuth.objects.filter(user=request.user, provider='apple_music').first()
        if not auth:
            return Response({"error": "Connexion Apple Music requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            provider = AppleMusicProvider(auth_token=auth.access_token)
            playlists = provider.get_user_playlists()
            return Response(playlists)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AppleMusicSearchView(APIView):
    """
    Endpoint GET /api/auth/providers/apple-music/search/
    Recherche dans le catalogue ou la bibliothèque Apple Music.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q')
        storefront = request.query_params.get('storefront', 'us')
        scope = request.query_params.get('scope', 'catalog') # 'catalog' ou 'library'
        
        if not query:
            return Response({"error": "Requête de recherche manquante"}, status=status.HTTP_400_BAD_REQUEST)

        auth = ProviderAuth.objects.filter(user=request.user, provider='apple_music').first()
        auth_token = auth.access_token if auth else None

        try:
            provider = AppleMusicProvider(auth_token=auth_token)
            if scope == 'library':
                if not auth_token:
                    return Response({"error": "Connexion Apple Music requise pour la recherche bibliothèque"}, status=status.HTTP_401_UNAUTHORIZED)
                results = provider.search_library(query)
            else:
                results = provider.search(query, storefront=storefront)
                
            return Response(results)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeezerFlowView(APIView):
    """Récupère et lance le téléchargement du Flow Deezer"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        auth = ProviderAuth.objects.filter(user=request.user, provider='deezer').first()
        if not auth:
            return Response({"error": "Connexion Deezer requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        provider = DeezerProvider(auth_token=auth.access_token)
        tracks = provider.get_user_flow()
        
        tasks_info = []
        for track in tracks:
            task = DownloadTask.objects.create(
                user=request.user,
                original_url=track.original_url,
                provider='deezer',
                media_type=DownloadTask.MediaType.AUDIO
            )
            process_playlist_item.delay(str(task.id))
            tasks_info.append({"task_id": str(task.id), "title": track.title})
            
        return Response({"type": "flow", "tasks": tasks_info}, status=status.HTTP_201_CREATED)

class DeezerFavoritesView(APIView):
    """Récupère les favoris Deezer"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        auth = ProviderAuth.objects.filter(user=request.user, provider='deezer').first()
        if not auth:
            return Response({"error": "Connexion Deezer requise"}, status=status.HTTP_401_UNAUTHORIZED)
        
        provider = DeezerProvider(auth_token=auth.access_token)
        tracks = provider.get_user_favorites()
        return Response([t.__dict__ for t in tracks])

class DeezerSearchView(APIView):
    """Recherche Smart Search Deezer"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        query = request.GET.get('q')
        if not query:
            return Response({"error": "Requête manquante"}, status=status.HTTP_400_BAD_REQUEST)
        
        provider = DeezerProvider()
        results = provider.search(query)
        return Response(results)

class DeezerChartsView(APIView):
    """Récupère les tendances Deezer"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        provider = DeezerProvider()
        charts = provider.get_charts()
        return Response(charts)

class RegisterView(CreateAPIView):
    """
    Endpoint POST /api/auth/register/
    Création d'un nouvel utilisateur.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

class UserProfileView(APIView):
    """
    Endpoint GET /api/auth/profile/
    Récupère les informations de l'utilisateur connecté.
    """
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

from rest_framework.throttling import UserRateThrottle

from .mixins import StandardizedErrorMixin

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
        media_type = serializer.validated_data.get('media_type', DownloadTask.MediaType.AUDIO)
        prefer_video = serializer.validated_data.get('prefer_video', False)
        quality = serializer.validated_data.get('quality')
        explicit_filter = serializer.validated_data.get('explicit_filter', False)
        
        try:
            provider = ProviderFactory.get_provider(url)
            provider_name = provider.__class__.__name__.lower().replace("provider", "")
            
            if "/playlist/" in url or "/album/" in url:
                tracks = provider.get_playlist_tracks(url)
                tasks_info = []
                
                for track in tracks:
                    # Filtre explicite
                    if explicit_filter and getattr(track, 'explicit', False):
                        continue
                        
                    task = DownloadTask.objects.create(
                        user=request.user,
                        original_url=track.original_url or url,
                        provider=provider_name,
                        media_type=media_type,
                        prefer_video=prefer_video,
                        quality=quality,
                        explicit_filter=explicit_filter
                    )
                    process_playlist_item.delay(str(task.id))
                    tasks_info.append({"task_id": str(task.id), "title": track.title})
                
                return Response({
                    "status": "success",
                    "type": "playlist",
                    "count": len(tasks_info),
                    "tasks": tasks_info,
                    "provider": provider_name
                }, status=status.HTTP_201_CREATED)
            
            else:
                # Track unique
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

class DownloadTaskStatusView(RetrieveAPIView):
    """
    Endpoint GET /api/task/{task_id}/status/
    Récupère l'état d'avancement d'une tâche (polling).
    """
    queryset = DownloadTask.objects.all()
    serializer_class = DownloadTaskSerializer
    lookup_field = 'id'

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

class DownloadFileView(APIView):
    """
    Endpoint GET /api/task/{task_id}/download/
    Fournit le fichier final si le téléchargement est terminé.
    """
    def get(self, request, task_id):
        task = get_object_or_404(DownloadTask, id=task_id)
        if task.status != DownloadTask.Status.COMPLETED or not task.result_file:
            return Response({"error": "Le fichier n'est pas encore prêt."}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({"download_url": task.result_file.url}, status=status.HTTP_200_OK)

class PlaylistActionView(APIView):
    """
    Endpoint POST /api/playlist/manage/
    Permet de créer, supprimer ou modifier des playlists sur un provider tiers.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PlaylistManagementSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        data = serializer.validated_data
        action = data['action']
        provider_url = data['provider_url']
        
        # Récupération automatique du token si non fourni
        auth_token = data.get('auth_token')
        if not auth_token:
            # On devine le provider depuis l'URL ou le champ provider
            provider_name = data.get('provider') or (
                'spotify' if 'spotify.com' in provider_url else 
                'deezer' if 'deezer.com' in provider_url else 
                'apple_music' if 'apple.com' in provider_url else 
                None
            )
            if provider_name:
                auth_obj = ProviderAuth.objects.filter(user=request.user, provider=provider_name).first()
                if auth_obj:
                    auth_token = auth_obj.access_token
        
        if not auth_token:
            return Response({"error": "Veuillez connecter votre compte pour cette action."}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            provider = ProviderFactory.get_provider(provider_url, auth_token=auth_token)
            
            if action == 'CREATE':
                if not data.get('name'):
                    return Response({"error": "Nom requis pour la création"}, status=status.HTTP_400_BAD_REQUEST)
                p_id = provider.create_playlist(data['name'], description=data.get('description', ''))
                return Response({"status": "created", "playlist_id": p_id}, status=status.HTTP_201_CREATED)
                
            elif action == 'DELETE':
                if not data.get('playlist_id'):
                    return Response({"error": "ID requis pour la suppression"}, status=status.HTTP_400_BAD_REQUEST)
                provider.delete_playlist(data['playlist_id'])
                return Response({"status": "deleted"}, status=status.HTTP_200_OK)
                
            elif action == 'ADD_TRACKS':
                if not data.get('playlist_id') or not data.get('track_urls'):
                    return Response({"error": "ID et URLs requis"}, status=status.HTTP_400_BAD_REQUEST)
                new_snapshot = provider.add_tracks_to_playlist(
                    data['playlist_id'], 
                    data['track_urls'], 
                    position=data.get('position')
                )
                return Response({"status": "tracks_added", "snapshot_id": new_snapshot}, status=status.HTTP_200_OK)
                
            elif action == 'REMOVE_TRACKS':
                if not data.get('playlist_id') or not data.get('track_urls'):
                    return Response({"error": "ID et URLs requis"}, status=status.HTTP_400_BAD_REQUEST)
                new_snapshot = provider.remove_tracks_from_playlist(
                    data['playlist_id'], 
                    data['track_urls'], 
                    snapshot_id=data.get('snapshot_id')
                )
                return Response({"status": "tracks_removed", "snapshot_id": new_snapshot}, status=status.HTTP_200_OK)

            elif action == 'REORDER':
                if not data.get('playlist_id') or data.get('range_start') is None or data.get('insert_before') is None:
                    return Response({"error": "ID, range_start et insert_before requis"}, status=status.HTTP_400_BAD_REQUEST)
                new_snapshot = provider.reorder_playlist_tracks(
                    data['playlist_id'],
                    range_start=data['range_start'],
                    insert_before=data['insert_before'],
                    range_length=data.get('range_length', 1),
                    snapshot_id=data.get('snapshot_id')
                )
                return Response({"status": "reordered", "snapshot_id": new_snapshot}, status=status.HTTP_200_OK)
                
            elif action == 'GET_LIST':
                playlists = provider.get_user_playlists()
                return Response({"status": "success", "playlists": playlists}, status=status.HTTP_200_OK)
                
            elif action == 'GET_DETAILS':
                details = provider.get_playlist_details(provider_url)
                return Response({"status": "success", "details": details}, status=status.HTTP_200_OK)

            elif action == 'GET_LIKES':
                if hasattr(provider, 'get_user_likes'):
                    tracks = provider.get_user_likes()
                    return Response({"status": "success", "tracks": [asdict(t) for t in tracks]}, status=status.HTTP_200_OK)
                return Response({"error": "Ce provider ne supporte pas les Likes."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

            elif action == 'GET_STREAM':
                if hasattr(provider, 'get_user_stream'):
                    tracks = provider.get_user_stream()
                    return Response({"status": "success", "tracks": [asdict(t) for t in tracks]}, status=status.HTTP_200_OK)
                return Response({"error": "Ce provider ne supporte pas le Stream."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

            elif action == 'LIKE_TRACK':
                if not data.get('playlist_id'):
                    return Response({"error": "ID du titre requis"}, status=status.HTTP_400_BAD_REQUEST)
                if hasattr(provider, 'like_track'):
                    provider.like_track(data['playlist_id'])
                    return Response({"status": "success"}, status=status.HTTP_200_OK)
                return Response({"error": "Ce provider ne supporte pas le Like direct."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
                
        except NotImplementedError as e:
            return Response({"error": str(e)}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        except Exception as e:
            return Response({"error": f"Erreur provider : {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
