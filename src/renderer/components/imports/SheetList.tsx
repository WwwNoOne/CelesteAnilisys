import type { ImportSheet } from '../../api';

type SheetListProps = {
  sheets: ImportSheet[];
  selectedSheet: string;
  approvedSheets?: string[];
  onSelectSheet: (sheetName: string) => void;
};

const SHEET_TYPE_LABELS: Record<string, string> = {
  BALANCE_COMPROBACION: 'Balance de Comprobación',
  ESTADO_SITUACION_FINANCIERA: 'Balance General',
  ESTADO_RESULTADOS: 'Estado de Resultados',
  FLUJO_EFECTIVO: 'Flujo de Efectivo',
  DESCONOCIDO: 'Hoja auxiliar',
};

export function SheetList({
  sheets,
  selectedSheet,
  approvedSheets = [],
  onSelectSheet,
}: SheetListProps) {
  return (
    <aside className="sheet-list-panel" aria-label="Hojas del archivo">
      <div className="sheet-list-header">
        <h3>Hojas ({sheets.length})</h3>
      </div>
      <div className="sheet-list-items">
        {sheets.map((sheet) => {
          const isSelected = selectedSheet === sheet.sheet_name;
          const isApproved = approvedSheets.includes(sheet.sheet_name);
          const displayType = SHEET_TYPE_LABELS[sheet.sheet_type] ?? sheet.sheet_type;
          return (
            <button
              key={sheet.sheet_name}
              type="button"
              className={`sheet-item-button ${isSelected ? 'active' : ''}`}
              onClick={() => onSelectSheet(sheet.sheet_name)}
            >
              <div className="sheet-item-name">
                <span className="sheet-bullet">{isSelected ? '●' : '○'}</span>
                <strong>{sheet.sheet_name}</strong>
                {isApproved && <span className="sheet-approved-tag">✓ Aprobada</span>}
              </div>
              <span className="sheet-item-type">{displayType}</span>
              {sheet.date_label && (
                <span className="sheet-item-date">{sheet.date_label}</span>
              )}
            </button>
          );
        })}
      </div>
    </aside>
  );
}
