from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import ImportStatus

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.import_row import ImportRow
    from app.models.period import Period


class FinancialImport(Base):
    __tablename__ = "financial_imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(300), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[ImportStatus] = mapped_column(
        Enum(ImportStatus, native_enum=False), nullable=False, default=ImportStatus.UPLOADED
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recognized_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_accounts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    company: Mapped["Company"] = relationship(back_populates="imports")
    period: Mapped["Period"] = relationship(back_populates="imports")
    rows: Mapped[list["ImportRow"]] = relationship(back_populates="source_import")
