import type { SheetPreviewRow } from '../../api';

type PreviewTableProps = {
  columns: string[];
  rows: Array<Array<string | number | null>>;
  rowDetails?: SheetPreviewRow[];
  selectedRowId?: number | null;
  onSelectRow?: (rowDetail: SheetPreviewRow) => void;
  invalidRowIds?: Set<number>;
};

const STATUS_LABELS: Record<string, { label: string; badgeClass: string }> = {
  MATCHED: { label: 'Reconocida', badgeClass: 'badge-matched' },
  NEEDS_REVIEW: { label: 'Revisar', badgeClass: 'badge-review' },
  UNKNOWN: { label: 'Desconocida', badgeClass: 'badge-unknown' },
  NEW_ACCOUNT: { label: 'Nueva', badgeClass: 'badge-new' },
  ERROR: { label: 'Error', badgeClass: 'badge-error' },
  IGNORED: { label: 'Ignorada', badgeClass: 'badge-ignored' },
};

const CLASSIFICATION_BADGES: Record<string, { label: string; badgeClass: string }> = {
  SUBTOTAL: { label: 'Subtotal', badgeClass: 'badge-subtotal' },
  TOTAL: { label: 'Total', badgeClass: 'badge-total' },
  ENCABEZADO: { label: 'Encabezado', badgeClass: 'badge-header' },
  NOTA: { label: 'Nota', badgeClass: 'badge-note' },
  IGNORAR: { label: 'Ignorada', badgeClass: 'badge-ignored' },
};

export function PreviewTable({
  columns,
  rows,
  rowDetails = [],
  selectedRowId = null,
  onSelectRow,
  invalidRowIds = new Set(),
}: PreviewTableProps) {
  if (rows.length === 0) {
    return (
      <div className="preview-empty-state">
        <p>No hay datos disponibles para esta hoja.</p>
      </div>
    );
  }

  return (
    <div className="preview-table-container">
      <table className="excel-preview-table">
        <thead>
          <tr>
            <th className="excel-row-header-th">#</th>
            <th className="excel-status-th">Estado / Tipo</th>
            {columns.map((colName, index) => (
              <th key={`${colName}-${index}`}>{colName}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((rowCells, rowIndex) => {
            const detail = rowDetails[rowIndex];
            const sourceRowNum = detail?.source_row ?? rowIndex + 1;
            const isSelected = detail?.import_row_id != null && detail.import_row_id === selectedRowId;
            const isInvalid = detail?.import_row_id != null && invalidRowIds.has(detail.import_row_id);
            const isNonAccount = detail?.row_classification && detail.row_classification !== 'CUENTA';
            const badgeInfo = isNonAccount
              ? CLASSIFICATION_BADGES[detail.row_classification]
              : detail?.status
              ? STATUS_LABELS[detail.status]
              : null;

            return (
              <tr
                key={`${sourceRowNum}-${detail?.import_row_id ?? rowIndex}`}
                className={`excel-preview-row ${isSelected ? 'row-selected' : ''} ${
                  detail?.import_row_id != null ? 'clickable-row' : ''
                } ${isInvalid ? 'financial-row-invalid' : ''}`}
                onClick={() => {
                  if (detail && onSelectRow) {
                    onSelectRow(detail);
                  }
                }}
              >
                <td className="excel-row-number">{sourceRowNum}</td>
                <td className="excel-row-status">
                  {badgeInfo ? (
                    <span className={`status-badge ${badgeInfo.badgeClass}`}>
                      {badgeInfo.label}
                    </span>
                  ) : (
                    <span className="status-badge badge-neutral">—</span>
                  )}
                </td>
                {columns.map((_, colIndex) => {
                  const cellValue = rowCells[colIndex];
                  const isNumber = typeof cellValue === 'number';
                  const isTextSource = detail?.source_text_column === colIndex;
                  const isAmountSource = detail?.source_amount_column === colIndex;
                  const formattedValue =
                    isNumber
                      ? Number(cellValue).toLocaleString('es-SV', {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })
                      : cellValue ?? '';

                  return (
                    <td
                      key={colIndex}
                      className={`${isNumber ? 'cell-number' : 'cell-text'} ${
                        isTextSource ? 'cell-text-source' : ''
                      } ${isAmountSource ? 'cell-amount-source' : ''}`}
                      title={
                        isTextSource
                          ? 'Columna de texto de la cuenta'
                          : isAmountSource
                          ? 'Columna de importe'
                          : String(cellValue ?? '')
                      }
                    >
                      {formattedValue}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
