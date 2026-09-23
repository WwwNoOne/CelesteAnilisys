"""Add is_generated flag to import_rows.

Revision ID: 011_add_generated_rows
Revises: 010_imported_statements
Create Date: 2026-09-22
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "011_add_generated_rows"
down_revision: str | Sequence[str] | None = "010_imported_statements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "import_rows",
        sa.Column("is_generated", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("import_rows", "is_generated")
