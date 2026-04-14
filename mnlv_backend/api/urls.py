from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    SubmitDownloadView, 
    DownloadTaskStatusView, 
    DownloadFileView,
    RegisterView,
    UserProfileView,
    PlaylistActionView,
    ProviderAuthStatusView,
    SpotifyLoginView,
    SpotifyCallbackView,
    DeezerLoginView,
    AppleMusicLoginView
)
from csv_handler.views import CSVUploadView
from media_tools.views import MediaConvertWavView, MediaEditTagsView

app_name = 'api'

urlpatterns = [
    # Auth
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/profile/', UserProfileView.as_view(), name='user_profile'),
    
    # Provider Auth
    path('auth/providers/status/', ProviderAuthStatusView.as_view(), name='provider_status'),
    path('auth/providers/spotify/login/', SpotifyLoginView.as_view(), name='spotify_login'),
    path('auth/providers/spotify/callback/', SpotifyCallbackView.as_view(), name='spotify_callback'),
    path('auth/providers/deezer/login/', DeezerLoginView.as_view(), name='deezer_login'),
    path('auth/providers/apple-music/login/', AppleMusicLoginView.as_view(), name='apple_music_login'),

    # Downloads
    path('download/', SubmitDownloadView.as_view(), name='submit_download'),
    path('task/<uuid:id>/status/', DownloadTaskStatusView.as_view(), name='task_status'),
    path('task/<uuid:task_id>/download/', DownloadFileView.as_view(), name='task_download'),

    # Playlists Management
    path('playlist/manage/', PlaylistActionView.as_view(), name='playlist_manage'),

    # CSV/Batch
    path('csv/upload/', CSVUploadView.as_view(), name='csv_upload'),

    # Media Tools
    path('media/convert-wav/', MediaConvertWavView.as_view(), name='convert_wav'),
    path('media/edit-tags/', MediaEditTagsView.as_view(), name='edit_tags'),
]
