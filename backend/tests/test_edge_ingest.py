import time
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.farm import Farm
from app.models.shed import Shed, AnimalType
from app.models.device import Device, DeviceStatus
from app.models.acoustic_event import AcousticEvent, EventType
from app.models.alert import Alert, AnomalySeverity, AlertStatus


def datetime_now():
    return datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_models_and_relationships(db_session: AsyncSession):
    farm = Farm(
        name="Model Test Farm",
        owner_name="Test Owner",
        contact_phone="+91-1234567890",
        latitude=19.0760,
        longitude=72.8777,
        district="Mumbai",
        state="Maharashtra",
    )
    db_session.add(farm)
    await db_session.flush()

    shed = Shed(
        farm_id=farm.id,
        shed_number="S1",
        animal_type=AnimalType.Buffalo,
        capacity=50,
        current_count=40,
    )
    db_session.add(shed)
    await db_session.flush()

    device = Device(
        shed_id=shed.id,
        device_uid="MIC-MODEL-TEST",
        firmware_version="0.2.0",
        status=DeviceStatus.Online,
    )
    db_session.add(device)
    await db_session.flush()

    evt_time = datetime_now()
    evt = AcousticEvent(
        device_id=device.id,
        shed_id=shed.id,
        event_type=EventType.Cough,
        confidence_score=0.95,
        yamnet_embedding_vector=[0.1] * 1024,
        audio_duration_sec=2.0,
        recorded_at=evt_time,
        is_synced_offline=False,
    )
    db_session.add(evt)
    await db_session.flush()

    alert = Alert(
        acoustic_event_id=evt.id,
        shed_id=shed.id,
        anomaly_severity=AnomalySeverity.Critical,
        status=AlertStatus.Pending_Triage,
    )
    db_session.add(alert)
    await db_session.commit()

    # Query back & verify relationships with selectinload
    res = await db_session.execute(
        select(Farm)
        .options(selectinload(Farm.sheds).selectinload(Shed.devices))
        .where(Farm.id == farm.id)
    )
    fetched_farm = res.scalar_one()
    assert len(fetched_farm.sheds) == 1
    assert fetched_farm.sheds[0].shed_number == "S1"
    assert fetched_farm.sheds[0].devices[0].device_uid == "MIC-MODEL-TEST"


@pytest.mark.asyncio
async def test_ingest_valid_event(async_client: AsyncClient, seed_test_device: Device):
    payload = {
        "device_uid": seed_test_device.device_uid,
        "timestamp": time.time(),
        "event_type": "Cough",
        "confidence": 0.89,
        "duration_sec": 2.4,
        "embedding": [0.012, -0.045, 0.12],
        "signature": "valid_hmac_sig_123",
    }
    response = await async_client.post("/api/v1/edge/ingest", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["accepted"] is True
    assert data["device_uid"] == seed_test_device.device_uid
    assert data["status"] == "stored"
    assert data["alert_created"] is True
    assert data["alert_id"] is not None


@pytest.mark.asyncio
async def test_ingest_invalid_confidence(async_client: AsyncClient, seed_test_device: Device):
    payload = {
        "device_uid": seed_test_device.device_uid,
        "timestamp": time.time(),
        "event_type": "Cough",
        "confidence": 1.5,  # Invalid: > 1.0
        "duration_sec": 2.4,
        "embedding": [0.1, 0.2],
        "signature": "sig",
    }
    response = await async_client.post("/api/v1/edge/ingest", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ingest_invalid_event_type(async_client: AsyncClient, seed_test_device: Device):
    payload = {
        "device_uid": seed_test_device.device_uid,
        "timestamp": time.time(),
        "event_type": "Invalid_Disease_Type",
        "confidence": 0.85,
        "duration_sec": 2.4,
        "embedding": [0.1],
        "signature": "sig",
    }
    response = await async_client.post("/api/v1/edge/ingest", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ingest_unknown_device(async_client: AsyncClient):
    payload = {
        "device_uid": "NON-EXISTENT-DEVICE-UID-999",
        "timestamp": time.time(),
        "event_type": "Cough",
        "confidence": 0.85,
        "duration_sec": 2.4,
        "embedding": [0.1],
        "signature": "sig",
    }
    response = await async_client.post("/api/v1/edge/ingest", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_ingest_missing_fields(async_client: AsyncClient):
    payload = {
        "device_uid": "MIC-FARM01-SHED02",
        "event_type": "Cough",
    }
    response = await async_client.post("/api/v1/edge/ingest", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_sync_batch_valid(async_client: AsyncClient, seed_test_device: Device):
    now_ts = time.time()
    events = [
        {
            "device_uid": seed_test_device.device_uid,
            "timestamp": now_ts - i * 10,
            "event_type": "Cough",
            "confidence": 0.80,
            "duration_sec": 2.0,
            "embedding": [0.05, -0.05],
            "signature": "sig",
        }
        for i in range(5)
    ]
    response = await async_client.post("/api/v1/edge/sync-batch", json={"events": events})
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] == 5
    assert data["duplicates"] == 0
    assert data["rejected"] == 0
    assert len(data["results"]) == 5


@pytest.mark.asyncio
async def test_sync_batch_max_50(async_client: AsyncClient, seed_test_device: Device):
    now_ts = time.time()
    events = [
        {
            "device_uid": seed_test_device.device_uid,
            "timestamp": now_ts - i * 100,
            "event_type": "Abnormal_Rumination",
            "confidence": 0.75,
            "duration_sec": 3.0,
            "embedding": [0.1],
            "signature": "sig",
        }
        for i in range(50)
    ]
    response = await async_client.post("/api/v1/edge/sync-batch", json={"events": events})
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] == 50


@pytest.mark.asyncio
async def test_sync_batch_exceeds_50_rejected(async_client: AsyncClient, seed_test_device: Device):
    now_ts = time.time()
    events = [
        {
            "device_uid": seed_test_device.device_uid,
            "timestamp": now_ts - i,
            "event_type": "Cough",
            "confidence": 0.80,
            "duration_sec": 2.0,
            "embedding": [0.1],
            "signature": "sig",
        }
        for i in range(51)
    ]
    response = await async_client.post("/api/v1/edge/sync-batch", json={"events": events})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_sync_batch_duplicates_and_idempotency(async_client: AsyncClient, seed_test_device: Device):
    fixed_ts = 1774900000.0
    single_event = {
        "device_uid": seed_test_device.device_uid,
        "timestamp": fixed_ts,
        "event_type": "Distress_Call",
        "confidence": 0.91,
        "duration_sec": 3.5,
        "embedding": [0.2],
        "signature": "sig",
    }
    # First sync
    res1 = await async_client.post("/api/v1/edge/sync-batch", json={"events": [single_event]})
    assert res1.status_code == 200
    assert res1.json()["accepted"] == 1

    # Second sync with exact same event -> should be detected as duplicate
    res2 = await async_client.post("/api/v1/edge/sync-batch", json={"events": [single_event]})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["accepted"] == 0
    assert data2["duplicates"] == 1
    assert data2["results"][0]["status"] == "duplicate"


@pytest.mark.asyncio
async def test_heartbeat_valid(async_client: AsyncClient, seed_test_device: Device):
    payload = {
        "device_uid": seed_test_device.device_uid,
        "firmware_version": "0.1.5-beta",
        "status": "Online",
    }
    response = await async_client.post("/api/v1/edge/heartbeat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["acknowledged"] is True
    assert data["device_uid"] == seed_test_device.device_uid
    assert data["status"] == "Online"
    assert "last_heartbeat_at" in data


@pytest.mark.asyncio
async def test_heartbeat_unknown_device(async_client: AsyncClient):
    payload = {
        "device_uid": "NON-EXISTENT-DEVICE",
        "firmware_version": "1.0.0",
        "status": "Online",
    }
    response = await async_client.post("/api/v1/edge/heartbeat", json=payload)
    assert response.status_code == 404
