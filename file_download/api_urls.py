from django.urls import path
from . import api_views

urlpatterns = [
    path('downloads/start/', api_views.downloads_start, name='downloads_start'),
]