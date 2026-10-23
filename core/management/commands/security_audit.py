from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from payments.models import Payment
from orders.models import Order


class Command(BaseCommand):
    help = "Audit rapide de sécurité et d'exploitation (lecture seule)."

    def handle(self, *args, **options):
        findings = []

        if settings.DEBUG:
            findings.append(("CRITIQUE", "DEBUG est activé : à désactiver en production."))
        if settings.ADMIN_URL == "admin/":
            findings.append(("AVERTISSEMENT", "L'adresse de l'admin est celle par défaut (ADMIN_URL)."))

        superusers = list(
            User.objects.filter(is_superuser=True, is_active=True).values_list("username", flat=True)
        )
        if len(superusers) > 2:
            findings.append((
                "AVERTISSEMENT",
                f"{len(superusers)} super-utilisateurs actifs : {', '.join(superusers)}. Gardez-en 1 ou 2.",
            ))

        no_group = list(
            User.objects.filter(is_staff=True, is_superuser=False, is_active=True, groups__isnull=True)
            .values_list("username", flat=True)
        )
        if no_group:
            findings.append(("AVERTISSEMENT", f"Équipe sans groupe de permissions : {', '.join(no_group)}."))

        dormant = list(
            User.objects.filter(
                is_staff=True, is_active=True, last_login__lt=timezone.now() - timedelta(days=90)
            ).values_list("username", flat=True)
        )
        if dormant:
            findings.append(("INFO", f"Comptes équipe inactifs depuis 90 jours (à désactiver ?) : {', '.join(dormant)}."))

        refunds = Payment.objects.filter(
            status=Payment.Status.CONFIRMED, order__status=Order.Status.CANCELLED
        ).count()
        if refunds:
            findings.append((
                "ACTION",
                f"{refunds} paiement(s) confirmé(s) sur des commandes annulées : remboursement ou nouvelle commande à traiter.",
            ))

        stale = (
            Payment.objects.filter(status=Payment.Status.PENDING, created_at__lt=timezone.now() - timedelta(hours=48))
            .exclude(transaction_id="")
            .count()
        )
        if stale:
            findings.append(("ACTION", f"{stale} paiement(s) à vérifier depuis plus de 48 h."))

        if findings:
            for level, text in findings:
                self.stdout.write(f"[{level}] {text}")
        else:
            self.stdout.write(self.style.SUCCESS("Aucun point d'attention."))