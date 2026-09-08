from django.contrib import admin

from .models import DocumentType, Worker, WorkerDocument


class WorkerDocumentInline(admin.TabularInline):
    model = WorkerDocument
    extra = 1


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "organization", "registration_number", "job_title", "company", "unit", "employment_type")
    list_filter = ("organization", "unit", "employment_type")
    search_fields = ("full_name", "registration_number", "company")
    inlines = [WorkerDocumentInline]


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "organization", "name", "description")
    list_filter = ("organization",)
