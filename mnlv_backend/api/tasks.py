from celery import shared_task
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta
from django.conf import settings
from .models import ProviderAuth
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import logging

logger = logging.getLogger("api.tasks")

@shared_task(name="api.tasks.refresh_provider_tokens")
def refresh_provider_tokens():
    """
    Tâche périodique pour rafraîchir les tokens d'accès des providers
    avant qu'ils n'expirent (ex: 15 minutes avant).
    """
    threshold = timezone.now() + timedelta(minutes=15)
    expired_auths = ProviderAuth.objects.filter(expires_at__lte=threshold)
    
    logger.info(f"Checking for tokens to refresh (threshold: {threshold})")
    
    for auth in expired_auths:
        try:
            if auth.provider == 'spotify':
                refresh_spotify_token(auth)
            elif auth.provider == 'deezer':
                refresh_deezer_token(auth)
            elif auth.provider == 'tidal':
                refresh_tidal_token(auth)
        except Exception as e:
            logger.error(f"Failed to refresh {auth.provider} token for user {auth.user.id}: {e}")

def refresh_spotify_token(auth):
    sp_oauth = SpotifyOAuth(
        client_id=settings.SPOTIFY_CLIENT_ID,
        client_secret=settings.SPOTIFY_CLIENT_SECRET,
        redirect_uri=settings.SPOTIFY_REDIRECT_URI
    )
    token_info = sp_oauth.refresh_access_token(auth.refresh_token)
    if token_info:
        auth.access_token = token_info['access_token']
        if token_info.get('refresh_token'):
            auth.refresh_token = token_info['refresh_token']
        auth.expires_at = timezone.now() + timedelta(seconds=token_info['expires_in'])
        auth.save()
        logger.info(f"Spotify token refreshed for user {auth.user.id}")

def refresh_deezer_token(auth):
    pass

def refresh_tidal_token(auth):
    pass
