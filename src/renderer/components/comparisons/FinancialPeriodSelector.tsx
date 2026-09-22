import type { ComparisonStatement } from '../../api';

type FinancialPeriodSelectorProps = {
  label: string;
  value: number | null;
  statements: ComparisonStatement[];
  disabled?: boolean;
  disabledPeriodId?: number | null;
  onChange: (periodId: number | null) => void;
};

export function FinancialPeriodSelector({
  label,
  value,
  statements,
  disabled = false,
  disabledPeriodId = null,
  onChange,
}: FinancialPeriodSelectorProps) {
  return (
    <label className="comparison-field">
      <span>{label}</span>
      <select
        value={value ?? ''}
        disabled={disabled}
        onChange={(event) => {
          onChange(event.target.value ? Number(event.target.value) : null);
        }}
      >
        <option value="">Seleccionar período</option>
        {statements.map((statement) => (
          <option
            key={statement.period_id}
            value={statement.period_id}
            disabled={statement.period_id === disabledPeriodId}
          >
            {statement.label}
          </option>
        ))}
      </select>
    </label>
  );
}
