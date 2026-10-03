import uuid

import pytest
from httpx import AsyncClient

from app.models.alert import AlertStatus
from app.models.audit_block import AuditBlock
from app.models.audit_block import AuditBlock
from app.models.lab_referral import LabReferral, LabReferralStatus
from app.models.vet_verification import VetVerification, VetVerificationOutcome


def vet_request(alert_id, outcome="Verified_Risk"):
    return {
        "alert_id": str(alert_id),
        "outcome": outcome,
        "vet_identifier": "DEMO-VET-017",
        "notes": "Demonstration assessment; not a clinical diagnosis.",
    }


@pytest.mark.asyncio
async def test_vet_can_mark_under_review_alert_verified_risk(async_client: AsyncClient, db_session, seed_test_alert):
    seed_test_alert.status = AlertStatus.Under_Vet_Review
    response = await async_client.post(
        "/api/v1/vet/verify", json=vet_request(seed_test_alert.id)
    )

    assert response.status_code == 200
    assert response.json()["alert_status"] == AlertStatus.Verified_Risk.value
    assert response.json()["verification_result"] == VetVerificationOutcome.Verified_Risk.value
    assert response.json()["alert_id"] == str(seed_test_alert.id)
    assert response.json()["verified_at"]
    assert seed_test_alert.status == AlertStatus.Verified_Risk
    assert len(db_session.records[VetVerification]) == 1
    assert [block.entity_type for block in db_session.records[AuditBlock]] == [
        "GENESIS",
        "VET_VERIFICATION",
    ]
    assert [block.entity_type for block in db_session.records[AuditBlock]] == [
        "GENESIS",
        "VET_VERIFICATION",
    ]


@pytest.mark.asyncio
async def test_false_positive_verification_resolves_alert(async_client: AsyncClient, seed_test_alert):
    seed_test_alert.status = AlertStatus.Under_Vet_Review
    response = await async_client.post(
        "/api/v1/vet/verify",
        json=vet_request(seed_test_alert.id, outcome="False_Positive"),
    )

    assert response.status_code == 200
    assert response.json()["verification_result"] == VetVerificationOutcome.False_Positive.value
    assert response.json()["alert_status"] == AlertStatus.Resolved.value
    assert seed_test_alert.resolved_at is not None


@pytest.mark.asyncio
async def test_vet_verification_rejects_unknown_alert(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/vet/verify", json=vet_request(uuid.uuid4())
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_vet_verification_requires_under_vet_review(async_client: AsyncClient, seed_test_alert):
    response = await async_client.post(
        "/api/v1/vet/verify", json=vet_request(seed_test_alert.id)
    )
    assert response.status_code == 409
    assert seed_test_alert.status == AlertStatus.Pending_Triage


@pytest.mark.asyncio
async def test_alert_cannot_be_verified_twice(async_client: AsyncClient, db_session, seed_test_alert):
    seed_test_alert.status = AlertStatus.Under_Vet_Review
    payload = vet_request(seed_test_alert.id)
    first = await async_client.post("/api/v1/vet/verify", json=payload)
    repeated = await async_client.post("/api/v1/vet/verify", json=payload)

    assert first.status_code == 200
    assert repeated.status_code == 409
    assert len(db_session.records[VetVerification]) == 1


@pytest.mark.asyncio
async def test_verified_risk_can_create_lab_referral_and_detail(async_client: AsyncClient, db_session, seed_verified_alert):
    payload = {
        "alert_id": str(seed_verified_alert.id),
        "sample_identifier": "DEMO-SAMPLE-05",
        "requested_tests": ["Demo screening panel", "Demo culture"],
        "notes": "Synthetic referral record for presentation.",
    }
    response = await async_client.post("/api/v1/lab/referrals", json=payload)

    assert response.status_code == 201
    result = response.json()
    assert result["alert_id"] == str(seed_verified_alert.id)
    assert result["status"] == LabReferralStatus.Pending.value
    assert result["sample_identifier"] == "DEMO-SAMPLE-05"
    assert result["result"] is None
    assert result["is_demo_result"] is False
    assert len(db_session.records[LabReferral]) == 1
    assert [block.entity_type for block in db_session.records[AuditBlock]] == [
        "GENESIS",
        "LAB_REFERRAL_CREATED",
    ]
    assert [block.entity_type for block in db_session.records[AuditBlock]] == [
        "GENESIS",
        "LAB_REFERRAL_CREATED",
    ]

    detail = await async_client.get(f"/api/v1/lab/referrals/{result['id']}")
    assert detail.status_code == 200
    assert detail.json()["alert"]["status"] == AlertStatus.Verified_Risk.value
    assert detail.json()["verification"]["vet_identifier"] == "DEMO-VET-001"
    assert detail.json()["referral"]["requested_tests"] == payload["requested_tests"]


@pytest.mark.asyncio
async def test_lab_referral_rejects_false_positive_and_nonexistent_alert(async_client: AsyncClient, seed_test_alert):
    seed_test_alert.status = AlertStatus.Resolved
    seed_test_alert.vet_verification = VetVerification(
        alert_id=seed_test_alert.id,
        vet_identifier="DEMO-VET-017",
        verification_status=VetVerificationOutcome.False_Positive,
        assessment_notes="Demo false positive",
    )
    false_positive = await async_client.post(
        "/api/v1/lab/referrals",
        json={"alert_id": str(seed_test_alert.id), "sample_identifier": "S1", "requested_tests": ["Demo test"]},
    )
    unknown = await async_client.post(
        "/api/v1/lab/referrals",
        json={"alert_id": str(uuid.uuid4()), "sample_identifier": "S2", "requested_tests": ["Demo test"]},
    )

    assert false_positive.status_code == 409
    assert unknown.status_code == 404


@pytest.mark.parametrize(
    "blocked_status",
    [
        AlertStatus.Pending_Triage,
        AlertStatus.Escalated,
        AlertStatus.Under_Vet_Review,
        AlertStatus.False_Positive,
    ],
)
@pytest.mark.asyncio
async def test_lab_referral_is_rejected_before_verified_risk(async_client: AsyncClient, seed_test_alert, blocked_status):
    seed_test_alert.status = blocked_status
    response = await async_client.post(
        "/api/v1/lab/referrals",
        json={
            "alert_id": str(seed_test_alert.id),
            "sample_identifier": "DEMO-BLOCKED-SAMPLE",
            "requested_tests": ["Demo-only test"],
        },
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_duplicate_referral_is_rejected(async_client: AsyncClient, seed_verified_alert):
    payload = {
        "alert_id": str(seed_verified_alert.id),
        "sample_identifier": "DEMO-SAMPLE-06",
        "requested_tests": ["Demo screening panel"],
    }
    first = await async_client.post("/api/v1/lab/referrals", json=payload)
    second = await async_client.post("/api/v1/lab/referrals", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_lab_status_requires_valid_transition_and_demo_result(async_client: AsyncClient, db_session, seed_verified_alert):
    create_response = await async_client.post(
        "/api/v1/lab/referrals",
        json={
            "alert_id": str(seed_verified_alert.id),
            "sample_identifier": "DEMO-SAMPLE-07",
            "requested_tests": ["Demo screening panel"],
        },
    )
    referral_id = create_response.json()["id"]

    invalid_skip = await async_client.patch(
        f"/api/v1/lab/referrals/{referral_id}/status", json={"status": "In_Lab"}
    )
    collected = await async_client.patch(
        f"/api/v1/lab/referrals/{referral_id}/status", json={"status": "Sample_Collected"}
    )
    in_lab = await async_client.patch(
        f"/api/v1/lab/referrals/{referral_id}/status", json={"status": "In_Lab"}
    )
    missing_result = await async_client.patch(
        f"/api/v1/lab/referrals/{referral_id}/status", json={"status": "Result_Available"}
    )
    result = await async_client.patch(
        f"/api/v1/lab/referrals/{referral_id}/status",
        json={"status": "Result_Available", "result": "Screening result recorded for demo"},
    )

    assert invalid_skip.status_code == 409
    assert missing_result.status_code == 422
    assert collected.status_code == 200
    assert in_lab.status_code == 200
    assert result.status_code == 200
    assert result.json()["result"].startswith("DEMO:")
    assert result.json()["is_demo_result"] is True
    assert seed_verified_alert.status == AlertStatus.Resolved
    assert [block.entity_type for block in db_session.records[AuditBlock]].count(
        "LAB_REFERRAL_STATUS_CHANGED"
    ) == 3
    assert [block.entity_type for block in db_session.records[AuditBlock]].count(
        "LAB_REFERRAL_STATUS_CHANGED"
    ) == 3


@pytest.mark.asyncio
async def test_missing_lab_referral_detail_returns_404(async_client: AsyncClient):
    response = await async_client.get(f"/api/v1/lab/referrals/{uuid.uuid4()}")
    assert response.status_code == 404