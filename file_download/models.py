from django.db import models
from django.conf import settings


class DownloadJob(models.Model):
    TASK_STATUS_CHOICES = (
        (0, '任务已创建'),
        (1, '任务进行中'),
        (2, '任务完成'),
        (3, '任务失败'),
    )
    task_name = models.CharField(max_length=255)
    task_status = models.SmallIntegerField(default=0, choices=TASK_STATUS_CHOICES)
    task_id = models.CharField(max_length=100, null=True, blank=True)
    file_name = models.CharField(max_length=255, null=True, blank=True)
    file = models.FileField(upload_to='files/dlct/', null=True, blank=True)
    size = models.BigIntegerField(default=0)
    md5sum = models.CharField(max_length=64, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    log_path = models.CharField(max_length=255, null=True, blank=True)
    err_log_path = models.CharField(max_length=255, null=True, blank=True)
    params = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'download_job'
        ordering = ('-created_at',)

# Create your models here.
