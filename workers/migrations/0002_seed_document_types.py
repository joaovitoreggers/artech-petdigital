from django.db import migrations

DOCUMENT_TYPES = [
    {"code": "ASO", "name": "Atestado de Saúde Ocupacional", "description": "Atestado de saúde ocupacional"},
    {"code": "NR-33", "name": "Espaço confinado", "description": "Espaço confinado · trabalhador autorizado"},
    {"code": "NR-18", "name": "Trabalho a quente", "description": "Trabalho a quente"},
    {"code": "NR-35", "name": "Trabalho em altura", "description": "Trabalho em altura"},
    {"code": "NR-10", "name": "Instalações elétricas", "description": "Segurança em instalações elétricas"},
    {"code": "NR-12", "name": "Máquinas e equipamentos", "description": "Máquinas e equipamentos · bloqueio"},
    {"code": "NR-13", "name": "Caldeiras e vasos de pressão", "description": "Caldeiras e vasos de pressão"},
]


def seed_data(apps, schema_editor):
    DocumentType = apps.get_model("workers", "DocumentType")
    for data in DOCUMENT_TYPES:
        DocumentType.objects.update_or_create(code=data["code"], defaults=data)


def remove_data(apps, schema_editor):
    DocumentType = apps.get_model("workers", "DocumentType")
    DocumentType.objects.filter(code__in=[d["code"] for d in DOCUMENT_TYPES]).delete()


class Migration(migrations.Migration):
    dependencies = [("workers", "0001_initial")]
    operations = [migrations.RunPython(seed_data, remove_data)]
