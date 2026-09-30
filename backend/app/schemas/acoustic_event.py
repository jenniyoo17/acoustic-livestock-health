import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.acoustic_event import EventType


class AcousticEventFields(BaseModel):
    device_id: uuid.UUID
    shed_id: uuid.UUID
    event_type: EventType
    confidence_score: float = Field(ge=0, le=1, allow_inf_nan=False)
    yamnet_embedding_vector: list[float] = Field(min_length=1)
    audio_duration_sec: float = Field(gt=0, allow_inf_nan=False)
    audio_snippet_url: str | None = Field(default=None, max_length=512)
    recorded_at: datetime
    is_synced_offline: bool = False


class AcousticEventCreate(AcousticEventFields):
    pass


class AcousticEventResponse(AcousticEventFields):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
