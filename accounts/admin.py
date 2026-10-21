from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("CongoPixel", {"fields": ("phone", "preferred_language")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("CongoPixel", {"fields": ("phone", "preferred_language")}),)
    list_display = ("username", "phone", "email", "is_staff")