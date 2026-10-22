import re

from django.core.exceptions import ValidationError


def normalize_phone(value):
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith("0"):
        digits = "243" + digits[1:]
    elif len(digits) == 9:
        digits = "243" + digits
    if not 11 <= len(digits) <= 15:
        raise ValidationError("Numéro invalide. Exemple : 0812345678 ou +243812345678.")
    return digits