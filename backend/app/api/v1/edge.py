from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_async_session
from app.models.device import Device
from app.models.acoustic_event import AcousticEvent, EventType
from app.models.alert import Alert, AnomalySeverity, AlertStatus, SLATier
from app.schemas.ingest import (
    IngestRequest,
    IngestResponse,
    BatchSyncRequest,
    BatchSyncResponse,
    BatchItemResult,
    HeartbeatRequest,
    HeartbeatResponse,
)

router = APIRouter()


def calculate_anomaly_severity(event_type: EventType, confidence: float) -> AnomalySeverity:
    """Determine statistical anomaly severity level based on acoustic confidence score."""
    if confidence >= 0.9:
        return AnomalySeverity.Critical
    elif confidence >= 0.8:
        return AnomalySeverity.High
    elif confidence >= 0.7:
        return AnomalySeverity.Medium
    return AnomalySeverity.Low


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Real-Time Edge Acoustic Event",
    description="Passively receives acoustic anomaly event data detected by shed-mounted micro-edge sensors.",
)
async def ingest_acoustic_event(
    payload: IngestRequest,
    db: AsyncSession = Depends(get_async_session),
):
    # 1. Identify device by unique hardware UID
    result = await db.execute(select(Device).where(Device.device_uid == payload.device_uid))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with UID '{payload.device_uid}' not found.",
        )

    recorded_dt = payload.get_recorded_datetime()

    # 2. Instantiate and persist Acoustic Event
    acoustic_event = AcousticEvent(
        device_id=device.id,
        shed_id=device.shed_id,
        event_type=payload.event_type,
        confidence_score=payload.confidence,
        yamnet_embedding_vector=payload.embedding,
        audio_duration_sec=payload.duration_sec,
        recorded_at=recorded_dt,
        is_synced_offline=False,
    )
    db.add(acoustic_event)
    await db.flush()

    # 3. Create Alert if event indicates statistical acoustic anomaly
    alert_created = False
    alert_id_str = None

    if payload.event_type != EventType.Environmental_Noise and payload.confidence >= 0.65:
        severity = calculate_anomaly_severity(payload.event_type, payload.confidence)
        alert = Alert(
            acoustic_event_id=acoustic_event.id,
            shed_id=device.shed_id,
            anomaly_severity=severity,
            status=AlertStatus.Pending_Triage,
            current_sla_tier=SLATier.Tier_1_Farm_Owner,
        )
        db.add(alert)
        await db.flush()
        alert_created = True
        alert_id_str = str(alert.id)

    await db.commit()

    return IngestResponse(
        accepted=True,
        event_id=str(acoustic_event.id),
        device_uid=payload.device_uid,
        status="stored",
        alert_created=alert_created,
        alert_id=alert_id_str,
    )


@router.post(
    "/sync-batch",
    response_model=BatchSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Store-and-Forward Batch Sync Endpoint",
    description="Receives batched offline acoustic events from edge devices returning online. Enforces max batch size of 50.",
)
async def sync_batch_events(
    payload: BatchSyncRequest,
    db: AsyncSession = Depends(get_async_session),
):
    accepted_count = 0
    duplicate_count = 0
    rejected_count = 0
    results: List[BatchItemResult] = []

    for index, event_item in enumerate(payload.events):
        # Identify Device
        result = await db.execute(select(Device).where(Device.device_uid == event_item.device_uid))
        device = result.scalar_one_or_none()

        if not device:
            rejected_count += 1
            results.append(
                BatchItemResult(
                    index=index,
                    device_uid=event_item.device_uid,
                    accepted=False,
                    status="invalid_device",
                    error_detail=f"Device UID '{event_item.device_uid}' not found",
                )
            )
            continue

        recorded_dt = event_item.get_recorded_datetime()

        # Idempotency check for duplicate insertion
        dup_query = await db.execute(
            select(AcousticEvent).where(
                AcousticEvent.device_id == device.id,
                AcousticEvent.recorded_at == recorded_dt,
                AcousticEvent.event_type == event_item.event_type,
            )
        )
        existing_event = dup_query.scalar_one_or_none()

        if existing_event:
            duplicate_count += 1
            results.append(
                BatchItemResult(
                    index=index,
                    device_uid=event_item.device_uid,
                    accepted=True,
                    status="duplicate",
                    event_id=str(existing_event.id),
                    error_detail="Event already synced",
                )
            )
            continue

        # Save new event with is_synced_offline = True
        acoustic_event = AcousticEvent(
            device_id=device.id,
            shed_id=device.shed_id,
            event_type=event_item.event_type,
            confidence_score=event_item.confidence,
            yamnet_embedding_vector=event_item.embedding,
            audio_duration_sec=event_item.duration_sec,
            recorded_at=recorded_dt,
            is_synced_offline=True,
        )
        db.add(acoustic_event)
        await db.flush()

        # Create alert if anomaly threshold met
        if event_item.event_type != EventType.Environmental_Noise and event_item.confidence >= 0.65:
            severity = calculate_anomaly_severity(event_item.event_type, event_item.confidence)
            alert = Alert(
                acoustic_event_id=acoustic_event.id,
                shed_id=device.shed_id,
                anomaly_severity=severity,
                status=AlertStatus.Pending_Triage,
                current_sla_tier=SLATier.Tier_1_Farm_Owner,
            )
            db.add(alert)

        accepted_count += 1
        results.append(
            BatchItemResult(
                index=index,
                device_uid=event_item.device_uid,
                accepted=True,
                status="stored",
                event_id=str(acoustic_event.id),
            )
        )

    await db.commit()

    return BatchSyncResponse(
        accepted=accepted_count,
        duplicates=duplicate_count,
        rejected=rejected_count,
        results=results,
    )


@router.post(
    "/heartbeat",
    response_model=HeartbeatResponse,
    status_code=status.HTTP_200_OK,
    summary="Edge Device Health & Heartbeat",
    description="Receives device status, firmware version, and timestamp heartbeat telemetry.",
)
async def device_heartbeat(
    payload: HeartbeatRequest,
    db: AsyncSession = Depends(get_async_session),
):
    result = await db.execute(select(Device).where(Device.device_uid == payload.device_uid))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with UID '{payload.device_uid}' not found.",
        )

    now = datetime.now(timezone.utc)
    device.status = payload.status
    if payload.firmware_version:
        device.firmware_version = payload.firmware_version
    device.last_heartbeat_at = now

    await db.commit()

    return HeartbeatResponse(
        acknowledged=True,
        device_uid=device.device_uid,
        status=device.status,
        last_heartbeat_at=now,
    )
