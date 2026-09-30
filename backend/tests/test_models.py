from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.orm import configure_mappers

from app.db.base import Base
from app.models import (
    AcousticEvent,
    Alert,
    AlertStatus,
    AnimalType,
    AnomalySeverity,
    Device,
    DeviceStatus,
    EventType,
    Farm,
    Shed,
    SLATier,
)
from app.models.escalation_record import EscalationRecord


def test_model_imports_enums_and_relationships():
    configure_mappers()

    assert set(Base.metadata.tables) == {
        "farms",
        "sheds",
        "escalation_records",
        "devices",
        "acoustic_events",
        "alerts",
    }
    assert {item.value for item in AnimalType} == {"Cattle", "Buffalo", "Goat", "Sheep"}
    assert {item.value for item in DeviceStatus} == {"Online", "Offline", "Degraded"}
    assert {item.value for item in EventType} == {
        "Cough",
        "Distress_Call",
        "Abnormal_Rumination",
        "Environmental_Noise",
    }
    assert {item.value for item in AnomalySeverity} == {"Low", "Medium", "High", "Critical"}
    assert {item.value for item in AlertStatus} == {
        "Pending_Triage",
        "Escalated",
        "Under_Vet_Review",
        "Verified_Risk",
        "False_Positive",
        "Resolved",
    }
    assert {item.value for item in SLATier} == {
        "Tier_1_Farm_Owner",
        "Tier_2_Field_Vet",
        "Tier_3_District_Officer",
    }
    assert Farm.sheds.property.back_populates == "farm"
    assert Shed.devices.property.back_populates == "shed"
    assert Device.acoustic_events.property.back_populates == "device"
    assert AcousticEvent.alert.property.back_populates == "acoustic_event"
    assert Alert.shed.property.back_populates == "alerts"
    assert Alert.escalation_records.property.back_populates == "alert"
    assert EscalationRecord.alert.property.back_populates == "escalation_records"


def test_model_foreign_keys_and_check_constraints():
    assert any(
        isinstance(constraint, ForeignKeyConstraint)
        for constraint in Shed.__table__.constraints
    )
    assert any(
        isinstance(constraint, ForeignKeyConstraint)
        for constraint in AcousticEvent.__table__.constraints
    )
    event_checks = {
        str(constraint.sqltext)
        for constraint in AcousticEvent.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    shed_checks = {
        str(constraint.sqltext)
        for constraint in Shed.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "confidence_score >= 0 AND confidence_score <= 1" in event_checks
    assert "audio_duration_sec > 0" in event_checks
    assert "current_count <= capacity" in shed_checks
    device_unique_names = {
        constraint.name
        for constraint in Device.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    event_unique_names = {
        constraint.name
        for constraint in AcousticEvent.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert "uq_devices_device_uid" in device_unique_names
    assert "uq_acoustic_events_idempotency_key" in event_unique_names
