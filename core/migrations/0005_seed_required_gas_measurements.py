from django.db import migrations

# Espaço confinado (NR-33) checks the full atmospheric panel; trabalho a
# quente (NR-18) only cares about an explosive atmosphere before
# welding/cutting. Every other area doesn't gate on gas readings at all.
REQUIRED_GAS_MEASUREMENTS = {
    "confinado": ["oxygen", "carbon_monoxide", "hydrogen_sulfide", "lower_explosive_limit"],
    "quente": ["lower_explosive_limit"],
}


def seed_data(apps, schema_editor):
    RiskArea = apps.get_model("core", "RiskArea")
    for slug, keys in REQUIRED_GAS_MEASUREMENTS.items():
        RiskArea.objects.filter(slug=slug).update(required_gas_measurements=keys)


def remove_data(apps, schema_editor):
    RiskArea = apps.get_model("core", "RiskArea")
    RiskArea.objects.filter(slug__in=REQUIRED_GAS_MEASUREMENTS).update(required_gas_measurements=[])


class Migration(migrations.Migration):
    dependencies = [("core", "0004_remove_riskarea_requires_gas_monitoring_and_more")]
    operations = [migrations.RunPython(seed_data, remove_data)]
