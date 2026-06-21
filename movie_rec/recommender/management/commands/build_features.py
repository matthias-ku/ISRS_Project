from django.core.management.base import BaseCommand

from recommender.features import build_all_features

class Command(BaseCommand):

    def handle(self, *args, **options):
        build_all_features()
        self.stdout.write(
            self.style.SUCCESS("Features successfully built.")
        )
