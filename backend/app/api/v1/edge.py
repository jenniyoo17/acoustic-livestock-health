import hashlib
import hmac
import json
from collections.abc import Sequence
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.device_auth import device_auth_service
from app.db.session import get_session
from app.models.acoustic_event import AcousticEvent, EventType
from app.models.alert import Alert, AlertStatus, AnomalySeverity, SLATier
from app.models.device import Device
from app.models.escalation_record import EscalationRecord
from app.schemas.ingest import (
    BatchItemResult,
    BatchSyncRequest,
    BatchSyncResponse,
    HeartbeatRequest,
    HeartbeatResponse,
    IngestRequest,
    IngestResponse,
)
from app.services.notifications import notification_service

router = APIRouter()


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def event_idempotency_key(event: IngestRequest) -> str:
    canonical = _canonical_json(event.model_dump(mode="json"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def calculate_batch_hash(events: Sequence[IngestRequest]) -> str:
    canonical_events = [event.model_dump(mode="json") for event in events]
    return hashlib.sha256(_canonical_json(canonical_events).encode("utf-8")).hexdigest()


def calculate_anomaly_severity(confidence: float) -> AnomalySeverity:
    if confidence >= 0.95:
        return AnomalySeverity.Critical
    if confidence >= 0.85:
        return AnomalySeverity.High
    if confidence >= 0.70:
        return AnomalySeverity.Medium
    return AnomalySeverity.Low


async def _get_device(db: AsyncSession, device_uid: str) -> Device | None:
    result = await db.execute(select(Device).where(Device.device_uid == device_uid))
    return result.scalar_one_or_none()


async def _existing_event(db: AsyncSession, idempotency_key: str) -> AcousticEvent | None:
    result = await db.execute(
        select(AcousticEvent).where(AcousticEvent.idempotency_key == idempotency_key)
    )
    return result.scalar_one_or_none()


def _verify_device_signature(payload: IngestRequest) -> None:
    if not device_auth_service.verify_signature(payload.signed_payload(), payload.signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device signature",
        )


def _new_event(payload: IngestRequest, device: Device, *, offline: bool) -> AcousticEvent:
    return AcousticEvent(
        device_id=device.id,
        shed_id=device.shed_id,
        event_type=payload.event_type,
        confidence_score=payload.confidence,
        yamnet_embedding_vector=payload.embedding,
        audio_duration_sec=payload.duration_sec,
        recorded_at=payload.recorded_datetime(),
        is_synced_offline=offline,
        idempotency_key=event_idempotency_key(payload),
    )


def _new_alert(event: AcousticEvent) -> Alert | None:
    if (
        event.event_type == EventType.Environmental_Noise
        or event.confidence_score < 0.65
    ):
        return None
    return Alert(
        acoustic_event=event,
        shed_id=event.shed_id,
        anomaly_severity=calculate_anomaly_severity(event.confidence_score),
        status=AlertStatus.Pending_Triage,
        current_sla_tier=SLATier.Tier_1_Farm_Owner,
        triggered_at=datetime.now(timezone.utc),
    )


def _new_initial_escalation_record(alert: Alert) -> EscalationRecord | None:
    if alert.anomaly_severity not in {AnomalySeverity.High, AnomalySeverity.Critical}:
        return None
    return EscalationRecord(
        alert_id=alert.id,
        from_tier=None,
        to_tier=SLATier.Tier_1_Farm_Owner,
        reason="Initial SLA notification",
        triggered_at=alert.triggered_at,
        created_at=alert.triggered_at,
    )


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a device acoustic event",
)
async def ingest_event(
    payload: IngestRequest,
    response: Response,
    db: AsyncSession = Depends(get_session),
) -> IngestResponse:
    device = await _get_device(db, payload.device_uid)
    if device is None:
        raise HTTPException(status_code=404, detail="Registered device not found")
    _verify_device_signature(payload)

    idempotency_key = event_idempotency_key(payload)
    existing = await _existing_event(db, idempotency_key)
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return IngestResponse(
            accepted=True,
            event_id=existing.id,
            device_uid=payload.device_uid,
            status="duplicate",
            alert_created=False,
            alert_id=None,
        )

    event = _new_event(payload, device, offline=False)
    db.add(event)
    await db.flush()
    alert = _new_alert(event)
    send_initial_notification = False
    if alert is not None:
        db.add(alert)
        await db.flush()
        initial_record = _new_initial_escalation_record(alert)
        if initial_record is not None:
            db.add(initial_record)
            send_initial_notification = True
            await db.flush()
    await db.commit()
    if send_initial_notification and alert is not None:
        notification_service.notify_tier(alert.id, SLATier.Tier_1_Farm_Owner)

    return IngestResponse(
        accepted=True,
        event_id=event.id,
        device_uid=device.device_uid,
        status="stored",
        alert_created=alert is not None,
        alert_id=alert.id if alert is not None else None,
    )


@router.post(
    "/sync-batch",
    response_model=BatchSyncResponse,
    summary="Synchronize offline acoustic events",
)
async def sync_batch(
    payload: BatchSyncRequest,
    db: AsyncSession = Depends(get_session),
) -> BatchSyncResponse:
    expected_hash = calculate_batch_hash(payload.events)
    if not hmac.compare_digest(expected_hash, payload.batch_hash.lower()):
        raise HTTPException(status_code=400, detail="Batch SHA-256 hash mismatch")

    accepted = 0
    duplicates = 0
    rejected = 0
    results: list[BatchItemResult] = []
    initial_notification_ids: list[uuid.UUID] = []

    for index, item in enumerate(payload.events):
        device = await _get_device(db, item.device_uid)
        if device is None:
            rejected += 1
            results.append(
                BatchItemResult(
                    index=index,
                    device_uid=item.device_uid,
                    accepted=False,
                    status="invalid_device",
                    error_detail="Registered device not found",
                )
            )
            continue
        if not device_auth_service.verify_signature(item.signed_payload(), item.signature):
            rejected += 1
            results.append(
                BatchItemResult(
                    index=index,
                    device_uid=item.device_uid,
                    accepted=False,
                    status="invalid_signature",
                    error_detail="Invalid device signature",
                )
            )
            continue

        idempotency_key = event_idempotency_key(item)
        existing = await _existing_event(db, idempotency_key)
        if existing is not None:
            duplicates += 1
            results.append(
                BatchItemResult(
                    index=index,
                    device_uid=item.device_uid,
                    accepted=True,
                    status="duplicate",
                    event_id=existing.id,
                )
            )
            continue

        event = _new_event(item, device, offline=True)
        db.add(event)
        await db.flush()
        alert = _new_alert(event)
        if alert is not None:
            db.add(alert)
            await db.flush()
            initial_record = _new_initial_escalation_record(alert)
            if initial_record is not None:
                db.add(initial_record)
                initial_notification_ids.append(alert.id)
                await db.flush()
        accepted += 1
        results.append(
            BatchItemResult(
                index=index,
                device_uid=device.device_uid,
                accepted=True,
                status="stored",
                event_id=event.id,
            )
        )

    await db.commit()
    for alert_id in initial_notification_ids:
        notification_service.notify_tier(alert_id, SLATier.Tier_1_Farm_Owner)
    return BatchSyncResponse(
        accepted=accepted,
        duplicates=duplicates,
        rejected=rejected,
        results=results,
    )


@router.post("/heartbeat", response_model=HeartbeatResponse)
async def heartbeat(
    payload: HeartbeatRequest,
    db: AsyncSession = Depends(get_session),
) -> HeartbeatResponse:
    device = await _get_device(db, payload.device_uid)
    if device is None:
        raise HTTPException(status_code=404, detail="Registered device not found")

    now = datetime.now(timezone.utc)
    device.status = payload.status
    if payload.firmware_version is not None:
        device.firmware_version = payload.firmware_version
    device.last_heartbeat_at = now
    await db.commit()

    return HeartbeatResponse(
        acknowledged=True,
        device_uid=device.device_uid,
        status=device.status,
        last_heartbeat_at=now,
    )
