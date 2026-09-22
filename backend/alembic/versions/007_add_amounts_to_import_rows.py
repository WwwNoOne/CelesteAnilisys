"""Add opening_balance, debits, credits, ending_balance to import_rows.

Revision ID: 007_add_amounts_to_import_rows
Revises: 006_add_temporal_metadata
Create Date: 2026-09-21
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "007_add_amounts_to_import_rows"
down_revision: str | Sequence[str] | None = "006_add_temporal_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("import_rows", sa.Column("opening_balance", sa.Numeric(precision=18, scale=2), nullable=True))
    op.add_column("import_rows", sa.Column("debits", sa.Numeric(precision=18, scale=2), nullable=True))
    op.add_column("import_rows", sa.Column("credits", sa.Numeric(precision=18, scale=2), nullable=True))
    op.add_column("import_rows", sa.Column("ending_balance", sa.Numeric(precision=18, scale=2), nullable=True))


def downgrade() -> None:
    op.drop_column("import_rows", "ending_balance")
    op.drop_column("import_rows", "credits")
    op.drop_column("import_rows", "debits")
    op.drop_column("import_rows", "opening_balance")
