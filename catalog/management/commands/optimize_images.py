from django.core.management.base import BaseCommand

from catalog.images import optimize
from catalog.models import ProductImage


class Command(BaseCommand):
    help = "Réduit les anciennes photos de produits et crée leurs miniatures."

    def handle(self, *args, **options):
        done = 0
        for img in ProductImage.objects.filter(thumb=""):
            if not img.image:
                continue
            storage = img.image.storage
            old_name = optimize(img)
            img.save()
            if old_name and old_name != img.image.name:
                storage.delete(old_name)
            done += 1
        self.stdout.write(self.style.SUCCESS(f"{done} photo(s) optimisée(s)."))