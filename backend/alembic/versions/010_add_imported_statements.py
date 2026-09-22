"""Add independently reviewed statements for workbook sheets.

Revision ID: 010_imported_statements
Revises: 009_canonical_accounting
Create Date: 2026-09-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "010_imported_statements"
down_revision: str | Sequence[str] | None = "009_canonical_accounting"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("financial_imports", "period_id", existing_type=sa.Integer(), nullable=True)
    op.create_table(
        "imported_statements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_import_id", sa.Integer(), sa.ForeignKey("financial_imports.id"), nullable=False),
        sa.Column("sheet_name", sa.String(length=200), nullable=False),
        sa.Column("source_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("statement_type", sa.String(length=50)),
        sa.Column("detection_confidence", sa.Numeric(5, 4)),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING_REVIEW"),
        sa.Column("discard_reason", sa.String(length=300)),
        sa.Column("period_id", sa.Integer(), sa.ForeignKey("periods.id")),
        sa.Column("detected_period_label", sa.String(length=50)),
        sa.Column("detected_period_year", sa.Integer()),
        sa.Column("detected_period_month", sa.Integer()),
        sa.Column("period_source", sa.String(length=30)),
        sa.Column("period_validated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("period_conflict", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("detected_as_of_date", sa.Date()),
        sa.Column("detected_period_start", sa.Date()),
        sa.Column("detected_period_end", sa.Date()),
        sa.Column("detected_timeframe", sa.String(length=30)),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recognized_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("review_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unknown_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("source_import_id", "sheet_name", name="uq_imported_statement_sheet"),
    )
    op.add_column("import_rows", sa.Column("imported_statement_id", sa.Integer(), nullable=True))
    op.add_column("import_rows", sa.Column("source_text_column", sa.Integer(), nullable=True))
    op.add_column("import_rows", sa.Column("source_amount_column", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_import_rows_statement", "import_rows", "imported_statements",
        ["imported_statement_id"], ["id"],
    )
    op.add_column("account_balances", sa.Column("imported_statement_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_account_balances_statement", "account_balances", "imported_statements",
        ["imported_statement_id"], ["id"],
    )

    op.execute(sa.text("""
        INSERT INTO imported_statements (
            source_import_id, sheet_name, source_order, statement_type, status,
            period_id, detected_period_label, detected_period_year,
            detected_period_month, period_source, period_validated,
            period_conflict, detected_as_of_date, detected_period_start,
            detected_period_end, detected_timeframe, total_rows,
            recognized_rows, review_rows, unknown_rows, error_rows
        )
        SELECT
            ir.source_import_id, ir.source_sheet,
            ROW_NUMBER() OVER (PARTITION BY ir.source_import_id ORDER BY MIN(ir.id)) - 1,
            fi.detected_statement_type,
            CASE WHEN fi.status = 'APPROVED' THEN 'APPROVED' ELSE 'PENDING_REVIEW' END,
            fi.period_id, fi.detected_period_label, fi.detected_period_year,
            fi.detected_period_month, fi.period_source, fi.period_validated,
            fi.period_conflict, fi.detected_as_of_date, fi.detected_period_start,
            fi.detected_period_end, fi.detected_timeframe, COUNT(ir.id),
            SUM(CASE WHEN ir.status = 'MATCHED' THEN 1 ELSE 0 END),
            SUM(CASE WHEN ir.status = 'NEEDS_REVIEW' THEN 1 ELSE 0 END),
            SUM(CASE WHEN ir.status = 'UNKNOWN' THEN 1 ELSE 0 END),
            SUM(CASE WHEN ir.status = 'ERROR' THEN 1 ELSE 0 END)
        FROM import_rows ir
        JOIN financial_imports fi ON fi.id = ir.source_import_id
        GROUP BY ir.source_import_id, ir.source_sheet, fi.id
    """))
    op.execute(sa.text("""
        UPDATE import_rows ir
        SET imported_statement_id = statement.id
        FROM imported_statements statement
        WHERE statement.source_import_id = ir.source_import_id
          AND statement.sheet_name = ir.source_sheet
    """))
    op.execute(sa.text("""
        UPDATE account_balances balance
        SET imported_statement_id = statement.id
        FROM imported_statements statement
        WHERE statement.source_import_id = balance.source_import_id
          AND statement.sheet_name = balance.source_sheet
    """))


def downgrade() -> None:
    op.drop_constraint("fk_account_balances_statement", "account_balances", type_="foreignkey")
    op.drop_column("account_balances", "imported_statement_id")
    op.drop_constraint("fk_import_rows_statement", "import_rows", type_="foreignkey")
    op.drop_column("import_rows", "source_amount_column")
    op.drop_column("import_rows", "source_text_column")
    op.drop_column("import_rows", "imported_statement_id")
    op.drop_table("imported_statements")
    op.alter_column("financial_imports", "period_id", existing_type=sa.Integer(), nullable=False)
