import { describe, expect, it } from 'vitest';
import type { ComparisonStatement } from '../../src/renderer/api';
import {
  formatComparisonChange,
  formatComparisonValue,
  isChronologicallyBefore,
} from '../../src/renderer/comparison-state';

function balance(asOfDate: string): ComparisonStatement {
  return {
    period_id: Number(asOfDate.replaceAll('-', '')),
    statement_type: 'BALANCE_GENERAL',
    label: asOfDate,
    as_of_date: asOfDate,
    period_start: null,
    period_end: null,
    duration_days: null,
  };
}

function results(start: string, end: string): ComparisonStatement {
  return {
    period_id: Number(end.replaceAll('-', '')),
    statement_type: 'ESTADO_RESULTADOS',
    label: `${start} — ${end}`,
    as_of_date: null,
    period_start: start,
    period_end: end,
    duration_days: 365,
  };
}

describe('comparison state', () => {
  it('orders balances by as-of date and results by interval', () => {
    expect(
      isChronologicallyBefore(balance('2024-12-31'), balance('2025-12-31')),
    ).toBe(true);
    expect(
      isChronologicallyBefore(
        results('2025-01-01', '2025-03-31'),
        results('2024-01-01', '2024-12-31'),
      ),
    ).toBe(false);
  });

  it('formats every non-numeric percentage state explicitly', () => {
    expect(formatComparisonChange(null, 'NEW')).toBe('Nueva');
    expect(formatComparisonChange(null, 'REMOVED')).toBe('Ya no presente');
    expect(formatComparisonChange(null, 'UNCHANGED')).toBe('Sin cambio');
    expect(formatComparisonChange(null, 'NO_BASE')).toBe('Sin base comparable');
    expect(formatComparisonChange(25, 'CALCULATED')).toBe('+25.0%');
    expect(formatComparisonChange(-12.5, 'CALCULATED')).toBe('-12.5%');
  });

  it('preserves null as unavailable and formats monetary values', () => {
    expect(formatComparisonValue(null, 'USD')).toBe('—');
    expect(formatComparisonValue(1250, 'USD')).toContain('1,250.00');
  });
});
