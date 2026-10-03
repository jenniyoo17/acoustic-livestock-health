import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.alert import Alert, AlertStatus
from app.models.vet_verification import VetVerification, VetVerificationOutcome
from app.schemas.vet import VetVerificationResponse, VetVerifyRequest
from app.services.sla import transition_alert_status

router = APIRouter()


@router.post("/verify", response_model=VetVerificationResponse)
async def verify_alert(
    payload: VetVerifyRequest,
    db: AsyncSession = Depends(get_session),
) -> VetVerificationResponse:
    alert_result = await db.execute(select(Alert).where(Alert.id == payload.alert_id))
    alert = alert_result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.status != AlertStatus.Under_Vet_Review:
        raise HTTPException(status_code=409, detail="Alert must be under veterinary review")

    existing_result = await db.execute(
        select(VetVerification).where(VetVerification.alert_id == alert.id)
    )
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Alert already has a veterinary verification")

    now = datetime.now(timezone.utc)
    transition_alert_status(alert, AlertStatus(payload.outcome.value))
    verification = VetVerification(
        alert_id=alert.id,
        vet_identifier=payload.vet_identifier,
        verification_status=payload.outcome,
        assessment_notes=payload.notes,
        verified_at=now,
        created_at=now,
    )
    db.add(verification)
    await db.flush()

    if payload.outcome == VetVerificationOutcome.False_Positive:
        transition_alert_status(alert, AlertStatus.Resolved)
        alert.resolved_at = now

    await db.commit()
    return VetVerificationResponse(
        verification_id=verification.id,
        alert_id=alert.id,
        verification_result=verification.verification_status,
        alert_status=alert.status.value,
        vet_identifier=verification.vet_identifier,
        verified_at=now,
    )