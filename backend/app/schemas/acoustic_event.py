import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.acoustic_event import EventType


class AcousticEventBase(BaseModel):
    device_id: uuid.UUID
    shed_id: uuid.UUID
    event_type: EventType
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    yamnet_embedding_vector: List[float]
    audio_duration_sec: float = Field(..., gt=0.0)
    audio_snippet_url: Optional[str] = None
    recorded_at: datetime
    is_synced_offline: bool = False


class AcousticEventCreate(AcousticEventBase):
    pass


class AcousticEventResponse(AcousticEventBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
