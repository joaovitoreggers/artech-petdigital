from django.contrib import admin

from .models import Organization, RiskArea, Unit


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "cnpj", "is_active", "created_at")
    search_fields = ("name", "cnpj")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "city", "state")
    list_filter = ("organization",)
    search_fields = ("name", "city")


@admin.register(RiskArea)
class RiskAreaAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "regulatory_code", "slug", "required_gas_measurements", "order")
    list_filter = ("organization",)
    ordering = ("organization", "order")
