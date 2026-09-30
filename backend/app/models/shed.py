import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base


class AnimalType(str, enum.Enum):
    Cattle = "Cattle"
    Buffalo = "Buffalo"
    Goat = "Goat"
    Sheep = "Sheep"


class Shed(Base):
    __tablename__ = "sheds"
    __table_args__ = (
        CheckConstraint("capacity >= 0", name="ck_sheds_capacity_nonnegative"),
        CheckConstraint("current_count >= 0", name="ck_sheds_count_nonnegative"),
        CheckConstraint("current_count <= capacity", name="ck_sheds_count_within_capacity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farm_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shed_number: Mapped[str] = mapped_column(String(50), nullable=False)
    animal_type: Mapped[AnimalType] = mapped_column(
        Enum(AnimalType, name="animal_type_enum", values_callable=lambda members: [item.value for item in members]),
        nullable=False,
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    current_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    farm: Mapped["Farm"] = relationship(back_populates="sheds")
    devices: Mapped[list["Device"]] = relationship(
        back_populates="shed", cascade="all, delete-orphan"
    )
    acoustic_events: Mapped[list["AcousticEvent"]] = relationship(
        back_populates="shed", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="shed", cascade="all, delete-orphan"
    )
