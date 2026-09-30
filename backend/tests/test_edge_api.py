import pytest
from fastapi import status
from httpx import AsyncClient
from pydantic import ValidationError

from app.api.v1.edge import calculate_batch_hash
from app.core.device_auth import device_auth_service
from app.models.acoustic_event import AcousticEvent
from app.models.alert import Alert
from app.schemas.ingest import IngestRequest
from app.services.notifications import NotificationService


def make_event(device_uid="MIC-TEST-001", timestamp=1_780_000_000.0, **overrides):
    payload = {
        "device_uid": device_uid,
        "timestamp": timestamp,
        "event_type": "Cough",
        "confidence": 0.89,
        "duration_sec": 2.4,
        "embedding": [0.01, -0.02],
    }
    signature_override = overrides.pop("signature", None)
    payload.update(overrides)
    payload["signature"] = signature_override or device_auth_service.create_signature(payload)
    return payload


@pytest.mark.asyncio
async def test_ingest_valid_event_persists_event_and_alert(async_client: AsyncClient, db_session, seed_test_device):
    response = await async_client.post("/api/v1/edge/ingest", json=make_event())

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["accepted"] is True
    assert data["status"] == "stored"
    assert data["alert_created"] is True
    assert data["alert_id"]
    assert len(db_session.records[AcousticEvent]) == 1
    assert len(db_session.records[Alert]) == 1
    assert db_session.records[AcousticEvent][0].shed_id == seed_test_device.shed_id


@pytest.mark.asyncio
async def test_high_alert_sends_mock_tier_one_sms(async_client: AsyncClient, seed_test_device, monkeypatch):
    notifications = NotificationService()
    monkeypatch.setattr("app.api.v1.edge.notification_service", notifications)

    response = await async_client.post("/api/v1/edge/ingest", json=make_event())

    assert response.status_code == status.HTTP_201_CREATED
    assert len(notifications.sms.records) == 1
    assert notifications.sms.records[0].recipient == "demo-farm-owner"
    assert str(notifications.sms.records[0].alert_id) == response.json()["alert_id"]


@pytest.mark.asyncio
async def test_ingest_unknown_device_is_rejected(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/edge/ingest", json=make_event(device_uid="UNKNOWN-DEVICE")
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_ingest_invalid_signature_is_rejected(async_client: AsyncClient, seed_test_device):
    response = await async_client.post(
        "/api/v1/edge/ingest", json=make_event(signature="0" * 64)
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_ingest_invalid_payload_is_rejected(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/edge/ingest", json=make_event(confidence=1.5)
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    with pytest.raises(ValidationError):
        IngestRequest(**make_event(event_type="Unrecognized"))


@pytest.mark.asyncio
async def test_signature_covers_event_contents(async_client: AsyncClient, seed_test_device):
    payload = make_event()
    payload["confidence"] = 0.11
    response = await async_client.post("/api/v1/edge/ingest", json=payload)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_single_ingest_is_idempotent(async_client: AsyncClient, seed_test_device):
    payload = make_event()
    first = await async_client.post("/api/v1/edge/ingest", json=payload)
    second = await async_client.post("/api/v1/edge/ingest", json=payload)

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_200_OK
    assert first.json()["event_id"] == second.json()["event_id"]


@pytest.mark.asyncio
async def test_batch_sync_accepts_valid_events(async_client: AsyncClient, seed_test_device):
    events = [
        IngestRequest(**make_event(timestamp=1_780_000_000.0 + index))
        for index in range(3)
    ]
    response = await async_client.post(
        "/api/v1/edge/sync-batch",
        json={
            "events": [event.model_dump(mode="json") for event in events],
            "batch_hash": calculate_batch_hash(events),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["accepted"] == 3
    assert response.json()["duplicates"] == 0
    assert response.json()["rejected"] == 0


@pytest.mark.asyncio
async def test_batch_sync_rejects_more_than_50_events(async_client: AsyncClient, seed_test_device):
    events = [
        IngestRequest(**make_event(timestamp=1_780_000_000.0 + index))
        for index in range(51)
    ]
    response = await async_client.post(
        "/api/v1/edge/sync-batch",
        json={
            "events": [event.model_dump(mode="json") for event in events],
            "batch_hash": calculate_batch_hash(events),
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_batch_sync_verifies_hash_and_is_idempotent(async_client: AsyncClient, seed_test_device):
    event = IngestRequest(**make_event())
    events = [event]
    request_body = {
        "events": [event.model_dump(mode="json")],
        "batch_hash": calculate_batch_hash(events),
    }

    invalid = await async_client.post(
        "/api/v1/edge/sync-batch",
        json={**request_body, "batch_hash": "0" * 64},
    )
    first = await async_client.post("/api/v1/edge/sync-batch", json=request_body)
    second = await async_client.post("/api/v1/edge/sync-batch", json=request_body)

    assert invalid.status_code == status.HTTP_400_BAD_REQUEST
    assert first.json()["accepted"] == 1
    assert second.json()["accepted"] == 0
    assert second.json()["duplicates"] == 1
    assert second.json()["results"][0]["status"] == "duplicate"


@pytest.mark.asyncio
async def test_batch_sync_reports_unknown_device_as_rejected(async_client: AsyncClient):
    event = IngestRequest(**make_event(device_uid="UNKNOWN-DEVICE"))
    response = await async_client.post(
        "/api/v1/edge/sync-batch",
        json={
            "events": [event.model_dump(mode="json")],
            "batch_hash": calculate_batch_hash([event]),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["rejected"] == 1


@pytest.mark.asyncio
async def test_heartbeat_updates_device(async_client: AsyncClient, seed_test_device):
    response = await async_client.post(
        "/api/v1/edge/heartbeat",
        json={"device_uid": seed_test_device.device_uid, "status": "Degraded"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["device_uid"] == seed_test_device.device_uid
    assert response.json()["status"] == "Degraded"
    assert response.json()["last_heartbeat_at"]
    assert seed_test_device.last_heartbeat_at is not None


@pytest.mark.asyncio
async def test_heartbeat_unknown_device_is_rejected(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/edge/heartbeat", json={"device_uid": "UNKNOWN-DEVICE"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND