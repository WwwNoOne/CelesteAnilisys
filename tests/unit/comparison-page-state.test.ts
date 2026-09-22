import { describe, expect, it } from 'vitest';
import type { ComparisonStatement } from '../../src/renderer/api';
import {
  createRequestTracker,
  getComparisonAvailability,
} from '../../src/renderer/comparison-state';

function statement(periodId: number): ComparisonStatement {
  return {
    period_id: periodId,
    statement_type: 'BALANCE_GENERAL',
    label: String(periodId),
    as_of_date: `202${periodId}-12-31`,
    period_start: null,
    period_end: null,
    duration_days: null,
  };
}

describe('comparison page state', () => {
  it('shows the empty-state action when fewer than two compatible statements exist', () => {
    expect(getComparisonAvailability([statement(1)])).toEqual({
      canCompare: false,
      reason: 'INSUFFICIENT',
    });
    expect(getComparisonAvailability([statement(1), statement(2)])).toEqual({
      canCompare: true,
      reason: null,
    });
  });

  it('invalidates an older request after the statement type changes', () => {
    const tracker = createRequestTracker();
    const first = tracker.begin();
    const second = tracker.begin();

    expect(tracker.isCurrent(first)).toBe(false);
    expect(tracker.isCurrent(second)).toBe(true);
  });
});
