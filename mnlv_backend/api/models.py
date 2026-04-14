from django.db import models
from django.contrib.auth.models import User

class ProviderAuth(models.Model):
    """
    Stockage sécurisé des tokens d'authentification pour les providers tiers.
    """
    PROVIDER_CHOICES = [
        ('spotify', 'Spotify'),
        ('deezer', 'Deezer'),
        ('apple_music', 'Apple Music'),
        ('tidal', 'Tidal'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='provider_auths')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    

    access_token = models.TextField()
    refresh_token = models.TextField(null=True, blank=True)
    
    expires_at = models.DateTimeField(null=True, blank=True)
    
    provider_user_id = models.CharField(max_length=255, null=True, blank=True)
    provider_user_name = models.CharField(max_length=255, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'provider')

    def __str__(self):
        return f"{self.user.username} - {self.provider}"
