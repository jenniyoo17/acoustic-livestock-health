from dataclasses import dataclass
from datetime import datetime, timedelta

from app.models.alert import Alert, AlertStatus, AnomalySeverity, SLATier
from app.models.escalation_record import EscalationRecord

SLA_THRESHOLDS = {
    SLATier.Tier_1_Farm_Owner: timedelta(minutes=15),
    SLATier.Tier_2_Field_Vet: timedelta(minutes=45),
}

STATUS_TRANSITIONS = {
    AlertStatus.Pending_Triage: {AlertStatus.Escalated, AlertStatus.Under_Vet_Review},
    AlertStatus.Escalated: {AlertStatus.Under_Vet_Review},
    AlertStatus.Under_Vet_Review: {
        AlertStatus.Verified_Risk,
        AlertStatus.False_Positive,
        AlertStatus.Escalated,
    },
    AlertStatus.Verified_Risk: {AlertStatus.Resolved},
    AlertStatus.False_Positive: {AlertStatus.Resolved},
    AlertStatus.Resolved: set(),
}


@dataclass(frozen=True)
class EscalationDecision:
    from_tier: SLATier
    to_tier: SLATier
    reason: str


def transition_alert_status(alert: Alert, new_status: AlertStatus) -> None:
    if new_status == alert.status:
        return
    if new_status not in STATUS_TRANSITIONS[alert.status]:
        raise ValueError(f"Invalid alert transition: {alert.status.value} -> {new_status.value}")
    alert.status = new_status


def sla_deadline(
    alert: Alert,
    active_record: EscalationRecord | None,
) -> datetime | None:
    if alert.anomaly_severity not in {AnomalySeverity.High, AnomalySeverity.Critical}:
        return None
    if alert.status in {AlertStatus.Verified_Risk, AlertStatus.False_Positive, AlertStatus.Resolved}:
        return None
    threshold = SLA_THRESHOLDS.get(alert.current_sla_tier)
    if threshold is None:
        return None
    if active_record is not None:
        if active_record.to_tier != alert.current_sla_tier or active_record.acknowledged_at is not None:
            return None
        started_at = active_record.triggered_at
    else:
        started_at = alert.triggered_at
    return started_at + threshold


def evaluate_alert_sla(
    alert: Alert,
    current_time: datetime,
    active_record: EscalationRecord | None,
) -> EscalationDecision | None:
    deadline = sla_deadline(alert, active_record)
    if deadline is None or current_time < deadline:
        return None

    from_tier = alert.current_sla_tier
    if from_tier == SLATier.Tier_1_Farm_Owner:
        to_tier = SLATier.Tier_2_Field_Vet
        threshold_minutes = 15
    elif from_tier == SLATier.Tier_2_Field_Vet:
        to_tier = SLATier.Tier_3_District_Officer
        threshold_minutes = 45
    else:
        return None
    return EscalationDecision(
        from_tier=from_tier,
        to_tier=to_tier,
        reason=f"{from_tier.value} acknowledgement exceeded its {threshold_minutes}-minute SLA",
    )
