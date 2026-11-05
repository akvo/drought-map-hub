import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.v1.v1_setup.models import SiteConfig, Organization
from api.v1.v1_users.models import SystemUser, Ability
from utils.soft_deletes_model import SoftDeletesQuerySet

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Reset instance setup so the setup wizard runs again (dev/testing).

    Deletes SiteConfig + Organization (the "configured" marker is
    ``SiteConfig.objects.exists()``). With ``--with-users`` it also removes
    all SystemUser accounts so the wizard's admin/reviewer step can re-run
    with the same emails. Destructive: confirmation is required unless
    ``--noinput`` is passed.
    """

    help = "Reset instance setup (SiteConfig/Org) so the wizard re-runs."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--noinput",
            action="store_true",
            help="Skip the interactive confirmation prompt.",
        )
        parser.add_argument(
            "--with-users",
            action="store_true",
            help="Also delete all SystemUser accounts (fresh admin/reviewers).",
        )

    def handle(self, *args, **options) -> None:
        with_users: bool = options["with_users"]
        site_count = SiteConfig.objects.count()
        org_count = Organization.objects.count()
        # Setup re-seeds abilities; leaving them triggers a duplicate-key
        # 500 when the wizard re-runs generate_roles_n_abilities_seeder.
        ability_count = Ability.objects.count()
        # SystemUser soft-deletes, so .objects hides already-deleted rows
        # whose unique email still blocks re-registration. Count/hard-delete
        # every row (SoftDeletesQuerySet with no filter = all rows).
        all_users = SoftDeletesQuerySet(SystemUser)
        user_count = all_users.count() if with_users else 0

        self.stdout.write(
            "This will delete: "
            f"{site_count} SiteConfig, {org_count} Organization, "
            f"{ability_count} Ability"
            + (f", {user_count} SystemUser" if with_users else "")
            + "."
        )

        if not options["noinput"]:
            answer = input('Type "yes" to continue: ')
            if answer.strip().lower() != "yes":
                raise CommandError("Aborted.")

        with transaction.atomic():
            SiteConfig.objects.all().delete()
            Organization.objects.all().delete()
            Ability.objects.all().delete()
            if with_users:
                SoftDeletesQuerySet(SystemUser).delete(hard=True)

        logger.info(
            "reset_setup: removed %s SiteConfig, %s Organization, "
            "%s Ability, %s users",
            site_count,
            org_count,
            ability_count,
            user_count,
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Setup reset. Clear the browser 'appConfig' cookie (or use "
                "a fresh/incognito window) so the app redirects to /setup."
            )
        )
