import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.device import DeviceStatus


class DeviceBase(BaseModel):
    shed_id: uuid.UUID
    device_uid: str = Field(..., max_length=100)
    firmware_version: str = Field(default="0.1.0", max_length=50)
    status: DeviceStatus = Field(default=DeviceStatus.Online)
    public_key: Optional[str] = None


class DeviceCreate(DeviceBase):
    pass


class DeviceResponse(DeviceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    last_heartbeat_at: Optional[datetime] = None
    created_at: datetime
