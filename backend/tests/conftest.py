import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.sql.elements import BinaryExpression

from app.db.session import get_session
from app.main import app
from app.models.device import Device, DeviceStatus
from app.models.acoustic_event import AcousticEvent, EventType
from app.models.alert import Alert, AlertStatus, AnomalySeverity, SLATier
from app.models.escalation_record import EscalationRecord
from app.models.farm import Farm
from app.models.shed import AnimalType, Shed


class MemoryResult:
    def __init__(self, records):
        self.records = records

    def scalar_one_or_none(self):
        if len(self.records) > 1:
            raise AssertionError("Expected the lookup to return at most one record")
        return self.records[0] if self.records else None

    def scalars(self):
        return self

    def all(self):
        return list(self.records)


class MemorySession:
    """Small deterministic session double for API behavior tests."""

    def __init__(self):
        self.records = defaultdict(list)
        self.commit_count = 0

    async def execute(self, statement):
        model = statement.column_descriptions[0]["entity"]
        where_clause = statement.whereclause
        conditions = (
            list(where_clause.clauses)
            if hasattr(where_clause, "clauses")
            else [where_clause]
        )
        matches = self.records[model]
        for condition in conditions:
            if isinstance(condition, BinaryExpression):
                field_name = condition.left.key
                expected = condition.right.value
                matches = [record for record in matches if getattr(record, field_name) == expected]
        return MemoryResult(matches)

    def add(self, record):
        if getattr(record, "id", None) is None:
            record.id = uuid.uuid4()
        self.records[type(record)].append(record)

    async def flush(self):
        return None

    async def commit(self):
        self.commit_count += 1

    async def rollback(self):
        return None


@pytest_asyncio.fixture
async def db_session():
    return MemorySession()


@pytest_asyncio.fixture
async def async_client(db_session) -> AsyncGenerator[AsyncClient, None]:
    async def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seed_test_device(db_session):
    farm = Farm(
        name="Test Farm",
        owner_name="Test Owner",
        contact_phone="+910000000000",
        latitude=22.5,
        longitude=72.9,
        district="Anand",
        state="Gujarat",
    )
    db_session.add(farm)
    shed = Shed(
        farm_id=farm.id,
        shed_number="S-01",
        animal_type=AnimalType.Cattle,
        capacity=20,
        current_count=12,
    )
    db_session.add(shed)
    device = Device(
        shed_id=shed.id,
        device_uid="MIC-TEST-001",
        status=DeviceStatus.Online,
    )
    db_session.add(device)
    return device


@pytest_asyncio.fixture
async def seed_test_alert(db_session):
    now = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
    farm = Farm(
        name="SLA Test Farm",
        owner_name="Test Owner",
        contact_phone="+910000000003",
        latitude=22.5,
        longitude=72.9,
        district="Anand",
        state="Gujarat",
        created_at=now,
    )
    db_session.add(farm)
    shed = Shed(
        farm_id=farm.id,
        shed_number="SLA-01",
        animal_type=AnimalType.Cattle,
        capacity=10,
        current_count=8,
        created_at=now,
    )
    db_session.add(shed)
    device = Device(
        shed_id=shed.id,
        device_uid="MIC-SLA-001",
        firmware_version="0.1.0",
        status=DeviceStatus.Online,
        created_at=now,
    )
    db_session.add(device)
    event = AcousticEvent(
        device_id=device.id,
        shed_id=shed.id,
        event_type=EventType.Cough,
        confidence_score=0.92,
        yamnet_embedding_vector=[0.1, 0.2],
        audio_duration_sec=2.0,
        recorded_at=now,
        is_synced_offline=False,
        created_at=now,
    )
    db_session.add(event)
    alert = Alert(
        acoustic_event_id=event.id,
        shed_id=shed.id,
        anomaly_severity=AnomalySeverity.High,
        status=AlertStatus.Pending_Triage,
        current_sla_tier=SLATier.Tier_1_Farm_Owner,
        triggered_at=now,
    )
    db_session.add(alert)
    db_session.add(
        EscalationRecord(
            alert_id=alert.id,
            from_tier=None,
            to_tier=SLATier.Tier_1_Farm_Owner,
            reason="Initial SLA notification",
            triggered_at=now,
            created_at=now,
        )
    )
    return alert