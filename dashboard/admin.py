from django.contrib import admin

from .models import EvacuationEvent


@admin.register(EvacuationEvent)
class EvacuationEventAdmin(admin.ModelAdmin):
    list_display = ("organization", "unit", "reason", "triggered_by", "triggered_at", "ended_at")
    list_filter = ("organization", "unit")
