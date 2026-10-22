import sqlite3
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

KEEP = 14


class Command(BaseCommand):
    help = "Sauvegarde la base SQLite dans backups/ (garde les 14 dernières copies)."

    def handle(self, *args, **options):
        db = settings.DATABASES["default"]
        if "sqlite3" not in db["ENGINE"]:
            raise CommandError("Cette commande ne gère que SQLite.")
        backups = Path(settings.BASE_DIR) / "backups"
        backups.mkdir(exist_ok=True)
        target = backups / f"db-{datetime.now():%Y%m%d-%H%M%S}.sqlite3"
        source = sqlite3.connect(db["NAME"])
        dest = sqlite3.connect(target)
        with dest:
            source.backup(dest)
        dest.close()
        source.close()
        for old in sorted(backups.glob("db-*.sqlite3"))[:-KEEP]:
            old.unlink()
        self.stdout.write(self.style.SUCCESS(f"Sauvegarde créée : {target}"))