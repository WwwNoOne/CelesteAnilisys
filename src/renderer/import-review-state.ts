import type { SheetPreviewRow } from './api';

export function isPendingPreviewRow(row: SheetPreviewRow): boolean {
  return row.import_row_id !== null
    && row.row_classification === 'CUENTA'
    && row.status !== 'MATCHED';
}
