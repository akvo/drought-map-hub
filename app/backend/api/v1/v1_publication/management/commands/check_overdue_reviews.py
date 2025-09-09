from django.core.management.base import BaseCommand
from django.utils.timezone import now, datetime
from django.conf import settings
from utils.email_helper import send_email, EmailTypes
from api.v1.v1_publication.models import Review


class Command(BaseCommand):
    help = "Send email notifications for overdue reviews"

    def add_arguments(self, parser):
        parser.add_argument(
            "--mock-now",
            type=str,
            help="Mock current datetime (format: YYYY-MM-DD)",
        )

    def handle(self, *args, **kwargs):
        today = now()
        if kwargs.get("mock_now"):
            today = datetime.strptime(kwargs["mock_now"], "%Y-%m-%d")
        overdue_reviews = Review.objects.filter(
            publication__due_date__lt=today,
            completed_at__isnull=True,
            is_completed=False,
            is_overdue_notified=False
        )

        for review in overdue_reviews.all():
            due_date = review.publication.due_date.strftime("%Y-%m-%d")
            year_month = review.publication.year_month.strftime("%Y-%m")
            if not settings.TEST_ENV:
                send_email(  # pragma: no cover
                    type=EmailTypes.review_overdue,
                    context={
                        "send_to": [review.user.email],
                        "name": review.user.name,
                        "year_month": year_month,
                        "due_date": due_date,
                        "id": review.id,
                    },
                )
            review.is_overdue_notified = True
            review.save()
        if not settings.TEST_ENV and overdue_reviews.count():
            self.stdout.write(  # pragma: no cover
                self.style.SUCCESS("Overdue emails sent successfully!")
            )
