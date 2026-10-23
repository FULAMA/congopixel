from django_otp.admin import OTPAdminSite


def apply_admin_2fa(site, enabled):
    """Exige un code à usage unique pour utiliser l'admin (si activé)."""
    if enabled and not isinstance(site, OTPAdminSite):
        site.__class__ = OTPAdminSite
    return site