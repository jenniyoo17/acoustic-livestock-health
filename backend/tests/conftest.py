import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from httpx import AsyncClient, ASGITransport

from app.db.base import Base
from app.db.session import get_async_session
from app.main import app
from app.models.farm import Farm
from app.models.shed import Shed, AnimalType
from app.models.device import Device, DeviceStatus

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_async_session():
        yield db_session

    app.dependency_overrides[get_async_session] = _override_get_async_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seed_test_device(db_session: AsyncSession) -> Device:
    farm = Farm(
        name="Test Gujarat Farm",
        owner_name="Test Owner",
        contact_phone="+91-9999999999",
        latitude=22.5645,
        longitude=72.9289,
        district="Anand",
        state="Gujarat",
    )
    db_session.add(farm)
    await db_session.flush()

    shed = Shed(
        farm_id=farm.id,
        shed_number="TEST-SHED-01",
        animal_type=AnimalType.Cattle,
        capacity=100,
        current_count=80,
    )
    db_session.add(shed)
    await db_session.flush()

    device = Device(
        shed_id=shed.id,
        device_uid="MIC-FARM01-SHED02",
        firmware_version="0.1.0",
        status=DeviceStatus.Online,
    )
    db_session.add(device)
    await db_session.commit()

    result = await db_session.execute(select(Device).where(Device.id == device.id))
    return result.scalar_one()
