import uuid
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator
from app.models.acoustic_event import EventType
from app.models.device import DeviceStatus


class IngestRequest(BaseModel):
    device_uid: str = Field(..., description="Unique hardware identifier for the shed microphone device")
    timestamp: float = Field(..., description="POSIX timestamp (seconds) when event was recorded")
    event_type: EventType = Field(..., description="Classified acoustic pattern category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    duration_sec: float = Field(..., gt=0.0, description="Audio event duration in seconds")
    embedding: List[float] = Field(..., description="YAMNet 1024-dim or feature embedding vector")
    signature: str = Field(..., description="Device HMAC SHA-256 signature")

    @field_validator("embedding")
    @classmethod
    def validate_embedding_non_empty(cls, v: List[float]) -> List[float]:
        if not v or len(v) == 0:
            raise ValueError("Embedding vector must not be empty")
        return v

    def get_recorded_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp, tz=timezone.utc)


class IngestResponse(BaseModel):
    accepted: bool
    event_id: str
    device_uid: str
    status: str
    alert_created: bool = False
    alert_id: Optional[str] = None


class BatchSyncRequest(BaseModel):
    events: List[IngestRequest] = Field(..., description="Batch of up to 50 offline acoustic events")

    @field_validator("events")
    @classmethod
    def validate_batch_size(cls, v: List[IngestRequest]) -> List[IngestRequest]:
        if len(v) > 50:
            raise ValueError("Batch size exceeds maximum limit of 50 events")
        return v


class BatchItemResult(BaseModel):
    index: int
    device_uid: str
    accepted: bool
    status: str  # "stored", "duplicate", "invalid_device", "error"
    event_id: Optional[str] = None
    error_detail: Optional[str] = None


class BatchSyncResponse(BaseModel):
    accepted: int
    duplicates: int
    rejected: int
    results: List[BatchItemResult]


class HeartbeatRequest(BaseModel):
    device_uid: str = Field(..., description="Unique hardware identifier for the device")
    firmware_version: Optional[str] = Field(None, description="Current firmware version")
    status: DeviceStatus = Field(default=DeviceStatus.Online, description="Device operational status")


class HeartbeatResponse(BaseModel):
    acknowledged: bool
    device_uid: str
    status: DeviceStatus
    last_heartbeat_at: datetime
