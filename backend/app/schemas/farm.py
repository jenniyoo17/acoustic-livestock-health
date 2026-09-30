import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FarmFields(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    owner_name: str = Field(min_length=1, max_length=255)
    contact_phone: str = Field(min_length=1, max_length=50)
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    district: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)


class FarmCreate(FarmFields):
    pass


class FarmResponse(FarmFields):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
