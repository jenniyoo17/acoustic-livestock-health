import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.acoustic_event import AcousticEvent
from app.models.alert import Alert, AlertStatus, AnomalySeverity, SLATier
from app.models.device import Device
from app.models.escalation_record import EscalationRecord
from app.models.shed import Shed
from app.schemas.acoustic_event import AcousticEventResponse
from app.schemas.alert import AlertResponse
from app.schemas.alerts import (
    AcknowledgeRequest,
    AcknowledgeResponse,
    AlertDetailResponse,
    AlertSLAStatus,
    EscalationEvaluationResponse,
    EscalationRecordResponse,
)
from app.schemas.device import DeviceResponse
from app.schemas.shed import ShedResponse
from app.services.notifications import notification_service
from app.services.sla import evaluate_alert_sla, sla_deadline, transition_alert_status

router = APIRouter()
HIGH_SEVERITIES = {AnomalySeverity.High, AnomalySeverity.Critical}
TERMINAL_STATUSES = {
    AlertStatus.Verified_Risk,
    AlertStatus.False_Positive,
    AlertStatus.Resolved,
}


async def _get_alert(db: AsyncSession, alert_id: uuid.UUID) -> Alert:
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


async def _get_history(db: AsyncSession, alert_id: uuid.UUID) -> list[EscalationRecord]:
    result = await db.execute(
        select(EscalationRecord)
        .where(EscalationRecord.alert_id == alert_id)
        .order_by(EscalationRecord.triggered_at)
    )
    return list(result.scalars().all())


def _current_record(
    history: list[EscalationRecord], tier: SLATier
) -> EscalationRecord | None:
    return next((record for record in reversed(history) if record.to_tier == tier), None)


async def _ensure_initial_record(
    db: AsyncSession,
    alert: Alert,
    history: list[EscalationRecord],
    now: datetime,
) -> EscalationRecord | None:
    if alert.anomaly_severity not in HIGH_SEVERITIES or history:
        return None
    record = EscalationRecord(
        alert_id=alert.id,
        from_tier=None,
        to_tier=alert.current_sla_tier,
        reason="Initial SLA notification",
        triggered_at=alert.triggered_at or now,
        created_at=now,
    )
    db.add(record)
    await db.flush()
    history.append(record)
    return record


def _status_response(
    alert: Alert,
    history: list[EscalationRecord],
    now: datetime,
) -> AlertSLAStatus:
    current_record = _current_record(history, alert.current_sla_tier)
    deadline = sla_deadline(alert, current_record)
    breached = deadline is not None and now >= deadline
    remaining = (deadline - now).total_seconds() if deadline is not None else None
    return AlertSLAStatus(
        alert_id=alert.id,
        status=alert.status,
        current_sla_tier=alert.current_sla_tier,
        triggered_at=alert.triggered_at,
        deadline=deadline,
        remaining_seconds=remaining,
        sla_enabled=alert.anomaly_severity in HIGH_SEVERITIES,
        sla_breached=breached,
        acknowledged_at=current_record.acknowledged_at if current_record else None,
        escalation_history=[EscalationRecordResponse.model_validate(row) for row in history],
    )


def _evaluation_time(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def _escalate_if_due(
    db: AsyncSession,
    alert: Alert,
    history: list[EscalationRecord],
    now: datetime,
) -> SLATier | None:
    if alert.status in TERMINAL_STATUSES:
        return None
    await _ensure_initial_record(db, alert, history, now)
    active_record = _current_record(history, alert.current_sla_tier)
    decision = evaluate_alert_sla(alert, now, active_record)
    if decision is None:
        return None

    previous_status = alert.status
    if previous_status in {AlertStatus.Pending_Triage, AlertStatus.Under_Vet_Review}:
        transition_alert_status(alert, AlertStatus.Escalated)
    alert.current_sla_tier = decision.to_tier
    record = EscalationRecord(
        alert_id=alert.id,
        from_tier=decision.from_tier,
        to_tier=decision.to_tier,
        reason=decision.reason,
        triggered_at=now,
        created_at=now,
    )
    db.add(record)
    await db.flush()
    history.append(record)
    return decision.to_tier


@router.post(
    "/escalations/evaluate",
    response_model=EscalationEvaluationResponse,
    summary="Evaluate overdue alert SLAs (demo time may be supplied)",
)
async def evaluate_escalations(
    at: datetime | None = Query(default=None, description="Optional simulated UTC time for demos"),
    db: AsyncSession = Depends(get_session),
) -> EscalationEvaluationResponse:
    now = _evaluation_time(at)
    result = await db.execute(select(Alert).order_by(Alert.triggered_at))
    alerts = list(result.scalars().all())
    notifications_to_send: list[tuple[uuid.UUID, SLATier]] = []
    statuses: list[AlertSLAStatus] = []

    for alert in alerts:
        history = await _get_history(db, alert.id)
        escalated_tier = await _escalate_if_due(db, alert, history, now)
        if escalated_tier is not None:
            notifications_to_send.append((alert.id, escalated_tier))
        statuses.append(_status_response(alert, history, now))

    await db.commit()
    for alert_id, tier in notifications_to_send:
        notification_service.notify_tier(alert_id, tier)
    return EscalationEvaluationResponse(
        evaluated_at=now,
        escalated_count=len(notifications_to_send),
        statuses=statuses,
    )


@router.get("/escalation-status", response_model=list[AlertSLAStatus])
async def escalation_status(
    at: datetime | None = Query(default=None, description="Optional simulated UTC time for demos"),
    db: AsyncSession = Depends(get_session),
) -> list[AlertSLAStatus]:
    now = _evaluation_time(at)
    result = await db.execute(select(Alert).order_by(Alert.triggered_at))
    alerts = list(result.scalars().all())
    statuses = []
    for alert in alerts:
        history = await _get_history(db, alert.id)
        statuses.append(_status_response(alert, history, now))
    return statuses


@router.post("/{alert_id}/acknowledge", response_model=AcknowledgeResponse)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    payload: AcknowledgeRequest,
    db: AsyncSession = Depends(get_session),
) -> AcknowledgeResponse:
    alert = await _get_alert(db, alert_id)
    if alert.status in TERMINAL_STATUSES:
        raise HTTPException(status_code=409, detail="Resolved alerts cannot be acknowledged")

    now = datetime.now(timezone.utc)
    history = await _get_history(db, alert.id)
    await _ensure_initial_record(db, alert, history, now)
    if payload.tier != alert.current_sla_tier:
        raise HTTPException(status_code=409, detail="Acknowledgement tier is not current")

    current_record = _current_record(history, payload.tier)
    if current_record is None or current_record.acknowledged_at is not None:
        raise HTTPException(status_code=409, detail="This SLA tier has already been acknowledged")
    if alert.status not in {
        AlertStatus.Pending_Triage,
        AlertStatus.Escalated,
        AlertStatus.Under_Vet_Review,
    }:
        raise HTTPException(status_code=409, detail="Alert cannot be acknowledged in its current state")

    current_record.acknowledged_at = now
    notify_vet = False
    if payload.tier == SLATier.Tier_1_Farm_Owner:
        transition_alert_status(alert, AlertStatus.Under_Vet_Review)
        alert.current_sla_tier = SLATier.Tier_2_Field_Vet
        vet_record = EscalationRecord(
            alert_id=alert.id,
            from_tier=SLATier.Tier_1_Farm_Owner,
            to_tier=SLATier.Tier_2_Field_Vet,
            reason="Farm owner acknowledged; veterinary review requested",
            triggered_at=now,
            created_at=now,
        )
        db.add(vet_record)
        await db.flush()
        notify_vet = True
    elif alert.status != AlertStatus.Under_Vet_Review:
        transition_alert_status(alert, AlertStatus.Under_Vet_Review)

    await db.commit()
    if notify_vet:
        notification_service.notify_tier(alert.id, SLATier.Tier_2_Field_Vet)
    return AcknowledgeResponse(
        alert_id=alert.id,
        status=alert.status,
        acknowledged_tier=payload.tier,
        current_sla_tier=alert.current_sla_tier,
        acknowledged_at=now,
    )


@router.get("/{alert_id}", response_model=AlertDetailResponse)
async def alert_detail(
    alert_id: uuid.UUID,
    at: datetime | None = Query(default=None, description="Optional simulated UTC time for demos"),
    db: AsyncSession = Depends(get_session),
) -> AlertDetailResponse:
    alert = await _get_alert(db, alert_id)
    event_result = await db.execute(
        select(AcousticEvent).where(AcousticEvent.id == alert.acoustic_event_id)
    )
    event = event_result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Alert acoustic event not found")
    shed_result = await db.execute(select(Shed).where(Shed.id == alert.shed_id))
    shed = shed_result.scalar_one_or_none()
    if shed is None:
        raise HTTPException(status_code=404, detail="Alert shed not found")
    device_result = await db.execute(select(Device).where(Device.id == event.device_id))
    device = device_result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="Event device not found")

    history = await _get_history(db, alert.id)
    return AlertDetailResponse(
        alert=AlertResponse.model_validate(alert),
        acoustic_event=AcousticEventResponse.model_validate(event),
        shed=ShedResponse.model_validate(shed),
        device=DeviceResponse.model_validate(device),
        sla=_status_response(alert, history, _evaluation_time(at)),
    )