# Diseño del módulo de Comparaciones

## Objetivo

Dar vida a la sección **Comparaciones** de Celeste Analysis para que el usuario compare manualmente dos estados financieros aprobados de la empresa activa. La comparación mostrará valores por grupo y cuenta, variación absoluta, variación porcentual y advertencias temporales.

El usuario siempre comparará un período base anterior contra un período posterior. La aplicación no elegirá períodos automáticamente ni modificará sus fechas.

## Alcance

La primera versión soportará:

- Estado de Situación Financiera o Balance General.
- Estado de Resultados.
- Comparación de exactamente dos estados por operación.
- Cualquier cantidad de estados históricos disponibles en los selectores.
- Grupos financieros principales con cuentas y subcuentas desplegables.
- Cálculo al momento, sin guardar resultados de comparaciones.

No incluye Dashboard automático, ratios financieros, análisis vertical, tendencias multianuales, pronósticos, presupuestos ni exportaciones.

El libro `data/examples/ANALISIS Y RATIOS FINANCIEROS.xls` será una referencia funcional para la organización de grupos y para trabajo futuro. Sus ratios, flujos y métricas no forman parte de esta implementación.

## Decisiones de arquitectura

La lógica financiera residirá en el backend. React administrará la selección, los estados de interfaz y la presentación, pero no implementará reglas de compatibilidad, agrupación o cálculo.

Se añadirán dos operaciones pequeñas al backend:

- `GET /api/companies/{company_id}/comparison-statements`
- `POST /api/companies/{company_id}/comparisons`

La implementación reutilizará `Company`, `Period`, `FinancialImport`, `AccountBalance` y `Account`. No se crearán tablas ni migraciones para Comparaciones.

Un servicio de comparación independiente será responsable de:

- Consultar estados aprobados disponibles.
- Normalizar los nombres equivalentes del tipo Balance.
- Validar empresa, tipo y orden temporal.
- Construir la jerarquía de grupos, cuentas y subcuentas.
- Evitar doble conteo.
- Emparejar saldos mediante `account_id`.
- Calcular variaciones y estados especiales.

## Fuente de datos y estados disponibles

Un estado estará disponible únicamente cuando tenga saldos en `account_balances` para la empresa solicitada y su importación de origen esté en estado `APPROVED`.

La consulta se limitará siempre mediante `AccountBalance.company_id`. Aunque `Period` no contiene `company_id`, nunca se expondrán períodos de otra empresa.

Cada opción disponible incluirá como mínimo:

- Identificador de período.
- Tipo de estado normalizado.
- Etiqueta visible.
- `as_of_date` para Balance.
- `period_start` y `period_end` para Resultados.
- Duración del intervalo cuando aplique.

Los estados se ordenarán del más reciente al más antiguo. Los selectores podrán mostrar todos los estados existentes; cada solicitud de comparación contendrá únicamente dos identificadores.

Los valores `BALANCE_GENERAL` y `ESTADO_SITUACION_FINANCIERA` se tratarán como el mismo tipo funcional de Balance. Estado de Resultados conservará `ESTADO_RESULTADOS` como tipo canónico.

## Identidad y compatibilidad temporal

### Balance

La identidad temporal se basa en `as_of_date`. Dos balances de la misma empresa pueden compararse cuando tienen fechas de corte distintas y el período base es anterior al período posterior.

No se sumarán balances de fechas diferentes. La comparación usará el saldo existente en cada fecha.

### Estado de Resultados

La identidad temporal se basa en `period_start` y `period_end`. Se compararán exactamente los intervalos elegidos, sin acumular, reconstruir ni ajustar períodos.

Cuando las duraciones sean diferentes, el backend devolverá una advertencia no bloqueante:

> Los períodos seleccionados tienen diferente duración. La comparación porcentual puede no ser directamente equivalente.

### Validaciones bloqueantes

La comparación será rechazada cuando:

- Alguno de los estados no pertenezca a la empresa activa.
- Alguno no provenga de datos aprobados.
- Se seleccione el mismo estado dos veces.
- Se mezclen Balance y Estado de Resultados.
- El período base no sea anterior al período posterior.
- Falten las fechas necesarias para establecer identidad u orden temporal.

Los errores de dominio se devolverán como mensajes comprensibles, sin detalles técnicos.

## Dirección de la comparación

Los controles tendrán estas etiquetas:

- **Período base:** estado anterior.
- **Comparar con:** estado posterior.

La variación siempre representará cuánto cambió el período posterior respecto al anterior:

```text
variación absoluta = valor posterior - valor base
variación porcentual = ((valor posterior - valor base) / abs(valor base)) * 100
```

La interfaz no permitirá invertir silenciosamente el orden. Si el usuario selecciona un orden inválido, deberá corregir su selección.

## Emparejamiento de cuentas y trazabilidad

La unión entre períodos se realizará por `account_id`, no por el texto original del Excel. Dos nombres de origen diferentes mapeados a la misma cuenta serán una sola fila comparable.

Cada fila conservará:

- `account_id`.
- Código y nombre normalizado del catálogo.
- Tipo de cuenta y ubicación jerárquica.
- Valor base y posterior.
- Referencias de origen disponibles, como importación, hoja y fila.

Una cuenta presente en un solo período seguirá apareciendo mediante una unión completa de ambos conjuntos.

## Agrupación y prevención de doble conteo

La vista principal mostrará grupos financieros y permitirá desplegar cuentas y subcuentas.

Para Balance se priorizarán:

- Activo corriente.
- Activo no corriente.
- Total activo.
- Pasivo corriente.
- Pasivo no corriente.
- Total pasivo.
- Patrimonio.
- Total pasivo y patrimonio.

Para Estado de Resultados se priorizarán:

- Ingresos.
- Costos.
- Utilidad bruta.
- Gastos.
- Utilidad operativa.
- Otros resultados.
- Impuestos.
- Utilidad o pérdida neta.

La jerarquía utilizará, en este orden:

1. `parent_code` y `level` cuando estén disponibles.
2. La metadata del catálogo estándar y sus rutas jerárquicas.
3. Código y tipo de cuenta como clasificación de respaldo.

La regla de cálculo será:

- Si una cuenta padre tiene saldo propio y también existen descendientes con saldo, el valor del padre será autoritativo y sus descendientes se mostrarán solo como detalle.
- Si el padre no tiene saldo, el grupo sumará las cuentas de detalle disponibles sin contar dos veces ninguna rama.
- Las cuentas sin clasificación confiable aparecerán en **Sin clasificar** y no se incorporarán silenciosamente a un total general.

Los saldos persistidos provienen de filas clasificadas como `CUENTA`. Encabezados, notas y texto auxiliar no participarán en la comparación. Los totales y resultados normalizados podrán representarse como grupos calculados o cuentas autoritativas, pero no como cuentas ordinarias duplicadas.

## Reglas numéricas

Cada fila tendrá un estado porcentual explícito:

- Ambos valores presentes y base distinta de cero: porcentaje calculado.
- Base igual a cero y posterior distinto de cero: `Nueva`.
- Ambos valores iguales a cero: `Sin cambio`.
- Cuenta ausente en el período base: `Nueva`.
- Cuenta ausente en el período posterior: `Ya no presente`.
- Valor necesario nulo: `Sin base comparable`.

Los valores negativos utilizarán la fórmula normal con `abs(valor base)` en el denominador. El backend nunca devolverá `Infinity` ni `NaN`.

La respuesta conservará valores nulos como nulos; no los convertirá en cero.

## Contratos de API

### Estados disponibles

`GET /api/companies/{company_id}/comparison-statements`

Podrá recibir un filtro opcional de tipo de estado. Su respuesta incluirá una lista de estados disponibles con etiquetas ya construidas por el backend, para evitar lógica temporal duplicada en React.

Ejemplos de etiqueta:

- `31 Dic 2025` para Balance.
- `2025 · 01 Ene — 31 Dic` para Resultados.

### Ejecutar comparación

`POST /api/companies/{company_id}/comparisons`

Solicitud conceptual:

```json
{
  "statement_type": "ESTADO_RESULTADOS",
  "base_period_id": 10,
  "comparison_period_id": 14
}
```

La respuesta incluirá:

- Identidad y etiquetas de ambos estados.
- Advertencias no bloqueantes.
- Grupos ordenados.
- Totales de grupo.
- Filas de detalle jerárquicas.
- Valores, variaciones y estados porcentuales.
- Trazabilidad de origen necesaria para auditoría futura.

## Interfaz

La ruta `/comparisons` reemplazará su placeholder por una página real. Mantendrá el menú lateral y el encabezado de empresa, pero ocultará en esta ruta los selectores globales **Período** y **Vista**.

La pantalla contendrá:

- Título **Comparaciones**.
- Descripción con el nombre de la empresa activa.
- Selector de tipo de estado.
- Selector de período base.
- Selector de período posterior.
- Botón **Comparar**.
- Área de advertencias.
- Tabla de resultados.

La tabla tendrá las columnas:

- Cuenta.
- Período base.
- Período posterior.
- Variación absoluta.
- Variación porcentual o estado especial.

Los grupos serán desplegables. Las subcuentas aparecerán indentadas y los encabezados permanecerán visibles durante el desplazamiento. Los signos también tendrán representación textual; el color será un apoyo visual, no la única forma de distinguir aumentos y disminuciones.

Los componentes previstos son:

- `ComparisonPage` para coordinación y estados.
- Selector de tipo de estado.
- Selector reutilizable de estado/período financiero.
- Panel de advertencias.
- Tabla de comparación jerárquica.

La capa `src/renderer/api.ts` contendrá tipos y funciones de acceso; ninguna regla financiera quedará incrustada en los componentes.

## Estados de interfaz y errores

La página manejará explícitamente:

- Carga de estados disponibles.
- Carga de resultado.
- Error de conexión con opción de reintento.
- Selección incompleta.
- Orden temporal inválido.
- Advertencia de distinta duración.
- Resultado disponible.
- Insuficiencia de estados compatibles.

Cuando no existan dos estados compatibles se mostrará:

> No hay suficientes períodos disponibles para realizar una comparación.

> Importa al menos dos Estados de Resultados o dos Balances de diferentes fechas o períodos.

El botón **Ir a Archivos** navegará a `/files`.

## Pruebas

El backend cubrirá al menos:

- Balance 31/12/2024 contra 31/12/2025.
- Estado de Resultados anual contra anual.
- Advertencia por intervalos de distinta duración.
- Rechazo de Balance contra Resultados.
- Rechazo del mismo estado y del orden temporal invertido.
- Base cero.
- Valores negativos.
- Valores nulos.
- Cuenta presente únicamente en un período.
- Nombres originales distintos con el mismo `account_id`.
- Agrupación padre y subcuentas sin doble conteo.
- Aislamiento estricto por empresa.
- Exclusión de importaciones no aprobadas.

El frontend cubrirá al menos:

- Carga y filtrado de estados por tipo.
- Ocultamiento de los controles globales en Comparaciones.
- Estado vacío y navegación a Archivos.
- Advertencias temporales.
- Despliegue y colapso de grupos.
- Formato de porcentajes y estados especiales.
- Tratamiento legible de errores.

Al finalizar se ejecutarán todas las pruebas existentes del backend y frontend, la revisión estática y la compilación de Electron para confirmar que el flujo de importación sigue funcionando.

## Criterios de aceptación

El módulo estará completo cuando, desde una empresa activa, el usuario pueda entrar a Comparaciones, elegir dos estados aprobados compatibles en orden cronológico y obtener una tabla real con grupos financieros, cuentas desplegables, ambos valores, variación absoluta, variación porcentual y advertencias temporales correctas.

La implementación no deberá inventar períodos, mezclar empresas, comparar tipos incompatibles, duplicar saldos por jerarquía ni presentar divisiones por cero como porcentajes válidos.
