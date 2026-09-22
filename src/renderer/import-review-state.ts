import type {
  AccountingValidationResponse,
  CanonicalRole,
  RowReviewPayload,
  SheetPreviewRow,
} from './api';

export function collectInvalidRowIds(validation: AccountingValidationResponse | null) {
  return new Set(
    validation?.rules
      .filter((rule) => rule.status !== 'VALID')
      .flatMap((rule) => rule.row_ids) ?? [],
  );
}

export function createRequestTracker() {
  let current = 0;
  return {
    begin() {
      current += 1;
      return current;
    },
    isCurrent(request: number) {
      return request === current;
    },
  };
}

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
