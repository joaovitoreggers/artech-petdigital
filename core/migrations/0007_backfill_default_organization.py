from django.db import migrations

DEFAULT_ORG_NAME = "Lar Cooperativa Agroindustrial"
DEFAULT_ORG_SLUG = "lar-cooperativa-agroindustrial"


def seed_data(apps, schema_editor):
    """Every row that existed before multi-tenancy belonged, implicitly, to
    the one company the system was built for — make that explicit as the
    platform's first Organization, and point all existing Units/RiskAreas
    at it. Every other app's own backfill migration (each depending on
    this one) does the same for its own organization-scoped models."""
    Organization = apps.get_model("core", "Organization")
    Unit = apps.get_model("core", "Unit")
    RiskArea = apps.get_model("core", "RiskArea")

    org, _ = Organization.objects.get_or_create(
        slug=DEFAULT_ORG_SLUG, defaults={"name": DEFAULT_ORG_NAME}
    )
    Unit.objects.filter(organization__isnull=True).update(organization=org)
    RiskArea.objects.filter(organization__isnull=True).update(organization=org)


def remove_data(apps, schema_editor):
    Organization = apps.get_model("core", "Organization")
    Organization.objects.filter(slug=DEFAULT_ORG_SLUG).delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0006_organization_alter_riskarea_slug_alter_unit_name_and_more")]
    operations = [migrations.RunPython(seed_data, remove_data)]
