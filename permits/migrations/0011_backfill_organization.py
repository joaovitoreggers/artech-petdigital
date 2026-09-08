from django.db import migrations

DEFAULT_ORG_SLUG = "lar-cooperativa-agroindustrial"


def seed_data(apps, schema_editor):
    Organization = apps.get_model("core", "Organization")
    WorkPermit = apps.get_model("permits", "WorkPermit")
    ChecklistItemTemplate = apps.get_model("permits", "ChecklistItemTemplate")
    MandatoryPPEItem = apps.get_model("permits", "MandatoryPPEItem")
    PermitSequenceCounter = apps.get_model("permits", "PermitSequenceCounter")
    org = Organization.objects.get(slug=DEFAULT_ORG_SLUG)
    WorkPermit.objects.filter(organization__isnull=True).update(organization=org)
    ChecklistItemTemplate.objects.filter(organization__isnull=True).update(organization=org)
    MandatoryPPEItem.objects.filter(organization__isnull=True).update(organization=org)
    PermitSequenceCounter.objects.filter(organization__isnull=True).update(organization=org)


def remove_data(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("permits", "0010_checklistitemtemplate_organization_and_more"),
        ("core", "0007_backfill_default_organization"),
    ]
    operations = [migrations.RunPython(seed_data, remove_data)]
