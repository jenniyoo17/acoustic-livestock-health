import uuid
from collections import defaultdict
from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.sql.elements import BinaryExpression

from app.db.session import get_session
from app.main import app
from app.models.device import Device, DeviceStatus
from app.models.farm import Farm
from app.models.shed import AnimalType, Shed


class MemoryResult:
    def __init__(self, record):
        self.record = record

    def scalar_one_or_none(self):
        return self.record


class MemorySession:
    """Small deterministic session double for API behavior tests."""

    def __init__(self):
        self.records = defaultdict(list)
        self.commit_count = 0

    async def execute(self, statement):
        model = statement.column_descriptions[0]["entity"]
        where_clause = statement.whereclause
        conditions = list(where_clause.clauses) if hasattr(where_clause, "clauses") else [where_clause]
        matches = self.records[model]
        for condition in conditions:
            if isinstance(condition, BinaryExpression):
                field_name = condition.left.key
                expected = condition.right.value
                matches = [record for record in matches if getattr(record, field_name) == expected]
        if len(matches) > 1:
            raise AssertionError("Expected the lookup to return at most one record")
        return MemoryResult(matches[0] if matches else None)

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