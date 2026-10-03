import asyncio
import json
import sqlite3

import pytest
from httpx import ASGITransport, AsyncClient

import src.main as edge_main
from app.core.device_auth import device_auth_service


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "edge.db"
    monkeypatch.setattr(edge_main, "DB_PATH", db_path)
    yield db_path


@pytest.mark.asyncio
async def test_edge_health_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=edge_main.app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "acoustic-livestock-edge-simulator",
    }


def test_sqlite_queue_initializes_and_records_unsynced_events(isolated_db):
    event = edge_main.generate_demo_event(event_type="Cough", confidence=0.91)
    queued = edge_main.queue_event(event)
    assert queued.status == edge_main.QueueStatus.UNSYNCED

    with sqlite3.connect(isolated_db) as connection:
        rows = connection.execute(
            "SELECT event_id, status FROM queued_events"
        ).fetchall()

    assert len(rows) == 1
    assert rows[0][1] == edge_main.QueueStatus.UNSYNCED


def test_multiple_events_queue_offline(isolated_db):
    for index in range(3):
        event = edge_main.generate_demo_event(event_type="Cough", confidence=0.81 + index * 0.05)
        edge_main.queue_event(event)

    events = edge_main.list_queue()
    assert len(events) == 3
    assert {event.status for event in events} == {edge_main.QueueStatus.UNSYNCED}
    assert edge_main.queue_summary()["UNSYNCED"] == 3


def test_batch_hash_is_deterministic_and_changes_when_event_changes():
    event_one = {
        "device_uid": edge_main.EDGE_DEVICE_UID,
        "timestamp": 1_700_000_000.0,
        "event_type": "Cough",
        "confidence": 0.89,
        "duration_sec": 2.4,
        "embedding": [0.01, -0.02],
    }
    event_two = {**event_one, "confidence": 0.90}
    signature_one = device_auth_service.create_signature(event_one)
    signature_two = device_auth_service.create_signature(event_two)
    payload_one = {**event_one, "signature": signature_one}
    payload_two = {**event_two, "signature": signature_two}
    hash_one = edge_main.calculate_batch_hash([payload_one, payload_one])
    hash_two = edge_main.calculate_batch_hash([payload_one, payload_one])
    hash_three = edge_main.calculate_batch_hash([payload_two, payload_one])

    assert hash_one == hash_two
    assert hash_one != hash_three


@pytest.mark.asyncio
async def test_sync_pending_events_uses_backend_contract_and_marks_acknowledged(isolated_db, monkeypatch):
    queue_events = [
        edge_main.generate_demo_event(event_type="Cough", confidence=0.90),
        edge_main.generate_demo_event(event_type="Distress_Call", confidence=0.87),
    ]
    for event in queue_events:
        edge_main.queue_event(event)

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "accepted": 2,
                "duplicates": 0,
                "rejected": 0,
                "results": [
                    {"index": 0, "device_uid": edge_main.EDGE_DEVICE_UID, "accepted": True, "status": "stored", "event_id": queue_events[0].event_id},
                    {"index": 1, "device_uid": edge_main.EDGE_DEVICE_UID, "accepted": True, "status": "stored", "event_id": queue_events[1].event_id},
                ],
            }

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json):
            assert url.endswith("/api/v1/edge/sync-batch")
            assert len(json["events"]) <= edge_main.MAX_BATCH_SIZE
            assert json["batch_hash"] == edge_main.calculate_batch_hash(json["events"])
            assert json["events"][0]["device_uid"] == edge_main.EDGE_DEVICE_UID
            return FakeResponse()

    monkeypatch.setattr(edge_main.httpx, "AsyncClient", FakeAsyncClient)
    result = await edge_main.sync_pending_events(offline=False)
    queued = edge_main.list_queue()

    assert result["acknowledged"] == 2
    assert {entry.status for entry in queued} == {edge_main.QueueStatus.ACKNOWLEDGED}


@pytest.mark.asyncio
async def test_failed_sync_returns_queue_to_unsynced_and_keeps_events(isolated_db, monkeypatch):
    event = edge_main.generate_demo_event(event_type="Cough", confidence=0.91)
    edge_main.queue_event(event)

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json):
            raise RuntimeError("simulated network failure")

    monkeypatch.setattr(edge_main.httpx, "AsyncClient", FakeAsyncClient)
    result = await edge_main.sync_pending_events(offline=False)
    queued = edge_main.list_queue()

    assert result["failed"] == 1
    assert queued[0].status == edge_main.QueueStatus.UNSYNCED
    assert queued[0].last_error is not None
    assert queued[0].sync_attempts == 1


@pytest.mark.asyncio
async def test_offline_mode_skips_http_and_keeps_unsynced(isolated_db, monkeypatch):
    events = [edge_main.generate_demo_event() for _ in range(3)]
    for event in events:
        edge_main.queue_event(event)

    class FailIfCalledAsyncClient:
        async def __aenter__(self):
            raise AssertionError("HTTP client should not be called in offline mode")

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(edge_main.httpx, "AsyncClient", FailIfCalledAsyncClient)
    result = await edge_main.sync_pending_events(offline=True)
    assert result["offline"] is True
    assert result["queued"] == 3
    assert result["acknowledged"] == 0
    assert edge_main.queue_summary()["UNSYNCED"] == 3


@pytest.mark.asyncio
async def test_heartbeat_uses_existing_backend_contract(monkeypatch):
    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"acknowledged": True, "device_uid": edge_main.EDGE_DEVICE_UID, "status": "Online", "last_heartbeat_at": "2026-10-03T10:00:00+00:00"}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json):
            assert url.endswith("/api/v1/edge/heartbeat")
            assert json["device_uid"] == edge_main.EDGE_DEVICE_UID
            assert json["status"] == "Online"
            return FakeResponse()

    monkeypatch.setattr(edge_main.httpx, "AsyncClient", FakeAsyncClient)
    result = await edge_main.send_heartbeat()
    assert result["acknowledged"] is True
    assert result["device_uid"] == edge_main.EDGE_DEVICE_UID


@pytest.mark.asyncio
async def test_event_signatures_are_compatible_with_backend_verification():
    event = edge_main.generate_demo_event(event_type="Cough", confidence=0.91)
    payload = {k: v for k, v in event.to_backend_payload().items() if k != "signature"}
    assert device_auth_service.verify_signature(payload, event.signature)


@pytest.mark.asyncio
async def test_queue_command_reports_information(monkeypatch, isolated_db):
    event = edge_main.generate_demo_event(event_type="Cough")
    edge_main.queue_event(event)
    queue = edge_main.list_queue()
    assert queue[0].event_id == event.event_id
    assert edge_main.queue_summary()["UNSYNCED"] == 1
    assert list(queue)[0].status == edge_main.QueueStatus.UNSYNCED


@pytest.mark.asyncio
async def test_queue_drains_when_recovery_occurs(isolated_db, monkeypatch):
    for _ in range(3):
        edge_main.queue_event(edge_main.generate_demo_event(event_type="Cough"))

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json):
            class Response:
                status_code = 200

                @staticmethod
                def json():
                    return {
                        "accepted": len(json["events"]),
                        "duplicates": 0,
                        "rejected": 0,
                        "results": [
                            {"index": idx, "device_uid": edge_main.EDGE_DEVICE_UID, "accepted": True, "status": "stored", "event_id": event.event_id}
                            for idx, event in enumerate(sorted(edge_main.list_queue(), key=lambda item: item.created_at))
                        ],
                    }

            return Response()

    monkeypatch.setattr(edge_main.httpx, "AsyncClient", FakeAsyncClient)
    result = await edge_main.sync_pending_events(offline=False)
    assert result["acknowledged"] == 3
    assert edge_main.queue_summary()["ACKNOWLEDGED"] == 3


def test_max_batch_size_is_50():
    assert edge_main.MAX_BATCH_SIZE == 50


def test_batch_split_is_50_plus_remaining(isolated_db):
    for _ in range(53):
        edge_main.queue_event(edge_main.generate_demo_event(event_type="Cough"))
    queue = edge_main.list_queue()
    assert len(queue) == 53
    first_batch = queue[:50]
    second_batch = queue[50:]
    assert len(first_batch) == 50
    assert len(second_batch) == 3
