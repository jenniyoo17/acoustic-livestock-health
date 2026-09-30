from datetime import datetime, timedelta, timezone
import uuid

import pytest
from httpx import AsyncClient

from app.api.v1.alerts import notification_service
from app.models.alert import AlertStatus, AnomalySeverity, SLATier
from app.models.escalation_record import EscalationRecord
from app.services.notifications import NotificationService

START = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_alert_detail_and_escalation_status(async_client: AsyncClient, seed_test_alert):
    status_response = await async_client.get(
        "/api/v1/alerts/escalation-status", params={"at": START.isoformat()}
    )
    detail_response = await async_client.get(
        f"/api/v1/alerts/{seed_test_alert.id}", params={"at": START.isoformat()}
    )

    assert status_response.status_code == 200
    sla = status_response.json()[0]
    assert sla["alert_id"] == str(seed_test_alert.id)
    assert sla["current_sla_tier"] == SLATier.Tier_1_Farm_Owner.value
    assert sla["deadline"] == "2026-09-30T12:15:00Z"
    assert sla["remaining_seconds"] == 900
    assert sla["sla_breached"] is False
    assert len(sla["escalation_history"]) == 1

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["alert"]["id"] == str(seed_test_alert.id)
    assert detail["acoustic_event"]["event_type"] == "Cough"
    assert detail["shed"]["shed_number"] == "SLA-01"
    assert detail["device"]["device_uid"] == "MIC-SLA-001"
    assert detail["sla"]["current_sla_tier"] == SLATier.Tier_1_Farm_Owner.value


@pytest.mark.asyncio
async def test_simulated_sla_evaluation_escalates_tier_one_then_tier_two(
    async_client: AsyncClient,
    db_session,
    seed_test_alert,
    monkeypatch,
):
    notifications = NotificationService()
    monkeypatch.setattr("app.api.v1.alerts.notification_service", notifications)

    first = await async_client.post(
        "/api/v1/alerts/escalations/evaluate",
        params={"at": (START + timedelta(minutes=16)).isoformat()},
    )
    assert first.status_code == 200
    first_status = first.json()["statuses"][0]
    assert first.json()["escalated_count"] == 1
    assert first_status["status"] == AlertStatus.Escalated.value
    assert first_status["current_sla_tier"] == SLATier.Tier_2_Field_Vet.value
    assert notifications.sms.records[-1].recipient == "demo-field-vet"

    second = await async_client.post(
        "/api/v1/alerts/escalations/evaluate",
        params={"at": (START + timedelta(minutes=61)).isoformat()},
    )
    assert second.status_code == 200
    second_status = second.json()["statuses"][0]
    assert second.json()["escalated_count"] == 1
    assert second_status["status"] == AlertStatus.Escalated.value
    assert second_status["current_sla_tier"] == SLATier.Tier_3_District_Officer.value
    assert notifications.voice.records[-1].recipient == "demo-district-officer"
    assert len(db_session.records[EscalationRecord]) == 3

    repeated = await async_client.post(
        "/api/v1/alerts/escalations/evaluate",
        params={"at": (START + timedelta(minutes=90)).isoformat()},
    )
    assert repeated.status_code == 200
    assert repeated.json()["escalated_count"] == 0
    assert len(notifications.voice.records) == 1


@pytest.mark.asyncio
async def test_acknowledgement_forwards_to_vet_and_rejects_repeat(
    async_client: AsyncClient,
    db_session,
    seed_test_alert,
    monkeypatch,
):
    notifications = NotificationService()
    monkeypatch.setattr("app.api.v1.alerts.notification_service", notifications)
    alert_id = str(seed_test_alert.id)

    first = await async_client.post(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        json={"tier": SLATier.Tier_1_Farm_Owner.value},
    )
    duplicate = await async_client.post(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        json={"tier": SLATier.Tier_1_Farm_Owner.value},
    )
    vet_ack = await async_client.post(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        json={"tier": SLATier.Tier_2_Field_Vet.value},
    )
    vet_duplicate = await async_client.post(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        json={"tier": SLATier.Tier_2_Field_Vet.value},
    )

    assert first.status_code == 200
    assert first.json()["status"] == AlertStatus.Under_Vet_Review.value
    assert first.json()["current_sla_tier"] == SLATier.Tier_2_Field_Vet.value
    assert duplicate.status_code == 409
    assert vet_ack.status_code == 200
    assert vet_ack.json()["status"] == AlertStatus.Under_Vet_Review.value
    assert vet_duplicate.status_code == 409
    assert notifications.sms.records[-1].recipient == "demo-field-vet"
    assert len(db_session.records[EscalationRecord]) == 2


@pytest.mark.asyncio
async def test_low_alert_has_no_sla_deadline(async_client: AsyncClient, seed_test_alert):
    seed_test_alert.anomaly_severity = AnomalySeverity.Low

    response = await async_client.get("/api/v1/alerts/escalation-status")

    assert response.status_code == 200
    assert response.json()[0]["sla_enabled"] is False
    assert response.json()[0]["deadline"] is None


@pytest.mark.asyncio
async def test_unknown_alert_detail_and_acknowledgement_return_404(async_client: AsyncClient):
    missing_id = uuid.uuid4()
    detail = await async_client.get(f"/api/v1/alerts/{missing_id}")
    acknowledge = await async_client.post(
        f"/api/v1/alerts/{missing_id}/acknowledge",
        json={"tier": SLATier.Tier_1_Farm_Owner.value},
    )

    assert detail.status_code == 404
    assert acknowledge.status_code == 404


@pytest.mark.asyncio
async def test_simulated_status_read_does_not_mutate_alert(async_client: AsyncClient, seed_test_alert):
    response = await async_client.get(
        "/api/v1/alerts/escalation-status",
        params={"at": (START + timedelta(minutes=16)).isoformat()},
    )

    assert response.status_code == 200
    assert response.json()[0]["sla_breached"] is True
    assert seed_test_alert.status == AlertStatus.Pending_Triage
    assert seed_test_alert.current_sla_tier == SLATier.Tier_1_Farm_Owner