"""Create initial import and accounting models.

Revision ID: 001_initial_import_models
Revises:
Create Date: 2026-09-18
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "001_initial_import_models"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    account_type = sa.Enum(
        "ACTIVO", "PASIVO", "PATRIMONIO", "INGRESO", "COSTO", "GASTO", "OTRO",
        name="accounttype", native_enum=False,
    )
    account_nature = sa.Enum("DEUDORA", "ACREEDORA", "OTRA", name="accountnature", native_enum=False)
    financial_statement = sa.Enum(
        "BALANCE_COMPROBACION", "ESTADO_SITUACION_FINANCIERA", "ESTADO_RESULTADOS",
        "FLUJO_EFECTIVO", "DESCONOCIDO", name="financialstatement", native_enum=False,
    )
    import_status = sa.Enum(
        "UPLOADED", "ANALYZING", "READY_FOR_REVIEW", "APPROVED", "IMPORTED", "FAILED",
        name="importstatus", native_enum=False,
    )
    match_type = sa.Enum(
        "EXACT_CODE", "CODE_AND_NAME", "NORMALIZED_NAME", "ALIAS", "CONTEXT", "FUZZY", "NONE",
        name="matchtype", native_enum=False,
    )
    row_status = sa.Enum(
        "MATCHED", "NEEDS_REVIEW", "UNKNOWN", "NEW_ACCOUNT", "ERROR", "IGNORED",
        name="rowstatus", native_enum=False,
    )

    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
    )
    op.create_table(
        "periods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("label", sa.String(length=50), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
    )
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("normalized_name", sa.String(length=300), nullable=False),
        sa.Column("account_type", account_type, nullable=False),
        sa.Column("nature", account_nature, nullable=False),
        sa.Column("level", sa.Integer()),
        sa.Column("parent_code", sa.String(length=64)),
        sa.Column("financial_statement", financial_statement, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "code", name="uq_accounts_company_code"),
    )
    op.create_table(
        "financial_imports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("period_id", sa.Integer(), sa.ForeignKey("periods.id"), nullable=False),
        sa.Column("file_name", sa.String(length=300), nullable=False),
        sa.Column("status", import_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recognized_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("review_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_accounts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_rows", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "account_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("alias", sa.String(length=300), nullable=False),
        sa.Column("normalized_alias", sa.String(length=300), nullable=False),
    )
    op.create_table(
        "import_rows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_import_id", sa.Integer(), sa.ForeignKey("financial_imports.id"), nullable=False),
        sa.Column("source_sheet", sa.String(length=200), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("original_code", sa.String(length=64)),
        sa.Column("original_name", sa.String(length=300)),
        sa.Column("normalized_name", sa.String(length=300)),
        sa.Column("matched_account_id", sa.Integer(), sa.ForeignKey("accounts.id")),
        sa.Column("match_type", match_type, nullable=False),
        sa.Column("confidence", sa.Numeric(5, 2)),
        sa.Column("status", row_status, nullable=False),
    )
    op.create_table(
        "account_balances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("period_id", sa.Integer(), sa.ForeignKey("periods.id"), nullable=False),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("source_import_id", sa.Integer(), sa.ForeignKey("financial_imports.id"), nullable=False),
        sa.Column("opening_balance", sa.Numeric(18, 2)),
        sa.Column("debits", sa.Numeric(18, 2)),
        sa.Column("credits", sa.Numeric(18, 2)),
        sa.Column("ending_balance", sa.Numeric(18, 2)),
        sa.Column("source_sheet", sa.String(length=200), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "company_id", "period_id", "account_id", name="uq_balances_company_period_account"
        ),
    )


def downgrade() -> None:
    op.drop_table("account_balances")
    op.drop_table("import_rows")
    op.drop_table("account_aliases")
    op.drop_table("financial_imports")
    op.drop_table("accounts")
    op.drop_table("periods")
    op.drop_table("companies")
