from django.db import models
from .constants import JobTypes, JobStatus


class Jobs(models.Model):
    task_id = models.CharField(
        max_length=50, unique=True, null=True, default=None
    )
    type = models.IntegerField(choices=JobTypes.FieldStr.items())
    status = models.IntegerField(
        choices=JobStatus.FieldStr.items(), default=JobStatus.pending
    )
    attempt = models.IntegerField(default=0)
    result = models.TextField(default=None, null=True)
    info = models.JSONField(default=None, null=True)
    created = models.DateTimeField(auto_now_add=True)
    available = models.DateTimeField(default=None, null=True)

    class Meta:
        db_table = "jobs"
