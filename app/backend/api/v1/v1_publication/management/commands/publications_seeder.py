import requests
import time
from datetime import timedelta, datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django_q.tasks import async_task
from api.v1.v1_jobs.models import Jobs, JobStatus, JobTypes
from api.v1.v1_publication.models import Publication
from api.v1.v1_publication.constants import (
    CDIGeonodeCategory,
    PublicationStatus,
)


class Command(BaseCommand):
    help = "Generates publication data"

    def add_arguments(self, parser):
        # category
        parser.add_argument(
            "-c",
            "--category",
            nargs="?",
            const=CDIGeonodeCategory.cdi,
            default=CDIGeonodeCategory.cdi,
            type=str,
        )

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting publication data generation...")
        self.create_publications(**kwargs)
        self.stdout.write(
            self.style.SUCCESS("Publication data generation completed.")
        )

    def create_publications(self, **kwargs):
        # Recursively fetch all pages from Geonode API
        category = kwargs.get("category", CDIGeonodeCategory.cdi)

        username = settings.GEONODE_ADMIN_USERNAME
        password = settings.GEONODE_ADMIN_PASSWORD
        page = 1
        while True:
            url = (
                "{0}/api/v2/resources"
                "?filter{{category.identifier}}={1}"
                "&filter{{subtype}}=raster&page={2}&sort[]=-date"
                .format(
                    settings.GEONODE_BASE_URL,
                    category,
                    page,
                )
            )
            response = requests.get(
                url,
                auth=(username, password),
            )
            if response.status_code != 200:
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to fetch page {page}: {response.status_code}"
                    )
                )
                break
            data = response.json()
            resources = data.get("resources", [])
            for resource in resources:
                self.stdout.write(f"Processing resource: {resource['pk']}")
                publication = Publication.objects.filter(
                    cdi_geonode_id=resource['pk']
                ).first()
                if publication:
                    if not publication.validated_values:
                        publication.validated_values = (
                            publication.initial_values
                        )
                        publication.narrative = ""
                        publication.published_at = timezone.make_aware(
                            publication.due_date
                        ) if isinstance(publication.due_date, datetime) \
                            else timezone.make_aware(
                                datetime.combine(
                                    publication.due_date,
                                    datetime.min.time()
                                )
                            )
                        publication.save()
                    self.stdout.write(
                        self.style.WARNING(
                            f"Publication with cdi_geonode_id "
                            f"{resource['pk']} already exists. Skipping."
                        )
                    )
                    continue

                # Create new publication if it doesn't exist
                date_str = resource.get('date', '')[:10]
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    due_date = date_obj + timedelta(days=30)
                except ValueError:
                    due_date = datetime.today()

                publication = Publication(
                    cdi_geonode_id=int(resource['pk']),
                    year_month=resource.get('date', '')[:7] + '-01',
                    initial_values={},
                    due_date=due_date,
                    status=PublicationStatus.published
                )
                publication.save()

                timestamp = int(time.time())
                filename = "raster_{0}_{1}.tif".format(
                    publication.cdi_geonode_id,
                    timestamp
                )
                job = Jobs.objects.create(
                    type=JobTypes.download_geonode_dataset,
                    status=JobStatus.on_progress,
                    info={
                        "publication_id": publication.id,
                        "filename": filename,
                        "subject": None,
                        "message": None,
                        "is_seeder": True,
                    },
                )
                hook = "download_geonode_dataset_results"
                task_id = async_task(
                    "api.v1.v1_jobs.job.download_geonode_dataset",
                    resource['download_url'],
                    filename,
                    hook=f"api.v1.v1_jobs.job.{hook}",
                )
                # Update the job with the task ID
                job.task_id = task_id
                job.save()
            # Pagination logic
            total_count = data.get("total", 0)
            page_size = data.get("page_size", len(resources))
            if page * page_size >= total_count or not resources:
                break
            page += 1
