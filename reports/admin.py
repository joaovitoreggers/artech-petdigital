from django.contrib import admin

from .models import PeriodReport


@admin.register(PeriodReport)
class PeriodReportAdmin(admin.ModelAdmin):
    list_display = ("organization", "period_start", "period_end", "unit", "generated_by", "generated_at")
    list_filter = ("organization", "unit")
