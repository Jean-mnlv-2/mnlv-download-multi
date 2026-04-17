from django.db import models
import uuid

class TrackMetadata(models.Model):
    """
    Cache pour les métadonnées des morceaux afin d'éviter les appels API redondants.
    Identifié de façon unique par le code ISRC.
    """
    isrc = models.CharField(max_length=20, unique=True, null=True, blank=True)
    title = models.CharField(max_length=500)
    artist = models.CharField(max_length=500)
    album = models.CharField(max_length=500, null=True, blank=True)
    release_year = models.IntegerField(null=True, blank=True)
    cover_url = models.URLField(max_length=1000, null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.artist} - {self.title}"

class DownloadTask(models.Model):
    """
    Suivi du cycle de vie d'une tâche de téléchargement asynchrone.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'En attente'
        PROCESSING = 'PROCESSING', 'En cours'
        COMPLETED = 'COMPLETED', 'Terminé'
        FAILED = 'FAILED', 'Échoué'

    class MediaType(models.TextChoices):
        AUDIO = 'AUDIO', 'Audio (MP3)'
        VIDEO = 'VIDEO', 'Vidéo (MP4)'
        WAV = 'WAV', 'Professionnel (WAV)'
        FLAC = 'FLAC', 'Professionnel (FLAC)'
        ALAC = 'ALAC', 'Professionnel (ALAC/Apple)'
        OPUS = 'OPUS', 'WebRadio (OPUS)'
        AAC = 'AAC', 'WebRadio/TV (AAC)'
        MKV = 'MKV', 'Haute Qualité Vidéo (MKV)'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_url = models.TextField()
    provider = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    progress = models.IntegerField(default=0)
    media_type = models.CharField(max_length=10, choices=MediaType.choices, default=MediaType.AUDIO)
    prefer_video = models.BooleanField(default=False)
    quality = models.CharField(max_length=20, null=True, blank=True)
    explicit_filter = models.BooleanField(default=False) # Si True, ignore les titres explicites
    result_file = models.FileField(upload_to='downloads/', null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    
    track = models.ForeignKey(TrackMetadata, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Task {self.id} - {self.status}"

    def save(self, *args, **kwargs):
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        is_new = self._state.adding
        super().save(*args, **kwargs)
        
        if self.user:
            channel_layer = get_channel_layer()
            group_name = f"user_{self.user.id}_tasks"
            
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "task_update",
                    "data": {
                        "task_id": str(self.id),
                        "status": self.status,
                        "progress": self.progress,
                        "error": self.error_message,
                        "result_file": self.result_file.url if self.result_file else None
                    }
                }
            )
