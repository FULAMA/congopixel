import io
from unittest import mock

from django.contrib.admin import AdminSite
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import RequestFactory, TestCase
from django_otp import match_token
from django_otp.admin import OTPAdminSite
from django_otp.oath import totp
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

from accounts.models import User
from core.admin_2fa import apply_admin_2fa
from core.testing import PASSWORD


def current_code(device):
    return str(totp(device.bin_key, step=device.step, t0=device.t0, digits=device.digits)).zfill(device.digits)


class TwoFactorTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("chef", password=PASSWORD, is_staff=True)

    def enroll(self):
        def fake_input(prompt=""):
            return current_code(TOTPDevice.objects.get(user=self.admin, confirmed=False))

        out = io.StringIO()
        with mock.patch("builtins.input", fake_input):
            call_command("setup_2fa", "chef", stdout=out)
        return out.getvalue()

    def test_setup_creates_confirmed_device_and_backup_codes(self):
        text = self.enroll()
        self.assertTrue(TOTPDevice.objects.filter(user=self.admin, confirmed=True).exists())
        self.assertEqual(StaticDevice.objects.get(user=self.admin).token_set.count(), 8)
        self.assertIn("otpauth://totp/", text)
        self.assertIn("CongoPixel", text)

    def test_wrong_code_leaves_no_device(self):
        with mock.patch("builtins.input", lambda prompt="": "000000"):
            with self.assertRaises(CommandError):
                call_command("setup_2fa", "chef", stdout=io.StringIO())
        self.assertFalse(TOTPDevice.objects.filter(user=self.admin).exists())

    def test_non_staff_user_is_refused(self):
        User.objects.create_user("client", password=PASSWORD)
        with self.assertRaises(CommandError):
            call_command("setup_2fa", "client", stdout=io.StringIO())

    def test_second_setup_requires_reset_flag(self):
        self.enroll()
        with self.assertRaises(CommandError):
            call_command("setup_2fa", "chef", stdout=io.StringIO())

    def test_reset_removes_all_devices(self):
        self.enroll()
        call_command("reset_2fa", "chef", stdout=io.StringIO())
        self.assertFalse(TOTPDevice.objects.filter(user=self.admin).exists())
        self.assertFalse(StaticDevice.objects.filter(user=self.admin).exists())

    def test_backup_codes_work_only_once(self):
        self.enroll()
        token = StaticDevice.objects.get(user=self.admin).token_set.first().token
        self.assertIsNotNone(match_token(self.admin, token))
        self.assertIsNone(match_token(self.admin, token))

    def test_otp_admin_site_requires_verified_staff(self):
        site = apply_admin_2fa(AdminSite(name="essai"), True)
        self.assertIsInstance(site, OTPAdminSite)
        request = RequestFactory().get("/")
        request.user = self.admin
        self.admin.is_verified = lambda: False
        self.assertFalse(site.has_permission(request))
        self.admin.is_verified = lambda: True
        self.assertTrue(site.has_permission(request))

    def test_disabled_flag_leaves_admin_unchanged(self):
        site = apply_admin_2fa(AdminSite(name="essai"), False)
        self.assertNotIsInstance(site, OTPAdminSite)

    def test_security_audit_flags_missing_two_factor(self):
        out = io.StringIO()
        call_command("security_audit", stdout=out)
        self.assertIn("sans 2FA", out.getvalue())
        self.assertIn("chef", out.getvalue())
        self.enroll()
        out = io.StringIO()
        call_command("security_audit", stdout=out)
        self.assertNotIn("sans 2FA", out.getvalue())