from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import User


class Command(BaseCommand):
    help = "Déconnecte tout le monde (ou un seul utilisateur) en supprimant les sessions."

    def add_arguments(self, parser):
        parser.add_argument("--user", help="Identifiant de l'utilisateur à déconnecter.")
        parser.add_argument("--deactivate", action="store_true", help="Désactive aussi le compte (avec --user).")

    def handle(self, *args, **options):
        username = options["user"]
        if not username:
            count = Session.objects.count()
            Session.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f"{count} session(s) supprimée(s)."))
            return
        user = User.objects.filter(username=username).first()
        if user is None:
            raise CommandError("Utilisateur introuvable.")
        count = 0
        for session in Session.objects.filter(expire_date__gt=timezone.now()):
            if session.get_decoded().get("_auth_user_id") == str(user.pk):
                session.delete()
                count += 1
        if options["deactivate"]:
            user.is_active = False
            user.save(update_fields=["is_active"])
        self.stdout.write(self.style.SUCCESS(f"{count} session(s) supprimée(s) pour {username}."))