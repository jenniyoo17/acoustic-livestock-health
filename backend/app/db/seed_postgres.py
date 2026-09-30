import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionFactory, engine
from app.models import (
    AcousticEvent,
    Alert,
    AlertStatus,
    AnomalySeverity,
    AnimalType,
    Device,
    DeviceStatus,
    EventType,
    Farm,
    Shed,
    SLATier,
)

SEED_NAMESPACE = uuid.UUID("288f5ac4-5a3c-45ed-90c4-6d2ac2e41ee0")
SEED_RECORDED_AT = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def seed_id(name: str) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, name)


async def _add_if_missing(session: AsyncSession, model, record_id, **values):
    record = await session.get(model, record_id)
    if record is None:
        record = model(id=record_id, **values)
        session.add(record)
    return record


async def seed_data() -> None:
    async with SessionFactory.begin() as session:
        farm_anand = await _add_if_missing(
            session,
            Farm,
            seed_id("farm-anand"),
            name="Anand Demonstration Farm",
            owner_name="Demo Farm Owner",
            contact_phone="+910000000001",
            latitude=22.5645,
            longitude=72.9289,
            district="Anand",
            state="Gujarat",
        )
        farm_karnal = await _add_if_missing(
            session,
            Farm,
            seed_id("farm-karnal"),
            name="Karnal Demonstration Farm",
            owner_name="Demo Research Owner",
            contact_phone="+910000000002",
            latitude=29.6857,
            longitude=76.9905,
            district="Karnal",
            state="Haryana",
        )
        await session.flush()

        shed_cattle = await _add_if_missing(
            session,
            Shed,
            seed_id("shed-anand-cattle"),
            farm_id=farm_anand.id,
            shed_number="A-01",
            animal_type=AnimalType.Cattle,
            capacity=40,
            current_count=32,
        )
        shed_buffalo = await _add_if_missing(
            session,
            Shed,
            seed_id("shed-anand-buffalo"),
            farm_id=farm_anand.id,
            shed_number="A-02",
            animal_type=AnimalType.Buffalo,
            capacity=24,
            current_count=18,
        )
        shed_goat = await _add_if_missing(
            session,
            Shed,
            seed_id("shed-karnal-goat"),
            farm_id=farm_karnal.id,
            shed_number="K-01",
            animal_type=AnimalType.Goat,
            capacity=30,
            current_count=21,
        )
        await session.flush()

        device_cattle = await _add_if_missing(
            session,
            Device,
            seed_id("device-anand-cattle"),
            shed_id=shed_cattle.id,
            device_uid="MIC-DEMO-ANAND-01",
            firmware_version="0.1.0",
            status=DeviceStatus.Online,
        )
        device_buffalo = await _add_if_missing(
            session,
            Device,
            seed_id("device-anand-buffalo"),
            shed_id=shed_buffalo.id,
            device_uid="MIC-DEMO-ANAND-02",
            firmware_version="0.1.0",
            status=DeviceStatus.Online,
        )
        await _add_if_missing(
            session,
            Device,
            seed_id("device-karnal-goat"),
            shed_id=shed_goat.id,
            device_uid="MIC-DEMO-KARNAL-01",
            firmware_version="0.1.0",
            status=DeviceStatus.Degraded,
        )
        await session.flush()

        event_cough = await _add_if_missing(
            session,
            AcousticEvent,
            seed_id("event-demo-cough"),
            device_id=device_cattle.id,
            shed_id=shed_cattle.id,
            event_type=EventType.Cough,
            confidence_score=0.88,
            yamnet_embedding_vector=[0.0, 0.1, -0.1],
            audio_duration_sec=2.4,
            recorded_at=SEED_RECORDED_AT,
            is_synced_offline=False,
            idempotency_key=None,
        )
        await _add_if_missing(
            session,
            AcousticEvent,
            seed_id("event-demo-noise"),
            device_id=device_buffalo.id,
            shed_id=shed_buffalo.id,
            event_type=EventType.Environmental_Noise,
            confidence_score=0.42,
            yamnet_embedding_vector=[0.0, 0.0, 0.1],
            audio_duration_sec=3.0,
            recorded_at=SEED_RECORDED_AT,
            is_synced_offline=True,
            idempotency_key=None,
        )
        await session.flush()

        await _add_if_missing(
            session,
            Alert,
            seed_id("alert-demo-cough"),
            acoustic_event_id=event_cough.id,
            shed_id=shed_cattle.id,
            anomaly_severity=AnomalySeverity.High,
            status=AlertStatus.Pending_Triage,
            current_sla_tier=SLATier.Tier_1_Farm_Owner,
            triggered_at=SEED_RECORDED_AT,
        )

    print("Seeded 2 farms, 3 sheds, 3 devices, 2 acoustic events, and 1 alert in PostgreSQL.")


async def main() -> None:
    try:
        await seed_data()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())