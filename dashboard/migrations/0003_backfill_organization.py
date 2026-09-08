from django.db import migrations

DEFAULT_ORG_SLUG = "lar-cooperativa-agroindustrial"


def seed_data(apps, schema_editor):
    Organization = apps.get_model("core", "Organization")
    EvacuationEvent = apps.get_model("dashboard", "EvacuationEvent")
    org = Organization.objects.get(slug=DEFAULT_ORG_SLUG)
    EvacuationEvent.objects.filter(organization__isnull=True).update(organization=org)


def remove_data(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0002_evacuationevent_organization"),
        ("core", "0007_backfill_default_organization"),
    ]
    operations = [migrations.RunPython(seed_data, remove_data)]
