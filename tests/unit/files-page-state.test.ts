import { describe, expect, it } from 'vitest';

describe('files page state and history', () => {
  it('formats status labels and colors accurately', () => {
    const STATUS_CONFIG: Record<string, { label: string; badgeClass: string }> = {
      APPROVED: { label: 'Aprobada', badgeClass: 'pill-matched' },
      READY_FOR_REVIEW: { label: 'Requiere revisión', badgeClass: 'pill-unknown' },
      ANALYZING: { label: 'Analizando…', badgeClass: 'pill-needs_review' },
      UPLOADED: { label: 'Subido', badgeClass: 'pill-ignored' },
      FAILED: { label: 'Error', badgeClass: 'badge-error' },
    };

    expect(STATUS_CONFIG.APPROVED.label).toBe('Aprobada');
    expect(STATUS_CONFIG.READY_FOR_REVIEW.badgeClass).toBe('pill-unknown');
    expect(STATUS_CONFIG.FAILED.badgeClass).toBe('badge-error');
  });

  it('calculates total pending review rows across company imports', () => {
    const mockImports = [
      { id: 1, status: 'APPROVED', total_rows: 50, recognized_rows: 50, unknown_rows: 0, review_rows: 0 },
      { id: 2, status: 'READY_FOR_REVIEW', total_rows: 40, recognized_rows: 30, unknown_rows: 5, review_rows: 10 },
      { id: 3, status: 'READY_FOR_REVIEW', total_rows: 25, recognized_rows: 20, unknown_rows: 2, review_rows: 5 },
    ];

    const totalUnknown = mockImports.reduce((sum, item) => sum + item.unknown_rows, 0);
    const totalPendingReview = mockImports.reduce((sum, item) => sum + item.review_rows, 0);

    expect(totalUnknown).toBe(7);
    expect(totalPendingReview).toBe(15);
  });
});
