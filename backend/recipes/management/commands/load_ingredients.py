import json

from django.conf import settings
from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):

    def handle(self, *args, **options):
        file_path = settings.BASE_DIR / 'data' / 'ingredients.json'

        with file_path.open(encoding='utf-8') as file:
            ingredients = json.load(file)

        Ingredient.objects.bulk_create(
            [Ingredient(**ingredient) for ingredient in ingredients],
            ignore_conflicts=True,
        )

        self.stdout.write(
            self.style.SUCCESS('Ингредиенты загружены.')
        )
