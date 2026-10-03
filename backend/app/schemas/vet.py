import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.vet_verification import VetVerificationOutcome


class VetVerifyRequest(BaseModel):
    alert_id: uuid.UUID
    outcome: VetVerificationOutcome
    vet_identifier: str = Field(min_length=1, max_length=120)
    notes: str = Field(min_length=1, max_length=4000)


class VetVerificationResponse(BaseModel):
    verification_id: uuid.UUID
    alert_id: uuid.UUID
    verification_result: VetVerificationOutcome
    alert_status: str
    vet_identifier: str
    verified_at: datetime


class VetVerificationDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_id: uuid.UUID
    vet_identifier: str
    verification_status: VetVerificationOutcome
    assessment_notes: str
    verified_at: datetime
    created_at: datetime