import { useEffect, useMemo, useRef, useState } from 'react';
import type { Company } from '../app-state';
import {
  createComparison,
  ensureCompany,
  listComparisonStatements,
  type ComparisonResult,
  type ComparisonStatement,
  type ComparisonStatementType,
} from '../api';
import {
  createRequestTracker,
  getComparisonAvailability,
  isChronologicallyBefore,
} from '../comparison-state';
import { ComparisonTable } from '../components/comparisons/ComparisonTable';
import { ComparisonWarnings } from '../components/comparisons/ComparisonWarnings';
import { FinancialPeriodSelector } from '../components/comparisons/FinancialPeriodSelector';
import { StatementTypeSelector } from '../components/comparisons/StatementTypeSelector';

type ComparisonPageProps = {
  company: Company;
  onFiles: () => void;
};

export function ComparisonPage({ company, onFiles }: ComparisonPageProps) {
  const [statementType, setStatementType] = useState<ComparisonStatementType>('ESTADO_RESULTADOS');
  const [statements, setStatements] = useState<ComparisonStatement[]>([]);
  const [basePeriodId, setBasePeriodId] = useState<number | null>(null);
  const [comparisonPeriodId, setComparisonPeriodId] = useState<number | null>(null);
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryVersion, setRetryVersion] = useState(0);
  const requestTrackerRef = useRef(createRequestTracker());
  const apiCompanyIdRef = useRef<number | null>(null);

  useEffect(() => {
    const requestId = requestTrackerRef.current.begin();
    setLoading(true);
    setError(null);
    setStatements([]);
    setBasePeriodId(null);
    setComparisonPeriodId(null);
    setResult(null);

    ensureCompany(company)
      .then(async (apiCompany) => {
        const items = await listComparisonStatements(apiCompany.id, statementType);
        if (!requestTrackerRef.current.isCurrent(requestId)) return;
        apiCompanyIdRef.current = apiCompany.id;
        setStatements(items);
      })
      .catch((reason: unknown) => {
        if (!requestTrackerRef.current.isCurrent(requestId)) return;
        setError(reason instanceof Error ? reason.message : 'No se pudieron cargar los períodos.');
      })
      .finally(() => {
        if (requestTrackerRef.current.isCurrent(requestId)) setLoading(false);
      });
  }, [company, statementType, retryVersion]);

  const availability = getComparisonAvailability(statements);
  const baseStatement = useMemo(
    () => statements.find((item) => item.period_id === basePeriodId) ?? null,
    [statements, basePeriodId],
  );
  const comparisonStatement = useMemo(
    () => statements.find((item) => item.period_id === comparisonPeriodId) ?? null,
    [statements, comparisonPeriodId],
  );

  async function runComparison() {
    if (!baseStatement || !comparisonStatement || apiCompanyIdRef.current === null) {
      setError('Selecciona el período base y el período posterior.');
      return;
    }
    if (!isChronologicallyBefore(baseStatement, comparisonStatement)) {
      setError('El período base debe ser anterior al período comparado.');
      return;
    }
    setComparing(true);
    setError(null);
    try {
      const nextResult = await createComparison(apiCompanyIdRef.current, {
        statement_type: statementType,
        base_period_id: baseStatement.period_id,
        comparison_period_id: comparisonStatement.period_id,
      });
      setResult(nextResult);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No se pudo realizar la comparación.');
    } finally {
      setComparing(false);
    }
  }

  return (
    <section className="comparison-page">
      <div className="page-heading comparison-page-heading">
        <div>
          <p className="eyebrow">COMPARACIONES</p>
          <h2>Compara estados financieros</h2>
          <p>Selecciona dos estados aprobados de {company.name} y revisa sus variaciones.</p>
        </div>
      </div>

      <div className="comparison-card">
        <div className="comparison-controls">
          <StatementTypeSelector
            value={statementType}
            disabled={loading || comparing}
            onChange={setStatementType}
          />
          <FinancialPeriodSelector
            label="Período base"
            value={basePeriodId}
            statements={statements}
            disabled={loading || comparing || !availability.canCompare}
            disabledPeriodId={comparisonPeriodId}
            onChange={(periodId) => {
              setBasePeriodId(periodId);
              setResult(null);
              setError(null);
            }}
          />
          <FinancialPeriodSelector
            label="Comparar con"
            value={comparisonPeriodId}
            statements={statements}
            disabled={loading || comparing || !availability.canCompare}
            disabledPeriodId={basePeriodId}
            onChange={(periodId) => {
              setComparisonPeriodId(periodId);
              setResult(null);
              setError(null);
            }}
          />
          <button
            className="primary-button comparison-submit"
            type="button"
            disabled={loading || comparing || !availability.canCompare}
            onClick={runComparison}
          >
            {comparing ? 'Comparando…' : 'Comparar'}
          </button>
        </div>

        <ComparisonWarnings warnings={result?.warnings ?? []} error={error} />

        {loading && <div className="comparison-loading" role="status">Cargando períodos disponibles…</div>}
        {!loading && error && statements.length === 0 && (
          <button className="secondary-button" type="button" onClick={() => setRetryVersion((value) => value + 1)}>
            Reintentar
          </button>
        )}
        {!loading && !error && !availability.canCompare && (
          <div className="comparison-empty">
            <div className="upload-icon" aria-hidden="true">⇄</div>
            <h3>No hay suficientes períodos disponibles para realizar una comparación.</h3>
            <p>Importa al menos dos Estados de Resultados o dos Balances de diferentes fechas o períodos.</p>
            <button className="secondary-button" type="button" onClick={onFiles}>Ir a Archivos</button>
          </div>
        )}
      </div>

      {result && <ComparisonTable result={result} currency={company.currency} />}
    </section>
  );
}
