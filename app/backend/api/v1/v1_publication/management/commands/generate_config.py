from django.core.management import BaseCommand
from django.conf import settings
from jsmin import jsmin


class Command(BaseCommand):
    def handle(self, *args, **options):
        topojson = open("source/country.topojson").read()

        min_config = jsmin(
            "".join(
                [
                    "var topojson=",
                    topojson,
                    ";",
                ]
            )
        )
        open("source/config/config.min.js", "w").write(min_config)
        if not settings.TEST_ENV:
            self.stdout.write(self.style.SUCCESS(
                "config.js successfully generated!"
            ))  # pragma: no cover
