import type { CanonicalRole, RowReviewPayload, SheetPreviewRow } from './api';

export function buildFinancialLineUpdate(
  accountId: number,
  rowClassification: string,
  canonicalRole: CanonicalRole,
  endingBalance: string,
): RowReviewPayload {
  return {
    action: 'update_financial_line',
    account_id: accountId,
    row_classification: rowClassification,
    canonical_role: canonicalRole,
    ending_balance: endingBalance,
  };
}

export function isPendingPreviewRow(row: SheetPreviewRow): boolean {
  return row.import_row_id !== null
    && row.row_classification === 'CUENTA'
    && row.status !== 'MATCHED';
}
