from django.db import migrations

DEFAULT_ORG_SLUG = "lar-cooperativa-agroindustrial"


def seed_data(apps, schema_editor):
    Organization = apps.get_model("core", "Organization")
    DocumentType = apps.get_model("workers", "DocumentType")
    Worker = apps.get_model("workers", "Worker")
    org = Organization.objects.get(slug=DEFAULT_ORG_SLUG)
    DocumentType.objects.filter(organization__isnull=True).update(organization=org)
    Worker.objects.filter(organization__isnull=True).update(organization=org)


def remove_data(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("workers", "0004_documenttype_organization_worker_organization_and_more"),
        ("core", "0007_backfill_default_organization"),
    ]
    operations = [migrations.RunPython(seed_data, remove_data)]
