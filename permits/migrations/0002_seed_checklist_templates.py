from django.db import migrations

# Snapshot of permits.constants as of this migration (superseded by
# 0004_reseed_checklist_templates, which deletes and reseeds everything —
# kept here, inlined, only so this already-applied migration doesn't break
# `manage.py` by importing a module shape that no longer exists).
RISK_AREA_CHECKLISTS = {
    "confinado": [
        {
            "group_title": "EPI conferido em campo",
            "items": [
                "Cinto paraquedista com trava-queda",
                "Respirador com filtro adequado ao contaminante",
                "Capacete com jugular",
                "Luvas e botina de segurança",
            ],
        },
        {
            "group_title": "Bloqueio e isolamento · NR-33",
            "items": [
                "Bloqueio físico de energia aplicado — cadeado e etiqueta",
                "Sistema despressurizado e drenado",
                "Válvulas de entrada travadas",
                "Ventilação forçada instalada",
                "Vigia posicionado externamente",
                "Plano de resgate acionável",
            ],
        },
    ],
    "quente": [
        {
            "group_title": "EPI conferido em campo",
            "items": [
                "Máscara de solda com filtro adequado",
                "Avental e mangote de raspa",
                "Luvas de solda",
                "Protetor auricular",
            ],
        },
        {
            "group_title": "Prevenção de incêndio · NR-18",
            "items": [
                "Área isolada e sinalizada no raio definido",
                "Combustíveis removidos ou cobertos com manta",
                "Extintores posicionados e inspecionados",
                "Detector de gás inflamável zerado (LEL 0%)",
                "Vigia de fogo escalado para 60 min após o término",
            ],
        },
    ],
    "altura": [
        {
            "group_title": "EPI conferido em campo",
            "items": [
                "Cinto paraquedista com duplo talabarte",
                "Trava-queda retrátil",
                "Capacete com jugular",
                "Calçado antiderrapante",
            ],
        },
        {
            "group_title": "Sistema de ancoragem · NR-35",
            "items": [
                "Ponto de ancoragem certificado e inspecionado",
                "Linha de vida instalada e testada",
                "Projeção no piso isolada e sinalizada",
                "Ferramentas amarradas ao cinto",
                "Condição climática avaliada (vento e chuva)",
            ],
        },
    ],
    "eletrico": [
        {
            "group_title": "EPI conferido em campo",
            "items": [
                "Vestimenta antiarco com ATPV compatível",
                "Luva isolante de classe adequada",
                "Capacete com viseira de policarbonato",
                "Calçado isolante",
            ],
        },
        {
            "group_title": "Desenergização · NR-10",
            "items": [
                "Seccionamento do circuito",
                "Impedimento de reenergização — cadeado e etiqueta",
                "Constatação da ausência de tensão",
                "Instalação de aterramento temporário",
                "Sinalização e delimitação da zona controlada",
            ],
        },
    ],
    "maquinas": [
        {
            "group_title": "EPI conferido em campo",
            "items": [
                "Luvas de proteção mecânica",
                "Óculos de segurança",
                "Capacete",
                "Calçado de segurança",
            ],
        },
        {
            "group_title": "Bloqueio LOTO · NR-12",
            "items": [
                "Parada do equipamento pelo comando local",
                "Cadeado e etiqueta individual por executante",
                "Energias residuais dissipadas",
                "Teste de tentativa de partida realizado",
                "Proteções fixas e móveis mapeadas para remontagem",
            ],
        },
    ],
}


def seed_data(apps, schema_editor):
    RiskArea = apps.get_model("core", "RiskArea")
    ChecklistItemTemplate = apps.get_model("permits", "ChecklistItemTemplate")
    for slug, groups in RISK_AREA_CHECKLISTS.items():
        try:
            risk_area = RiskArea.objects.get(slug=slug)
        except RiskArea.DoesNotExist:
            continue
        order = 0
        for group in groups:
            for description in group["items"]:
                ChecklistItemTemplate.objects.update_or_create(
                    risk_area=risk_area,
                    group_title=group["group_title"],
                    description=description,
                    defaults={"order": order},
                )
                order += 1


def remove_data(apps, schema_editor):
    ChecklistItemTemplate = apps.get_model("permits", "ChecklistItemTemplate")
    ChecklistItemTemplate.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("permits", "0001_initial"),
        ("core", "0002_seed_reference_data"),
    ]
    operations = [migrations.RunPython(seed_data, remove_data)]
