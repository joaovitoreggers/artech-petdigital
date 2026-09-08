from django.db import migrations

DEFAULT_ORG_SLUG = "lar-cooperativa-agroindustrial"


def seed_data(apps, schema_editor):
    Organization = apps.get_model("core", "Organization")
    PeriodReport = apps.get_model("reports", "PeriodReport")
    org = Organization.objects.get(slug=DEFAULT_ORG_SLUG)
    PeriodReport.objects.filter(organization__isnull=True).update(organization=org)


def remove_data(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0002_periodreport_organization_alter_periodreport_unit"),
        ("core", "0007_backfill_default_organization"),
    ]
    operations = [migrations.RunPython(seed_data, remove_data)]
