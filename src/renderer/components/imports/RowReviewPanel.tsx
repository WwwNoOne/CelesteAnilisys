import { useEffect, useState } from 'react';
import {
  createCompanyAccount,
  searchCompanyAccounts,
  type ApiAccount,
  type CanonicalRole,
  type RowReviewPayload,
  type SheetPreviewRow,
} from '../../api';
import { buildFinancialLineUpdate } from '../../import-review-state';

type RowReviewPanelProps = {
  companyId: number;
  sheetType?: string;
  selectedRow: SheetPreviewRow | null;
  onMatch: (rowId: number, accountId: number) => Promise<void>;
  onIgnore: (rowId: number) => Promise<void>;
  onClassify: (rowId: number, classification: string) => Promise<void>;
  onUpdateFinancialLine: (rowId: number, payload: RowReviewPayload) => Promise<void>;
  onClose: () => void;
};

const STATEMENT_TABS = [
  { id: 'ALL', label: 'Todos' },
  { id: 'BALANCE_GENERAL', label: 'Balance General' },
  { id: 'ESTADO_RESULTADOS', label: 'Estado de Resultados' },
  { id: 'FLUJO_EFECTIVO', label: 'Flujo de Efectivo' },
  { id: 'AUXILIARES', label: 'Cuentas auxiliares/control' },
];

const CATEGORIES_BY_STATEMENT: Record<string, string[]> = {
  BALANCE_GENERAL: ['Activos', 'Pasivos', 'Patrimonio'],
  ESTADO_RESULTADOS: [
    'Ingresos',
    'Costos',
    'Gastos',
    'Otros ingresos/gastos',
    'Impuestos',
    'Resultados',
  ],
  FLUJO_EFECTIVO: ['Operación', 'Inversión', 'Financiamiento'],
  AUXILIARES: ['Control y Conciliación', 'Cuentas de Orden'],
};

const CLASSIFICATION_OPTIONS = [
  { id: 'CUENTA', label: 'Cuenta' },
  { id: 'SUBTOTAL', label: 'Subtotal' },
  { id: 'TOTAL', label: 'Total' },
  { id: 'ENCABEZADO', label: 'Encabezado' },
  { id: 'NOTA', label: 'Nota' },
  { id: 'IGNORAR', label: 'Ignorar' },
];

const CANONICAL_ROLE_OPTIONS: CanonicalRole[] = [
  'ACTIVO',
  'PASIVO',
  'PATRIMONIO',
  'VENTAS',
  'COSTO_VENTAS',
  'UTILIDAD_BRUTA',
  'GASTOS',
  'IMPUESTOS',
  'RESULTADO_EJERCICIO',
];

function defaultStatementForSheet(sheetType?: string): string {
  if (sheetType === 'ESTADO_RESULTADOS') return 'ESTADO_RESULTADOS';
  if (sheetType === 'ESTADO_SITUACION_FINANCIERA') return 'BALANCE_GENERAL';
  if (sheetType === 'FLUJO_EFECTIVO') return 'FLUJO_EFECTIVO';
  return 'ALL';
}

export function RowReviewPanel({
  companyId,
  sheetType,
  selectedRow,
  onMatch,
  onIgnore,
  onClassify,
  onUpdateFinancialLine,
  onClose,
}: RowReviewPanelProps) {
  const [selectedStatement, setSelectedStatement] = useState<string>('ALL');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [query, setQuery] = useState('');
  const [accounts, setAccounts] = useState<ApiAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showNewAccountForm, setShowNewAccountForm] = useState(false);
  const [newCode, setNewCode] = useState('');
  const [newName, setNewName] = useState('');
  const [newStatement, setNewStatement] = useState('ESTADO_RESULTADOS');
  const [newCategory, setNewCategory] = useState('Ingresos');
  const [error, setError] = useState('');
  const [canonicalRole, setCanonicalRole] = useState<CanonicalRole | ''>('');
  const [endingBalance, setEndingBalance] = useState('');

  // Set initial statement filter prioritizing sheet type
  useEffect(() => {
    const initialStatement = defaultStatementForSheet(sheetType);
    setSelectedStatement(initialStatement);
    setSelectedCategory('ALL');
  }, [sheetType]);

  useEffect(() => {
    if (!selectedRow) return;
    setQuery(selectedRow.account_name ?? '');
    setSelectedAccountId(null);
    setShowNewAccountForm(false);
    setCanonicalRole(selectedRow.canonical_role ?? '');
    setEndingBalance(selectedRow.ending_balance ?? '');
    setError('');
  }, [selectedRow]);

  useEffect(() => {
    if (!selectedRow) return;
    void loadAccounts(query, selectedStatement, selectedCategory);
  }, [selectedRow, query, selectedStatement, selectedCategory]);

  async function loadAccounts(searchTerm: string, stmt: string, cat: string) {
    setLoading(true);
    try {
      const results = await searchCompanyAccounts(
        companyId,
        searchTerm,
        stmt === 'ALL' ? undefined : stmt,
        cat === 'ALL' ? undefined : cat,
      );
      setAccounts(results);
      if (results.length > 0 && !selectedAccountId) {
        setSelectedAccountId(results[0].id);
      }
    } catch {
      setAccounts([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleClassificationChange(classification: string) {
    if (!selectedRow?.import_row_id) return;
    setSaving(true);
    setError('');
    try {
      if (classification === 'IGNORAR') {
        await onIgnore(selectedRow.import_row_id);
      } else {
        await onClassify(selectedRow.import_row_id, classification);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Error al clasificar la fila');
    } finally {
      setSaving(false);
    }
  }

  async function handleAssign() {
    if (
      !selectedRow?.import_row_id
      || !selectedAccountId
      || !canonicalRole
      || endingBalance.trim() === ''
    ) return;
    setSaving(true);
    setError('');
    try {
      await onUpdateFinancialLine(
        selectedRow.import_row_id,
        buildFinancialLineUpdate(
          selectedAccountId,
          currentClassification,
          canonicalRole,
          endingBalance.trim(),
        ),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Error al asignar cuenta');
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateAndAssign() {
    if (!selectedRow?.import_row_id || !newCode.trim() || !newName.trim()) return;
    setSaving(true);
    setError('');
    try {
      const created = await createCompanyAccount(
        companyId,
        newCode.trim(),
        newName.trim(),
        'ACTIVO',
        newStatement,
        newCategory,
      );
      await onMatch(selectedRow.import_row_id, created.id);
      setShowNewAccountForm(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Error al crear cuenta');
    } finally {
      setSaving(false);
    }
  }

  if (!selectedRow) {
    return (
      <aside className="row-review-panel empty" aria-label="Panel de corrección">
        <div className="review-empty-prompt">
          <span className="prompt-icon">🔍</span>
          <h4>Selecciona una fila</h4>
          <p>
            Haz clic en cualquier fila de la tabla para clasificarla (Subtotal, Total, Encabezado,
            Nota) o asignarle una cuenta del catálogo contable.
          </p>
        </div>
      </aside>
    );
  }

  const currentClassification = selectedRow.row_classification || 'CUENTA';
  const isStructural = ['ENCABEZADO', 'NOTA', 'IGNORAR'].includes(currentClassification);
  const availableCategories =
    selectedStatement !== 'ALL' ? CATEGORIES_BY_STATEMENT[selectedStatement] ?? [] : [];

  return (
    <aside className="row-review-panel" aria-label="Panel de corrección">
      <div className="review-panel-header">
        <div>
          <span className="eyebrow">Fila {selectedRow.source_row}</span>
          <h3>Mapeo y Clasificación</h3>
        </div>
        <button className="icon-button" type="button" onClick={onClose} aria-label="Cerrar panel">
          ×
        </button>
      </div>

      <div className="review-panel-content">
        {/* Row identity card */}
        <div className="review-info-card">
          <div className="info-item">
            <span className="info-label">Código original</span>
            <strong>{selectedRow.account_code || '— Sin código —'}</strong>
          </div>
          <div className="info-item">
            <span className="info-label">Texto original</span>
            <strong>{selectedRow.account_name || '— Sin nombre —'}</strong>
          </div>
        </div>

        {/* Row classification picker */}
        <div className="classification-section">
          <label className="field-label">Clasificación de la fila:</label>
          <div className="classification-pill-group">
            {CLASSIFICATION_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                type="button"
                className={`classification-pill ${
                  currentClassification === opt.id ? 'active' : ''
                }`}
                disabled={saving}
                onClick={() => void handleClassificationChange(opt.id)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="form-error" role="alert">{error}</p>}

        {isStructural ? (
          <div className="structural-row-notice">
            <span className="notice-icon">✓</span>
            <div>
              <strong>Fila clasificada como {currentClassification}</strong>
              <p>
                No se convertirá en cuenta del catálogo ni bloqueará la aprobación de la
                importación.
              </p>
            </div>
          </div>
        ) : (
          /* Account catalog searchable browser */
          <div className="account-mapping-section">
            <label className="field-label">
              Rol canónico
              <select
                value={canonicalRole}
                onChange={(event) => setCanonicalRole(event.target.value as CanonicalRole)}
              >
                <option value="">Selecciona un rol</option>
                {CANONICAL_ROLE_OPTIONS.map((role) => (
                  <option key={role} value={role}>{role.replaceAll('_', ' ')}</option>
                ))}
              </select>
            </label>
            <label className="field-label">
              Saldo
              <input
                type="number"
                step="0.01"
                value={endingBalance}
                onChange={(event) => setEndingBalance(event.target.value)}
              />
            </label>
            <div className="catalog-browser-header">
              <label className="field-label">Buscador en catálogo contable</label>
              {sheetType && (
                <span className="sheet-priority-hint">
                  Priorizando: {defaultStatementForSheet(sheetType)}
                </span>
              )}
            </div>

            {/* Financial statement tabs */}
            <div className="statement-tabs">
              {STATEMENT_TABS.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  className={`statement-tab-button ${
                    selectedStatement === tab.id ? 'active' : ''
                  }`}
                  onClick={() => {
                    setSelectedStatement(tab.id);
                    setSelectedCategory('ALL');
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Subcategories pills if statement selected */}
            {availableCategories.length > 0 && (
              <div className="category-pills">
                <button
                  type="button"
                  className={`category-pill ${selectedCategory === 'ALL' ? 'active' : ''}`}
                  onClick={() => setSelectedCategory('ALL')}
                >
                  Todas las categorías
                </button>
                {availableCategories.map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    className={`category-pill ${selectedCategory === cat ? 'active' : ''}`}
                    onClick={() => setSelectedCategory(cat)}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            )}

            <input
              type="search"
              className="catalog-search-input"
              value={query}
              placeholder="Escribe código o nombre para filtrar..."
              onChange={(e) => setQuery(e.target.value)}
            />

            <div className="account-options-list">
              {loading && <p className="search-hint">Cargando catálogo...</p>}
              {!loading && accounts.length === 0 && (
                <div className="no-accounts-found">
                  <p>No se encontraron cuentas con los filtros actuales.</p>
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => {
                      setNewCode(selectedRow.account_code ?? '');
                      setNewName(selectedRow.account_name ?? '');
                      setNewStatement(
                        selectedStatement !== 'ALL' ? selectedStatement : 'ESTADO_RESULTADOS',
                      );
                      setShowNewAccountForm(true);
                    }}
                  >
                    + Crear esta cuenta en el catálogo
                  </button>
                </div>
              )}
              {accounts.map((account) => (
                <label
                  key={account.id}
                  className={`account-option ${
                    selectedAccountId === account.id ? 'selected' : ''
                  }`}
                >
                  <input
                    type="radio"
                    name="account-selection"
                    checked={selectedAccountId === account.id}
                    onChange={() => setSelectedAccountId(account.id)}
                  />
                  <div className="account-option-details">
                    <div className="account-title-row">
                      <span className="account-code">{account.code}</span>
                      <strong className="account-name">{account.name}</strong>
                    </div>
                    {account.hierarchy_path && (
                      <span className="account-hierarchy-path">{account.hierarchy_path}</span>
                    )}
                  </div>
                </label>
              ))}
            </div>

            <div className="panel-button-stack">
              <button
                type="button"
                className="primary-button"
                disabled={
                  saving
                  || !selectedAccountId
                  || !selectedRow.import_row_id
                  || !canonicalRole
                  || endingBalance.trim() === ''
                }
                onClick={() => void handleAssign()}
              >
                {saving ? 'Guardando…' : 'Guardar línea financiera'}
              </button>
              <button
                type="button"
                className="tertiary-button"
                onClick={() => {
                  setNewCode(selectedRow.account_code ?? '');
                  setNewName(selectedRow.account_name ?? '');
                  setNewStatement(
                    selectedStatement !== 'ALL' ? selectedStatement : 'ESTADO_RESULTADOS',
                  );
                  setShowNewAccountForm(true);
                }}
              >
                + Crear cuenta nueva
              </button>
            </div>
          </div>
        )}

        {showNewAccountForm && (
          <div className="new-account-form">
            <h4>Nueva cuenta en catálogo</h4>
            <label className="field-label">
              Código contable
              <input
                value={newCode}
                placeholder="Ej. 510103"
                onChange={(e) => setNewCode(e.target.value)}
              />
            </label>
            <label className="field-label">
              Nombre de cuenta
              <input
                value={newName}
                placeholder="Ej. Servicios de Producción"
                onChange={(e) => setNewName(e.target.value)}
              />
            </label>
            <label className="field-label">
              Estado financiero
              <select
                value={newStatement}
                onChange={(e) => {
                  setNewStatement(e.target.value);
                  const firstCat = CATEGORIES_BY_STATEMENT[e.target.value]?.[0] ?? 'General';
                  setNewCategory(firstCat);
                }}
              >
                <option value="BALANCE_GENERAL">Balance General</option>
                <option value="ESTADO_RESULTADOS">Estado de Resultados</option>
                <option value="FLUJO_EFECTIVO">Flujo de Efectivo</option>
                <option value="AUXILIARES">Cuentas auxiliares/control</option>
              </select>
            </label>
            <label className="field-label">
              Categoría
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
              >
                {(CATEGORIES_BY_STATEMENT[newStatement] ?? ['General']).map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </label>
            <div className="panel-button-stack">
              <button
                type="button"
                className="primary-button"
                disabled={saving || !newCode.trim() || !newName.trim()}
                onClick={() => void handleCreateAndAssign()}
              >
                {saving ? 'Creando…' : 'Crear y asignar'}
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={() => setShowNewAccountForm(false)}
              >
                Cancelar
              </button>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
