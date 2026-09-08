from django.contrib import admin

from .models import (
    ChecklistItemTemplate,
    GasReading,
    MandatoryPPEItem,
    PermitChecklistItem,
    PermitFieldValue,
    PermitLogEntry,
    PermitPhoto,
    PermitPPEVerification,
    PermitSequenceCounter,
    PermitSignature,
    PermitTeamMember,
    WorkPermit,
)


class GasReadingInline(admin.TabularInline):
    model = GasReading
    extra = 0
    readonly_fields = ("is_within_limits", "recorded_at")


class PermitLogEntryInline(admin.TabularInline):
    model = PermitLogEntry
    extra = 0
    readonly_fields = ("occurred_at", "event_type", "description", "actor")


class PermitTeamMemberInline(admin.TabularInline):
    model = PermitTeamMember
    extra = 0


class PermitPPEVerificationInline(admin.TabularInline):
    model = PermitPPEVerification
    extra = 0
    readonly_fields = ("submitted_at", "passed", "ai_summary", "error_message")


@admin.register(WorkPermit)
class WorkPermitAdmin(admin.ModelAdmin):
    list_display = ("permit_number", "organization", "unit", "status", "requested_by", "created_at")
    list_filter = ("organization", "status", "unit")
    search_fields = ("permit_number", "specific_location")
    readonly_fields = ("permit_number", "created_at")
    filter_horizontal = ("risk_areas",)
    inlines = [GasReadingInline, PermitTeamMemberInline, PermitPPEVerificationInline, PermitLogEntryInline]


@admin.register(ChecklistItemTemplate)
class ChecklistItemTemplateAdmin(admin.ModelAdmin):
    list_display = ("organization", "risk_area", "group_title", "description", "regulatory_code", "order")
    list_filter = ("organization", "risk_area", "regulatory_code")


@admin.register(MandatoryPPEItem)
class MandatoryPPEItemAdmin(admin.ModelAdmin):
    list_display = ("organization", "risk_area", "description", "order")
    list_filter = ("organization", "risk_area")
    ordering = ("organization", "risk_area", "order")


@admin.register(PermitPPEVerification)
class PermitPPEVerificationAdmin(admin.ModelAdmin):
    list_display = ("work_permit", "worker", "passed", "submitted_at")
    list_filter = ("passed",)
    readonly_fields = ("submitted_at", "items_result", "ai_summary", "error_message")


admin.site.register(PermitSequenceCounter)
admin.site.register(PermitFieldValue)
admin.site.register(PermitChecklistItem)
admin.site.register(PermitSignature)
admin.site.register(PermitPhoto)
admin.site.register(PermitLogEntry)
