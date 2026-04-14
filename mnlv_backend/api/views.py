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

class AppleMusicLoginView(APIView):
    """
    Placeholder pour le login Apple Music
    """
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        return Response({"message": "Le flux OAuth Apple Music sera bientôt disponible."}, status=status.HTTP_200_OK)

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

class DownloadRateThrottle(UserRateThrottle):
    scope = 'downloads'

class SubmitDownloadView(APIView):
    """
    Endpoint POST /api/download/
    Reçoit l'URL, valide, crée une ou plusieurs DownloadTask et lance Celery.
    """
    throttle_classes = [DownloadRateThrottle]
    
    def post(self, request):
        serializer = CreateDownloadTaskSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        url = serializer.validated_data['url']
        media_type = serializer.validated_data.get('media_type', DownloadTask.MediaType.AUDIO)
        quality = serializer.validated_data.get('quality')
        
        try:
            provider = ProviderFactory.get_provider(url)
            provider_name = provider.__class__.__name__.lower().replace("provider", "")
            
            if "/playlist/" in url or "/album/" in url:
                tracks = provider.get_playlist_tracks(url)
                tasks_info = []
                
                for track in tracks:
                    task = DownloadTask.objects.create(
                        user=request.user,
                        original_url=track.original_url or url,
                        provider=provider_name,
                        media_type=media_type,
                        quality=quality
                    )
                    process_playlist_item.delay(str(task.id))
                    tasks_info.append({"task_id": str(task.id), "title": track.title})
                
                return Response({
                    "type": "playlist",
                    "count": len(tasks_info),
                    "tasks": tasks_info
                }, status=status.HTTP_201_CREATED)
            
            else:
                # Track unique
                task = DownloadTask.objects.create(
                    user=request.user,
                    original_url=url,
                    provider=provider_name,
                    media_type=media_type,
                    quality=quality
                )
                process_single_track.delay(str(task.id))
                
                return Response({
                    "type": "track",
                    "task_id": str(task.id),
                    "status": task.status,
                    "provider": task.provider
                }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Erreur serveur : {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DownloadTaskStatusView(RetrieveAPIView):
    """
    Endpoint GET /api/task/{task_id}/status/
    Récupère l'état d'avancement d'une tâche (polling).
    """
    queryset = DownloadTask.objects.all()
    serializer_class = DownloadTaskSerializer
    lookup_field = 'id'

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
            provider_name = data.get('provider') or ('spotify' if 'spotify.com' in provider_url else 'deezer' if 'deezer.com' in provider_url else None)
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
                provider.add_tracks_to_playlist(data['playlist_id'], data['track_urls'])
                return Response({"status": "tracks_added"}, status=status.HTTP_200_OK)
                
            elif action == 'REMOVE_TRACKS':
                if not data.get('playlist_id') or not data.get('track_urls'):
                    return Response({"error": "ID et URLs requis"}, status=status.HTTP_400_BAD_REQUEST)
                provider.remove_tracks_from_playlist(data['playlist_id'], data['track_urls'])
                return Response({"status": "tracks_removed"}, status=status.HTTP_200_OK)
                
            elif action == 'GET_LIST':
                playlists = provider.get_user_playlists()
                return Response({"status": "success", "playlists": playlists}, status=status.HTTP_200_OK)
                
            elif action == 'GET_DETAILS':
                details = provider.get_playlist_details(provider_url)
                return Response({"status": "success", "details": details}, status=status.HTTP_200_OK)
                
        except NotImplementedError as e:
            return Response({"error": str(e)}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        except Exception as e:
            return Response({"error": f"Erreur provider : {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
