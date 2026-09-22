"""Add canonical account roles and authoritative balance markers.

Revision ID: 009_canonical_accounting
Revises: 008_add_approved_sheets
Create Date: 2026-09-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "009_canonical_accounting"
down_revision: str | Sequence[str] | None = "008_add_approved_sheets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("canonical_role", sa.String(length=40), nullable=True))
    op.add_column(
        "account_balances",
        sa.Column(
            "is_authoritative",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("account_balances", "is_authoritative")
    op.drop_column("accounts", "canonical_role")
