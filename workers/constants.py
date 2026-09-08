"""The starter document-type library every new organization is seeded with
(see core.onboarding.provision_organization) — editable per-organization
afterwards through the admin."""

DEFAULT_DOCUMENT_TYPES = [
    {"code": "ASO", "name": "Atestado de Saúde Ocupacional", "description": "Atestado de saúde ocupacional"},
    {"code": "NR-33", "name": "Espaço confinado", "description": "Espaço confinado · trabalhador autorizado"},
    {"code": "NR-18", "name": "Trabalho a quente", "description": "Trabalho a quente"},
    {"code": "NR-35", "name": "Trabalho em altura", "description": "Trabalho em altura"},
    {"code": "NR-10", "name": "Instalações elétricas", "description": "Segurança em instalações elétricas"},
    {"code": "NR-12", "name": "Máquinas e equipamentos", "description": "Máquinas e equipamentos · bloqueio"},
    {"code": "NR-13", "name": "Caldeiras e vasos de pressão", "description": "Caldeiras e vasos de pressão"},
    {"code": "NR-11", "name": "Movimentação e transporte de materiais", "description": "Içamento de carga · operador capacitado"},
    {"code": "NR-20", "name": "Inflamáveis e combustíveis", "description": "Descarga de gases/líquidos · NR-20 / MOPP"},
]
