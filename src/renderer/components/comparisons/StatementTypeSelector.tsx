import type { ComparisonStatementType } from '../../api';

type StatementTypeSelectorProps = {
  value: ComparisonStatementType;
  disabled?: boolean;
  onChange: (value: ComparisonStatementType) => void;
};

export function StatementTypeSelector({
  value,
  disabled = false,
  onChange,
}: StatementTypeSelectorProps) {
  return (
    <label className="comparison-field">
      <span>Tipo de estado</span>
      <select
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value as ComparisonStatementType)}
      >
        <option value="ESTADO_RESULTADOS">Estado de Resultados</option>
        <option value="BALANCE_GENERAL">Balance General</option>
      </select>
    </label>
  );
}
