from django.contrib import admin

from .models import EvacuationEvent, PhysicalAlertEndpoint


@admin.register(EvacuationEvent)
class EvacuationEventAdmin(admin.ModelAdmin):
    list_display = ("organization", "unit", "source", "reason", "triggered_by", "triggered_at", "ended_at")
    list_filter = ("organization", "unit", "source")


@admin.register(PhysicalAlertEndpoint)
class PhysicalAlertEndpointAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "organization",
        "unit",
        "webhook_url",
        "is_active",
        "last_delivery_status",
        "last_triggered_at",
    )
    list_filter = ("organization", "is_active", "last_delivery_status")
    readonly_fields = ("last_triggered_at", "last_delivery_status", "last_delivery_error")
