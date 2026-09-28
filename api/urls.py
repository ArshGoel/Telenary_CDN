from django.urls import path
from api import views

urlpatterns = [
    # Dashboard & Developer Portal
    path('', views.dashboard_view, name='dashboard'),

    # Cloudinary REST API v1 Endpoints
    path('api/v1/upload', views.api_v1_upload, name='api_v1_upload'),
    path('api/v1/upload/', views.api_v1_upload, name='api_v1_upload_slash'),
    path('api/v1/resources', views.api_v1_resources, name='api_v1_resources'),
    path('api/v1/resources/', views.api_v1_resources, name='api_v1_resources_slash'),
    path('api/v1/resources/<uuid:asset_id>', views.api_v1_resource_detail, name='api_v1_resource_detail'),
    
    # CDN Streaming & Dynamic Image Transformation
    path('api/v1/media/<uuid:asset_id>/stream', views.api_v1_stream, name='api_v1_stream'),
    path('api/v1/media/<uuid:asset_id>/thumbnail', views.api_v1_thumbnail, name='api_v1_thumbnail'),
    path('api/v1/media/<uuid:asset_id>/transform', views.api_v1_transform, name='api_v1_transform'),
    
    # API Keys Management
    path('api/v1/keys', views.api_v1_keys, name='api_v1_keys'),
]
