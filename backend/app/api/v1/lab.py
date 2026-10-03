import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.alert import Alert, AlertStatus
from app.models.lab_referral import LabReferral, LabReferralStatus
from app.models.vet_verification import VetVerification
from app.schemas.alert import AlertResponse
from app.schemas.lab import (
    LabReferralCreate,
    LabReferralDetail,
    LabReferralResponse,
    LabStatusUpdate,
)
from app.schemas.vet import VetVerificationDetail
from app.services.sla import transition_alert_status

router = APIRouter()

LAB_STATUS_TRANSITIONS = {
    LabReferralStatus.Pending: {LabReferralStatus.Sample_Collected, LabReferralStatus.Cancelled},
    LabReferralStatus.Sample_Collected: {LabReferralStatus.In_Lab, LabReferralStatus.Cancelled},
    LabReferralStatus.In_Lab: {LabReferralStatus.Result_Available, LabReferralStatus.Cancelled},
    LabReferralStatus.Result_Available: set(),
    LabReferralStatus.Cancelled: set(),
}


async def _get_referral(db: AsyncSession, referral_id: uuid.UUID) -> LabReferral:
    result = await db.execute(select(LabReferral).where(LabReferral.id == referral_id))
    referral = result.scalar_one_or_none()
    if referral is None:
        raise HTTPException(status_code=404, detail="Lab referral not found")
    return referral


@router.post("/referrals", response_model=LabReferralResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_referral(
    payload: LabReferralCreate,
    db: AsyncSession = Depends(get_session),
) -> LabReferralResponse:
    alert_result = await db.execute(select(Alert).where(Alert.id == payload.alert_id))
    alert = alert_result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.status != AlertStatus.Verified_Risk:
        raise HTTPException(status_code=409, detail="Lab referrals require a Verified_Risk alert")

    verification_result = await db.execute(
        select(VetVerification).where(VetVerification.alert_id == alert.id)
    )
    verification = verification_result.scalar_one_or_none()
    if verification is None or verification.verification_status.value != AlertStatus.Verified_Risk.value:
        raise HTTPException(status_code=409, detail="Verified veterinary assessment is required")

    existing_result = await db.execute(
        select(LabReferral).where(LabReferral.alert_id == alert.id)
    )
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Alert already has a lab referral")

    now = datetime.now(timezone.utc)
    referral = LabReferral(
        alert_id=alert.id,
        verification_id=verification.id,
        sample_identifier=payload.sample_identifier,
        requested_tests=payload.requested_tests,
        status=LabReferralStatus.Pending,
        referred_at=now,
        notes=payload.notes,
        is_demo_result=False,
        created_at=now,
    )
    db.add(referral)
    await db.commit()
    return LabReferralResponse.model_validate(referral)


@router.get("/referrals/{referral_id}", response_model=LabReferralDetail)
async def lab_referral_detail(
    referral_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
) -> LabReferralDetail:
    referral = await _get_referral(db, referral_id)
    alert_result = await db.execute(select(Alert).where(Alert.id == referral.alert_id))
    alert = alert_result.scalar_one_or_none()
    verification_result = await db.execute(
        select(VetVerification).where(VetVerification.id == referral.verification_id)
    )
    verification = verification_result.scalar_one_or_none()
    if alert is None or verification is None:
        raise HTTPException(status_code=404, detail="Referral workflow record not found")
    return LabReferralDetail(
        referral=LabReferralResponse.model_validate(referral),
        alert=AlertResponse.model_validate(alert),
        verification=VetVerificationDetail.model_validate(verification),
    )


@router.patch("/referrals/{referral_id}/status", response_model=LabReferralResponse)
async def update_lab_referral_status(
    referral_id: uuid.UUID,
    payload: LabStatusUpdate,
    db: AsyncSession = Depends(get_session),
) -> LabReferralResponse:
    referral = await _get_referral(db, referral_id)
    if payload.status not in LAB_STATUS_TRANSITIONS[referral.status]:
        raise HTTPException(
            status_code=409,
            detail=f"Invalid lab referral transition: {referral.status.value} -> {payload.status.value}",
        )
    if payload.status == LabReferralStatus.Result_Available and payload.result is None:
        raise HTTPException(
            status_code=422,
            detail="A manually supplied demo result is required for Result_Available",
        )
    if payload.result is not None and payload.status != LabReferralStatus.Result_Available:
        raise HTTPException(
            status_code=422,
            detail="Results may only be supplied when setting Result_Available",
        )

    now = datetime.now(timezone.utc)
    referral.status = payload.status
    if payload.notes is not None:
        referral.notes = payload.notes
    if payload.status == LabReferralStatus.Result_Available:
        supplied_result = payload.result.strip()
        referral.result = supplied_result if supplied_result.startswith("DEMO:") else f"DEMO: {supplied_result}"
        referral.result_at = now
        referral.is_demo_result = True

        alert_result = await db.execute(select(Alert).where(Alert.id == referral.alert_id))
        alert = alert_result.scalar_one_or_none()
        if alert is None:
            raise HTTPException(status_code=404, detail="Referral alert not found")
        if alert.status == AlertStatus.Verified_Risk:
            transition_alert_status(alert, AlertStatus.Resolved)
            alert.resolved_at = now

    await db.commit()
    return LabReferralResponse.model_validate(referral)