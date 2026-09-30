import asyncio
import os
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings
from app.db.base import Base
from app.models.farm import Farm
from app.models.shed import Shed, AnimalType
from app.models.device import Device, DeviceStatus
from app.models.acoustic_event import AcousticEvent, EventType
from app.models.alert import Alert, AnomalySeverity, AlertStatus, SLATier


async def get_seed_engine():
    """Returns PostgreSQL engine if available, or falls back to local SQLite engine."""
    db_url = settings.get_database_url()
    try:
        engine = create_async_engine(db_url, echo=False)
        async with engine.connect() as conn:
            pass
        return engine, False
    except Exception as e:
        print(f"PostgreSQL not reachable on {db_url} ({e}). Falling back to local SQLite database...")
        sqlite_url = "sqlite+aiosqlite:///acoustic_livestock_dev.db"
        sqlite_engine = create_async_engine(sqlite_url, echo=False)
        return sqlite_engine, True


async def seed_data():
    """Development Seed Script for SIH 2026 Acoustic Livestock Health System.
    
    DEMO DATA DISCLAIMER:
    All records created below are synthetic demonstration data for development,
    testing, and hackathon presentation. They do NOT represent real animal disease outbreaks.
    """
    print("Initializing Database Seed Process...")
    engine, is_sqlite = await get_seed_engine()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SeedSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with SeedSessionLocal() as db:
        # Check if already seeded
        result = await db.execute(select(Farm))
        existing_farms = result.scalars().all()
        if existing_farms:
            print(f"Database already contains {len(existing_farms)} seeded farms. Skipping seed.")
            return

        now = datetime.now(timezone.utc)

        # 1. Create 3 Farms in prominent Indian agricultural livestock hubs
        farm1 = Farm(
            name="Amul Cooperative Livestock Farm 01 [DEMO DATA]",
            owner_name="Rajesh Patel",
            contact_phone="+91-9825012345",
            latitude=22.5645,
            longitude=72.9289,
            district="Anand",
            state="Gujarat",
        )
        farm2 = Farm(
            name="NDRI Research & Dairy Farm 02 [DEMO DATA]",
            owner_name="Suresh Kumar",
            contact_phone="+91-9416054321",
            latitude=29.6857,
            longitude=76.9905,
            district="Karnal",
            state="Haryana",
        )
        farm3 = Farm(
            name="Sahyadri Pastoral Livestock Hub 03 [DEMO DATA]",
            owner_name="Mahesh Deshmukh",
            contact_phone="+91-9822098765",
            latitude=18.5204,
            longitude=73.8567,
            district="Pune",
            state="Maharashtra",
        )
        db.add_all([farm1, farm2, farm3])
        await db.flush()

        # 2. Create Sheds for each Farm
        shed1_1 = Shed(
            farm_id=farm1.id,
            shed_number="SHED-A1 (Cattle)",
            animal_type=AnimalType.Cattle,
            capacity=120,
            current_count=105,
        )
        shed1_2 = Shed(
            farm_id=farm1.id,
            shed_number="SHED-A2 (Buffalo)",
            animal_type=AnimalType.Buffalo,
            capacity=80,
            current_count=72,
        )
        shed2_1 = Shed(
            farm_id=farm2.id,
            shed_number="SHED-K1 (Cattle)",
            animal_type=AnimalType.Cattle,
            capacity=200,
            current_count=185,
        )
        shed3_1 = Shed(
            farm_id=farm3.id,
            shed_number="SHED-P1 (Goat & Sheep)",
            animal_type=AnimalType.Goat,
            capacity=150,
            current_count=130,
        )
        db.add_all([shed1_1, shed1_2, shed2_1, shed3_1])
        await db.flush()

        # 3. Create Shed-Mounted Micro-Edge Acoustic Sensing Devices
        dev1 = Device(
            shed_id=shed1_1.id,
            device_uid="MIC-FARM01-SHED01",
            firmware_version="0.1.0",
            status=DeviceStatus.Online,
            last_heartbeat_at=now - timedelta(minutes=2),
        )
        dev2 = Device(
            shed_id=shed1_2.id,
            device_uid="MIC-FARM01-SHED02",
            firmware_version="0.1.0",
            status=DeviceStatus.Online,
            last_heartbeat_at=now - timedelta(minutes=5),
        )
        dev3 = Device(
            shed_id=shed2_1.id,
            device_uid="MIC-FARM02-SHED01",
            firmware_version="0.1.0",
            status=DeviceStatus.Online,
            last_heartbeat_at=now - timedelta(minutes=1),
        )
        dev4 = Device(
            shed_id=shed3_1.id,
            device_uid="MIC-FARM03-SHED01",
            firmware_version="0.1.0",
            status=DeviceStatus.Degraded,
            last_heartbeat_at=now - timedelta(hours=3),
        )
        db.add_all([dev1, dev2, dev3, dev4])
        await db.flush()

        dummy_embedding = [0.01 * (i % 10 - 5) for i in range(1024)]

        # 4. Create Acoustic Events
        evt1 = AcousticEvent(
            device_id=dev1.id,
            shed_id=shed1_1.id,
            event_type=EventType.Cough,
            confidence_score=0.88,
            yamnet_embedding_vector=dummy_embedding,
            audio_duration_sec=2.4,
            recorded_at=now - timedelta(minutes=25),
            is_synced_offline=False,
        )
        evt2 = AcousticEvent(
            device_id=dev1.id,
            shed_id=shed1_1.id,
            event_type=EventType.Distress_Call,
            confidence_score=0.92,
            yamnet_embedding_vector=dummy_embedding,
            audio_duration_sec=3.1,
            recorded_at=now - timedelta(minutes=10),
            is_synced_offline=False,
        )
        evt3 = AcousticEvent(
            device_id=dev2.id,
            shed_id=shed1_2.id,
            event_type=EventType.Environmental_Noise,
            confidence_score=0.45,
            yamnet_embedding_vector=dummy_embedding,
            audio_duration_sec=5.0,
            recorded_at=now - timedelta(hours=1),
            is_synced_offline=True,
        )
        evt4 = AcousticEvent(
            device_id=dev3.id,
            shed_id=shed2_1.id,
            event_type=EventType.Abnormal_Rumination,
            confidence_score=0.78,
            yamnet_embedding_vector=dummy_embedding,
            audio_duration_sec=4.2,
            recorded_at=now - timedelta(minutes=40),
            is_synced_offline=False,
        )
        db.add_all([evt1, evt2, evt3, evt4])
        await db.flush()

        # 5. Create Anomaly Alerts requiring clinical verification
        alert1 = Alert(
            acoustic_event_id=evt1.id,
            shed_id=shed1_1.id,
            anomaly_severity=AnomalySeverity.High,
            status=AlertStatus.Pending_Triage,
            current_sla_tier=SLATier.Tier_1_Farm_Owner,
            triggered_at=now - timedelta(minutes=25),
        )
        alert2 = Alert(
            acoustic_event_id=evt2.id,
            shed_id=shed1_1.id,
            anomaly_severity=AnomalySeverity.Critical,
            status=AlertStatus.Escalated,
            current_sla_tier=SLATier.Tier_2_Field_Vet,
            triggered_at=now - timedelta(minutes=10),
        )
        alert3 = Alert(
            acoustic_event_id=evt4.id,
            shed_id=shed2_1.id,
            anomaly_severity=AnomalySeverity.Medium,
            status=AlertStatus.Pending_Triage,
            current_sla_tier=SLATier.Tier_1_Farm_Owner,
            triggered_at=now - timedelta(minutes=40),
        )
        db.add_all([alert1, alert2, alert3])

        await db.commit()
        db_type = "SQLite (acoustic_livestock_dev.db)" if is_sqlite else "PostgreSQL"
        print(f"Successfully seeded 3 Farms, 4 Sheds, 4 Devices, 4 Acoustic Events, and 3 Anomaly Alerts in {db_type}!")


if __name__ == "__main__":
    asyncio.run(seed_data())
