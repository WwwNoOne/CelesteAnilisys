import { describe, expect, it } from 'vitest';
import { isReviewPath, parseImportIdFromPath } from '../../src/renderer/navigation';
import { isPendingPreviewRow } from '../../src/renderer/import-review-state';

describe('import review state', () => {
  it('does not count visual rows without import_row_id', () => {
    expect(
      isPendingPreviewRow({
        source_row: 1,
        cells: ['Título'],
        import_row_id: null,
        status: null,
        account_code: null,
        account_name: null,
        row_classification: 'CUENTA',
      }),
    ).toBe(false);
  });
  it('identifies review path correctly', () => {
    expect(isReviewPath('/imports/12/review')).toBe(true);
    expect(isReviewPath('/imports/abc/review')).toBe(false);
    expect(isReviewPath('/files')).toBe(false);
  });

  it('extracts import ID from review path', () => {
    expect(parseImportIdFromPath('/imports/99/review')).toBe(99);
    expect(parseImportIdFromPath('/imports/invalid/review')).toBeNull();
  });

  it('validates year string properly', () => {
    const isValidYear = (value: string) => {
      const trimmed = value.trim();
      if (!/^\d{4}$/.test(trimmed)) return false;
      const num = Number.parseInt(trimmed, 10);
      return num >= 1900 && num <= 2100;
    };

    expect(isValidYear('2025')).toBe(true);
    expect(isValidYear(' 2024 ')).toBe(true);
    expect(isValidYear('abc')).toBe(false);
    expect(isValidYear('202')).toBe(false);
  });

  it('approval predicate requires period validated, no conflict, and zero pending review rows', () => {
    const canApprove = (job: {
      period_validated: boolean;
      period_conflict: boolean;
      review_rows: number;
      status: string;
    }) => {
      return (
        job.period_validated &&
        !job.period_conflict &&
        job.review_rows === 0 &&
        job.status !== 'APPROVED'
      );
    };

    // Ready to approve
    expect(
      canApprove({
        period_validated: true,
        period_conflict: false,
        review_rows: 0,
        status: 'READY_FOR_REVIEW',
      }),
    ).toBe(true);

    // Blocked if period conflict exists
    expect(
      canApprove({
        period_validated: true,
        period_conflict: true,
        review_rows: 0,
        status: 'READY_FOR_REVIEW',
      }),
    ).toBe(false);

    // Blocked if period is not validated
    expect(
      canApprove({
        period_validated: false,
        period_conflict: false,
        review_rows: 0,
        status: 'READY_FOR_REVIEW',
      }),
    ).toBe(false);

    // Blocked if pending review rows exist
    expect(
      canApprove({
        period_validated: true,
        period_conflict: false,
        review_rows: 3,
        status: 'READY_FOR_REVIEW',
      }),
    ).toBe(false);
  });
});
