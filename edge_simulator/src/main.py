import hashlib
import json
import sqlite3
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

try:
    from app.core.device_auth import device_auth_service
except ModuleNotFoundError:
    backend_root = Path(__file__).resolve().parents[2] / "backend"
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    from app.core.device_auth import device_auth_service

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "edge.db"
MAX_BATCH_SIZE = 50
EDGE_DEVICE_UID = "EDGE-DEMO-001"
BACKEND_URL = "http://localhost:8000"


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def create_signature(payload: dict[str, object]) -> str:
    return device_auth_service.create_signature(payload)


class QueueStatus(str):
    UNSYNCED = "UNSYNCED"
    SYNCING = "SYNCING"
    ACKNOWLEDGED = "ACKNOWLEDGED"


@dataclass
class EdgeEvent:
    event_id: str
    device_uid: str
    shed_id: str
    event_type: str
    confidence: float
    duration_sec: float
    embedding: list[float]
    timestamp: float
    signature: str
    status: str = QueueStatus.UNSYNCED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sync_attempts: int = 0
    last_error: str | None = None
    batch_id: str | None = None

    def to_backend_payload(self) -> dict[str, object]:
        return {
            "device_uid": self.device_uid,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "confidence": self.confidence,
            "duration_sec": self.duration_sec,
            "embedding": self.embedding,
            "signature": self.signature,
        }

    def idempotency_key(self) -> str:
        canonical = _canonical_json(self.to_backend_payload())
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class HealthResponse(BaseModel):
    status: str
    service: str


class QueueEntryResponse(BaseModel):
    event_id: str
    device_uid: str
    shed_id: str
    event_type: str
    confidence: float
    duration_sec: float
    timestamp: float
    status: str
    sync_attempts: int = 0
    last_error: str | None = None


class EdgeStatusResponse(BaseModel):
    device_uid: str
    offline: bool
    queue_summary: dict[str, int]


def _initialize_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS queued_events (
            id TEXT PRIMARY KEY,
            event_id TEXT UNIQUE NOT NULL,
            device_uid TEXT NOT NULL,
            shed_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            confidence REAL NOT NULL,
            duration_sec REAL NOT NULL,
            embedding TEXT NOT NULL,
            timestamp REAL NOT NULL,
            signature TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            batch_id TEXT,
            sync_attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT
        )
        """
    )
    connection.commit()
    return connection


def get_db_connection() -> sqlite3.Connection:
    return _initialize_db()


def _decode_embedding(raw: str) -> list[float]:
    return json.loads(raw)


def queue_event(event: EdgeEvent) -> EdgeEvent:
    connection = get_db_connection()
    connection.execute(
        """
        INSERT INTO queued_events (
            id, event_id, device_uid, shed_id, event_type, confidence, duration_sec,
            embedding, timestamp, signature, status, created_at, batch_id, sync_attempts, last_error
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            uuid.uuid4().hex,
            event.event_id,
            event.device_uid,
            event.shed_id,
            event.event_type,
            event.confidence,
            event.duration_sec,
            json.dumps(event.embedding),
            event.timestamp,
            event.signature,
            event.status,
            event.created_at.isoformat(),
            event.batch_id,
            event.sync_attempts,
            event.last_error,
        ),
    )
    connection.commit()
    return event


def list_queue() -> list[EdgeEvent]:
    connection = get_db_connection()
    rows = connection.execute(
        """
        SELECT event_id, device_uid, shed_id, event_type, confidence, duration_sec,
               embedding, timestamp, signature, status, created_at, batch_id, sync_attempts, last_error
        FROM queued_events
        ORDER BY created_at ASC
        """
    ).fetchall()
    events: list[EdgeEvent] = []
    for row in rows:
        events.append(
            EdgeEvent(
                event_id=row[0],
                device_uid=row[1],
                shed_id=row[2],
                event_type=row[3],
                confidence=row[4],
                duration_sec=row[5],
                embedding=_decode_embedding(row[6]),
                timestamp=row[7],
                signature=row[8],
                status=row[9],
                created_at=datetime.fromisoformat(row[10]),
                batch_id=row[11],
                sync_attempts=row[12],
                last_error=row[13],
            )
        )
    return events


def queue_summary() -> dict[str, int]:
    statuses = {"UNSYNCED": 0, "SYNCING": 0, "ACKNOWLEDGED": 0}
    for event in list_queue():
        statuses[event.status] = statuses.get(event.status, 0) + 1
    return statuses


def calculate_batch_hash(events: list[dict[str, object]]) -> str:
    return hashlib.sha256(_canonical_json(events).encode("utf-8")).hexdigest()


def build_batch(events: list[EdgeEvent]) -> tuple[list[dict[str, object]], str]:
    payload = [event.to_backend_payload() for event in events]
    return payload, calculate_batch_hash(payload)


def update_event_status(event_id: str, *, status: str, batch_id: str | None = None, last_error: str | None = None, sync_attempts: int | None = None) -> None:
    connection = get_db_connection()
    sql = (
        "UPDATE queued_events SET status = ?, batch_id = ?, last_error = ?"
        + (", sync_attempts = ?" if sync_attempts is not None else "")
        + " WHERE event_id = ?"
    )
    params: list[object] = [status, batch_id, last_error]
    if sync_attempts is not None:
        params.append(sync_attempts)
    params.append(event_id)
    connection.execute(sql, tuple(params))
    connection.commit()


def generate_demo_event(event_type: str = "Cough", confidence: float = 0.91) -> EdgeEvent:
    timestamp = datetime.now(timezone.utc).timestamp()
    payload = {
        "device_uid": EDGE_DEVICE_UID,
        "timestamp": timestamp,
        "event_type": event_type,
        "confidence": confidence,
        "duration_sec": 2.4,
        "embedding": [0.01, -0.02, 0.06],
    }
    payload["signature"] = create_signature(payload)
    return EdgeEvent(
        event_id=f"evt-{uuid.uuid4().hex}",
        device_uid=payload["device_uid"],
        shed_id="SHED-DEMO-001",
        event_type=event_type,
        confidence=confidence,
        duration_sec=payload["duration_sec"],
        embedding=payload["embedding"],
        timestamp=timestamp,
        signature=payload["signature"],
    )


async def sync_pending_events(offline: bool = False, fail_sync: bool = False) -> dict[str, object]:
    queued = [event for event in list_queue() if event.status == QueueStatus.UNSYNCED]
    if offline or not queued:
        return {"queued": len(queued), "acknowledged": 0, "failed": 0, "offline": offline}

    acknowledged_count = 0
    failed_count = 0
    batch_size = min(MAX_BATCH_SIZE, len(queued))
    batch = queued[:batch_size]
    for event in batch:
        update_event_status(event.event_id, status=QueueStatus.SYNCING, batch_id=f"batch-{uuid.uuid4().hex}")
    payload, batch_hash = build_batch(batch)

    if fail_sync:
        for event in batch:
            update_event_status(
                event.event_id,
                status=QueueStatus.UNSYNCED,
                last_error="simulated network failure",
                sync_attempts=(event.sync_attempts + 1),
            )
        return {"queued": len(queued), "acknowledged": 0, "failed": len(batch), "offline": False, "simulated_failure": True}

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                f"{BACKEND_URL}/api/v1/edge/sync-batch",
                json={"events": payload, "batch_hash": batch_hash},
            )
        except Exception as exc:
            for event in batch:
                update_event_status(event.event_id, status=QueueStatus.UNSYNCED, last_error=str(exc), sync_attempts=(event.sync_attempts + 1))
            failed_count = len(batch)
            return {"queued": len(queued), "acknowledged": 0, "failed": failed_count, "offline": False, "error": str(exc)}

    if response.status_code != 200:
        for event in batch:
            update_event_status(event.event_id, status=QueueStatus.UNSYNCED, last_error=f"HTTP {response.status_code}", sync_attempts=(event.sync_attempts + 1))
        failed_count = len(batch)
        return {"queued": len(queued), "acknowledged": 0, "failed": failed_count, "offline": False, "error": response.text}

    data = response.json()
    for event in batch:
        current = next((item for item in data.get("results", []) if str(item.get("event_id")) == event.event_id), None)
        if current and current.get("accepted"):
            update_event_status(event.event_id, status=QueueStatus.ACKNOWLEDGED, last_error=None, sync_attempts=(event.sync_attempts + 1))
            acknowledged_count += 1
        else:
            update_event_status(event.event_id, status=QueueStatus.UNSYNCED, last_error=(current or {}).get("error_detail") or "sync rejected", sync_attempts=(event.sync_attempts + 1))
            failed_count += 1
    return {"queued": len(queued), "acknowledged": acknowledged_count, "failed": failed_count, "offline": False}


async def send_heartbeat() -> dict[str, object]:
    payload = {
        "device_uid": EDGE_DEVICE_UID,
        "firmware_version": "demo-edge-v1",
        "status": "Online",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(f"{BACKEND_URL}/api/v1/edge/heartbeat", json=payload)
        except httpx.HTTPError as exc:
            return {"acknowledged": False, "error": str(exc)}
    if response.status_code != 200:
        return {"acknowledged": False, "error": response.text}
    return response.json()


app = FastAPI(title="Acoustic Livestock Edge Simulator", version="0.1.0")


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="healthy", service="acoustic-livestock-edge-simulator")


@app.get("/status", response_model=EdgeStatusResponse)
async def status_endpoint() -> EdgeStatusResponse:
    return EdgeStatusResponse(device_uid=EDGE_DEVICE_UID, offline=False, queue_summary=queue_summary())


@app.get("/queue", response_model=list[QueueEntryResponse])
async def queue_endpoint() -> list[QueueEntryResponse]:
    return [
        QueueEntryResponse(
            event_id=event.event_id,
            device_uid=event.device_uid,
            shed_id=event.shed_id,
            event_type=event.event_type,
            confidence=event.confidence,
            duration_sec=event.duration_sec,
            timestamp=event.timestamp,
            status=event.status,
            sync_attempts=event.sync_attempts,
            last_error=event.last_error,
        )
        for event in list_queue()
    ]


@app.post("/generate")
async def generate_event(count: int = 1, offline: bool = False) -> dict[str, object]:
    generated = []
    for _ in range(max(1, count)):
        event = generate_demo_event()
        queue_event(event)
        generated.append(event)
    return {"generated": len(generated), "offline": offline, "queue_summary": queue_summary()}


@app.post("/sync")
async def sync_endpoint(offline: bool = False, fail_sync: bool = False) -> dict[str, object]:
    return await sync_pending_events(offline=offline, fail_sync=fail_sync)


@app.post("/heartbeat")
async def heartbeat_endpoint() -> dict[str, object]:
    return await send_heartbeat()
