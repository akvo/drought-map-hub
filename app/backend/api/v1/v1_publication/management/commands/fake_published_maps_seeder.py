import random
import json
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from faker import Faker
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from api.v1.v1_users.models import SystemUser, UserRoleTypes
from api.v1.v1_publication.models import (
    Publication,
    Review,
)
from api.v1.v1_publication.constants import (
    PublicationStatus,
    CDIGeonodeCategory,
)
from api.v1.v1_publication.utils import get_category
from django.db import transaction

fake = Faker()


# Generate dummy narrative content
def generate_dummy_narrative():
    title = fake.sentence(nb_words=6)  # Generate a title with 6 words
    author = fake.name()  # Generate a random author name
    date = fake.date()  # Generate a random date
    content = "\n".join(
        [f"<p>{fake.paragraph(nb_sentences=5)}</p>" for _ in range(15)]
    )

    # Combine into HTML
    html_narrative = f"""
    <narrative>
        <h1>{title}</h1>
        <p><strong>Author:</strong> {author}</p>
        <p><strong>Date:</strong> {date}</p>
        {content}
    </narrative>
    """
    return html_narrative


class Command(BaseCommand):
    help = "Generates fake publication data"

    def add_arguments(self, parser):
        parser.add_argument(
            "-t",
            "--test",
            nargs="?",
            const=False,
            default=False,
            type=bool,
        )
        parser.add_argument(
            "-p",
            "--page",
            nargs="?",
            const=1,
            default=1,
            type=int,
        )

    def handle(self, *args, **kwargs):
        test = kwargs.get("test")
        page = kwargs.get("page")
        topojson_file_path = "./source/country.topojson"

        with open(topojson_file_path, "r") as f:
            topo_data = json.load(f)
        features = topo_data.get("objects", {}).values()
        administration_ids = [
            f["properties"]["administration_id"]
            for fg in features
            for f in fg.get("geometries", [])
        ]

        geonode_cdi_maps = []
        if test:
            geonode_cdi_maps = [
                {
                    "id": 1,
                    "date": "2020-01-01T00:00:00Z",
                },
                {
                    "id": 2,
                    "date": "2020-02-01T00:00:00Z",
                }
            ]
        else:
            category = CDIGeonodeCategory.cdi
            url = (
                "{0}/api/v2/resources"
                "?filter{{category.identifier}}={1}"
                "&filter{{subtype}}=raster&page={2}".format(
                    settings.GEONODE_BASE_URL,
                    category,
                    page,
                )
            )
            username = settings.GEONODE_ADMIN_USERNAME
            password = settings.GEONODE_ADMIN_PASSWORD
            response = requests.get(
                url,
                auth=(username, password),
            )
            if response.status_code != 200:
                self.stdout.write(
                    self.style.ERROR(
                        "Failed to fetch data from GeoNode API."
                        f"Status code: {response.status_code}"
                    )
                )
                return
            data = response.json()
            data = data.get("resources", [])
            geonode_cdi_maps = [
                {
                    "id": d.get("pk"),
                    "date": d["date"],
                }
                for d in data
            ]

        for cdi_map in geonode_cdi_maps:
            try:
                with transaction.atomic():
                    year_month = datetime.strptime(
                        cdi_map["date"], "%Y-%m-%dT%H:%M:%SZ"
                    ).date()
                    cdi_geonode_id = cdi_map["id"]
                    start_date = year_month.replace(day=1)
                    end_date = start_date + relativedelta(months=1)
                    end_date -= timedelta(days=1)
                    due_date = end_date + timedelta(days=random.randint(1, 7))
                    status = PublicationStatus.published
                    initial_values = []

                    for a_id in administration_ids:
                        init_value = random.uniform(0, 100)
                        initial_values.append({
                            "administration_id": a_id,
                            "value": init_value,
                            "category": get_category(init_value)
                        })

                    publication = Publication.objects.filter(
                        cdi_geonode_id=cdi_geonode_id,
                        year_month=year_month,
                    ).first()

                    if not publication:
                        publication = Publication.objects.create(
                            cdi_geonode_id=cdi_geonode_id,
                            year_month=year_month,
                            initial_values=initial_values,
                            status=status,
                            due_date=due_date,
                        )

                    reviewers = SystemUser.objects.filter(
                        role=UserRoleTypes.reviewer
                    ).all()

                    published_at = datetime.combine(
                        due_date + timedelta(days=random.randint(1, 7)),
                        datetime.min.time()
                    )
                    publication.status = PublicationStatus.published
                    publication.published_at = timezone.make_aware(
                        published_at
                    )
                    publication.narrative = generate_dummy_narrative()
                    publication.bulletin_url = (
                        "https://www.ipcinfo.org/fileadmin/"
                        "user_upload/ipcinfo/docs/"
                        "IPC_Eswatini_AFI_2019June2020March.pdf"
                    )
                    publication.validated_values = [
                        {
                            "administration_id": v["administration_id"],
                            "value": v["value"] + 5,
                            "category": get_category(v["value"] + 5)
                        }
                        for v in initial_values
                    ]
                    publication.save()

                    for reviewer in reviewers:
                        review, _ = Review.objects.get_or_create(
                            publication=publication,
                            user=reviewer
                        )
                        suggestion_values = []
                        for v in initial_values:
                            s_value = v["value"]
                            comment = None
                            reviewed = True

                            is_diff = fake.boolean()
                            if is_diff:
                                comment = fake.sentence(nb_words=8)
                                s_value = random.uniform(0, 100)

                            suggestion_values.append({
                                "administration_id": v["administration_id"],
                                "value": s_value,
                                "comment": comment,
                                "reviewed": reviewed,
                                "category": get_category(s_value),
                            })
                        completed_at = datetime.combine(
                            start_date + timedelta(
                                days=random.randint(
                                    0, (due_date - start_date).days
                                )
                            ),
                            datetime.min.time()
                        )
                        review.is_completed = True
                        review.completed_at = timezone.make_aware(completed_at)

                        review.suggestion_values = suggestion_values
                        review.save()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error: {e}"))
                continue

        if not settings.TEST_ENV:
            self.stdout.write(
                self.style.SUCCESS(  # pragma: no cover
                    "Fake published maps generation complete!"
                )
            )
