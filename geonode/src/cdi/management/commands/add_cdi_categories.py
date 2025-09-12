from django.core.management.base import BaseCommand
from geonode.base.models import TopicCategory


class Command(BaseCommand):
    help = 'Test print command for Django'

    def handle(self, *args, **options):
        cdi_categories = [
            "cdi-raster-map",
            "spi-raster-map",
            "ndvi-raster-map",
            "lst-raster-map"
        ]
        for category_name in cdi_categories:
            category, created = TopicCategory.objects.get_or_create(
                identifier=category_name
            )
            if created:
                category_name = category_name.replace(" ", "-")
                # convert category name to camel case
                category.description = " ".join(
                    [
                        word.upper() if i == 0 else word.capitalize()
                        for i, word in enumerate(category_name.split("-"))
                    ]
                )
                category.gn_description_en = category.description
                category.description_en = category.description
                category.fa_class = "fa-globe"
                category.is_choice = True
                category.save()
                msg = (
                    f'Category "{category.description}" created successfully.'
                )
                self.stdout.write(
                    self.style.SUCCESS(msg)
                )
            else:
                msg = (
                    f'Category "{category.description}" already exists.'
                )
                self.stdout.write(
                    self.style.WARNING(msg)
                )
