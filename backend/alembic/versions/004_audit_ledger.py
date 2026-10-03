"""Add append-only SHA-256 audit ledger.

Revision ID: 004_audit_ledger
Revises: 003_vet_lab_workflow
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "004_audit_ledger"
down_revision: Union[str, None] = "003_vet_lab_workflow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_blocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("block_index", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_hash", sa.String(64), nullable=True),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("block_hash", sa.String(64), nullable=False),
        sa.Column("transition_key", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("block_index >= 0", name="ck_audit_blocks_nonnegative_index"),
        sa.CheckConstraint(
            "(block_index = 0 AND previous_hash IS NULL) OR "
            "(block_index > 0 AND previous_hash IS NOT NULL)",
            name="ck_audit_blocks_genesis_previous_hash",
        ),
        sa.UniqueConstraint("block_index", name="uq_audit_blocks_block_index"),
        sa.UniqueConstraint("block_hash", name="uq_audit_blocks_block_hash"),
        sa.UniqueConstraint("transition_key", name="uq_audit_blocks_transition_key"),
    )


def downgrade() -> None:
    op.drop_table("audit_blocks")