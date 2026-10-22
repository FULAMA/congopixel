from django.core.management.base import BaseCommand
from django.utils.text import slugify

from catalog.models import Category, PixelModel
from core.models import SiteSettings
from orders.models import DeliveryZone

PIXELS = [
    ("Pixel 6", 2021), ("Pixel 6 Pro", 2021), ("Pixel 6a", 2022),
    ("Pixel 7", 2022), ("Pixel 7 Pro", 2022), ("Pixel 7a", 2023),
    ("Pixel 8", 2023), ("Pixel 8 Pro", 2023), ("Pixel 8a", 2024),
    ("Pixel 9", 2024), ("Pixel 9 Pro", 2024), ("Pixel 9 Pro XL", 2024), ("Pixel 9a", 2025),
    ("Pixel 10", 2025), ("Pixel 10 Pro", 2025), ("Pixel 10 Pro XL", 2025),
]

CATEGORIES = [
    "Coques et protections",
    "Protections d'écran",
    "Chargeurs et câbles",
    "Écouteurs et audio",
    "Batteries externes",
    "Supports et divers",
]

ZONES = [
    "Kinshasa",
    "Kongo Central - Matadi",
    "Kongo Central - Boma",
    "Kongo Central - Mbanza-Ngungu",
    "Kongo Central - autres villes",
    "Autres provinces",
]


class Command(BaseCommand):
    help = "Crée les données de départ (modèles Pixel, catégories, zones). Peut être relancée sans doublons."

    def handle(self, *args, **options):
        SiteSettings.load()
        for name, year in PIXELS:
            PixelModel.objects.get_or_create(slug=slugify(name), defaults={"name": name, "release_year": year})
        for position, name in enumerate(CATEGORIES):
            Category.objects.get_or_create(slug=slugify(name), defaults={"name": name, "position": position})
        for position, name in enumerate(ZONES):
            DeliveryZone.objects.get_or_create(name=name, defaults={"position": position})
        self.stdout.write(self.style.SUCCESS("Données de départ créées."))