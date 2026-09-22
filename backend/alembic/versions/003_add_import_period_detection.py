"""Store detected import period and validation state.

Revision ID: 003_add_import_period_detection
Revises: 002_add_import_storage_path
Create Date: 2026-09-21
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003_add_import_period_detection"
down_revision: str | Sequence[str] | None = "002_add_import_storage_path"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("financial_imports", sa.Column("detected_period_label", sa.String(length=50)))
    op.add_column("financial_imports", sa.Column("detected_period_year", sa.Integer()))
    op.add_column("financial_imports", sa.Column("detected_period_month", sa.Integer()))
    op.add_column("financial_imports", sa.Column("period_source", sa.String(length=30)))
    op.add_column("financial_imports", sa.Column("period_validated", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("financial_imports", sa.Column("period_conflict", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("financial_imports", "period_conflict")
    op.drop_column("financial_imports", "period_validated")
    op.drop_column("financial_imports", "period_source")
    op.drop_column("financial_imports", "detected_period_month")
    op.drop_column("financial_imports", "detected_period_year")
    op.drop_column("financial_imports", "detected_period_label")
