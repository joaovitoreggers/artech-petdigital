"""Step order and navigation helpers for the "Nova PET" field wizard.

Steps are persisted directly on the draft WorkPermit (not session state) so
a technician who loses signal or closes the browser mid-flow can resume
exactly where they left off.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WizardStep:
    slug: str
    title: str
    url_name: str


STEPS = [
    WizardStep("area", "Área de risco", "permits:wizard_area"),
    WizardStep("activity", "Atividade e local", "permits:wizard_activity"),
    WizardStep("gas", "Medição atmosférica", "permits:wizard_gas"),
    WizardStep("team", "Crachá e permissão", "permits:wizard_team"),
    WizardStep("ppe", "Verificação de EPI", "permits:wizard_ppe"),
    WizardStep("checklist", "Checklist e foto", "permits:wizard_checklist"),
    WizardStep("signatures", "Assinaturas", "permits:wizard_signatures"),
]


def steps_for(work_permit):
    """The step list that applies to this permit (skips 'gas' when no
    selected risk area requires atmospheric monitoring)."""
    if work_permit.pk and work_permit.requires_gas_monitoring:
        return STEPS
    return [step for step in STEPS if step.slug != "gas"]


def step_context(work_permit, current_slug):
    """Numbering/progress-bar data for the wizard header."""
    applicable = steps_for(work_permit)
    slugs = [step.slug for step in applicable]
    index = slugs.index(current_slug)
    return {
        "steps": applicable,
        "step_index": index,
        "step_number": index + 1,
        "step_total": len(applicable),
        "step_title": applicable[index].title,
    }


def next_step(work_permit, current_slug):
    applicable = steps_for(work_permit)
    slugs = [step.slug for step in applicable]
    index = slugs.index(current_slug)
    if index + 1 < len(applicable):
        return applicable[index + 1]
    return None


def previous_step(work_permit, current_slug):
    applicable = steps_for(work_permit)
    slugs = [step.slug for step in applicable]
    index = slugs.index(current_slug)
    if index > 0:
        return applicable[index - 1]
    return None
