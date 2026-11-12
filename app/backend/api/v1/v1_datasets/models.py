"""Client data model (DIH-7).

One value per admin unit per month (MC-1 B-2), in long format on purpose:
``v1_indicators`` is a fixed-column wide table and can't hold per-client
columns. Display-only — no link to ``Publication`` (B-6 keeps client data out
of review/validation).
"""

from django.db import models

from api.v1.v1_publication.models import Administration


class AdminDatasetValue(models.Model):
    administration = models.ForeignKey(
        Administration, on_delete=models.CASCADE, related_name="dataset_values"
    )
    # Dataset key declared in country.json -> datasets (DIH-4). Until that
    # pack exists the key is free-form; the import command validates ids, not
    # keys.
    # ponytail: validate key against country.json datasets once DIH-4 lands.
    dataset = models.SlugField(max_length=50)
    period = models.DateField()  # first day of the month
    value = models.FloatField(null=True)  # null = reported missing, never 0

    class Meta:
        db_table = "admin_dataset_values"
        constraints = [
            models.UniqueConstraint(
                fields=["administration", "dataset", "period"],
                name="uniq_admin_dataset_period",
            )
        ]

    def __str__(self) -> str:
        adm = self.administration_id
        return f"{self.dataset}@{self.period:%Y-%m} adm={adm}"
