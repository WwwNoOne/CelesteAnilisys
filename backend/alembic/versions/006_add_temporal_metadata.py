"""Add temporal metadata (as_of_date, period_start, period_end, timeframe, statement_type) to periods and financial_imports.

Revision ID: 006_add_temporal_metadata
Revises: 005_add_row_classification
Create Date: 2026-09-21
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "006_add_temporal_metadata"
down_revision: str | Sequence[str] | None = "005_add_row_classification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add columns to periods
    op.add_column("periods", sa.Column("statement_type", sa.String(length=50), nullable=True))
    op.add_column("periods", sa.Column("as_of_date", sa.Date(), nullable=True))
    op.add_column("periods", sa.Column("period_start", sa.Date(), nullable=True))
    op.add_column("periods", sa.Column("period_end", sa.Date(), nullable=True))
    op.add_column("periods", sa.Column("timeframe", sa.String(length=30), nullable=True))

    # Add columns to financial_imports
    op.add_column("financial_imports", sa.Column("detected_statement_type", sa.String(length=50), nullable=True))
    op.add_column("financial_imports", sa.Column("detected_as_of_date", sa.Date(), nullable=True))
    op.add_column("financial_imports", sa.Column("detected_period_start", sa.Date(), nullable=True))
    op.add_column("financial_imports", sa.Column("detected_period_end", sa.Date(), nullable=True))
    op.add_column("financial_imports", sa.Column("detected_timeframe", sa.String(length=30), nullable=True))


def downgrade() -> None:
    op.drop_column("financial_imports", "detected_timeframe")
    op.drop_column("financial_imports", "detected_period_end")
    op.drop_column("financial_imports", "detected_period_start")
    op.drop_column("financial_imports", "detected_as_of_date")
    op.drop_column("financial_imports", "detected_statement_type")

    op.drop_column("periods", "timeframe")
    op.drop_column("periods", "period_end")
    op.drop_column("periods", "period_start")
    op.drop_column("periods", "as_of_date")
    op.drop_column("periods", "statement_type")
