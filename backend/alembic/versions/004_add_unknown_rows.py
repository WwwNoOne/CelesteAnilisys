"""Add unknown_rows counter to financial_imports.

Revision ID: 004_add_unknown_rows
Revises: 003_add_import_period_detection
Create Date: 2026-09-21
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "004_add_unknown_rows"
down_revision: str | Sequence[str] | None = "003_add_import_period_detection"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "financial_imports",
        sa.Column("unknown_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("financial_imports", "unknown_rows")
