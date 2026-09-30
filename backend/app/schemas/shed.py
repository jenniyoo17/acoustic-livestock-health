import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.shed import AnimalType


class ShedFields(BaseModel):
    farm_id: uuid.UUID
    shed_number: str = Field(min_length=1, max_length=50)
    animal_type: AnimalType
    capacity: int = Field(ge=0)
    current_count: int = Field(ge=0)

    @model_validator(mode="after")
    def current_count_within_capacity(self):
        if self.current_count > self.capacity:
            raise ValueError("current_count cannot exceed capacity")
        return self


class ShedCreate(ShedFields):
    pass


class ShedResponse(ShedFields):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
