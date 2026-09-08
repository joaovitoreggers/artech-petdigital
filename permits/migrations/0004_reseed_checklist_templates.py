from django.db import migrations

# Snapshot of permits.constants as of this migration — data migrations must
# not import live application constants, since a later refactor of that
# module (as happened here) would break every future `manage.py` invocation
# that has to load this already-applied migration from disk.
SHARED_CHECKLIST_GROUPS = [
    {
        "group_title": "Equipamento de Proteção Individual",
        "items": [
            ("Capacete com jugular", "NR-06"),
            ("Protetor auricular", "NR-06"),
            ("Óculos de segurança", "NR-06"),
            ("Luvas de proteção (mecânica/química)", "NR-06"),
            ("Botina de segurança (mecânica/química)", "NR-06"),
            ("Cinto de segurança com talabarte ou trava-quedas", "NR-06"),
            ("Proteção para solda, luva, avental e máscara", "NR-06"),
            ("Vestimenta impermeável", "NR-06"),
            ("Respirador semifacial (amônia)", "NR-06"),
            ("Respirador facial completo (cartucho HN3/multigases)", "NR-06"),
            ("Proteção respiratória — EPR ou ar mandado (usando ou próximo)", "NR-06"),
            ("Outros EPIs exigidos pela atividade", "NR-06"),
            ("Todos os EPIs foram inspecionados?", "NR-06"),
        ],
    },
]

RISK_AREA_CHECKLISTS = {
    "confinado": [
        {
            "group_title": "Condições atmosféricas e do ambiente",
            "items": [
                ("Limite de explosividade (LIE/LEL) está nulo?", "NR-33"),
                ("Possibilidade de formação de gases foi anulada?", "NR-33"),
                ("Poeira e pó em suspensão estão controlados?", "NR-33"),
                ("Existe ventilação?", "NR-33"),
                ("Realizado bloqueio e sinalização? (elétrico/mecânico)", "NR-33"),
                ("Eliminado risco de afogamento, engolfamento e soterramento?", "NR-33"),
                ("Ambiente iluminado?", "NR-33"),
            ],
        },
        {
            "group_title": "Equipe e comunicação",
            "items": [
                ("Trabalhadores com treinamentos válidos em NR-33?", "NR-33"),
                ("Trabalhadores em condições físicas/clínicas?", "NR-33"),
                ("Comunicação clara entre vigia e trabalhadores?", "NR-33"),
                ("Comunicação entre equipe de vigia e resgate?", "NR-33"),
                ("Equipamentos de monitoramento testados e calibrados?", "NR-33"),
            ],
        },
        {
            "group_title": "Escavação (quando aplicável)",
            "items": [
                ("Escavação escorada? (se +1,5 m de profundidade)", "NR-33"),
                ("Trabalhadores com treinamentos válidos em NR-18?", "NR-18"),
            ],
        },
    ],
    "quente": [
        {
            "group_title": "Prevenção de incêndio",
            "items": [
                ("Equipamentos e ferramentas em boas condições?", "NR-18"),
                ("Área está sinalizada e isolada?", "NR-18"),
                ("Realizado bloqueio? (elétrico/mecânico)", "NR-18"),
                ("Retirado todo inflamável do ambiente?", "NR-18"),
                ("Retirado material combustível?", "NR-18"),
                ("Lonas resistentes a fogo para recolher fagulhas?", "NR-18"),
                ("Aberturas nas paredes e piso foram cobertas?", "NR-18"),
                ("Equipamento de combate a incêndio próximo?", "NR-18"),
                ("Vigias capacitados em combate a incêndio?", "NR-18"),
            ],
        },
    ],
    "altura": [
        {
            "group_title": "Condições gerais",
            "items": [
                ("Trabalhador com treinamento válido em NR-35?", "NR-35"),
                ("Trabalhadores em condições físicas/clínicas?", "NR-35"),
                ("Ausência de condições impeditivas? (clima, etc.)", "NR-35"),
                ("Área está sinalizada e isolada?", "NR-35"),
                ("Meio seguro para deslocamento de material?", "NR-35"),
                ("Local suficientemente afastado de redes energizadas?", "NR-35"),
                ("Há comunicação clara entre os trabalhadores?", "NR-35"),
                ("Foi instalada linha de vida?", "NR-35"),
                ("Pontos seguros de ancoragem?", "NR-35"),
            ],
        },
        {
            "group_title": "Escada (quando aplicável)",
            "items": [
                ("A escada está amarrada e estaiada?", "NR-35"),
                ("A escada está em piso com aderência e nivelada?", "NR-35"),
            ],
        },
        {
            "group_title": "Andaime (quando aplicável)",
            "items": [
                ("O andaime está nivelado, com freio/trava nos rodízios?", "NR-35"),
                ("O andaime possui forração completa?", "NR-35"),
                ("O andaime possui escada, rodapé e guarda-corpo?", "NR-35"),
                ("O andaime está estaiado? (altura +4x a base menor)", "NR-35"),
            ],
        },
    ],
    "eletrico": [
        {
            "group_title": "Desenergização",
            "items": [
                ("Seccionamento do circuito", "NR-10"),
                ("Impedimento de reenergização — cadeado e etiqueta", "NR-10"),
                ("Constatação da ausência de tensão", "NR-10"),
                ("Instalação de aterramento temporário", "NR-10"),
                ("Sinalização e delimitação da zona controlada", "NR-10"),
            ],
        },
    ],
    "maquinas": [
        {
            "group_title": "Bloqueio LOTO",
            "items": [
                ("Parada do equipamento pelo comando local", "NR-12"),
                ("Cadeado e etiqueta individual por executante", "NR-12"),
                ("Energias residuais dissipadas", "NR-12"),
                ("Teste de tentativa de partida realizado", "NR-12"),
                ("Proteções fixas e móveis mapeadas para remontagem", "NR-12"),
            ],
        },
    ],
    "icamento": [
        {
            "group_title": "Operação de içamento",
            "items": [
                ("Operador capacitado?", "NR-11"),
                ("Trabalhadores em condições físicas/clínicas?", "NR-11"),
                ("Ausência de condições impeditivas? (clima, vento, etc.)", "NR-11"),
                ("Boa iluminação e visibilidade?", "NR-11"),
                ("Área está sinalizada e isolada?", "NR-11"),
                ("Avisados envolvidos diretos/indiretos sobre risco de queda?", "NR-11"),
                ("Distante das redes de energia? (+5 m em alta tensão)", "NR-11"),
                ("Plano de rigging e ART estão conformes?", "NR-11"),
                ("Máquina nivelada e patolada?", "NR-11"),
                ("Peso da carga conforme com a capacidade da máquina?", "NR-11"),
                ("Máquina, cintas e cordas em boas condições?", "NR-11"),
                ("Carga está amarrada/presa?", "NR-11"),
                ("Cabo guia para estabilização da carga?", "NR-11"),
            ],
        },
    ],
    "descarga": [
        {
            "group_title": "Descarga de gases/líquidos",
            "items": [
                ("Motorista capacitado NR-20 / MOPP?", "NR-20"),
                ("Trabalhadores em condições físicas/clínicas?", "NR-20"),
                ("Ausência de condições impeditivas? (clima, raios, etc.)", "NR-20"),
                ("Ausência de equipamentos elétricos/eletrônicos?", "NR-20"),
                ("Área está sinalizada e isolada?", "NR-20"),
                ("Equipamento de combate a incêndio próximo?", "NR-20"),
                ("Caminhão direcionado para saída?", "NR-20"),
                ("Caminhão está aterrado?", "NR-20"),
                ("Caminhão, mangueiras e bombas em boas condições?", "NR-20"),
            ],
        },
    ],
}


def seed_data(apps, schema_editor):
    RiskArea = apps.get_model("core", "RiskArea")
    ChecklistItemTemplate = apps.get_model("permits", "ChecklistItemTemplate")

    # The old (pre-paper-form) seed is fully superseded by this one — start clean.
    ChecklistItemTemplate.objects.all().delete()

    order = 0
    for group in SHARED_CHECKLIST_GROUPS:
        for description, regulatory_code in group["items"]:
            ChecklistItemTemplate.objects.create(
                risk_area=None,
                group_title=group["group_title"],
                description=description,
                regulatory_code=regulatory_code,
                order=order,
            )
            order += 1

    for slug, groups in RISK_AREA_CHECKLISTS.items():
        try:
            risk_area = RiskArea.objects.get(slug=slug)
        except RiskArea.DoesNotExist:
            continue
        for group in groups:
            for description, regulatory_code in group["items"]:
                ChecklistItemTemplate.objects.create(
                    risk_area=risk_area,
                    group_title=group["group_title"],
                    description=description,
                    regulatory_code=regulatory_code,
                    order=order,
                )
                order += 1


def remove_data(apps, schema_editor):
    ChecklistItemTemplate = apps.get_model("permits", "ChecklistItemTemplate")
    ChecklistItemTemplate.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("permits", "0003_alter_checklistitemtemplate_options_and_more"),
        ("core", "0003_seed_lifting_and_unloading_areas"),
    ]
    operations = [migrations.RunPython(seed_data, remove_data)]
