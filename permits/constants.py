"""Domain data ported from the prototype's per-risk-area configuration
(EXTRAS in PET Digital.dc.html) plus the checklist transcribed verbatim
from the paper PET form (FO 060 330-37, Lar Cooperativa Agroindustrial),
keyed by `core.RiskArea.slug` so it stays in sync with the seeded risk
areas. Checklist items are `(description, regulatory_code)` pairs — the
code is the NR *the question itself* maps to, which is occasionally not
the area it's grouped under on the paper form (e.g. an excavation-depth
question inside the confined-space section that references NR-18).
"""

GAS_LIMITS = {
    "oxygen": {"label": "O₂", "unit": "%", "min": 19.5, "max": 23.0},
    "carbon_monoxide": {"label": "CO", "unit": "ppm", "min": None, "max": 25},
    "hydrogen_sulfide": {"label": "H₂S", "unit": "ppm", "min": None, "max": 8},
    "lower_explosive_limit": {"label": "LEL", "unit": "%", "min": None, "max": 10},
}

# The starter risk-area library every new organization is seeded with (see
# core.onboarding.provision_organization) — the same 7 NRs the platform
# shipped with, editable per-organization afterwards through the admin.
DEFAULT_RISK_AREAS = [
    {
        "slug": "confinado",
        "name": "Espaço confinado",
        "regulatory_code": "NR-33",
        "description": "Silos, moegas, tanques, elevatórias",
        "required_gas_measurements": ["oxygen", "carbon_monoxide", "hydrogen_sulfide", "lower_explosive_limit"],
        "order": 1,
    },
    {
        "slug": "quente",
        "name": "Trabalho a quente",
        "regulatory_code": "NR-18",
        "description": "Solda, corte, esmerilhamento",
        "required_gas_measurements": ["lower_explosive_limit"],
        "order": 2,
    },
    {
        "slug": "altura",
        "name": "Trabalho em altura",
        "regulatory_code": "NR-35",
        "description": "Acima de 2 m do nível inferior",
        "required_gas_measurements": [],
        "order": 3,
    },
    {
        "slug": "eletrico",
        "name": "Serviço elétrico",
        "regulatory_code": "NR-10",
        "description": "Painéis, CCM, alta tensão",
        "required_gas_measurements": [],
        "order": 4,
    },
    {
        "slug": "maquinas",
        "name": "Máquinas e bloqueio",
        "regulatory_code": "NR-12",
        "description": "Intervenção em equipamento motorizado",
        "required_gas_measurements": [],
        "order": 5,
    },
    {
        "slug": "icamento",
        "name": "Içamento de carga",
        "regulatory_code": "NR-11",
        "description": "Guindaste, munck, talha — movimentação de cargas suspensas",
        "required_gas_measurements": [],
        "order": 6,
    },
    {
        "slug": "descarga",
        "name": "Descarga de gases/líquidos",
        "regulatory_code": "NR-20",
        "description": "Carga/descarga de inflamáveis e combustíveis",
        "required_gas_measurements": [],
        "order": 7,
    },
]


def gas_limit_display(key):
    """Human-readable limit text for a GAS_LIMITS key, e.g. '19,5 – 23,0 %' or 'máx. 25 ppm'."""
    limits = GAS_LIMITS[key]

    def fmt(value):
        return f"{value:g}".replace(".", ",")

    if limits["min"] is not None:
        return f"{fmt(limits['min'])} – {fmt(limits['max'])} {limits['unit']}"
    return f"máx. {fmt(limits['max'])} {limits['unit']}"


def gas_measurement_specs(measurement_keys):
    """[{"key", "label", "unit", "limit_text"}, ...] for the given GAS_LIMITS
    keys, in a stable order — what the gas step's gauges/form are built from."""
    return [
        {
            "key": key,
            "label": GAS_LIMITS[key]["label"],
            "unit": GAS_LIMITS[key]["unit"],
            "limit_text": gas_limit_display(key),
        }
        for key in GAS_LIMITS
        if key in measurement_keys
    ]

# Extra fields captured on the "Atividade e local" step, one set per
# selected risk area, rendered as free-text inputs.
RISK_AREA_EXTRA_FIELDS = {
    "confinado": [
        {"key": "space_type", "label": "Tipo de espaço confinado"},
        {"key": "access_openings", "label": "Aberturas de acesso"},
        {"key": "external_watcher", "label": "Vigia externo designado"},
        {"key": "rescue_team", "label": "Equipe de resgate acionável"},
        {"key": "ventilation", "label": "Ventilação forçada"},
        {"key": "excavation_engineer", "label": "Responsável pela escavação (engenheiro, se aplicável)"},
    ],
    "quente": [
        {"key": "hot_work_process", "label": "Processo de trabalho a quente"},
        {"key": "isolation_radius", "label": "Raio de isolamento da área"},
        {"key": "combustible_materials", "label": "Materiais combustíveis"},
        {"key": "fire_fighting_resource", "label": "Recurso de combate a incêndio"},
        {"key": "fire_watcher", "label": "Vigia de fogo (60 min após)"},
    ],
    "altura": [
        {"key": "work_height", "label": "Altura do trabalho"},
        {"key": "access_method", "label": "Meio de acesso (escada/estrutura/andaime/PEMT/gaiola/outro)"},
        {"key": "anchor_point", "label": "Ponto de ancoragem certificado"},
        {"key": "drop_zone_isolation", "label": "Isolamento da projeção no piso"},
        {"key": "rescue_plan", "label": "Plano de resgate em altura"},
    ],
    "eletrico": [
        {"key": "working_voltage", "label": "Tensão de trabalho"},
        {"key": "panel_circuit", "label": "Painel / circuito"},
        {"key": "circuit_state", "label": "Estado do circuito"},
        {"key": "temporary_grounding", "label": "Aterramento temporário"},
        {"key": "voltage_absence_test", "label": "Teste de ausência de tensão"},
    ],
    "maquinas": [
        {"key": "equipment", "label": "Equipamento"},
        {"key": "asset_tag", "label": "TAG do ativo"},
        {"key": "lockout_points", "label": "Pontos de bloqueio de energia"},
        {"key": "locks_applied", "label": "Cadeados aplicados"},
        {"key": "residual_energy", "label": "Energia residual dissipada"},
    ],
    "icamento": [
        {"key": "equipment", "label": "Equipamento de içamento"},
        {"key": "load_weight", "label": "Peso da carga"},
        {"key": "rigging_plan", "label": "Plano de rigging / ART"},
        {"key": "crane_operator", "label": "Operador responsável"},
    ],
    "descarga": [
        {"key": "product", "label": "Produto descarregado"},
        {"key": "vehicle_plate", "label": "Placa do veículo/caminhão"},
        {"key": "driver", "label": "Motorista responsável"},
    ],
}

# Mandatory PPE per risk area (NR-06 + the area's own NR). No longer a
# yes/no checklist: the executing worker proves these are being worn with
# a single photo, checked by permits.ppe_verification against this list
# (see the "Verificação de EPI" wizard step).
RISK_AREA_MANDATORY_PPE = {
    "confinado": [
        "Capacete com jugular",
        "Respirador com filtro adequado ao contaminante",
        "Cinto paraquedista com trava-queda",
        "Luvas e botina de segurança",
    ],
    "quente": [
        "Máscara de solda com filtro adequado",
        "Avental e mangote de raspa",
        "Luvas de solda",
        "Protetor auricular",
    ],
    "altura": [
        "Capacete com jugular",
        "Cinto paraquedista com duplo talabarte",
        "Trava-queda retrátil",
        "Calçado antiderrapante",
    ],
    "eletrico": [
        "Vestimenta antiarco com ATPV compatível",
        "Luva isolante de classe adequada",
        "Capacete com viseira de policarbonato",
        "Calçado isolante",
    ],
    "maquinas": [
        "Luvas de proteção mecânica",
        "Óculos de segurança",
        "Capacete",
        "Calçado de segurança",
    ],
    "icamento": [
        "Capacete de segurança",
        "Luvas de proteção mecânica",
        "Óculos de segurança",
        "Calçado de segurança",
        "Colete de sinalização",
    ],
    "descarga": [
        "Capacete de segurança",
        "Luvas resistentes a produtos químicos",
        "Óculos de proteção química",
        "Vestimenta antiestática",
        "Calçado de segurança condutivo",
    ],
}

# Checklist templates seeded into ChecklistItemTemplate per risk area,
# transcribed from the paper PET form (Lar Cooperativa Agroindustrial,
# FO 060 330-37 v5 09/2025) where the area is covered by that form, plus
# the system's own NR-10/NR-12 content where it isn't.
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

# Shown as guidance text on the checklist step when NR-33 applies —
# condensed from the paper form's "Orientações Gerais Espaço Confinado".
CONFINED_SPACE_GENERAL_GUIDANCE = (
    "É proibida a entrada e trabalho sem uso de equipamento de proteção respiratória quando a "
    "concentração de oxigênio estiver fora de 19,5–23%, o monóxido de carbono acima de 39 ppm ou o "
    "gás sulfídrico acima de 8 ppm. Qualquer saída de toda a equipe implica no encerramento da PET — "
    "a situação deve ser regularizada e uma nova PET aberta após novo monitoramento."
)

# Document types (workers.DocumentType.code) a worker must have valid before
# being added to a permit's team, based on the permit's selected risk areas.
# ASO is always required regardless of area.
RISK_AREA_REQUIRED_DOCUMENTS = {
    "confinado": ["NR-33"],
    "quente": ["NR-18"],
    "altura": ["NR-35"],
    "eletrico": ["NR-10"],
    "maquinas": ["NR-12"],
    "icamento": ["NR-11"],
    "descarga": ["NR-20"],
}
BASE_REQUIRED_DOCUMENTS = ["ASO"]

INTERVENTION_TYPES = [
    "Manutenção corretiva",
    "Manutenção preventiva",
    "Limpeza técnica",
    "Inspeção",
    "Montagem / obra",
]
