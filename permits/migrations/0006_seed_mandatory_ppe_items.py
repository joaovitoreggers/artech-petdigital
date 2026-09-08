from django.db import migrations

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


def seed_data(apps, schema_editor):
    RiskArea = apps.get_model("core", "RiskArea")
    ChecklistItemTemplate = apps.get_model("permits", "ChecklistItemTemplate")
    MandatoryPPEItem = apps.get_model("permits", "MandatoryPPEItem")

    # PPE is proven by photo now, not answered as a checklist question.
    ChecklistItemTemplate.objects.filter(risk_area__isnull=True).delete()

    for slug, items in RISK_AREA_MANDATORY_PPE.items():
        try:
            risk_area = RiskArea.objects.get(slug=slug)
        except RiskArea.DoesNotExist:
            continue
        for order, description in enumerate(items):
            MandatoryPPEItem.objects.update_or_create(
                risk_area=risk_area, description=description, defaults={"order": order}
            )


def remove_data(apps, schema_editor):
    MandatoryPPEItem = apps.get_model("permits", "MandatoryPPEItem")
    MandatoryPPEItem.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("permits", "0005_mandatoryppeitem_permitppeverification")]
    operations = [migrations.RunPython(seed_data, remove_data)]
