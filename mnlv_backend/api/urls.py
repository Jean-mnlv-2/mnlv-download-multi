from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    SubmitDownloadView, 
    BulkDownloadView,
    DownloadTaskListView,
    BulkCancelTasksView,
    DownloadTaskStatusView, 
    DownloadFileView,
    HealthCheckView,
    RegisterView,
    UserProfileView,
    PlaylistActionView,
    ProviderAuthStatusView,
    SpotifyLoginView,
    SpotifyCallbackView,
    DeezerLoginView,
    DeezerCallbackView,
    SoundCloudLoginView,
    SoundCloudCallbackView,
    AmazonMusicLoginView,
    TidalLoginView,
    TidalCallbackView,
    AppleMusicLoginView,
    AppleMusicTokenView,
    AppleMusicPlaylistsView,
    AppleMusicSearchView,
    DeezerFlowView,
    DeezerFavoritesView,
    DeezerSearchView,
    DeezerChartsView
)
from csv_handler.views import CSVUploadView, PendingUploadsView
from media_tools.views import MediaConvertView, MediaEditTagsView

app_name = 'api'

urlpatterns = [
    # Auth
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/profile/', UserProfileView.as_view(), name='user_profile'),
    path('health/', HealthCheckView.as_view(), name='health_check'),
    
    # Provider Auth
    path('auth/providers/status/', ProviderAuthStatusView.as_view(), name='provider_status'),
    path('auth/providers/spotify/login/', SpotifyLoginView.as_view(), name='spotify_login'),
    path('auth/providers/spotify/callback/', SpotifyCallbackView.as_view(), name='spotify_callback'),
    path('auth/providers/apple-music/login/', AppleMusicLoginView.as_view(), name='apple_music_login'),
    path('auth/providers/apple-music/token/', AppleMusicTokenView.as_view(), name='apple_music_token'),
    path('auth/providers/apple-music/playlists/', AppleMusicPlaylistsView.as_view(), name='apple_music_playlists'),
    path('auth/providers/apple-music/search/', AppleMusicSearchView.as_view(), name='apple_music_search'),
    path('auth/providers/deezer/login/', DeezerLoginView.as_view(), name='deezer_login'),
    path('auth/providers/deezer/callback/', DeezerCallbackView.as_view(), name='deezer_callback'),
    path('auth/providers/soundcloud/login/', SoundCloudLoginView.as_view(), name='soundcloud_login'),
    path('auth/providers/soundcloud/callback/', SoundCloudCallbackView.as_view(), name='soundcloud_callback'),
    path('auth/providers/amazon-music/login/', AmazonMusicLoginView.as_view(), name='amazon_music_login'),
    path('auth/providers/tidal/login/', TidalLoginView.as_view(), name='tidal_login'),
    path('auth/providers/tidal/callback/', TidalCallbackView.as_view(), name='tidal_callback'),
    path('auth/providers/deezer/flow/', DeezerFlowView.as_view(), name='deezer_flow'),
    path('auth/providers/deezer/favorites/', DeezerFavoritesView.as_view(), name='deezer_favorites'),
    path('auth/providers/deezer/search/', DeezerSearchView.as_view(), name='deezer_search'),
    path('auth/providers/deezer/charts/', DeezerChartsView.as_view(), name='deezer_charts'),

    # Downloads
    path('download/', SubmitDownloadView.as_view(), name='submit_download'),
    path('download/bulk/', BulkDownloadView.as_view(), name='bulk_download'),
    path('tasks/history/', DownloadTaskListView.as_view(), name='tasks_history'),
    path('tasks/cancel-all/', BulkCancelTasksView.as_view(), name='tasks_cancel_all'),
    path('task/<uuid:id>/status/', DownloadTaskStatusView.as_view(), name='task_status'),
    path('task/<uuid:task_id>/download/', DownloadFileView.as_view(), name='task_download'),

    # Playlists Management
    path('playlist/manage/', PlaylistActionView.as_view(), name='playlist_manage'),

    # CSV/Batch
    path('csv/upload/', CSVUploadView.as_view(), name='csv_upload'),
    path('csv/pending/', PendingUploadsView.as_view(), name='csv_pending'),

    # Media Tools
    path('media/convert/', MediaConvertView.as_view(), name='media_convert'),
    path('media/edit-tags/', MediaEditTagsView.as_view(), name='media_edit_tags'),
]
