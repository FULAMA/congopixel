from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

CRUD = ["add", "change", "delete", "view"]

GROUPS = {
    "Gestionnaire de commandes": [
        ("orders", "order", ["view", "change"]),
        ("orders", "orderitem", ["view"]),
        ("orders", "deliveryzone", ["view"]),
        ("payments", "payment", ["view", "change"]),
    ],
    "Gestionnaire du catalogue": [
        ("catalog", model, CRUD)
        for model in ["product", "productimage", "productvariant", "category", "pixelmodel"]
    ],
}


class Command(BaseCommand):
    help = "Crée les groupes de permissions (peut être relancée sans risque)."

    def handle(self, *args, **options):
        for group_name, rules in GROUPS.items():
            group, _ = Group.objects.get_or_create(name=group_name)
            permissions = []
            for app_label, model, actions in rules:
                for action in actions:
                    permissions.append(
                        Permission.objects.get(content_type__app_label=app_label, codename=f"{action}_{model}")
                    )
            group.permissions.set(permissions)
        self.stdout.write(self.style.SUCCESS("Groupes créés ou mis à jour."))