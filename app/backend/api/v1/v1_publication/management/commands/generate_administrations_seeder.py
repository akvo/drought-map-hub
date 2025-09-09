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
        for adm in administrations:
            adm_exits = Administration.objects.filter(
                pk=adm["administration_id"]
            ).first()
            if not adm_exits:
                Administration.objects.create(
                    pk=adm["administration_id"],
                    name=adm["name"],
                    region=adm["region"]
                )
        if not test:
            self.stdout.write(self.style.SUCCESS(
                f"Created {len(administrations)} Administrations successfully."
            ))  # pragma: no cover
