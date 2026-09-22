import { useState } from 'react';
import type { ComparisonResult, ComparisonRow } from '../../api';
import { formatComparisonChange, formatComparisonValue } from '../../comparison-state';

type ComparisonTableProps = {
  result: ComparisonResult;
  currency: string;
};

function changeClass(value: number | null): string {
  if (value === null || value === 0) return 'comparison-neutral';
  return value > 0 ? 'comparison-positive' : 'comparison-negative';
}

export function ComparisonTable({ result, currency }: ComparisonTableProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  function toggle(key: string) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function renderRow(row: ComparisonRow, isGroup = false): React.ReactNode {
    const hasChildren = row.children.length > 0;
    const isExpanded = expanded.has(row.key);
    return (
      <tbody key={row.key}>
        <tr className={isGroup ? 'comparison-group-row' : 'comparison-detail-row'}>
          <th scope="row" style={{ '--comparison-level': row.level } as React.CSSProperties}>
            {hasChildren ? (
              <button
                type="button"
                className="comparison-expand"
                aria-expanded={isExpanded}
                onClick={() => toggle(row.key)}
              >
                <span aria-hidden="true">{isExpanded ? '▾' : '▸'}</span>
                <span>{row.name}</span>
              </button>
            ) : (
              <span className="comparison-row-name">{row.name}</span>
            )}
            {row.code && <small>{row.code}</small>}
          </th>
          <td>{formatComparisonValue(row.base_value, currency)}</td>
          <td>{formatComparisonValue(row.comparison_value, currency)}</td>
          <td className={changeClass(row.absolute_change)}>
            {formatComparisonValue(row.absolute_change, currency)}
          </td>
          <td className={changeClass(row.percentage_change)}>
            {formatComparisonChange(row.percentage_change, row.change_status)}
          </td>
        </tr>
        {hasChildren && isExpanded && row.children.map((child) => renderRow(child))}
      </tbody>
    );
  }

  return (
    <section className="comparison-results" aria-labelledby="comparison-results-title">
      <div className="comparison-results-heading">
        <div>
          <p className="eyebrow">RESULTADO</p>
          <h2 id="comparison-results-title">Comparación financiera</h2>
        </div>
        <p>{result.base_statement.label} frente a {result.comparison_statement.label}</p>
      </div>
      <div className="comparison-table-wrap">
        <table className="comparison-table">
          <thead>
            <tr>
              <th>Cuenta</th>
              <th>{result.base_statement.label}</th>
              <th>{result.comparison_statement.label}</th>
              <th>Variación absoluta</th>
              <th>Variación %</th>
            </tr>
          </thead>
          {result.groups.map((group) => renderRow(group, true))}
        </table>
      </div>
    </section>
  );
}
