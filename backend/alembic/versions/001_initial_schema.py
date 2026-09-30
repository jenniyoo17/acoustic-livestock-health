"""Create core livestock acoustics schema.

Revision ID: 001_initial_schema
Revises:
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "farms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("owner_name", sa.String(255), nullable=False),
        sa.Column("contact_phone", sa.String(50), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("district", sa.String(100), nullable=False),
        sa.Column("state", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_farms_latitude"),
        sa.CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_farms_longitude"),
    )
    op.create_index("ix_farms_name", "farms", ["name"])
    op.create_index("ix_farms_district", "farms", ["district"])
    op.create_index("ix_farms_state", "farms", ["state"])

    op.create_table(
        "sheds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("farm_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shed_number", sa.String(50), nullable=False),
        sa.Column("animal_type", sa.Enum("Cattle", "Buffalo", "Goat", "Sheep", name="animal_type_enum"), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("current_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("capacity >= 0", name="ck_sheds_capacity_nonnegative"),
        sa.CheckConstraint("current_count >= 0", name="ck_sheds_count_nonnegative"),
        sa.CheckConstraint("current_count <= capacity", name="ck_sheds_count_within_capacity"),
    )
    op.create_index("ix_sheds_farm_id", "sheds", ["farm_id"])

    op.create_table(
        "devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("shed_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sheds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_uid", sa.String(100), nullable=False),
        sa.Column("firmware_version", sa.String(50), server_default="0.1.0", nullable=False),
        sa.Column("status", sa.Enum("Online", "Offline", "Degraded", name="device_status_enum"), server_default="Online", nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("public_key", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("device_uid", name="uq_devices_device_uid"),
    )
    op.create_index("ix_devices_shed_id", "devices", ["shed_id"])

    op.create_table(
        "acoustic_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shed_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sheds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.Enum("Cough", "Distress_Call", "Abnormal_Rumination", "Environmental_Noise", name="event_type_enum"), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("yamnet_embedding_vector", sa.JSON(), nullable=False),
        sa.Column("audio_duration_sec", sa.Float(), nullable=False),
        sa.Column("audio_snippet_url", sa.String(512), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_synced_offline", sa.Boolean(), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("confidence_score >= 0 AND confidence_score <= 1", name="ck_acoustic_events_confidence_range"),
        sa.CheckConstraint("audio_duration_sec > 0", name="ck_acoustic_events_duration_positive"),
        sa.UniqueConstraint("idempotency_key", name="uq_acoustic_events_idempotency_key"),
    )
    op.create_index("ix_acoustic_events_device_id", "acoustic_events", ["device_id"])
    op.create_index("ix_acoustic_events_shed_id", "acoustic_events", ["shed_id"])
    op.create_index("ix_acoustic_events_event_type", "acoustic_events", ["event_type"])
    op.create_index("ix_acoustic_events_recorded_at", "acoustic_events", ["recorded_at"])
    op.create_index("ix_acoustic_events_shed_recorded", "acoustic_events", ["shed_id", "recorded_at"])

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("acoustic_event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("acoustic_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shed_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sheds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("anomaly_severity", sa.Enum("Low", "Medium", "High", "Critical", name="anomaly_severity_enum"), nullable=False),
        sa.Column("status", sa.Enum("Pending_Triage", "Escalated", "Under_Vet_Review", "Verified_Risk", "False_Positive", "Resolved", name="alert_status_enum"), server_default="Pending_Triage", nullable=False),
        sa.Column("current_sla_tier", sa.Enum("Tier_1_Farm_Owner", "Tier_2_Field_Vet", "Tier_3_District_Officer", name="sla_tier_enum"), server_default="Tier_1_Farm_Owner", nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("acoustic_event_id", name="uq_alerts_acoustic_event_id"),
    )
    op.create_index("ix_alerts_shed_id", "alerts", ["shed_id"])
    op.create_index("ix_alerts_anomaly_severity", "alerts", ["anomaly_severity"])
    op.create_index("ix_alerts_status", "alerts", ["status"])
    op.create_index("ix_alerts_triggered_at", "alerts", ["triggered_at"])


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_index("ix_acoustic_events_shed_recorded", table_name="acoustic_events")
    op.drop_table("acoustic_events")
    op.drop_table("devices")
    op.drop_table("sheds")
    op.drop_table("farms")
    for enum_name in (
        "sla_tier_enum",
        "alert_status_enum",
        "anomaly_severity_enum",
        "event_type_enum",
        "device_status_enum",
        "animal_type_enum",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
