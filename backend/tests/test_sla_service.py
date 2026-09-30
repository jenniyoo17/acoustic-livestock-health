from datetime import datetime, timedelta, timezone
import uuid

import pytest

from app.models.alert import Alert, AlertStatus, AnomalySeverity, SLATier
from app.models.escalation_record import EscalationRecord
from app.services.sla import evaluate_alert_sla, sla_deadline, transition_alert_status

START = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)


def make_alert(
    severity=AnomalySeverity.High,
    status=AlertStatus.Pending_Triage,
    tier=SLATier.Tier_1_Farm_Owner,
):
    return Alert(
        id=uuid.uuid4(),
        acoustic_event_id=uuid.uuid4(),
        shed_id=uuid.uuid4(),
        anomaly_severity=severity,
        status=status,
        current_sla_tier=tier,
        triggered_at=START,
    )


def make_record(alert, tier, started_at=START, acknowledged_at=None):
    return EscalationRecord(
        alert_id=alert.id,
        from_tier=None,
        to_tier=tier,
        reason="test",
        triggered_at=started_at,
        acknowledged_at=acknowledged_at,
    )


def test_tier_one_within_sla_and_breach_boundary():
    alert = make_alert()
    record = make_record(alert, SLATier.Tier_1_Farm_Owner)

    assert sla_deadline(alert, record) == START + timedelta(minutes=15)
    assert evaluate_alert_sla(alert, START + timedelta(minutes=14), record) is None
    decision = evaluate_alert_sla(alert, START + timedelta(minutes=15), record)
    assert decision is not None
    assert decision.to_tier == SLATier.Tier_2_Field_Vet


def test_tier_two_escalates_after_45_minutes():
    alert = make_alert(
        status=AlertStatus.Escalated,
        tier=SLATier.Tier_2_Field_Vet,
    )
    tier_two_start = START + timedelta(minutes=15)
    record = make_record(alert, SLATier.Tier_2_Field_Vet, tier_two_start)

    assert evaluate_alert_sla(alert, tier_two_start + timedelta(minutes=44), record) is None
    decision = evaluate_alert_sla(alert, tier_two_start + timedelta(minutes=45), record)
    assert decision is not None
    assert decision.to_tier == SLATier.Tier_3_District_Officer


def test_acknowledged_and_low_severity_alerts_do_not_escalate():
    alert = make_alert()
    acknowledged = make_record(
        alert,
        SLATier.Tier_1_Farm_Owner,
        acknowledged_at=START + timedelta(minutes=10),
    )
    assert sla_deadline(alert, acknowledged) is None
    assert evaluate_alert_sla(alert, START + timedelta(hours=2), acknowledged) is None

    low_alert = make_alert(severity=AnomalySeverity.Low)
    assert evaluate_alert_sla(low_alert, START + timedelta(days=1), None) is None


def test_critical_alert_uses_tier_one_sla_and_tier_three_has_no_next_escalation():
    critical_alert = make_alert(severity=AnomalySeverity.Critical)
    tier_one = make_record(critical_alert, SLATier.Tier_1_Farm_Owner)
    decision = evaluate_alert_sla(critical_alert, START + timedelta(minutes=15), tier_one)
    assert decision is not None
    assert decision.to_tier == SLATier.Tier_2_Field_Vet

    tier_three_alert = make_alert(
        status=AlertStatus.Escalated,
        tier=SLATier.Tier_3_District_Officer,
    )
    tier_three = make_record(tier_three_alert, SLATier.Tier_3_District_Officer)
    assert evaluate_alert_sla(tier_three_alert, START + timedelta(days=2), tier_three) is None


@pytest.mark.parametrize(
    ("initial", "final"),
    [
        (AlertStatus.Pending_Triage, AlertStatus.Escalated),
        (AlertStatus.Pending_Triage, AlertStatus.Under_Vet_Review),
        (AlertStatus.Escalated, AlertStatus.Under_Vet_Review),
        (AlertStatus.Under_Vet_Review, AlertStatus.Verified_Risk),
        (AlertStatus.Under_Vet_Review, AlertStatus.False_Positive),
        (AlertStatus.Verified_Risk, AlertStatus.Resolved),
        (AlertStatus.False_Positive, AlertStatus.Resolved),
    ],
)
def test_allowed_status_transitions(initial, final):
    alert = make_alert(status=initial)
    transition_alert_status(alert, final)
    assert alert.status == final


def test_verified_status_cannot_be_set_from_pending_triage():
    alert = make_alert()
    with pytest.raises(ValueError, match="Invalid alert transition"):
        transition_alert_status(alert, AlertStatus.Verified_Risk)
