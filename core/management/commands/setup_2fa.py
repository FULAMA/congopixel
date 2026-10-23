from urllib.parse import parse_qs, urlparse

import segno
from django.core.management.base import BaseCommand, CommandError
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from accounts.models import User

BLACK, WHITE = 16, 231


def terminal_qr(text):
    """Code QR affiché dans le terminal (noir sur blanc, compatible avec la plupart des consoles)."""
    qr = segno.make(text, error="m", micro=False)
    matrix = [list(row) for row in qr.matrix]
    size = len(matrix)
    border = 2

    def dark(x, y):
        return 0 <= x < size and 0 <= y < size and bool(matrix[y][x])

    lines = []
    for y in range(-border, size + border, 2):
        row = ""
        for x in range(-border, size + border):
            top = BLACK if dark(x, y) else WHITE
            bottom = BLACK if dark(x, y + 1) else WHITE
            row += f"\x1b[38;5;{top}m\x1b[48;5;{bottom}m▀"
        lines.append(row + "\x1b[0m")
    return "\n".join(lines)


class Command(BaseCommand):
    help = "Active la double authentification (application + codes de secours) pour un compte équipe."

    def add_arguments(self, parser):
        parser.add_argument("username", help="Identifiant du compte équipe.")
        parser.add_argument("--reset", action="store_true", help="Remplace l'appareil existant.")

    def handle(self, *args, **options):
        user = User.objects.filter(username=options["username"], is_staff=True, is_active=True).first()
        if user is None:
            raise CommandError("Compte équipe introuvable ou inactif.")
        if TOTPDevice.objects.filter(user=user, confirmed=True).exists() and not options["reset"]:
            raise CommandError("Ce compte a déjà un appareil 2FA. Utilisez --reset pour le remplacer.")

        TOTPDevice.objects.filter(user=user).delete()
        device = TOTPDevice.objects.create(user=user, name="Application d'authentification", confirmed=False)
        url = device.config_url
        secret = parse_qs(urlparse(url).query).get("secret", [""])[0]

        self.stdout.write("Scannez ce code QR avec votre application d'authentification :")
        self.stdout.write(terminal_qr(url))
        self.stdout.write(f"Si le QR ne s'affiche pas bien, saisissez cette clé à la main : {secret}")
        self.stdout.write(f"Adresse complète : {url}")

        try:
            code = input("Code à 6 chiffres affiché par l'application : ").strip()
        except EOFError:
            device.delete()
            raise CommandError("Commande interactive : lancez-la seule, sans la coller avec d'autres lignes.")
        if not device.verify_token(code):
            device.delete()
            raise CommandError(
                "Code incorrect : rien n'a été activé. Vérifiez que l'heure de votre téléphone est automatique, puis recommencez."
            )
        device.confirmed = True
        device.save()

        StaticDevice.objects.filter(user=user).delete()
        backup = StaticDevice.objects.create(user=user, name="Codes de secours", confirmed=True)
        codes = []
        for _ in range(8):
            token = StaticToken.random_token()
            StaticToken.objects.create(device=backup, token=token)
            codes.append(token)

        self.stdout.write(self.style.SUCCESS(f"Double authentification activée pour {user.username}."))
        self.stdout.write("Codes de secours (à usage unique, à noter sur papier, à ne pas garder dans le téléphone) :")
        for code in codes:
            self.stdout.write(f"  {code}")