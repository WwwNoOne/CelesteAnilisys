import type {
  ComparisonChangeStatus,
  ComparisonStatement,
} from './api';

export function isChronologicallyBefore(
  base: ComparisonStatement,
  comparison: ComparisonStatement,
): boolean {
  if (base.statement_type !== comparison.statement_type) return false;
  if (base.statement_type === 'BALANCE_GENERAL') {
    return Boolean(
      base.as_of_date
      && comparison.as_of_date
      && base.as_of_date < comparison.as_of_date,
    );
  }
  return Boolean(
    base.period_start
    && base.period_end
    && comparison.period_start
    && comparison.period_end
    && `${base.period_start}|${base.period_end}`
      < `${comparison.period_start}|${comparison.period_end}`,
  );
}

export function formatComparisonValue(
  value: number | null,
  currency: string,
): string {
  if (value === null) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatComparisonChange(
  value: number | null,
  status: ComparisonChangeStatus,
): string {
  if (status === 'NEW') return 'Nueva';
  if (status === 'REMOVED') return 'Ya no presente';
  if (status === 'UNCHANGED') return 'Sin cambio';
  if (status === 'NO_BASE' || value === null) return 'Sin base comparable';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}%`;
}
