from django.db import migrations

RISK_AREAS = [
    {
        "slug": "confinado",
        "name": "Espaço confinado",
        "regulatory_code": "NR-33",
        "description": "Silos, moegas, tanques, elevatórias",
        "requires_gas_monitoring": True,
        "order": 1,
    },
    {
        "slug": "quente",
        "name": "Trabalho a quente",
        "regulatory_code": "NR-18",
        "description": "Solda, corte, esmerilhamento",
        "requires_gas_monitoring": True,
        "order": 2,
    },
    {
        "slug": "altura",
        "name": "Trabalho em altura",
        "regulatory_code": "NR-35",
        "description": "Acima de 2 m do nível inferior",
        "requires_gas_monitoring": False,
        "order": 3,
    },
    {
        "slug": "eletrico",
        "name": "Serviço elétrico",
        "regulatory_code": "NR-10",
        "description": "Painéis, CCM, alta tensão",
        "requires_gas_monitoring": False,
        "order": 4,
    },
    {
        "slug": "maquinas",
        "name": "Máquinas e bloqueio",
        "regulatory_code": "NR-12",
        "description": "Intervenção em equipamento motorizado",
        "requires_gas_monitoring": False,
        "order": 5,
    },
]

UNITS = ["Matelândia", "Medianeira", "Céu Azul", "Itaipulândia", "Missal"]


def seed_data(apps, schema_editor):
    RiskArea = apps.get_model("core", "RiskArea")
    Unit = apps.get_model("core", "Unit")
    for data in RISK_AREAS:
        RiskArea.objects.update_or_create(slug=data["slug"], defaults=data)
    for name in UNITS:
        Unit.objects.get_or_create(name=name)


def remove_data(apps, schema_editor):
    RiskArea = apps.get_model("core", "RiskArea")
    Unit = apps.get_model("core", "Unit")
    RiskArea.objects.filter(slug__in=[a["slug"] for a in RISK_AREAS]).delete()
    Unit.objects.filter(name__in=UNITS).delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [migrations.RunPython(seed_data, remove_data)]
