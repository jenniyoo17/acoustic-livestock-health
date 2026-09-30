import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.shed import AnimalType


class ShedBase(BaseModel):
    farm_id: uuid.UUID
    shed_number: str = Field(..., max_length=50)
    animal_type: AnimalType
    capacity: int = Field(..., gt=0)
    current_count: int = Field(..., ge=0)


class ShedCreate(ShedBase):
    pass


class ShedResponse(ShedBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
