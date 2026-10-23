from django.core.management.base import BaseCommand, CommandError
from django_otp import devices_for_user

from accounts.models import User


class Command(BaseCommand):
    help = "Supprime les appareils 2FA d'un compte (téléphone perdu). Il faudra relancer setup_2fa."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **options):
        user = User.objects.filter(username=options["username"]).first()
        if user is None:
            raise CommandError("Utilisateur introuvable.")
        count = 0
        for device in list(devices_for_user(user, confirmed=None)):
            device.delete()
            count += 1
        self.stdout.write(self.style.SUCCESS(f"{count} appareil(s) 2FA supprimé(s) pour {user.username}."))