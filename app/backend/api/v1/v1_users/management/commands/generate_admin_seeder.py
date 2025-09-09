from django.core.management import BaseCommand
from api.v1.v1_users.models import SystemUser


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "-t", "--test", nargs="?", const=False, default=False, type=bool
        )

    def handle(self, *args, **options):
        total_admins = SystemUser.objects.filter(
            is_superuser=True
        ).count()
        index = total_admins + 1
        email = f"admin{index}@mail.com"
        SystemUser.objects.create_superuser(
            email=email,
            password="Changeme123",
            name=f"Admin {index}",
        )
        test = options.get("test")
        if not test:
            self.stdout.write(  # pragma: no cover
                self.style.SUCCESS(f"{email} created successfully")
            )
