from django.db import migrations

DOCUMENT_TYPES = [
    {"code": "NR-11", "name": "Movimentação e transporte de materiais", "description": "Içamento de carga · operador capacitado"},
    {"code": "NR-20", "name": "Inflamáveis e combustíveis", "description": "Descarga de gases/líquidos · NR-20 / MOPP"},
]


def seed_data(apps, schema_editor):
    DocumentType = apps.get_model("workers", "DocumentType")
    for data in DOCUMENT_TYPES:
        DocumentType.objects.update_or_create(code=data["code"], defaults=data)


def remove_data(apps, schema_editor):
    DocumentType = apps.get_model("workers", "DocumentType")
    DocumentType.objects.filter(code__in=[d["code"] for d in DOCUMENT_TYPES]).delete()


class Migration(migrations.Migration):
    dependencies = [("workers", "0002_seed_document_types")]
    operations = [migrations.RunPython(seed_data, remove_data)]
