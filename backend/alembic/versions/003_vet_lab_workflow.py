"""Add veterinary verification and lab referrals.

Revision ID: 003_vet_lab_workflow
Revises: 002_escalation_records
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003_vet_lab_workflow"
down_revision: Union[str, None] = "002_escalation_records"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vet_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vet_identifier", sa.String(120), nullable=False),
        sa.Column(
            "verification_status",
            sa.Enum("Verified_Risk", "False_Positive", name="vet_verification_outcome_enum"),
            nullable=False,
        ),
        sa.Column("assessment_notes", sa.Text(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("alert_id", name="uq_vet_verifications_alert_id"),
    )

    op.create_table(
        "lab_referrals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("verification_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vet_verifications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sample_identifier", sa.String(120), nullable=False),
        sa.Column("requested_tests", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("Pending", "Sample_Collected", "In_Lab", "Result_Available", "Cancelled", name="lab_referral_status_enum"),
            nullable=False,
            server_default="Pending",
        ),
        sa.Column("referred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("result_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_demo_result", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("alert_id", name="uq_lab_referrals_alert_id"),
        sa.UniqueConstraint("verification_id", name="uq_lab_referrals_verification_id"),
    )
    op.create_index("ix_lab_referrals_status", "lab_referrals", ["status"])


def downgrade() -> None:
    op.drop_index("ix_lab_referrals_status", table_name="lab_referrals")
    op.drop_table("lab_referrals")
    op.drop_table("vet_verifications")
    sa.Enum(name="lab_referral_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="vet_verification_outcome_enum").drop(op.get_bind(), checkfirst=True)