from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import StatementImportStatus

if TYPE_CHECKING:
    from app.models.account_balance import AccountBalance
    from app.models.financial_import import FinancialImport
    from app.models.import_row import ImportRow
    from app.models.period import Period


class ImportedStatement(Base):
    __tablename__ = "imported_statements"
    __table_args__ = (
        UniqueConstraint("source_import_id", "sheet_name", name="uq_imported_statement_sheet"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_import_id: Mapped[int] = mapped_column(
        ForeignKey("financial_imports.id"), nullable=False
    )
    sheet_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    statement_type: Mapped[str | None] = mapped_column(String(50))
    detection_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    status: Mapped[StatementImportStatus] = mapped_column(
        Enum(StatementImportStatus, native_enum=False),
        nullable=False,
        default=StatementImportStatus.PENDING_REVIEW,
    )
    discard_reason: Mapped[str | None] = mapped_column(String(300))
    period_id: Mapped[int | None] = mapped_column(ForeignKey("periods.id"))
    detected_period_label: Mapped[str | None] = mapped_column(String(50))
    detected_period_year: Mapped[int | None] = mapped_column(Integer)
    detected_period_month: Mapped[int | None] = mapped_column(Integer)
    period_source: Mapped[str | None] = mapped_column(String(30))
    period_validated: Mapped[bool] = mapped_column(nullable=False, default=False)
    period_conflict: Mapped[bool] = mapped_column(nullable=False, default=False)
    detected_as_of_date: Mapped[date | None] = mapped_column(Date)
    detected_period_start: Mapped[date | None] = mapped_column(Date)
    detected_period_end: Mapped[date | None] = mapped_column(Date)
    detected_timeframe: Mapped[str | None] = mapped_column(String(30))
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recognized_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unknown_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    source_import: Mapped["FinancialImport"] = relationship(back_populates="statements")
    period: Mapped["Period | None"] = relationship()
    rows: Mapped[list["ImportRow"]] = relationship(back_populates="imported_statement")
    balances: Mapped[list["AccountBalance"]] = relationship(
        back_populates="imported_statement"
    )
