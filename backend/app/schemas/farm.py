import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class FarmBase(BaseModel):
    name: str = Field(..., max_length=255)
    owner_name: str = Field(..., max_length=255)
    contact_phone: str = Field(..., max_length=50)
    latitude: float
    longitude: float
    district: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)


class FarmCreate(FarmBase):
    pass


class FarmResponse(FarmBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
