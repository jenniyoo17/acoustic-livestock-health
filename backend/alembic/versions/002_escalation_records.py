"""Add alert escalation history.

Revision ID: 002_escalation_records
Revises: 001_initial_schema
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002_escalation_records"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    sla_tier = postgresql.ENUM(
        "Tier_1_Farm_Owner",
        "Tier_2_Field_Vet",
        "Tier_3_District_Officer",
        name="sla_tier_enum",
        create_type=False,
    )
    op.create_table(
        "escalation_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_tier", sla_tier, nullable=True),
        sa.Column("to_tier", sla_tier, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_escalation_records_alert_id", "escalation_records", ["alert_id"])
    op.create_index(
        "ix_escalation_records_alert_created",
        "escalation_records",
        ["alert_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_escalation_records_alert_created", table_name="escalation_records")
    op.drop_index("ix_escalation_records_alert_id", table_name="escalation_records")
    op.drop_table("escalation_records")