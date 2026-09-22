from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domain.enums import AccountType, CanonicalRole, FinancialStatement
from app.models import Account
from app.normalizers.text_normalizer import normalize_account_name

ACCOUNT_TYPE_PREFIX: dict[AccountType, str] = {
    AccountType.ACTIVO: "1",
    AccountType.PASIVO: "2",
    AccountType.PATRIMONIO: "3",
    AccountType.INGRESO: "4",
    AccountType.COSTO: "5",
    AccountType.GASTO: "6",
    AccountType.OTRO: "9",
}

CANONICAL_ROLE_TO_ACCOUNT_TYPE: dict[CanonicalRole, AccountType] = {
    CanonicalRole.ACTIVO: AccountType.ACTIVO,
    CanonicalRole.PASIVO: AccountType.PASIVO,
    CanonicalRole.PATRIMONIO: AccountType.PATRIMONIO,
    CanonicalRole.VENTAS: AccountType.INGRESO,
    CanonicalRole.COSTO_VENTAS: AccountType.COSTO,
    CanonicalRole.UTILIDAD_BRUTA: AccountType.INGRESO,
    CanonicalRole.GASTOS: AccountType.GASTO,
    CanonicalRole.IMPUESTOS: AccountType.GASTO,
    CanonicalRole.RESULTADO_EJERCICIO: AccountType.PATRIMONIO,
}


def account_type_for_role(role: CanonicalRole | None) -> AccountType:
    if role is None:
        return AccountType.OTRO
    return CANONICAL_ROLE_TO_ACCOUNT_TYPE.get(role, AccountType.OTRO)


def generate_account_code(db: Session, company_id: int, account_type: AccountType) -> str:
    prefix = ACCOUNT_TYPE_PREFIX.get(account_type, "9")
    existing = db.query(Account.code).filter(
        Account.company_id == company_id,
        Account.code.like(f"{prefix}%"),
    ).all()
    max_num = 0
    for (code,) in existing:
        suffix = code[len(prefix):]
        if suffix.isdigit():
            max_num = max(max_num, int(suffix))
    return f"{prefix}{max_num + 1:03d}"


def derive_account_hierarchy(code: str | None) -> tuple[str | None, int]:
    """Derive the parent code and nesting level from a hierarchical account code.

    Account codes use fixed 2-digit segments after the leading digit(s), e.g.
    ``1`` -> ``11`` -> ``1101`` -> ``110102`` -> ``11010201``.
    """
    if not code or not code.strip():
        return None, 1
    code = code.strip()
    if len(code) >= 3:
        parent = code[:-2]
    elif len(code) == 2:
        parent = code[0]
    else:
        parent = None
    level = len(code) // 2 + 1 if len(code) % 2 == 0 else (len(code) + 1) // 2
    return parent or None, level


@dataclass(slots=True)
class StandardAccountTemplate:
    code: str
    name: str
    account_type: AccountType
    statement: str
    statement_label: str
    category: str
    hierarchy_path: str


STANDARD_CATALOG_TEMPLATES: list[StandardAccountTemplate] = [
    # -------------------------------------------------------------
    # 1. BALANCE GENERAL
    # -------------------------------------------------------------
    # Activos
    StandardAccountTemplate("1101", "Efectivo y Equivalentes", AccountType.ACTIVO, "BALANCE_GENERAL", "Balance General", "Activos", "Balance General > Activos > Activo Corriente"),
    StandardAccountTemplate("110101", "Caja General", AccountType.ACTIVO, "BALANCE_GENERAL", "Balance General", "Activos", "Balance General > Activos > Activo Corriente"),
    StandardAccountTemplate("110102", "Bancos", AccountType.ACTIVO, "BALANCE_GENERAL", "Balance General", "Activos", "Balance General > Activos > Activo Corriente"),
    StandardAccountTemplate("11010201", "Cuentas Corrientes", AccountType.ACTIVO, "BALANCE_GENERAL", "Balance General", "Activos", "Balance General > Activos > Activo Corriente"),
    StandardAccountTemplate("1102", "Cuentas y Documentos por Cobrar", AccountType.ACTIVO, "BALANCE_GENERAL", "Balance General", "Activos", "Balance General > Activos > Activo Corriente"),
    StandardAccountTemplate("110201", "Clientes Comerciales", AccountType.ACTIVO, "BALANCE_GENERAL", "Balance General", "Activos", "Balance General > Activos > Activo Corriente"),
    StandardAccountTemplate("110205", "Cuentas por Cobrar a Accionistas", AccountType.ACTIVO, "BALANCE_GENERAL", "Balance General", "Activos", "Balance General > Activos > Activo Corriente"),
    StandardAccountTemplate("1107", "Pagos Anticipados", AccountType.ACTIVO, "BALANCE_GENERAL", "Balance General", "Activos", "Balance General > Activos > Activo Corriente"),
    StandardAccountTemplate("1108", "IVA Crédito Fiscal", AccountType.ACTIVO, "BALANCE_GENERAL", "Balance General", "Activos", "Balance General > Activos > Activo Corriente"),
    StandardAccountTemplate("1201", "Propiedad, Planta y Equipo", AccountType.ACTIVO, "BALANCE_GENERAL", "Balance General", "Activos", "Balance General > Activos > Activo No Corriente"),
    StandardAccountTemplate("120102", "Vehículos / Equipo de Transporte", AccountType.ACTIVO, "BALANCE_GENERAL", "Balance General", "Activos", "Balance General > Activos > Activo No Corriente"),
    StandardAccountTemplate("120103", "Mobiliario y Equipo de Oficina", AccountType.ACTIVO, "BALANCE_GENERAL", "Balance General", "Activos", "Balance General > Activos > Activo No Corriente"),
    StandardAccountTemplate("120104", "Equipo de Computación", AccountType.ACTIVO, "BALANCE_GENERAL", "Balance General", "Activos", "Balance General > Activos > Activo No Corriente"),
    StandardAccountTemplate("1202", "Depreciación Acumulada Propiedad P. y E.", AccountType.ACTIVO, "BALANCE_GENERAL", "Balance General", "Activos", "Balance General > Activos > Activo No Corriente"),
    StandardAccountTemplate("1205", "Activos Intangibles", AccountType.ACTIVO, "BALANCE_GENERAL", "Balance General", "Activos", "Balance General > Activos > Activo No Corriente"),

    # Pasivos
    StandardAccountTemplate("2101", "Cuentas y Documentos por Pagar", AccountType.PASIVO, "BALANCE_GENERAL", "Balance General", "Pasivos", "Balance General > Pasivos > Pasivo Corriente"),
    StandardAccountTemplate("210101", "Proveedores Locales", AccountType.PASIVO, "BALANCE_GENERAL", "Balance General", "Pasivos", "Balance General > Pasivos > Pasivo Corriente"),
    StandardAccountTemplate("2102", "Préstamos Bancarios Corto Plazo", AccountType.PASIVO, "BALANCE_GENERAL", "Balance General", "Pasivos", "Balance General > Pasivos > Pasivo Corriente"),
    StandardAccountTemplate("2103", "Retenciones por Pagar", AccountType.PASIVO, "BALANCE_GENERAL", "Balance General", "Pasivos", "Balance General > Pasivos > Pasivo Corriente"),
    StandardAccountTemplate("2104", "Impuestos por Pagar", AccountType.PASIVO, "BALANCE_GENERAL", "Balance General", "Pasivos", "Balance General > Pasivos > Pasivo Corriente"),
    StandardAccountTemplate("2201", "Préstamos Bancarios Largo Plazo", AccountType.PASIVO, "BALANCE_GENERAL", "Balance General", "Pasivos", "Balance General > Pasivos > Pasivo No Corriente"),
    StandardAccountTemplate("2202", "Documentos por Pagar Largo Plazo", AccountType.PASIVO, "BALANCE_GENERAL", "Balance General", "Pasivos", "Balance General > Pasivos > Pasivo No Corriente"),

    # Patrimonio
    StandardAccountTemplate("3101", "Capital Social", AccountType.PATRIMONIO, "BALANCE_GENERAL", "Balance General", "Patrimonio", "Balance General > Patrimonio > Capital"),
    StandardAccountTemplate("3102", "Reserva Legal", AccountType.PATRIMONIO, "BALANCE_GENERAL", "Balance General", "Patrimonio", "Balance General > Patrimonio > Reservas"),
    StandardAccountTemplate("3103", "Utilidades Acumuladas", AccountType.PATRIMONIO, "BALANCE_GENERAL", "Balance General", "Patrimonio", "Balance General > Patrimonio > Resultados Acumulados"),
    StandardAccountTemplate("3104", "Pérdidas Acumuladas", AccountType.PATRIMONIO, "BALANCE_GENERAL", "Balance General", "Patrimonio", "Balance General > Patrimonio > Resultados Acumulados"),
    StandardAccountTemplate("3105", "Resultado del Ejercicio", AccountType.PATRIMONIO, "BALANCE_GENERAL", "Balance General", "Patrimonio", "Balance General > Patrimonio > Resultados"),

    # -------------------------------------------------------------
    # 2. ESTADO DE RESULTADOS
    # -------------------------------------------------------------
    # Ingresos
    StandardAccountTemplate("5101", "Ingresos de Operación", AccountType.INGRESO, "ESTADO_RESULTADOS", "Estado de Resultados", "Ingresos", "Estado de Resultados > Ingresos > Operación"),
    StandardAccountTemplate("510101", "Ingresos por Servicios", AccountType.INGRESO, "ESTADO_RESULTADOS", "Estado de Resultados", "Ingresos", "Estado de Resultados > Ingresos > Servicios"),
    StandardAccountTemplate("510102", "Elaboración de Videos y Producción", AccountType.INGRESO, "ESTADO_RESULTADOS", "Estado de Resultados", "Ingresos", "Estado de Resultados > Ingresos > Servicios"),
    StandardAccountTemplate("5102", "Ventas Netas", AccountType.INGRESO, "ESTADO_RESULTADOS", "Estado de Resultados", "Ingresos", "Estado de Resultados > Ingresos > Ventas"),

    # Costos
    StandardAccountTemplate("4101", "Costo de Ventas", AccountType.COSTO, "ESTADO_RESULTADOS", "Estado de Resultados", "Costos", "Estado de Resultados > Costos > Operación"),
    StandardAccountTemplate("410101", "Costo de Elaboración de Videos", AccountType.COSTO, "ESTADO_RESULTADOS", "Estado de Resultados", "Costos", "Estado de Resultados > Costos > Producción"),
    StandardAccountTemplate("4102", "Costo de Servicios Prestados", AccountType.COSTO, "ESTADO_RESULTADOS", "Estado de Resultados", "Costos", "Estado de Resultados > Costos > Servicios"),

    # Gastos
    StandardAccountTemplate("4201", "Gastos de Operación", AccountType.GASTO, "ESTADO_RESULTADOS", "Estado de Resultados", "Gastos", "Estado de Resultados > Gastos > Operación"),
    StandardAccountTemplate("420101", "Gastos de Administración", AccountType.GASTO, "ESTADO_RESULTADOS", "Estado de Resultados", "Gastos", "Estado de Resultados > Gastos > Administración"),
    StandardAccountTemplate("420102", "Gastos de Ventas", AccountType.GASTO, "ESTADO_RESULTADOS", "Estado de Resultados", "Gastos", "Estado de Resultados > Gastos > Ventas"),
    StandardAccountTemplate("420110", "Honorarios Profesionales", AccountType.GASTO, "ESTADO_RESULTADOS", "Estado de Resultados", "Gastos", "Estado de Resultados > Gastos > Administración"),
    StandardAccountTemplate("420112", "Combustibles y Lubricantes", AccountType.GASTO, "ESTADO_RESULTADOS", "Estado de Resultados", "Gastos", "Estado de Resultados > Gastos > Operación"),

    # Otros ingresos/gastos
    StandardAccountTemplate("5201", "Otros Ingresos de Operación", AccountType.INGRESO, "ESTADO_RESULTADOS", "Estado de Resultados", "Otros ingresos/gastos", "Estado de Resultados > Otros ingresos/gastos > Ingresos"),
    StandardAccountTemplate("5202", "Ingresos Financieros", AccountType.INGRESO, "ESTADO_RESULTADOS", "Estado de Resultados", "Otros ingresos/gastos", "Estado de Resultados > Otros ingresos/gastos > Financieros"),
    StandardAccountTemplate("4301", "Gastos Financieros", AccountType.GASTO, "ESTADO_RESULTADOS", "Estado de Resultados", "Otros ingresos/gastos", "Estado de Resultados > Otros ingresos/gastos > Financieros"),
    StandardAccountTemplate("4302", "Gastos No Deducibles", AccountType.GASTO, "ESTADO_RESULTADOS", "Estado de Resultados", "Otros ingresos/gastos", "Estado de Resultados > Otros ingresos/gastos > No Deducibles"),

    # Impuestos
    StandardAccountTemplate("4401", "Impuesto Sobre la Renta (ISR)", AccountType.GASTO, "ESTADO_RESULTADOS", "Estado de Resultados", "Impuestos", "Estado de Resultados > Impuestos > Renta"),
    StandardAccountTemplate("4402", "Pago a Cuenta I.S.R.", AccountType.ACTIVO, "ESTADO_RESULTADOS", "Estado de Resultados", "Impuestos", "Estado de Resultados > Impuestos > Anticipos"),

    # Resultados
    StandardAccountTemplate("3201", "Utilidad Bruta", AccountType.INGRESO, "ESTADO_RESULTADOS", "Estado de Resultados", "Resultados", "Estado de Resultados > Resultados > Operativos"),
    StandardAccountTemplate("3202", "Utilidad de Operación", AccountType.INGRESO, "ESTADO_RESULTADOS", "Estado de Resultados", "Resultados", "Estado de Resultados > Resultados > Operativos"),
    StandardAccountTemplate("3203", "Utilidad / Pérdida del Ejercicio", AccountType.INGRESO, "ESTADO_RESULTADOS", "Estado de Resultados", "Resultados", "Estado de Resultados > Resultados > Ejercicio"),

    # -------------------------------------------------------------
    # 3. FLUJO DE EFECTIVO
    # -------------------------------------------------------------
    StandardAccountTemplate("7101", "Cobros por Ventas y Servicios", AccountType.INGRESO, "FLUJO_EFECTIVO", "Flujo de Efectivo", "Operación", "Flujo de Efectivo > Operación > Cobros"),
    StandardAccountTemplate("7102", "Pagos a Proveedores", AccountType.GASTO, "FLUJO_EFECTIVO", "Flujo de Efectivo", "Operación", "Flujo de Efectivo > Operación > Pagos"),
    StandardAccountTemplate("7103", "Pagos a Empleados", AccountType.GASTO, "FLUJO_EFECTIVO", "Flujo de Efectivo", "Operación", "Flujo de Efectivo > Operación > Sueldos"),
    StandardAccountTemplate("7104", "Pagos de Impuestos", AccountType.GASTO, "FLUJO_EFECTIVO", "Flujo de Efectivo", "Operación", "Flujo de Efectivo > Operación > Tributos"),
    StandardAccountTemplate("7201", "Adquisición de Propiedad, Planta y Equipo", AccountType.ACTIVO, "FLUJO_EFECTIVO", "Flujo de Efectivo", "Inversión", "Flujo de Efectivo > Inversión > Activos Fijos"),
    StandardAccountTemplate("7301", "Aportes de Capital Recibidos", AccountType.PATRIMONIO, "FLUJO_EFECTIVO", "Flujo de Efectivo", "Financiamiento", "Flujo de Efectivo > Financiamiento > Patrimonio"),
    StandardAccountTemplate("7302", "Préstamos y Financiamientos Recibidos", AccountType.PASIVO, "FLUJO_EFECTIVO", "Flujo de Efectivo", "Financiamiento", "Flujo de Efectivo > Financiamiento > Deuda"),

    # -------------------------------------------------------------
    # 4. CUENTAS AUXILIARES / CONTROL
    # -------------------------------------------------------------
    StandardAccountTemplate("8101", "Conciliación de Impuestos", AccountType.OTRO, "AUXILIARES", "Cuentas auxiliares/control", "Control y Conciliación", "Cuentas auxiliares/control > Control y Conciliación"),
    StandardAccountTemplate("8102", "Anticipos y Excedentes Fiscales", AccountType.OTRO, "AUXILIARES", "Cuentas auxiliares/control", "Control y Conciliación", "Cuentas auxiliares/control > Excedentes"),
    StandardAccountTemplate("9101", "Cuentas de Orden / Garantías", AccountType.OTRO, "AUXILIARES", "Cuentas auxiliares/control", "Cuentas de Orden", "Cuentas auxiliares/control > Cuentas de Orden"),
]


def ensure_company_standard_catalog(db: Session, company_id: int) -> None:
    """Ensure company has standard accounts seeded for all financial statements."""
    existing_codes = {
        code for (code,) in db.query(Account.code).filter(Account.company_id == company_id).all()
    }
    new_accounts: list[Account] = []
    for t in STANDARD_CATALOG_TEMPLATES:
        if t.code not in existing_codes:
            acc = Account(
                company_id=company_id,
                code=t.code,
                name=t.name,
                normalized_name=normalize_account_name(t.name),
                account_type=t.account_type,
                financial_statement=FinancialStatement(t.statement) if t.statement in FinancialStatement.__members__ else FinancialStatement.DESCONOCIDO,
            )
            new_accounts.append(acc)
    if new_accounts:
        db.add_all(new_accounts)
        db.commit()


def get_account_hierarchy_info(account: Account) -> dict[str, str]:
    """Derive statement, category, and hierarchy path for any account."""
    # Find matching template by code or name
    for t in STANDARD_CATALOG_TEMPLATES:
        if t.code == account.code or normalize_account_name(t.name) == account.normalized_name:
            return {
                "statement": t.statement,
                "statement_label": t.statement_label,
                "category": t.category,
                "hierarchy_path": t.hierarchy_path,
            }

    # Derive from account_type
    type_str = account.account_type.value if hasattr(account.account_type, "value") else str(account.account_type)
    if type_str in ("ACTIVO", "PASIVO", "PATRIMONIO"):
        statement = "BALANCE_GENERAL"
        statement_label = "Balance General"
        category = "Activos" if type_str == "ACTIVO" else ("Pasivos" if type_str == "PASIVO" else "Patrimonio")
    elif type_str in ("INGRESO", "COSTO", "GASTO"):
        statement = "ESTADO_RESULTADOS"
        statement_label = "Estado de Resultados"
        category = "Ingresos" if type_str == "INGRESO" else ("Costos" if type_str == "COSTO" else "Gastos")
    else:
        statement = "AUXILIARES"
        statement_label = "Cuentas auxiliares/control"
        category = "Control y Conciliación"

    path = f"{statement_label} > {category} > {account.name}"
    return {
        "statement": statement,
        "statement_label": statement_label,
        "category": category,
        "hierarchy_path": path,
    }
