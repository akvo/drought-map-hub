import logging
import requests
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand

from api.v1.v1_geonode.models import PublicationGeonode
from api.v1.v1_publication.constants import CDIGeonodeCategory

logger = logging.getLogger(__name__)

# ponytail: one network loop, a plain timeout keeps it from hanging forever.
REQUEST_TIMEOUT = 30
PAGE_SIZE = 20


def _parse_year_month(date_str):
    """GeoNode `date` -> date. Accept full date or YYYY-MM; None if neither."""
    if not date_str:
        return None
    for fmt, length in (("%Y-%m-%d", 10), ("%Y-%m", 7)):
        try:
            return datetime.strptime(date_str[:length], fmt).date()
        except ValueError:
            continue
    return None


def _parse_created(created_str):
    if not created_str:
        return None
    try:
        return datetime.fromisoformat(created_str.replace("Z", "+00:00"))
    except ValueError:
        return None


class Command(BaseCommand):
    help = (
        "Backfill/refresh the PublicationGeonode cache from GeoNode "
        "(history import / manual recovery)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "-c",
            "--category",
            nargs="?",
            default=None,
            help="Target category identifier. If omitted, syncs all.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report resources that would be written, without writing.",
        )

    def handle(self, *args, **options):
        category = options.get("category")
        dry_run = options.get("dry_run")
        categories = (
            [category] if category
            else list(CDIGeonodeCategory.FieldStr.keys())
        )

        self.stdout.write(f"Syncing GeoNode cache for categories: {categories}")
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN: no database writes.")
            )

        for cat in categories:
            self.stdout.write(f"Syncing category: {cat}...")
            self._sync_category(cat, dry_run)

        self.stdout.write(self.style.SUCCESS("GeoNode cache sync completed."))

    def _sync_category(self, category, dry_run):
        page = 1
        total_synced = 0
        while True:
            url = (
                f"{settings.GEONODE_BASE_URL}/api/v2/resources"
                f"?filter{{category.identifier}}={category}"
                f"&filter{{subtype}}=raster"
                f"&page={page}&page_size={PAGE_SIZE}&sort[]=-date"
            )
            try:
                response = requests.get(
                    url,
                    auth=(
                        settings.GEONODE_ADMIN_USERNAME,
                        settings.GEONODE_ADMIN_PASSWORD,
                    ),
                    headers={"Host": settings.GEONODE_HOST},
                    timeout=REQUEST_TIMEOUT,
                )
            except requests.RequestException as e:
                self.stderr.write(
                    self.style.ERROR(
                        f"Failed to fetch page {page} for {category}: {e}"
                    )
                )
                break

            if response.status_code != 200:
                self.stderr.write(
                    self.style.ERROR(
                        f"GeoNode returned {response.status_code} "
                        f"for page {page} ({category})."
                    )
                )
                break

            data = response.json()
            resources = data.get("resources", [])
            if not resources:
                break

            for res in resources:
                if self._upsert(category, res, dry_run):
                    total_synced += 1

            total = data.get("total", 0)
            if page * PAGE_SIZE >= total:
                break
            page += 1

        self.stdout.write(
            f"Synced {total_synced} resources for category {category}."
        )

    def _upsert(self, category, res, dry_run):
        geonode_id = res.get("pk")
        year_month = _parse_year_month(res.get("date"))
        if not year_month:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipping resource {geonode_id}: "
                    f"invalid date '{res.get('date')}'"
                )
            )
            return False

        self.stdout.write(
            f"Resource {geonode_id} ({year_month}): '{res.get('title')}'"
        )
        if dry_run:
            return True

        PublicationGeonode.objects.update_or_create(
            geonode_id=geonode_id,
            defaults={
                "category": category,
                "title": res.get("title"),
                "year_month": year_month,
                "subtype": res.get("subtype", "raster"),
                "detail_url": res.get("detail_url"),
                "embed_url": res.get("embed_url"),
                "thumbnail_url": res.get("thumbnail_url"),
                "download_url": res.get("download_url"),
                "file_size": res.get("filesize"),
                "resource_created": _parse_created(res.get("created")),
                "raw": res,
            },
        )
        return True
