from django.urls import path
from .views import (
    AdAccountsView,
    BusinessesView,
    CampaignsView,
    AdSetsView,
    AdsView,
    AssetsView,
    ReportsView,
    AsyncReportsView,
    TargetingView,
    PixelsView,
    AudiencesView,
    CapiView,
    EstimationsView,
    AssetUploadView
)

app_name = 'spotify_ads'

urlpatterns = [
    path('ad_accounts/', AdAccountsView.as_view(), name='ad_accounts'),
    path('businesses/', BusinessesView.as_view(), name='businesses'),
    path('ad_accounts/<str:ad_account_id>/campaigns/', CampaignsView.as_view(), name='campaigns'),
    path('ad_accounts/<str:ad_account_id>/ad_sets/', AdSetsView.as_view(), name='ad_sets'),
    path('ad_accounts/<str:ad_account_id>/ads/', AdsView.as_view(), name='ads'),
    path('ad_accounts/<str:ad_account_id>/assets/', AssetsView.as_view(), name='assets'),
    path('ad_accounts/<str:ad_account_id>/assets/upload/', AssetUploadView.as_view(), name='assets_upload'),
    path('ad_accounts/<str:ad_account_id>/reports/<str:report_type>/', ReportsView.as_view(), name='reports'),
    path('ad_accounts/<str:ad_account_id>/async_reports/', AsyncReportsView.as_view(), name='async_reports'),
    path('ad_accounts/<str:ad_account_id>/async_reports/<str:report_id>/', AsyncReportsView.as_view(), name='async_report_status'),
    path('ad_accounts/<str:ad_account_id>/audiences/', AudiencesView.as_view(), name='audiences'),
    path('ad_accounts/<str:ad_account_id>/estimations/<str:est_type>/', EstimationsView.as_view(), name='estimations'),
    path('targeting/<str:target_type>/', TargetingView.as_view(), name='targeting'),
    path('businesses/<str:business_id>/pixels/', PixelsView.as_view(), name='pixels'),
    path('businesses/<str:business_id>/capi_integrations/', CapiView.as_view(), name='capi'),
]
