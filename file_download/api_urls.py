from django.urls import path
from . import api_views

# This module is included under prefix 'api/downloads/' in project urls.
# So the final endpoint is: /api/downloads/start/
urlpatterns = [
    path('start/', api_views.downloads_start, name='downloads_start'),
    path('status/', api_views.downloads_status, name='downloads_status'),
    path('cancel/', api_views.downloads_cancel, name='downloads_cancel'),
]