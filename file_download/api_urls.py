from django.urls import path
from . import api_views

# This module is included under prefix 'api/downloads/' in project urls.
# So the final endpoint is: /api/downloads/start/
urlpatterns = [
    path('start/', api_views.downloads_start, name='downloads_start'),
    path('status/', api_views.downloads_status, name='downloads_status'),
    path('cancel/', api_views.downloads_cancel, name='downloads_cancel'),
    path('jobs/', api_views.jobs_list_or_create, name='downloads_jobs'),
    path('jobs/<int:job_id>/', api_views.job_detail, name='downloads_job_detail'),
    path('jobs/<int:job_id>/logs/', api_views.job_logs, name='downloads_job_logs'),
    path('jobs/<int:job_id>/cancel/', api_views.job_cancel, name='downloads_job_cancel'),
    path('jobs/<int:job_id>/retry/', api_views.job_retry, name='downloads_job_retry'),
    path('jobs/<int:job_id>/delete/', api_views.job_delete, name='downloads_job_delete'),
]
