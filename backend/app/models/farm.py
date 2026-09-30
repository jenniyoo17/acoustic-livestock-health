import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base


class Farm(Base):
    __tablename__ = "farms"
    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_farms_latitude"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_farms_longitude"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    owner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sheds: Mapped[list["Shed"]] = relationship(
        back_populates="farm", cascade="all, delete-orphan"
    )
