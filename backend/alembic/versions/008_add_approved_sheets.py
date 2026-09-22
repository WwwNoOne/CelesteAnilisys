"""Track sheets persisted from each financial import.

Revision ID: 008_add_approved_sheets
Revises: 007_add_amounts_to_import_rows
Create Date: 2026-09-21
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "008_add_approved_sheets"
down_revision: str | Sequence[str] | None = "007_add_amounts_to_import_rows"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "financial_imports",
        sa.Column("approved_sheets", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )


def downgrade() -> None:
    op.drop_column("financial_imports", "approved_sheets")
