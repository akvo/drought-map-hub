import random
import json
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from faker import Faker
from datetime import datetime, timedelta
from calendar import monthrange
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
            "-t", "--test", nargs="?", const=False, default=False, type=bool,
        )
        parser.add_argument(
            "-r",
            "--repeat",
            nargs="?",
            const=3,
            default=3,
            type=int
        )
        # page
        parser.add_argument(
            "-p",
            "--page",
            nargs="?",
            const=1,
            default=1,
            type=int,
        )
        # status
        parser.add_argument(
            "-s",
            "--status",
            nargs="?",
            const=PublicationStatus.in_review,
            default=PublicationStatus.in_review,
            type=str,
        )

    def handle(self, *args, **kwargs):
        test = kwargs.get("test")
        repeat = kwargs.get("repeat")
        topojson_file_path = "./source/country.topojson"
        # validate the status argument
        status = kwargs.get("status")
        # convert status to integer if it's a string
        if isinstance(status, str):
            status = int(status)
        if status not in PublicationStatus.FieldStr.keys():
            status_keys = [
                str(x)
                for x in PublicationStatus.FieldStr.keys()
            ]
            self.stdout.write(self.style.ERROR(
                f"Invalid status: {status}. "
                f"Valid statuses are: "
                f"{', '.join(status_keys)}"
            ))
            return

        # Remove all existing publications and reviews
        for publication in Publication.objects.all():
            publication.delete(hard=True)

        with open(topojson_file_path, "r") as f:
            topo_data = json.load(f)
        features = topo_data.get('objects', {}).values()
        administration_ids = [
            f["properties"]["administration_id"]
            for fg in features
            for f in fg.get('geometries', [])
        ]
        max_total = 0

        cdi_geonode_ids = []
        if test:
            cdi_geonode_ids = [44, 106]
        else:
            category = CDIGeonodeCategory.cdi
            page = kwargs.get("page", 1)
            url = (
                "{0}/api/v2/resources"
                "?filter{{category.identifier}}={1}"
                "&filter{{subtype}}=raster&page={2}&sort[]=-date"
                # "&page=1"
                .format(
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
            if response.status_code == 200:
                data = response.json()
                max_total = data.get("total", 0)
                data = data.get("resources", [])
                cdi_geonode_ids = sorted(
                    [d.get("pk") for d in data],
                    reverse=True
                )

        total = repeat * 2
        # Limit the number of publications to generate
        if total > max_total and not test:
            warning_message = (
                "The maximum number of publications "
                f"to create is {max_total}"
            )
            if max_total == 0:
                warning_message = "Unable to fetch CDI Geonode IDs"
            self.stdout.write(self.style.WARNING(warning_message))
            return
        # Initialize the start date to December of the previous year
        current_date = datetime(datetime.now().year, datetime.now().month, 1)

        for index, cdi_geonode_id in enumerate(cdi_geonode_ids[:total]):
            # Calculate the last day of the current month
            year = current_date.year
            month = current_date.month
            last_day_of_month = monthrange(year, month)[1]
            due_date = datetime(year, month, last_day_of_month)

            # Calculate the previous month from due_date
            due_date_obj = datetime.strptime(
                due_date.strftime("%Y-%m-%d"), "%Y-%m-%d"
            )
            prev_month = due_date_obj - relativedelta(months=1)
            year_month = f"{prev_month.strftime('%Y-%m')}-01"

            # Get the start of the previous month
            start_date = datetime(prev_month.year, prev_month.month, 1)

            # Decrement the current date by one month for the next iteration
            current_date -= relativedelta(months=1)

            if index + 1 > repeat and status == PublicationStatus.in_review:
                status = PublicationStatus.in_validation
            initial_values = []
            for a_id in administration_ids:
                init_value = random.uniform(0.02, 0.4)
                initial_values.append({
                    "administration_id": a_id,
                    "value": init_value,
                    "category": get_category(init_value)
                })

            publication = Publication.objects.filter(
                cdi_geonode_id=cdi_geonode_id,
                # year_month=year_month,
            ).first()

            if not publication:
                publication = Publication.objects.create(
                    cdi_geonode_id=cdi_geonode_id,
                    year_month=year_month,
                    initial_values=initial_values,
                    status=status,
                    due_date=due_date,
                )

            if status == PublicationStatus.published:
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
                        "value": v["value"],
                        "category": get_category(v["value"])
                    }
                    for v in initial_values
                ]
                publication.save()

            reviewers = SystemUser.objects.filter(
                role=UserRoleTypes.reviewer
            ).all()

            for reviewer in reviewers:
                review, _ = Review.objects.get_or_create(
                    publication=publication,
                    user=reviewer
                )

                is_completed = (
                    publication.status != PublicationStatus.in_review
                )

                review.is_completed = is_completed

                suggestion_values = None
                if is_completed:
                    suggestion_values = []
                    for v in initial_values:
                        s_value = v["value"]
                        comment = None
                        reviewed = random.choice([
                            None,
                            True
                        ])
                        if is_completed:
                            reviewed = True

                        is_diff = fake.boolean()
                        if is_diff:
                            comment = fake.sentence(nb_words=8)
                            s_value = random.uniform(0.02, 0.4)

                        suggestion_values.append({
                            "administration_id": v["administration_id"],
                            "value": s_value,
                            "comment": comment,
                            "reviewed": reviewed,
                            "category": get_category(s_value),
                        })
                    completed_at = start_date + timedelta(
                        days=random.randint(0, (due_date - start_date).days)
                    )
                    review.is_completed = True
                    review.completed_at = timezone.make_aware(completed_at)

                review.suggestion_values = suggestion_values
                review.save()

        if not settings.TEST_ENV:
            self.stdout.write(self.style.SUCCESS(  # pragma: no cover
                "Fake publication generation complete!"
            ))
