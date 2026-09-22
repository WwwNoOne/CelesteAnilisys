import calendar
import re
from datetime import date
from pathlib import Path

from app.schemas.import_analysis import SheetSnapshot
from app.schemas.period_detection import PeriodDetection

YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")

SPANISH_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

_MONTH_REGEX = "|".join(SPANISH_MONTHS.keys())

RANGE_TEXT_RE = re.compile(
    rf"del?\s+(\d{{1,2}})\s+(?:de\s+)?({_MONTH_REGEX})\s+(?:de\s+)?(?:(\d{{4}})\s+)?al\s+(\d{{1,2}})\s+(?:de\s+)?({_MONTH_REGEX})\s+(?:de\s+)?(\d{{4}})",
    re.IGNORECASE,
)

RANGE_NUM_RE = re.compile(
    r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\s*(?:al|a|-)\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})",
    re.IGNORECASE,
)

AS_OF_TEXT_RE = re.compile(
    rf"al?\s+(\d{{1,2}})\s+(?:de\s+)?({_MONTH_REGEX})\s+(?:de\s+)?(\d{{4}})",
    re.IGNORECASE,
)

AS_OF_NUM_RE = re.compile(
    r"al?\s+(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})",
    re.IGNORECASE,
)

MONTH_YEAR_RE = re.compile(
    rf"mes\s+de\s+({_MONTH_REGEX})\s+de\s+(\d{{4}})",
    re.IGNORECASE,
)


def parse_statement_dates(text: str) -> dict:
    """Extract period_start, period_end, as_of_date and timeframe from Spanish financial headers."""
    clean_text = " ".join(text.split())

    # 1. Range text: del 1 de enero al 31 de diciembre de 2025
    m_range = RANGE_TEXT_RE.search(clean_text)
    if m_range:
        d1, m1_str, y1, d2, m2_str, y2 = m_range.groups()
        year1 = int(y1) if y1 else int(y2)
        year2 = int(y2)
        start = date(year1, SPANISH_MONTHS[m1_str.lower()], int(d1))
        end = date(year2, SPANISH_MONTHS[m2_str.lower()], int(d2))
        return {
            "period_start": start,
            "period_end": end,
            "as_of_date": end,
            "timeframe": classify_range_timeframe(start, end),
            "year": end.year,
            "month": end.month,
            "date_label": f"{start.strftime('%d/%m/%Y')} — {end.strftime('%d/%m/%Y')}",
        }

    # 2. Range numeric: del 01/01/2025 al 31/12/2025
    m_num_range = RANGE_NUM_RE.search(clean_text)
    if m_num_range:
        d1, m1, y1, d2, m2, y2 = m_num_range.groups()
        start = date(int(y1), int(m1), int(d1))
        end = date(int(y2), int(m2), int(d2))
        return {
            "period_start": start,
            "period_end": end,
            "as_of_date": end,
            "timeframe": classify_range_timeframe(start, end),
            "year": end.year,
            "month": end.month,
            "date_label": f"{start.strftime('%d/%m/%Y')} — {end.strftime('%d/%m/%Y')}",
        }

    # 3. As of text: al 31 de diciembre de 2025
    m_as_of = AS_OF_TEXT_RE.search(clean_text)
    if m_as_of:
        d, m_str, y = m_as_of.groups()
        as_of = date(int(y), SPANISH_MONTHS[m_str.lower()], int(d))
        return {
            "period_start": None,
            "period_end": None,
            "as_of_date": as_of,
            "timeframe": classify_as_of_timeframe(as_of),
            "year": as_of.year,
            "month": as_of.month,
            "date_label": f"Al {as_of.strftime('%d/%m/%Y')}",
        }

    # 4. As of numeric: al 31/12/2025
    m_as_of_num = AS_OF_NUM_RE.search(clean_text)
    if m_as_of_num:
        d, m, y = m_as_of_num.groups()
        as_of = date(int(y), int(m), int(d))
        return {
            "period_start": None,
            "period_end": None,
            "as_of_date": as_of,
            "timeframe": classify_as_of_timeframe(as_of),
            "year": as_of.year,
            "month": as_of.month,
            "date_label": f"Al {as_of.strftime('%d/%m/%Y')}",
        }

    # 5. Month of year: mes de diciembre de 2025
    m_month_year = MONTH_YEAR_RE.search(clean_text)
    if m_month_year:
        m_str, y = m_month_year.groups()
        month = SPANISH_MONTHS[m_str.lower()]
        year = int(y)
        last_day = calendar.monthrange(year, month)[1]
        as_of = date(year, month, last_day)
        start = date(year, month, 1)
        return {
            "period_start": start,
            "period_end": as_of,
            "as_of_date": as_of,
            "timeframe": "MONTHLY",
            "year": year,
            "month": month,
            "date_label": f"{start.strftime('%d/%m/%Y')} — {as_of.strftime('%d/%m/%Y')}",
        }

    return {}


def classify_range_timeframe(start: date, end: date) -> str:
    if start.month == 1 and start.day == 1 and end.month == 12 and end.day == 31:
        return "ANNUAL"
    if start.month == end.month and start.year == end.year and start.day == 1 and end.day >= 28:
        return "MONTHLY"
    if start.day == 1 and end.day >= 30 and (end.month - start.month == 2):
        return "QUARTERLY"
    if start.month == 1 and start.day == 1 and not (end.month == 12 and end.day == 31):
        return "YTD"
    return "CUSTOM_RANGE"


def classify_as_of_timeframe(as_of: date) -> str:
    if as_of.month == 12 and as_of.day == 31:
        return "YEAR_END"
    if as_of.month in (3, 6, 9) and as_of.day in (30, 31):
        return "QUARTER_END"
    if as_of.day >= 28:
        return "MONTH_END"
    return "CUSTOM_DATE"


def detect_sheet_temporal_info(sheet: SheetSnapshot) -> dict:
    """Extract statement type and temporal bounds from a single sheet."""
    for row in sheet.rows[:10]:
        for val in row[:10]:
            if isinstance(val, str) and val.strip():
                parsed = parse_statement_dates(val)
                if parsed:
                    parsed["source"] = "sheet_title"
                    return parsed

    # Fallback to year in sheet name
    sheet_years = _years_from_values([sheet.name])
    if sheet_years:
        year = next(iter(sheet_years))
        return {
            "year": year,
            "month": None,
            "as_of_date": date(year, 12, 31),
            "period_start": date(year, 1, 1),
            "period_end": date(year, 12, 31),
            "timeframe": "ANNUAL",
            "date_label": str(year),
            "source": "sheet_name",
        }
    return {}


def detect_period(file_name: str, sheets: list[SheetSnapshot]) -> PeriodDetection:
    # 1. Check conflicts in sheet names
    sheet_name_years = _years_from_values(sheet.name for sheet in sheets)
    if len(sheet_name_years) > 1:
        return PeriodDetection(conflict=True, source="sheet_name")

    # 2. Check dates inside sheets
    sheet_dates: list[dict] = []
    for s in sheets:
        info = detect_sheet_temporal_info(s)
        if info:
            sheet_dates.append(info)

    years_in_content = {d["year"] for d in sheet_dates if d.get("year")}
    if len(years_in_content) > 1:
        return PeriodDetection(conflict=True, source="sheet_title")

    if sheet_dates:
        primary = sheet_dates[0]
        return PeriodDetection(
            label=primary.get("date_label") or str(primary.get("year")),
            year=primary.get("year"),
            month=primary.get("month"),
            source=primary.get("source", "sheet_title"),
            confidence=0.95,
            as_of_date=primary.get("as_of_date"),
            period_start=primary.get("period_start"),
            period_end=primary.get("period_end"),
            timeframe=primary.get("timeframe"),
        )

    if sheet_name_years:
        year = next(iter(sheet_name_years))
        return PeriodDetection(
            label=str(year),
            year=year,
            source="sheet_name",
            confidence=0.98,
            as_of_date=date(year, 12, 31),
            period_start=date(year, 1, 1),
            period_end=date(year, 12, 31),
            timeframe="ANNUAL",
        )

    file_years = _years_from_values([Path(file_name).stem])
    if file_years:
        year = next(iter(file_years))
        return PeriodDetection(
            label=str(year),
            year=year,
            source="file_name",
            confidence=0.75,
            as_of_date=date(year, 12, 31),
            period_start=date(year, 1, 1),
            period_end=date(year, 12, 31),
            timeframe="ANNUAL",
        )

    return PeriodDetection()


def _years_from_values(values) -> set[int]:
    years: set[int] = set()
    for value in values:
        years.update(int(match) for match in YEAR_PATTERN.findall(value))
    return years
