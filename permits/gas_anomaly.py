"""Flags a gas reading that's statistically inconsistent with the historical
pattern for its kind of risk area — a possible faulty or miscalibrated
sensor, or a fat-fingered manual entry, not necessarily a genuinely unsafe
atmosphere (that's what GasReading.is_within_limits already checks against
the fixed NR-33 limits). This only ever warns; it never blocks the wizard,
since a real reading can legitimately be unusual.

Like permits.priority_score, this is a plain statistical calculation
(z-score against a rolling baseline), not an LLM call: spotting an outlier
in a numeric series is exactly what a formula does reliably and
transparently — the technician sees the actual mean/spread behind the
warning instead of an opaque judgment.
"""

import statistics
from dataclasses import dataclass

from .constants import GAS_LIMITS

MIN_SAMPLES = 5
Z_SCORE_THRESHOLD = 2.5


@dataclass
class Anomaly:
    key: str
    label: str
    value: float
    mean: float
    stdev: float
    sample_size: int

    @property
    def message(self):
        return (
            f"Leitura de {self.label} ({self.value}{GAS_LIMITS[self.key]['unit']}) fora do padrão "
            f"histórico deste tipo de área (média {self.mean}{GAS_LIMITS[self.key]['unit']}, "
            f"desvio {self.stdev} · {self.sample_size} leituras anteriores) — confira se o sensor "
            f"está calibrado antes de prosseguir."
        )


def detect_anomalies(work_permit, reading):
    """Compares each measurement filled in on `reading` against past
    readings from other permits sharing at least one risk area with this
    one (same organization). Returns a list of Anomaly, one per
    measurement whose z-score against that history exceeds the threshold —
    only when there's enough history (MIN_SAMPLES) to make the comparison
    meaningful.
    """
    risk_areas = list(work_permit.risk_areas.all())
    if not risk_areas:
        return []

    from .models import GasReading

    baseline_readings = (
        GasReading.objects.filter(
            work_permit__organization=work_permit.organization,
            work_permit__risk_areas__in=risk_areas,
        )
        .exclude(work_permit=work_permit)
        .distinct()
    )

    anomalies = []
    for key in work_permit.required_gas_measurement_keys:
        value = getattr(reading, key)
        if value is None:
            continue
        history = [
            float(v) for v in baseline_readings.values_list(key, flat=True) if v is not None
        ]
        if len(history) < MIN_SAMPLES:
            continue
        mean = statistics.mean(history)
        stdev = statistics.pstdev(history)
        if stdev == 0:
            continue
        z_score = abs(float(value) - mean) / stdev
        if z_score >= Z_SCORE_THRESHOLD:
            anomalies.append(
                Anomaly(
                    key=key,
                    label=GAS_LIMITS[key]["label"],
                    value=float(value),
                    mean=round(mean, 1),
                    stdev=round(stdev, 1),
                    sample_size=len(history),
                )
            )
    return anomalies
