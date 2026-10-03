import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditBlockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    block_index: int
    timestamp: datetime
    previous_hash: str | None
    entity_type: str
    entity_id: str
    payload_hash: str
    block_hash: str


class AuditIntegrityResponse(BaseModel):
    valid: bool
    checked_blocks: int
    error: str | None = None
