import asyncio
import uuid
from datetime import datetime, timedelta, timezone

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
    EscalationRecord,
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
        device_goat = await _add_if_missing(
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
        event_noise = await _add_if_missing(
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
        event_escalated = await _add_if_missing(
            session,
            AcousticEvent,
            seed_id("event-demo-escalated-cough"),
            device_id=device_goat.id,
            shed_id=shed_goat.id,
            event_type=EventType.Cough,
            confidence_score=0.91,
            yamnet_embedding_vector=[0.1, 0.2, 0.3],
            audio_duration_sec=2.8,
            recorded_at=SEED_RECORDED_AT + timedelta(minutes=16),
            is_synced_offline=True,
            idempotency_key=None,
        )
        event_critical = await _add_if_missing(
            session,
            AcousticEvent,
            seed_id("event-demo-critical-distress"),
            device_id=device_cattle.id,
            shed_id=shed_cattle.id,
            event_type=EventType.Distress_Call,
            confidence_score=0.99,
            yamnet_embedding_vector=[0.2, -0.1, 0.4],
            audio_duration_sec=3.2,
            recorded_at=SEED_RECORDED_AT + timedelta(minutes=2),
            is_synced_offline=False,
            idempotency_key=None,
        )
        await session.flush()

        high_pending = await _add_if_missing(
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
        await _add_if_missing(
            session,
            Alert,
            seed_id("alert-demo-low-noise"),
            acoustic_event_id=event_noise.id,
            shed_id=shed_buffalo.id,
            anomaly_severity=AnomalySeverity.Low,
            status=AlertStatus.Pending_Triage,
            current_sla_tier=SLATier.Tier_1_Farm_Owner,
            triggered_at=SEED_RECORDED_AT,
        )
        high_escalated = await _add_if_missing(
            session,
            Alert,
            seed_id("alert-demo-high-tier-two"),
            acoustic_event_id=event_escalated.id,
            shed_id=shed_goat.id,
            anomaly_severity=AnomalySeverity.High,
            status=AlertStatus.Escalated,
            current_sla_tier=SLATier.Tier_2_Field_Vet,
            triggered_at=SEED_RECORDED_AT + timedelta(minutes=16),
        )
        critical_alert = await _add_if_missing(
            session,
            Alert,
            seed_id("alert-demo-critical"),
            acoustic_event_id=event_critical.id,
            shed_id=shed_cattle.id,
            anomaly_severity=AnomalySeverity.Critical,
            status=AlertStatus.Pending_Triage,
            current_sla_tier=SLATier.Tier_1_Farm_Owner,
            triggered_at=SEED_RECORDED_AT + timedelta(minutes=2),
        )
        await session.flush()
        await _add_if_missing(
            session,
            EscalationRecord,
            seed_id("escalation-high-tier-one"),
            alert_id=high_pending.id,
            from_tier=None,
            to_tier=SLATier.Tier_1_Farm_Owner,
            reason="Initial SLA notification",
            triggered_at=SEED_RECORDED_AT,
            acknowledged_at=None,
            created_at=SEED_RECORDED_AT,
        )
        await _add_if_missing(
            session,
            EscalationRecord,
            seed_id("escalation-high-tier-two-ack"),
            alert_id=high_escalated.id,
            from_tier=None,
            to_tier=SLATier.Tier_1_Farm_Owner,
            reason="Initial SLA notification",
            triggered_at=SEED_RECORDED_AT,
            acknowledged_at=SEED_RECORDED_AT + timedelta(minutes=15),
            created_at=SEED_RECORDED_AT,
        )
        await _add_if_missing(
            session,
            EscalationRecord,
            seed_id("escalation-high-tier-two"),
            alert_id=high_escalated.id,
            from_tier=SLATier.Tier_1_Farm_Owner,
            to_tier=SLATier.Tier_2_Field_Vet,
            reason="Tier 1 acknowledged; veterinary review requested",
            triggered_at=SEED_RECORDED_AT + timedelta(minutes=15),
            acknowledged_at=None,
            created_at=SEED_RECORDED_AT + timedelta(minutes=15),
        )
        await _add_if_missing(
            session,
            EscalationRecord,
            seed_id("escalation-critical-tier-one"),
            alert_id=critical_alert.id,
            from_tier=None,
            to_tier=SLATier.Tier_1_Farm_Owner,
            reason="Initial SLA notification",
            triggered_at=critical_alert.triggered_at,
            acknowledged_at=None,
            created_at=critical_alert.triggered_at,
        )

    print("Seeded demo farms, sheds, devices, acoustic events, and low/high/critical SLA alerts in PostgreSQL.")


async def main() -> None:
    try:
        await seed_data()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())