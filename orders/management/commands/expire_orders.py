from django.core.management.base import BaseCommand

from orders.services import expire_stale_orders


class Command(BaseCommand):
    help = "Annule les commandes Mobile Money impayées trop anciennes et remet le stock."

    def add_arguments(self, parser):
        parser.add_argument("--hours", type=int, default=None, help="Ancienneté minimale en heures.")

    def handle(self, *args, **options):
        count = expire_stale_orders(options["hours"])
        self.stdout.write(self.style.SUCCESS(f"{count} commande(s) expirée(s)."))