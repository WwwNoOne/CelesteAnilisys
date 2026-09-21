"""Add import file storage path.

Revision ID: 002_add_import_storage_path
Revises: 001_initial_import_models
Create Date: 2026-09-21
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002_add_import_storage_path"
down_revision: str | Sequence[str] | None = "001_initial_import_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("financial_imports", sa.Column("storage_path", sa.String(length=500)))


def downgrade() -> None:
    op.drop_column("financial_imports", "storage_path")
