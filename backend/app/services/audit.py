import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_block import AuditBlock

GENESIS_TIMESTAMP = datetime(1970, 1, 1, tzinfo=timezone.utc)
GENESIS_ENTITY_TYPE = "GENESIS"
GENESIS_ENTITY_ID = "0"
GENESIS_PAYLOAD = {"type": "GENESIS"}
AUDIT_BLOCK_NAMESPACE = uuid.UUID("96548551-5cb5-4d40-8641-a355ca5f4a87")
POSTGRES_AUDIT_LOCK_KEY = 1_397_602_561


@dataclass(frozen=True)
class IntegrityResult:
    valid: bool
    checked_blocks: int
    error: str | None = None


class AuditLedgerIntegrityError(RuntimeError):
    pass


def _json_default(value: Any) -> str:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return _normalize_timestamp(value).isoformat()
    if isinstance(value, Enum):
        return str(value.value)
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    raise TypeError(f"Unsupported audit payload value: {type(value).__name__}")


def _normalize_timestamp(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_json_default,
    )


def calculate_payload_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def calculate_transition_key(entity_type: str, entity_id: str, payload_hash: str) -> str:
    key_fields = {
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "payload_hash": payload_hash,
    }
    return hashlib.sha256(canonical_json(key_fields).encode("utf-8")).hexdigest()


def calculate_block_hash(
    block_index: int,
    timestamp: datetime,
    previous_hash: str | None,
    entity_type: str,
    entity_id: str,
    payload_hash: str,
) -> str:
    block_fields = {
        "block_index": block_index,
        "timestamp": _normalize_timestamp(timestamp).isoformat(),
        "previous_hash": previous_hash,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "payload_hash": payload_hash,
    }
    return hashlib.sha256(canonical_json(block_fields).encode("utf-8")).hexdigest()


def _make_block(
    *,
    block_index: int,
    timestamp: datetime,
    previous_hash: str | None,
    entity_type: str,
    entity_id: str,
    payload_hash: str,
    transition_key: str,
) -> AuditBlock:
    timestamp = _normalize_timestamp(timestamp)
    block_hash = calculate_block_hash(
        block_index,
        timestamp,
        previous_hash,
        entity_type,
        str(entity_id),
        payload_hash,
    )
    return AuditBlock(
        id=uuid.uuid5(AUDIT_BLOCK_NAMESPACE, f"{block_index}:{block_hash}"),
        block_index=block_index,
        timestamp=timestamp,
        previous_hash=previous_hash,
        entity_type=entity_type,
        entity_id=str(entity_id),
        payload_hash=payload_hash,
        block_hash=block_hash,
        transition_key=transition_key,
        created_at=timestamp,
    )


def _genesis_block() -> AuditBlock:
    payload_hash = calculate_payload_hash(GENESIS_PAYLOAD)
    transition_key = calculate_transition_key(
        GENESIS_ENTITY_TYPE, GENESIS_ENTITY_ID, payload_hash
    )
    return _make_block(
        block_index=0,
        timestamp=GENESIS_TIMESTAMP,
        previous_hash=None,
        entity_type=GENESIS_ENTITY_TYPE,
        entity_id=GENESIS_ENTITY_ID,
        payload_hash=payload_hash,
        transition_key=transition_key,
    )


async def list_audit_blocks(session: AsyncSession) -> list[AuditBlock]:
    result = await session.execute(select(AuditBlock))
    return sorted(result.scalars().all(), key=lambda block: block.block_index)


def verify_audit_blocks(blocks: list[AuditBlock]) -> IntegrityResult:
    if not blocks:
        return IntegrityResult(False, 0, "Missing genesis block")

    indexes = [block.block_index for block in blocks]
    if len(indexes) != len(set(indexes)):
        return IntegrityResult(False, 0, "Duplicate block index detected")
    hashes = [block.block_hash for block in blocks]
    if len(hashes) != len(set(hashes)):
        return IntegrityResult(False, 0, "Duplicate block hash detected")

    expected_genesis = _genesis_block()
    previous_hash: str | None = None
    for expected_index, block in enumerate(blocks):
        if block.block_index != expected_index:
            return IntegrityResult(
                False,
                expected_index,
                f"Block index gap or order mismatch at position {expected_index}",
            )
        if expected_index == 0:
            if (
                block.previous_hash is not None
                or block.entity_type != GENESIS_ENTITY_TYPE
                or block.entity_id != GENESIS_ENTITY_ID
                or _normalize_timestamp(block.timestamp) != GENESIS_TIMESTAMP
                or block.payload_hash != expected_genesis.payload_hash
            ):
                return IntegrityResult(False, 0, "Invalid genesis block")
        else:
            if block.entity_type == GENESIS_ENTITY_TYPE:
                return IntegrityResult(False, expected_index, "Duplicate genesis block")
            if block.previous_hash != previous_hash:
                return IntegrityResult(
                    False,
                    expected_index,
                    f"Block {expected_index} previous hash mismatch",
                )

        calculated_hash = calculate_block_hash(
            block.block_index,
            block.timestamp,
            block.previous_hash,
            block.entity_type,
            block.entity_id,
            block.payload_hash,
        )
        if block.block_hash != calculated_hash:
            return IntegrityResult(False, expected_index, f"Block {expected_index} hash mismatch")
        expected_id = uuid.uuid5(
            AUDIT_BLOCK_NAMESPACE,
            f"{block.block_index}:{block.block_hash}",
        )
        if block.id != expected_id:
            return IntegrityResult(False, expected_index, f"Block {expected_index} ID mismatch")
        if _normalize_timestamp(block.created_at) != _normalize_timestamp(block.timestamp):
            return IntegrityResult(False, expected_index, f"Block {expected_index} creation timestamp mismatch")
        if block.transition_key != calculate_transition_key(
            block.entity_type, block.entity_id, block.payload_hash
        ):
            return IntegrityResult(False, expected_index, f"Block {expected_index} transition key mismatch")
        previous_hash = block.block_hash

    return IntegrityResult(True, len(blocks))


async def verify_audit_chain(session: AsyncSession) -> IntegrityResult:
    return verify_audit_blocks(await list_audit_blocks(session))


async def _acquire_append_lock(session: AsyncSession) -> None:
    get_bind = getattr(session, "get_bind", None)
    if get_bind is None:
        return
    bind = get_bind()
    if bind.dialect.name == "postgresql":
        await session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": POSTGRES_AUDIT_LOCK_KEY},
        )


async def append_audit_block(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: uuid.UUID | str,
    payload: Any,
    timestamp: datetime | None = None,
) -> AuditBlock:
    """Append an event and genesis block in the caller's current transaction."""
    await _acquire_append_lock(session)
    entity_id = str(entity_id)
    payload_hash = calculate_payload_hash(payload)
    transition_key = calculate_transition_key(entity_type, entity_id, payload_hash)

    blocks = await list_audit_blocks(session)
    integrity = verify_audit_blocks(blocks)
    if blocks and not integrity.valid:
        raise AuditLedgerIntegrityError(integrity.error or "Audit chain is invalid")

    existing_result = await session.execute(
        select(AuditBlock).where(AuditBlock.transition_key == transition_key)
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        return existing

    if not blocks:
        genesis = _genesis_block()
        session.add(genesis)
        await session.flush()
        blocks = [genesis]

    previous = blocks[-1]
    block = _make_block(
        block_index=previous.block_index + 1,
        timestamp=timestamp or datetime.now(timezone.utc),
        previous_hash=previous.block_hash,
        entity_type=entity_type,
        entity_id=entity_id,
        payload_hash=payload_hash,
        transition_key=transition_key,
    )
    session.add(block)
    await session.flush()
    return block