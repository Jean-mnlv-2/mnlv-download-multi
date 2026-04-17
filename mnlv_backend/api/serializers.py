from rest_framework import serializers
from django.contrib.auth.models import User
from downloader.models import DownloadTask, TrackMetadata

class UserSerializer(serializers.ModelSerializer):
    """
    Sérialiseur pour la création et l'affichage des utilisateurs.
    """
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user

class TrackMetadataSerializer(serializers.ModelSerializer):
    """
    Sérialiseur pour les métadonnées d'une chanson.
    """
    class Meta:
        model = TrackMetadata
        fields = '__all__'

class DownloadTaskSerializer(serializers.ModelSerializer):
    """
    Sérialiseur complet pour le suivi d'une tâche de téléchargement.
    """
    track = TrackMetadataSerializer(read_only=True)
    result_file = serializers.SerializerMethodField()
    result_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = DownloadTask
        fields = [
            'id', 'original_url', 'provider', 'status', 'progress', 
            'media_type', 'quality', 'result_file', 'result_file_url', 'error_message', 
            'track', 'created_at', 'updated_at'
        ]
    
    def get_result_file(self, obj: DownloadTask):
        if not obj.result_file:
            return None
        return obj.result_file.name
    
    def get_result_file_url(self, obj: DownloadTask):
        if not obj.result_file:
            return None
        try:
            return obj.result_file.url
        except Exception:
            return None

class CreateDownloadTaskSerializer(serializers.Serializer):
    """
    Sérialiseur pour la création d'une nouvelle tâche.
    Validation de l'URL source.
    """
    url = serializers.URLField(required=True)
    media_type = serializers.ChoiceField(
        choices=DownloadTask.MediaType.choices, 
        default=DownloadTask.MediaType.AUDIO
    )
    quality = serializers.CharField(required=False, default="192")
    prefer_video = serializers.BooleanField(default=False)
    explicit_filter = serializers.BooleanField(default=False)
    
    def validate_quality(self, value: str):
        if value is None:
            return "192"
        normalized = str(value).strip().lower()
        normalized = normalized.replace("kbps", "").replace("k", "")
        normalized = normalized.strip()
        if normalized in {"128", "192", "256", "320", "720", "1080"}:
            return normalized
        return "192"

class PlaylistManagementSerializer(serializers.Serializer):
    """
    Sérialiseur pour la gestion des playlists (création/ajout).
    """
    provider_url = serializers.URLField(required=True, help_text="URL du provider (ex: spotify.com)")
    name = serializers.CharField(required=False, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    track_urls = serializers.ListField(
        child=serializers.URLField(), 
        required=False, 
        help_text="Liste des URLs des titres à ajouter/supprimer"
    )
    auth_token = serializers.CharField(required=False, allow_null=True, help_text="Jeton OAuth du provider (optionnel si déjà connecté)")
    provider = serializers.CharField(required=False, help_text="Nom du provider (ex: spotify)")
    playlist_id = serializers.CharField(required=False, help_text="ID de la playlist (pour ajout/suppression)")
    action = serializers.ChoiceField(
        choices=['CREATE', 'DELETE', 'ADD_TRACKS', 'REMOVE_TRACKS', 'GET_LIST', 'GET_DETAILS', 'REORDER', 'GET_LIKES', 'GET_STREAM', 'LIKE_TRACK'], 
        default='CREATE'
    )
    range_start = serializers.IntegerField(required=False)
    insert_before = serializers.IntegerField(required=False)
    range_length = serializers.IntegerField(required=False, default=1)
    snapshot_id = serializers.CharField(required=False, allow_null=True)
    position = serializers.IntegerField(required=False, allow_null=True)
