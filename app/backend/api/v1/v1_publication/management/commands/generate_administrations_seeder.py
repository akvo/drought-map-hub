import json
from django.core.management.base import BaseCommand
from api.v1.v1_publication.models import Administration


class Command(BaseCommand):
    help = "Generates administrations from the country.topojson file."

    def add_arguments(self, parser):
        parser.add_argument(
            "-t", "--test", nargs="?", const=False, default=False, type=bool,
        )

    def handle(self, *args, **options):
        test = options.get("test")

        topojson_file_path = "./source/country.topojson"

        with open(topojson_file_path, "r") as f:
            topo_data = json.load(f)
        features = topo_data.get('objects', {}).values()
        administrations = [
            f["properties"]
            for fg in features
            for f in fg.get('geometries', [])
        ]
        for index, adm in enumerate(administrations):
            adm_id = adm.get("administration_id")
            adm_name = adm.get("name", f"Administration #{index + 1}")
            if not adm_id or not str(adm_id).isdigit():
                Administration.objects.update_or_create(
                    name=adm_name,
                )
            else:
                adm_id = int(adm_id)
                adm_exists = Administration.objects.filter(
                    pk=adm_id
                ).first()
                if (
                    not adm_exists or
                    (adm_exists and adm_exists.name != adm_name)
                ):
                    Administration.objects.create(
                        name=adm_name,
                    )
        if not test:
            self.stdout.write(self.style.SUCCESS(
                f"Created {len(administrations)} Administrations successfully."
            ))  # pragma: no cover
