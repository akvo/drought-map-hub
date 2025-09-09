from django.db import models


class Settings(models.Model):
    project_name = models.CharField(
        max_length=255,
        unique=True,
    )
    job_id = models.UUIDField()
    job_config = models.JSONField(
        null=True,
        blank=True
    )
    on_success_emails = models.JSONField(
        null=True,
        blank=True
    )
    on_failure_emails = models.JSONField(
        null=True,
        blank=True
    )
    on_exceeded_emails = models.JSONField(
        null=True,
        blank=True
    )
    lst_weight = models.FloatField(
        default=0.3,
    )
    ndvi_weight = models.FloatField(
        default=0.3,
    )
    spi_weight = models.FloatField(
        default=0.4,
    )
    sm_weight = models.FloatField(
        default=0.0,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "settings"
