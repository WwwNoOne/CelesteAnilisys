"""Add row_classification to import_rows.

Revision ID: 005_add_row_classification
Revises: 004_add_unknown_rows
Create Date: 2026-09-21
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "005_add_row_classification"
down_revision: str | Sequence[str] | None = "004_add_unknown_rows"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "import_rows",
        sa.Column(
            "row_classification",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'CUENTA'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("import_rows", "row_classification")
