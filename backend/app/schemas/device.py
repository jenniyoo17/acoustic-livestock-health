import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.device import DeviceStatus


class DeviceFields(BaseModel):
    shed_id: uuid.UUID
    device_uid: str = Field(min_length=1, max_length=100)
    firmware_version: str = Field(default="0.1.0", max_length=50)
    status: DeviceStatus = DeviceStatus.Online
    public_key: str | None = Field(default=None, max_length=512)


class DeviceCreate(DeviceFields):
    pass


class DeviceResponse(DeviceFields):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    last_heartbeat_at: datetime | None = None
    created_at: datetime
