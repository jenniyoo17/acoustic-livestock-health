from datetime import datetime, timezone
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.session import get_session
from app.main import app
from app.models.audit_block import AuditBlock
from app.services.audit import (
    GENESIS_ENTITY_ID,
    GENESIS_ENTITY_TYPE,
    GENESIS_TIMESTAMP,
    append_audit_block,
    calculate_block_hash,
    calculate_payload_hash,
    calculate_transition_key,
    verify_audit_chain,
    verify_audit_blocks,
    _make_block,
)

FIXED_TIME = datetime(2026, 10, 3, 10, 0, tzinfo=timezone.utc)


async def append_event(db_session, *, payload=None, entity_id="00000000-0000-0000-0000-000000000001"):
    return await append_audit_block(
        db_session,
        entity_type="ALERT_CREATED",
        entity_id=entity_id,
        payload=payload or {"status": "Pending_Triage", "severity": "High"},
        timestamp=FIXED_TIME,
    )


@pytest_asyncio.fixture
async def audit_client(db_session):
    async def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_append_creates_deterministic_genesis_then_sequential_blocks(db_session):
    first = await append_event(db_session)
    second = await append_event(
        db_session,
        entity_id="00000000-0000-0000-0000-000000000002",
        payload={"status": "Escalated", "to_tier": "Tier_2_Field_Vet"},
    )
    blocks = sorted(db_session.records[AuditBlock], key=lambda block: block.block_index)
    genesis = blocks[0]

    assert [block.block_index for block in blocks] == [0, 1, 2]
    assert genesis.previous_hash is None
    assert genesis.entity_type == GENESIS_ENTITY_TYPE
    assert genesis.entity_id == GENESIS_ENTITY_ID
    assert genesis.timestamp == GENESIS_TIMESTAMP
    assert first.previous_hash == genesis.block_hash
    assert second.previous_hash == first.block_hash


def test_payload_and_block_hashes_are_deterministic_and_canonical():
    assert calculate_payload_hash({"b": 2, "a": 1}) == calculate_payload_hash({"a": 1, "b": 2})
    assert calculate_payload_hash({"status": "Pending"}) != calculate_payload_hash({"status": "Resolved"})

    first = calculate_block_hash(1, FIXED_TIME, "a" * 64, "ALERT_CREATED", "alert-1", "b" * 64)
    second = calculate_block_hash(1, FIXED_TIME, "a" * 64, "ALERT_CREATED", "alert-1", "b" * 64)
    assert first == second
    assert len(first) == 64


@pytest.mark.asyncio
async def test_same_transition_is_idempotent(db_session):
    first = await append_event(db_session)
    repeated = await append_event(db_session)

    assert repeated.id == first.id
    assert len(db_session.records[AuditBlock]) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        ("payload_hash", "hash mismatch"),
        ("block_hash", "hash mismatch"),
        ("previous_hash", "previous hash mismatch"),
        ("delete_middle", "index gap"),
        ("change_index", "index gap"),
        ("id", "id mismatch"),
        ("created_at", "creation timestamp mismatch"),
    ],
)
async def test_tampering_is_detected(db_session, mutation, expected_error):
    await append_event(db_session)
    await append_event(
        db_session,
        entity_id="00000000-0000-0000-0000-000000000002",
        payload={"status": "Escalated"},
    )
    await append_event(
        db_session,
        entity_id="00000000-0000-0000-0000-000000000003",
        payload={"status": "Under_Vet_Review"},
    )
    blocks = sorted(db_session.records[AuditBlock], key=lambda block: block.block_index)

    if mutation == "payload_hash":
        blocks[1].payload_hash = "f" * 64
    elif mutation == "block_hash":
        blocks[1].block_hash = "e" * 64
    elif mutation == "previous_hash":
        blocks[2].previous_hash = "d" * 64
    elif mutation == "delete_middle":
        db_session.records[AuditBlock].remove(blocks[2])
    elif mutation == "change_index":
        blocks[2].block_index = 9
    elif mutation == "id":
        blocks[1].id = uuid.uuid4()
    elif mutation == "created_at":
        blocks[1].created_at = FIXED_TIME.replace(minute=1)

    result = await verify_audit_chain(db_session)
    assert result.valid is False
    assert result.error is not None
    assert expected_error in result.error.lower()


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["block_index", "block_hash"])
async def test_duplicate_indexes_and_hashes_are_rejected(db_session, field):
    await append_event(db_session)
    await append_event(
        db_session,
        entity_id="00000000-0000-0000-0000-000000000002",
        payload={"status": "Escalated"},
    )
    blocks = sorted(db_session.records[AuditBlock], key=lambda block: block.block_index)
    if field == "block_index":
        blocks[2].block_index = blocks[1].block_index
    else:
        blocks[2].block_hash = blocks[1].block_hash

    result = await verify_audit_chain(db_session)

    assert result.valid is False
    assert "duplicate block" in result.error.lower()


def test_duplicate_genesis_marker_is_rejected():
    genesis = _make_block(
        block_index=0,
        timestamp=GENESIS_TIMESTAMP,
        previous_hash=None,
        entity_type=GENESIS_ENTITY_TYPE,
        entity_id=GENESIS_ENTITY_ID,
        payload_hash=calculate_payload_hash({"type": "GENESIS"}),
        transition_key=calculate_transition_key(
            GENESIS_ENTITY_TYPE,
            GENESIS_ENTITY_ID,
            calculate_payload_hash({"type": "GENESIS"}),
        ),
    )
    previous = _make_block(
        block_index=1,
        timestamp=FIXED_TIME,
        previous_hash=genesis.block_hash,
        entity_type="GENESIS",
        entity_id="0",
        payload_hash=calculate_payload_hash({"type": "GENESIS", "extra": True}),
        transition_key=calculate_transition_key(
            "GENESIS", "0", calculate_payload_hash({"type": "GENESIS", "extra": True})
        ),
    )

    result = verify_audit_blocks([genesis, previous])
    assert result.valid is False
    assert result.error == "Duplicate genesis block"


@pytest.mark.asyncio
async def test_valid_chain_passes_integrity_verification(db_session):
    await append_event(db_session)
    await append_event(
        db_session,
        entity_id="00000000-0000-0000-0000-000000000002",
        payload={"status": "Under_Vet_Review"},
    )

    result = await verify_audit_chain(db_session)

    assert result.valid is True
    assert result.checked_blocks == 3
    assert result.error is None


@pytest.mark.asyncio
async def test_audit_chain_api_returns_chronological_blocks(audit_client, db_session):
    await append_event(db_session)
    await append_event(
        db_session,
        entity_id="00000000-0000-0000-0000-000000000002",
        payload={"status": "Escalated"},
    )
    db_session.records[AuditBlock].reverse()

    response = await audit_client.get("/api/v1/audit/chain")

    assert response.status_code == 200
    indexes = [block["block_index"] for block in response.json()]
    assert indexes == [0, 1, 2]


@pytest.mark.asyncio
async def test_verify_integrity_api_reports_valid_and_tampered_chains(audit_client, db_session):
    await append_event(db_session)
    valid = await audit_client.post("/api/v1/audit/verify-integrity")
    db_session.records[AuditBlock][1].payload_hash = "a" * 64
    invalid = await audit_client.post("/api/v1/audit/verify-integrity")

    assert valid.status_code == 200
    assert valid.json() == {"valid": True, "checked_blocks": 2, "error": None}
    assert invalid.status_code == 200
    assert invalid.json()["valid"] is False
    assert invalid.json()["error"] == "Block 1 hash mismatch"