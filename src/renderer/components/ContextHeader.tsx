import type { Company } from '../app-state';

type ContextHeaderProps = {
  company: Company;
  period: string;
  view: string;
  onPeriodChange: (period: string) => void;
  onViewChange: (view: string) => void;
};

export function ContextHeader({
  company,
  period,
  view,
  onPeriodChange,
  onViewChange,
}: ContextHeaderProps) {
  return (
    <header className="context-header">
      <div>
        <p className="eyebrow">WORKSPACE FINANCIERO</p>
        <h1>{company.name}</h1>
      </div>
      <div className="context-controls">
        <label>
          <span>Período</span>
          <select value={period} onChange={(event) => onPeriodChange(event.target.value)}>
            {company.periods.map((availablePeriod) => (
              <option key={availablePeriod}>{availablePeriod}</option>
            ))}
          </select>
        </label>
        <label>
          <span>Vista</span>
          <select value={view} onChange={(event) => onViewChange(event.target.value)}>
            <option>Mensual</option>
            <option>Trimestral</option>
            <option>Semestral</option>
            <option>Anual</option>
          </select>
        </label>
      </div>
    </header>
  );
}
