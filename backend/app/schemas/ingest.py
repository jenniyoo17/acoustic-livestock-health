import math
import uuid
from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.acoustic_event import EventType
from app.models.device import DeviceStatus


class IngestRequest(BaseModel):
    device_uid: str = Field(min_length=1, max_length=100)
    timestamp: float = Field(gt=0, allow_inf_nan=False)
    event_type: EventType
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    duration_sec: float = Field(gt=0, allow_inf_nan=False)
    embedding: list[float] = Field(min_length=1)
    signature: str = Field(pattern=r"^[0-9a-fA-F]{64}$")

    @field_validator("embedding")
    @classmethod
    def embedding_values_must_be_finite(cls, values: list[float]) -> list[float]:
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Embedding values must be finite numbers")
        return values

    def recorded_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp, tz=timezone.utc)

    def signed_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"signature"})


class IngestResponse(BaseModel):
    accepted: bool
    event_id: uuid.UUID
    device_uid: str
    status: str
    alert_created: bool = False
    alert_id: uuid.UUID | None = None


class BatchSyncRequest(BaseModel):
    events: Annotated[list[IngestRequest], Field(min_length=1, max_length=50)]
    batch_hash: str = Field(pattern=r"^[0-9a-fA-F]{64}$")


class BatchItemResult(BaseModel):
    index: int
    device_uid: str
    accepted: bool
    status: str
    event_id: uuid.UUID | None = None
    error_detail: str | None = None


class BatchSyncResponse(BaseModel):
    accepted: int
    duplicates: int
    rejected: int
    results: list[BatchItemResult]


class HeartbeatRequest(BaseModel):
    device_uid: str = Field(min_length=1, max_length=100)
    firmware_version: str | None = Field(default=None, max_length=50)
    status: DeviceStatus = DeviceStatus.Online


class HeartbeatResponse(BaseModel):
    acknowledged: bool
    device_uid: str
    status: DeviceStatus
    last_heartbeat_at: datetime

    model_config = ConfigDict(from_attributes=True)
