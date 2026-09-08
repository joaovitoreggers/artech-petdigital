from django import template

from permits.constants import gas_measurement_specs

register = template.Library()


@register.filter
def gauge_specs(work_permit):
    """The gas-gauge specs (label/unit/limit) for a permit's required
    measurements — `{{ permit|gauge_specs }}`, used wherever a permit's
    latest reading is rendered outside the wizard's own gas step."""
    return gas_measurement_specs(work_permit.required_gas_measurement_keys)
