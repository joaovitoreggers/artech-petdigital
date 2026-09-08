from django.db import migrations

RISK_AREAS = [
    {
        "slug": "icamento",
        "name": "Içamento de carga",
        "regulatory_code": "NR-11",
        "description": "Guindaste, munck, talha — movimentação de cargas suspensas",
        "requires_gas_monitoring": False,
        "order": 6,
    },
    {
        "slug": "descarga",
        "name": "Descarga de gases/líquidos",
        "regulatory_code": "NR-20",
        "description": "Carga/descarga de inflamáveis e combustíveis",
        "requires_gas_monitoring": False,
        "order": 7,
    },
]


def seed_data(apps, schema_editor):
    RiskArea = apps.get_model("core", "RiskArea")
    for data in RISK_AREAS:
        RiskArea.objects.update_or_create(slug=data["slug"], defaults=data)


def remove_data(apps, schema_editor):
    RiskArea = apps.get_model("core", "RiskArea")
    RiskArea.objects.filter(slug__in=[a["slug"] for a in RISK_AREAS]).delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0002_seed_reference_data")]
    operations = [migrations.RunPython(seed_data, remove_data)]
