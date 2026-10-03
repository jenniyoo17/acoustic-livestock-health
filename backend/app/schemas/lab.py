import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.lab_referral import LabReferralStatus
from app.schemas.alert import AlertResponse
from app.schemas.vet import VetVerificationDetail


class LabReferralCreate(BaseModel):
    alert_id: uuid.UUID
    sample_identifier: str = Field(min_length=1, max_length=120)
    requested_tests: list[str] = Field(min_length=1, max_length=20)
    notes: str = Field(default="", max_length=4000)

    @field_validator("requested_tests")
    @classmethod
    def requested_tests_must_be_nonempty(cls, tests: list[str]) -> list[str]:
        cleaned = [test.strip() for test in tests]
        if any(not test for test in cleaned):
            raise ValueError("Requested test names must not be empty")
        return cleaned


class LabStatusUpdate(BaseModel):
    status: LabReferralStatus
    result: str | None = Field(default=None, min_length=1, max_length=4000)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("result")
    @classmethod
    def result_must_contain_text(cls, result: str | None) -> str | None:
        if result is not None:
            result = result.strip()
            if not result:
                raise ValueError("Demo result must contain non-whitespace text")
        return result


class LabReferralResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_id: uuid.UUID
    verification_id: uuid.UUID
    sample_identifier: str
    requested_tests: list[str]
    status: LabReferralStatus
    referred_at: datetime
    result: str | None
    result_at: datetime | None
    notes: str
    is_demo_result: bool
    created_at: datetime


class LabReferralDetail(BaseModel):
    referral: LabReferralResponse
    alert: AlertResponse
    verification: VetVerificationDetail