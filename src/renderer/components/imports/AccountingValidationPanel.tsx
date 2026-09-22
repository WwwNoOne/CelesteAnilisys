import type { AccountingValidationResponse } from '../../api';

type AccountingValidationPanelProps = {
  validation: AccountingValidationResponse | null;
};

export function AccountingValidationPanel({ validation }: AccountingValidationPanelProps) {
  if (!validation || validation.rules.length === 0) return null;

  return (
    <section className="accounting-validation-panel" aria-label="Validación contable">
      <div className="accounting-validation-heading">
        <h3>Validación contable</h3>
        <span className={validation.valid ? 'validation-ok' : 'validation-blocked'}>
          {validation.valid ? '✓ Todo cuadra' : 'Bloqueada'}
        </span>
      </div>
      <div className="accounting-rule-list">
        {validation.rules.map((rule) => {
          const blocking = rule.status !== 'VALID';
          return (
            <article
              key={rule.rule_id}
              className={`accounting-rule-card ${blocking ? 'rule-invalid' : 'rule-valid'}`}
              role={blocking ? 'alert' : undefined}
            >
              <strong>{rule.label}</strong>
              {rule.status === 'MISSING_COMPONENTS' && (
                <p>
                  Faltan: {rule.missing_roles.join(', ')}. Cada componente debe existir
                  explícitamente, aunque su saldo sea 0.
                </p>
              )}
              {rule.status === 'MISMATCH' && (
                <p>
                  Lado izquierdo: {rule.left_value} · lado derecho: {rule.right_value} ·
                  diferencia: {rule.difference}
                </p>
              )}
              {rule.status === 'VALID' && <p>La ecuación cuadra dentro de la tolerancia.</p>}
            </article>
          );
        })}
      </div>
    </section>
  );
}
