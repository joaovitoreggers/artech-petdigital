from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "PET Digital",
            {"fields": ("role", "can_self_authorize", "organization", "unit", "registration_number")},
        ),
    )
    list_display = ("username", "get_full_name", "organization", "role", "unit", "can_self_authorize", "is_active")
    list_filter = ("organization", "role", "unit", "can_self_authorize", "is_active")
