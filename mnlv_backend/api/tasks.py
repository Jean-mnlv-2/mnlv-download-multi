from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from .models import ProviderAuth
import requests
from spotipy.oauth2 import SpotifyOAuth
import logging
import asyncio
from asgiref.sync import sync_to_async

logger = logging.getLogger("api.tasks")

@shared_task(name="api.tasks.refresh_provider_tokens")
def refresh_provider_tokens():
    """
    Tâche périodique pour rafraîchir les tokens d'accès des providers
    avant qu'ils n'expirent (ex: 15 minutes avant).
    Utilise asyncio pour paralléliser les appels I/O.
    """
    threshold = timezone.now() + timedelta(minutes=15)
    expired_auths = ProviderAuth.objects.filter(expires_at__lte=threshold).iterator()
    
    logger.info(f"Checking for tokens to refresh (threshold: {threshold})")
    
    async def refresh_all():
        tasks = []
        for auth in expired_auths:
            if auth.provider == 'spotify':
                tasks.append(sync_to_async(refresh_spotify_token)(auth))
            elif auth.provider == 'deezer':
                tasks.append(sync_to_async(refresh_deezer_token)(auth))
            elif auth.provider == 'tidal':
                tasks.append(sync_to_async(refresh_tidal_token)(auth))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(refresh_all())
    finally:
        loop.close()

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
    """
    Rafraîchit le token Deezer via l'API OAuth.
    """
    token_url = "https://connect.deezer.com/oauth/access_token.php"
    params = {
        'app_id': settings.DEEZER_APP_ID,
        'secret': settings.DEEZER_SECRET_KEY,
        'code': auth.refresh_token,
        'output': 'json'
    }
    
    try:
        logger.info(f"Deezer refresh not fully implemented as per Deezer SDK specs (often long-lived)")
        pass
    except Exception as e:
        logger.error(f"Error refreshing Deezer token: {e}")

def refresh_tidal_token(auth):
    """
    Rafraîchit le token Tidal via OAuth2.
    Utilise l'URL canonique auth.tidal.com
    """
    token_url = "https://auth.tidal.com/v1/oauth2/token"
    
    if not auth.refresh_token:
        logger.error(f"No refresh token for Tidal user {auth.user.id}")
        raise ValueError("No refresh token available for Tidal")

    data = {
        'grant_type': 'refresh_token',
        'refresh_token': auth.refresh_token,
        'client_id': settings.TIDAL_CLIENT_ID,
    }
    
    if settings.TIDAL_CLIENT_SECRET:
        data['client_secret'] = settings.TIDAL_CLIENT_SECRET
    
    try:
        logger.info(f"Attempting Tidal token refresh for user {auth.user.id} at {token_url}")
        response = requests.post(token_url, data=data)
        
        if response.status_code != 200:
            logger.warning(f"Tidal refresh failed ({response.status_code}), trying with Basic Auth header")
            auth_header = (settings.TIDAL_CLIENT_ID, settings.TIDAL_CLIENT_SECRET)
            response = requests.post(token_url, data=data, auth=auth_header)
            
        if response.status_code == 200:
            token_data = response.json()
            auth.access_token = token_data['access_token']
            if token_data.get('refresh_token'):
                auth.refresh_token = token_data['refresh_token']
            
            expires_in = int(token_data.get('expires_in', 3600))
            auth.expires_at = timezone.now() + timedelta(seconds=expires_in)
            auth.save()
            logger.info(f"Tidal token refreshed successfully for user {auth.user.id}")
        else:
            logger.error(f"Failed to refresh Tidal token: {response.status_code} - {response.text}")
            raise Exception(f"Tidal refresh failed: {response.text}")
    except Exception as e:
        logger.error(f"Error refreshing Tidal token for user {auth.user.id}: {e}")
        raise
