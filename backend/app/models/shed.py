import enum
import uuid
from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum as SQLEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.farm import Farm
    from app.models.device import Device
    from app.models.acoustic_event import AcousticEvent
    from app.models.alert import Alert


class AnimalType(str, enum.Enum):
    Cattle = "Cattle"
    Buffalo = "Buffalo"
    Goat = "Goat"
    Sheep = "Sheep"


class Shed(Base):
    __tablename__ = "sheds"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shed_number: Mapped[str] = mapped_column(String(50), nullable=False)
    animal_type: Mapped[AnimalType] = mapped_column(
        SQLEnum(AnimalType, name="animal_type_enum"), nullable=False
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    current_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    farm: Mapped["Farm"] = relationship("Farm", back_populates="sheds")
    devices: Mapped[List["Device"]] = relationship(
        "Device", back_populates="shed", cascade="all, delete-orphan"
    )
    acoustic_events: Mapped[List["AcousticEvent"]] = relationship(
        "AcousticEvent", back_populates="shed", cascade="all, delete-orphan"
    )
    alerts: Mapped[List["Alert"]] = relationship(
        "Alert", back_populates="shed", cascade="all, delete-orphan"
    )
